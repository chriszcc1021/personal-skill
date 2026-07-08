// Big-screen renderer. Connects as a "screen", draws each snapshot (arena +
// animal balls + names), and shows countdown / KO / winner banners. It never
// computes physics — it just paints what the server sends.

const cv = document.getElementById("cv");
const ctx = cv.getContext("2d");
const bannerEl = document.getElementById("banner");
const bannerBig = document.getElementById("bannerBig");
const bannerSub = document.getElementById("bannerSub");
const playersEl = document.getElementById("players");
const pcountEl = document.getElementById("pcount");
const joinUrlEl = document.getElementById("joinUrl");

// preload the 8 animal portraits (cropped to a circle at draw time)
const ANIMALS = ["brazil","argentina","england","france","germany","portugal","spain","usa"];
const imgs = {};
for (const a of ANIMALS) { const im = new Image(); im.src = `/portraits/${a}.png`; imgs[a] = im; }

// stadium background (drawn behind the arena)
const bgImg = new Image(); bgImg.src = "/assets/ui/bg-stadium.png";

// ── sound effects (unlocked on first click; browsers block autoplay) ──
const sfx = {};
function loadSfx(name, file, vol = 1) { const a = new Audio(`/assets/audio/${file}`); a.volume = vol; sfx[name] = a; }
loadSfx("whistle", "whistle_kickoff.mp3", 0.7);
loadSfx("end", "whistle_fulltime.mp3", 0.7);
loadSfx("cheer", "goal_cheer.mp3", 0.8);
loadSfx("out", "ball_bounce.mp3", 0.9);
loadSfx("click", "ui_click.mp3", 0.6);
const crowd = new Audio("/assets/audio/crowd_ambience.mp3"); crowd.loop = true; crowd.volume = 0.25;
let soundOn = false;
function play(name) { if (!soundOn) return; const a = sfx[name]; if (a) { try { a.currentTime = 0; a.play().catch(() => {}); } catch {} } }
const soundHint = document.getElementById("soundHint");
if (soundHint) soundHint.addEventListener("click", () => {
  soundOn = true; soundHint.classList.add("hidden");
  try { crowd.play().catch(() => {}); } catch {}
  play("click");
});

let snap = null;
let lastPhase = null; // to fire phase-transition sounds
const flashes = []; // transient KO/dash markers {x,y,t,kind}

// per-player render state (client-side only; derived from snapshots, never sent
// back). Gives us velocity for squash&stretch + dash trails without touching
// the authoritative server. id -> { x,y,vx,vy, trail:[{x,y,a}], t0 }
const pstate = new Map();
function pstateFor(p) {
  let s = pstate.get(p.id);
  if (!s) { s = { x: p.x, y: p.y, vx: 0, vy: 0, trail: [], t0: performance.now() }; pstate.set(p.id, s); }
  return s;
}

// ── QR + join URL ──
fetch("/config").then((r) => r.json()).then((cfg) => {
  const url = `${cfg.padBase}/pad`;
  joinUrlEl.textContent = url;
  // eslint-disable-next-line no-undef
  new QRCode(document.getElementById("qr"), { text: url, width: 200, height: 200,
    colorDark: "#0d1117", colorLight: "#ffffff" });
}).catch(() => {});

