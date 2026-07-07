// Animal Sumo server: static file host + WebSocket relay + one shared room.
//
// Topology mirrors the football game's proven model, upgraded to N players and
// server-authoritative physics:
//   • big screen  → opens "/", becomes the display (draws snapshots)
//   • phones      → open "/pad", each is a wireless gamepad (send input/dash)
//   • this server → runs the Matter.js world, broadcasts snapshots @20Hz
//
// Single global room for the MVP (one arena, up to 8). Room code kept for
// parity with the QR-join flow but everyone shares the same arena for now.
import express from "express";
import { WebSocketServer } from "ws";
import http from "node:http";
import os from "node:os";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createGame } from "./game.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 14000);

// Optional public base URL (tunnel) the QR should encode; falls back to LAN IP.
const PAD_BASE = process.env.PAD_BASE_URL || null;

function lanIP() {
  const ifaces = os.networkInterfaces();
  for (const name of Object.keys(ifaces)) {
    for (const ni of ifaces[name] || []) {
      if (ni.family === "IPv4" && !ni.internal &&
          /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/.test(ni.address)) return ni.address;
    }
  }
  return "127.0.0.1";
}

const app = express();
const PUBLIC = join(__dirname, "..", "public");
// extensionless routes so the QR can encode a clean /pad URL
app.get("/pad", (_req, res) => res.sendFile(join(PUBLIC, "pad.html")));
app.use(express.static(PUBLIC));

// The pad page asks where to connect + what URL the QR should show.
app.get("/config", (_req, res) => {
  const base = PAD_BASE || `http://${lanIP()}:${PORT}`;
  res.json({ padBase: base });
});

const server = http.createServer(app);
const wss = new WebSocketServer({ server });

// clients: ws -> { role:"screen"|"pad", id }
let seq = 1;
const screens = new Set();

const game = createGame({
  onSnapshot(snap) { broadcastScreens({ t: "snap", s: snap }); },
  onEvent(ev) { broadcastScreens(ev); }, // screens show dashes/outs/phase
});

function send(ws, obj) {
  if (ws && ws.readyState === 1) { try { ws.send(JSON.stringify(obj)); } catch {} }
}
function broadcastScreens(obj) { for (const ws of screens) send(ws, obj); }

wss.on("connection", (ws) => {
  ws.__role = null;
  ws.__id = null;

  ws.on("message", (raw) => {
    let msg;
    try { msg = JSON.parse(String(raw)); } catch { return; }

    if (msg.t === "hello") {
      if (msg.role === "screen") {
        ws.__role = "screen";
        screens.add(ws);
        send(ws, { t: "snap", s: game.snapshot() });
      } else {
        // pad joins the game
        ws.__role = "pad";
        ws.__id = `p${seq++}`;
        const r = game.addPlayer(ws.__id, msg.name);
        if (!r.ok) { send(ws, { t: "joinErr", reason: r.reason }); ws.__role = null; return; }
        send(ws, { t: "joined", id: ws.__id, animal: r.animal });
      }
      return;
    }

    if (ws.__role !== "pad" || !ws.__id) return;
    if (msg.t === "input") game.setInput(ws.__id, msg.d || {});
    else if (msg.t === "dash") game.dash(ws.__id);
  });

  ws.on("close", () => {
    if (ws.__role === "screen") screens.delete(ws);
    else if (ws.__role === "pad" && ws.__id) game.removePlayer(ws.__id);
  });
});

server.listen(PORT, "0.0.0.0", () => {
  const ip = lanIP();
  console.log(`[animal-sumo] http://${ip}:${PORT}  (screen: /  · pad: /pad)`);
  if (PAD_BASE) console.log(`[animal-sumo] QR base: ${PAD_BASE}`);
});
