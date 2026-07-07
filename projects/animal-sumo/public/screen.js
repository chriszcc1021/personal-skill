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

let snap = null;
const flashes = []; // transient KO/dash markers {x,y,t,kind}

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
    if (m.t === "snap") { snap = m.s; renderSide(); }
    else if (m.t === "out") flashes.push({ kind: "out", name: m.name, t: performance.now() });
    else if (m.t === "roundover") { /* banner handled by phase in snap */ }
  };
  ws.onclose = () => setTimeout(connect, 500);
  ws.onerror = () => { try { ws.close(); } catch {} };
}
connect();

// ── coordinate transform: world (0,0 centre) -> canvas ──
function toScreen(x, y) { return [cv.width / 2 + x, cv.height / 2 + y]; }

function draw() {
  requestAnimationFrame(draw);
  ctx.clearRect(0, 0, cv.width, cv.height);
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
  for (const p of snap.players) {
    if (!p.alive) continue;
    const [sx, sy] = toScreen(p.x, p.y);
    const r = snap.playerR;
    // shadow
    ctx.beginPath(); ctx.arc(sx, sy + 4, r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0,0,0,.25)"; ctx.fill();
    // circular portrait
    ctx.save();
    ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.closePath(); ctx.clip();
    const im = imgs[p.animal];
    if (im && im.complete) {
      // portraits are 512 half-body; bias upward so the face sits in the circle
      ctx.drawImage(im, sx - r, sy - r * 1.15, r * 2, r * 2 * 1.2);
    } else {
      ctx.fillStyle = "#889"; ctx.fillRect(sx - r, sy - r, r * 2, r * 2);
    }
    ctx.restore();
    // ring (green if dash ready)
    ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
    ctx.lineWidth = 3; ctx.strokeStyle = p.dashReady ? "#3fb950" : "rgba(255,255,255,.5)"; ctx.stroke();
    // name
    ctx.font = "bold 14px system-ui"; ctx.textAlign = "center";
    ctx.fillStyle = "#fff"; ctx.strokeStyle = "rgba(0,0,0,.6)"; ctx.lineWidth = 3;
    ctx.strokeText(p.name, sx, sy - r - 6); ctx.fillText(p.name, sx, sy - r - 6);
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
}
function escapeHtml(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;" }[c])); }

draw();