// ── WebSocket ──
let ws = null;
function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}`);
  ws.onopen = () => ws.send(JSON.stringify({ t: "hello", role: "screen" }));
  ws.onmessage = (ev) => {
    let m; try { m = JSON.parse(ev.data); } catch { return; }
    if (m.t === "snap") {
      snap = m.s; renderSide();
      if (snap.phase !== lastPhase) {
        if (snap.phase === "playing") play("whistle");
        else if (snap.phase === "roundover") { play("end"); play("cheer"); }
        lastPhase = snap.phase;
      }
    }
    else if (m.t === "out") { flashes.push({ kind: "out", name: m.name, t: performance.now() }); play("out"); }
    else if (m.t === "roundover") { /* banner handled by phase in snap */ }
  };
  ws.onclose = () => setTimeout(connect, 500);
  ws.onerror = () => { try { ws.close(); } catch {} };
}
connect();

// world (0,0 centre) -> canvas. Nudge the arena down a touch so the top-centre
// wood-sign logo doesn't overlap players near the top edge.
const Y_OFFSET = 70;
function toScreen(x, y) { return [cv.width / 2 + x, cv.height / 2 + y + Y_OFFSET]; }

function draw() {
  requestAnimationFrame(draw);
  ctx.clearRect(0, 0, cv.width, cv.height);

  // stadium backdrop (cover-fit the square canvas)
  if (bgImg.complete && bgImg.naturalWidth) {
    const s = Math.max(cv.width / bgImg.naturalWidth, cv.height / bgImg.naturalHeight);
    const w = bgImg.naturalWidth * s, h = bgImg.naturalHeight * s;
    ctx.drawImage(bgImg, (cv.width - w) / 2, (cv.height - h) / 2, w, h);
    ctx.fillStyle = "rgba(10,14,22,.28)"; ctx.fillRect(0, 0, cv.width, cv.height);
  } else {
    ctx.fillStyle = "#1a2233"; ctx.fillRect(0, 0, cv.width, cv.height);
  }
  if (!snap) return;

  const [cx, cy] = toScreen(0, 0);

  // platform
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, snap.arenaR, 0, Math.PI * 2);
  const g = ctx.createRadialGradient(cx, cy, snap.arenaR * 0.2, cx, cy, snap.arenaR);
  g.addColorStop(0, "#2b3a52"); g.addColorStop(1, "#1b2536");
  ctx.fillStyle = g; ctx.fill();
  ctx.lineWidth = 8; ctx.strokeStyle = "#ffcf33"; ctx.stroke();
  // inner ring accent
  ctx.beginPath(); ctx.arc(cx, cy, snap.arenaR * 0.5, 0, Math.PI * 2);
  ctx.lineWidth = 2; ctx.strokeStyle = "rgba(255,255,255,.08)"; ctx.stroke();
  ctx.restore();

  // players
  const nowT = performance.now();
  for (const p of snap.players) {
    if (!p.alive) { pstate.delete(p.id); continue; }
    const [sx, sy] = toScreen(p.x, p.y);
    const r = snap.playerR;
    const st = pstateFor(p);

    // smooth toward the authoritative position; derive velocity for effects
    const nx = sx, ny = sy;
    st.vx = st.vx * 0.6 + (nx - st.x) * 0.4;
    st.vy = st.vy * 0.6 + (ny - st.y) * 0.4;
    st.x = st.x + (nx - st.x) * 0.5;
    st.y = st.y + (ny - st.y) * 0.5;
    const dx = st.x, dy = st.y;
    const speed = Math.hypot(st.vx, st.vy);
    const ang = speed > 0.3 ? Math.atan2(st.vy, st.vx) : 0;
    const dashing = speed > 6; // fast = dash boost

    // dash trail: fading ghost copies of the body while moving fast
    if (speed > 6) st.trail.push({ x: dx, y: dy, a: 0.4 });
    while (st.trail.length > 6) st.trail.shift();
    for (const g of st.trail) {
      g.a *= 0.8;
      if (g.a < 0.04) continue;
      ctx.save();
      ctx.globalAlpha = g.a * 0.6;
      ctx.beginPath(); ctx.arc(g.x, g.y, r * 0.88, 0, Math.PI * 2); ctx.clip();
      const gi = imgs[p.animal];
      if (gi && gi.complete) ctx.drawImage(gi, g.x - r, g.y - r * 1.15, r * 2, r * 2 * 1.2);
      ctx.restore();
    }

    // squash & stretch: subtle stretch along motion; gentle breathing when idle
    const stretch = 1 + Math.min(0.18, speed * 0.016);
    const squash = 1 / stretch;
    const breathe = speed < 0.6 ? 1 + Math.sin((nowT - st.t0) / 420) * 0.03 : 1;

    // ground shadow (fixed ellipse, not rotated)
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(dx, dy + r * 0.86, r * 0.82, r * 0.34, 0, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0,0,0,.32)"; ctx.fill();
    ctx.restore();

    // body: rotate to motion, apply squash/stretch, draw a 3D-ish ball
    ctx.save();
    ctx.translate(dx, dy);
    ctx.rotate(ang);
    ctx.scale(stretch * breathe, squash * breathe);
    ctx.rotate(-ang); // keep the portrait upright after stretching the frame

    // base sphere with radial shading (gives volume vs. flat sticker)
    const bg = ctx.createRadialGradient(-r * 0.3, -r * 0.35, r * 0.2, 0, 0, r);
    bg.addColorStop(0, "#ffffff"); bg.addColorStop(0.55, "#f3e6c6"); bg.addColorStop(1, "#b98d52");
    ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.fillStyle = bg; ctx.fill();

    // clipped portrait on the upper body
    ctx.save();
    ctx.beginPath(); ctx.arc(0, 0, r - 1, 0, Math.PI * 2); ctx.clip();
    const im = imgs[p.animal];
    if (im && im.complete) ctx.drawImage(im, -r, -r * 1.15, r * 2, r * 2 * 1.2);
    ctx.restore();

    // top-left glossy highlight for the "rounded" look
    ctx.beginPath(); ctx.arc(-r * 0.32, -r * 0.38, r * 0.32, 0, Math.PI * 2);
    const hl = ctx.createRadialGradient(-r * 0.32, -r * 0.38, 0, -r * 0.32, -r * 0.38, r * 0.32);
    hl.addColorStop(0, "rgba(255,255,255,.55)"); hl.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = hl; ctx.fill();

    // rim: green when dash is ready, gold otherwise; brighter while dashing
    ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.lineWidth = dashing ? 5 : 3.5;
    ctx.strokeStyle = dashing ? "#fff2a8" : (p.dashReady ? "#3fb950" : "#8a6a3a");
    ctx.stroke();
    ctx.restore();

    // name (upright, not affected by squash)
    ctx.font = "bold 15px system-ui"; ctx.textAlign = "center";
    ctx.fillStyle = "#fff"; ctx.strokeStyle = "rgba(0,0,0,.65)"; ctx.lineWidth = 3.5;
    ctx.strokeText(p.name, dx, dy - r - 8); ctx.fillText(p.name, dx, dy - r - 8);
  }

  drawBanner();
}

function drawBanner() {
  const p = snap.phase;
  if (p === "countdown") {
    const left = Math.max(0, Math.ceil((snap.until - Date.now()) / 1000));
    showBanner(left > 0 ? String(left) : "GO!", "准备…把对手挤下台！");
  } else if (p === "roundover") {
    showBanner(snap.winner ? `🏆 ${snap.winner}` : "平局", "下一局马上开始…");
  } else if (p === "waiting") {
    showBanner("等待玩家", "扫码加入，≥2 人自动开始");
  } else {
    hideBanner();
  }
}
function showBanner(big, sub) { bannerEl.classList.remove("hidden"); bannerBig.textContent = big; bannerSub.textContent = sub; }
function hideBanner() { bannerEl.classList.add("hidden"); }

function renderSide() {
  if (!snap) return;
  pcountEl.textContent = snap.players.length;
  playersEl.innerHTML = "";
  for (const p of snap.players) {
    const row = document.createElement("div");
    row.className = "prow" + (p.alive ? "" : " dead");
    row.innerHTML = `<span class="dot"></span><span>${escapeHtml(p.name)}</span>`;
    playersEl.appendChild(row);
  }
  // show remaining empty slots as placeholders (up to 8)
  for (let i = snap.players.length; i < 8; i++) {
    const row = document.createElement("div");
    row.className = "prow";
    row.innerHTML = `<span class="dot" style="background:#c9b389;box-shadow:none"></span><span class="empty-slot">空位 · waiting…</span>`;
    playersEl.appendChild(row);
  }
}
function escapeHtml(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;" }[c])); }

draw();
