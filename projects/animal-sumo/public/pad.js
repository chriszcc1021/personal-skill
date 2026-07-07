// Phone gamepad. Analog stick -> continuous {vx,vy} streamed at ~30Hz; dash
// button -> one-shot. It never renders the game; the big screen does. Keeps the
// phone light and the physics authoritative on the server.

const whoEl = document.getElementById("who");
const stateEl = document.getElementById("state");
const overlay = document.getElementById("overlay");
const nameForm = document.getElementById("nameForm");
const nameInput = document.getElementById("nameInput");
const base = document.getElementById("stickBase");
const thumb = document.getElementById("stickThumb");
const dashBtn = document.getElementById("dash");

const input = { vx: 0, vy: 0 };
let ws = null, myId = null, joined = false, dashReady = true;

const STATE_TXT = {
  connecting: "连接中", joining: "加入中", ready: "准备", playing: "对战中",
  dead: "已淘汰", full: "房间已满", "in-progress": "本局进行中，等下一局", closed: "已断开",
};
function setState(s) { stateEl.textContent = STATE_TXT[s] || s; }

// ── name -> connect ──
nameForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const name = (nameInput.value || "Player").trim().slice(0, 12) || "Player";
  overlay.classList.add("hidden");
  connect(name);
});

function connect(name) {
  setState("connecting");
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}`);
  ws.onopen = () => { setState("joining"); ws.send(JSON.stringify({ t: "hello", role: "pad", name })); };
  ws.onmessage = (ev) => {
    let m; try { m = JSON.parse(ev.data); } catch { return; }
    if (m.t === "joined") { myId = m.id; joined = true; whoEl.textContent = animalName(m.animal); setState("ready"); }
    else if (m.t === "joinErr") { joined = false; showOverlayMsg(m.reason); setState(m.reason); }
    else if (m.t === "snap") { syncFromSnap(m.s); }
  };
  ws.onclose = () => { setState("closed"); if (joined) setTimeout(() => connect(name), 600); };
  ws.onerror = () => { try { ws.close(); } catch {} };
}

// keep the pad's notion of phase/alive in sync with the authoritative snapshot
function syncFromSnap(s) {
  const me = s.players.find((p) => p.id === myId);
  if (!me) { if (joined) { setState(s.phase === "playing" ? "dead" : "ready"); } return; }
  dashReady = me.dashReady;
  dashBtn.classList.toggle("cool", !dashReady);
  if (!me.alive) setState("dead");
  else if (s.phase === "playing") setState("playing");
  else if (s.phase === "countdown") setState("ready");
  else setState(s.phase === "roundover" ? "ready" : s.phase);
}

function showOverlayMsg(reason) {
  overlay.classList.remove("hidden");
  nameForm.innerHTML = `<h2>😅 ${reason === "full" ? "房间已满" : "本局进行中"}</h2>
    <p>${reason === "full" ? "已经 8 人了，等有人出局。" : "等这一局结束，下一局开局时再加入。"}</p>
    <button type="button" onclick="location.reload()">重试</button>`;
}

function animalName(a) {
  const M = { brazil:"豹",argentina:"鹰",england:"狮",france:"鸡",germany:"犀牛",portugal:"狼",spain:"牛",usa:"熊" };
  return M[a] || a;
}

// ── stream input @30Hz ──
setInterval(() => {
  if (ws && ws.readyState === 1 && joined) ws.send(JSON.stringify({ t: "input", d: { vx: input.vx, vy: input.vy } }));
}, 33);

// ── analog stick (pointer events) ──
let stick = { id: null, cx: 0, cy: 0, r: 1 };
base.addEventListener("pointerdown", (e) => {
  const rect = base.getBoundingClientRect();
  stick.id = e.pointerId; stick.cx = rect.left + rect.width / 2; stick.cy = rect.top + rect.height / 2;
  stick.r = rect.width / 2;
  base.setPointerCapture(e.pointerId);
  moveStick(e);
});
base.addEventListener("pointermove", moveStick);
base.addEventListener("pointerup", endStick);
base.addEventListener("pointercancel", endStick);
function moveStick(e) {
  if (stick.id !== e.pointerId) return;
  e.preventDefault();
  const dx = e.clientX - stick.cx, dy = e.clientY - stick.cy;
  const d = Math.hypot(dx, dy) || 1;
  const k = Math.min(1, stick.r / d);
  thumb.style.transform = `translate(${dx * k}px, ${dy * k}px)`;
  let vx = dx / stick.r, vy = dy / stick.r;
  const m = Math.hypot(vx, vy);
  if (m > 1) { vx /= m; vy /= m; }
  if (m < 0.15) { input.vx = 0; input.vy = 0; } else { input.vx = vx; input.vy = vy; }
}
function endStick(e) {
  if (stick.id !== e.pointerId) return;
  stick.id = null; thumb.style.transform = "translate(0,0)";
  input.vx = 0; input.vy = 0;
}

// ── dash ──
dashBtn.addEventListener("pointerdown", (e) => {
  e.preventDefault();
  if (ws && ws.readyState === 1 && joined && dashReady) ws.send(JSON.stringify({ t: "dash" }));
});

// lock scrolling
document.addEventListener("touchmove", (e) => e.preventDefault(), { passive: false });
