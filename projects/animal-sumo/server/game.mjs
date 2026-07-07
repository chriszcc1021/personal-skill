// Server-authoritative sumo physics + round logic (Matter.js).
//
// One arena = one physics World. Players are circular bodies on a circular
// platform; walking off the edge (body centre outside the platform radius)
// eliminates you. Dash = a short velocity boost used to shove others off.
//
// The engine here is HEADLESS: only Matter's Engine/World/Body maths run — no
// Render, no DOM — so it lives happily in Node. The big screen just draws the
// snapshot we broadcast; it never computes physics. That keeps all clients in
// agreement (single source of truth).
import Matter from "matter-js";

const { Engine, World, Bodies, Body, Composite } = Matter;

// ── World tunables (pixels; the big screen scales to fit) ──
export const ARENA_R = 360; // platform radius
const PLAYER_R = 30; // animal ball radius
const SPAWN_R = ARENA_R * 0.6; // ring on which players spawn
const WALK_FORCE = 0.0016; // per-tick force from stick (scaled by body mass)
const DASH_SPEED = 14; // instantaneous speed set on dash
const DASH_COOLDOWN_MS = 900;
const DASH_DURATION_MS = 220; // how long the dash "shove" boost lasts
const MAX_PLAYERS = 8;
const COUNTDOWN_MS = 3000;
const ROUNDOVER_MS = 5000;
const TICK_HZ = 60;
const SNAPSHOT_HZ = 20; // network broadcast rate

// The 8 reusable animal characters (portraits shipped in /public/portraits).
export const ANIMALS = [
  "brazil", "argentina", "england", "france",
  "germany", "portugal", "spain", "usa",
];

export function createGame({ onSnapshot, onEvent } = {}) {
  const engine = Engine.create();
  engine.gravity.x = 0;
  engine.gravity.y = 0; // top-down: no gravity, movement is all forces

  // players: id -> { id, name, animal, body, alive, dashReadyAt, dashUntil,
  //                   input:{vx,vy}, joinedRound }
  const players = new Map();
  let phase = "waiting"; // waiting | countdown | playing | roundover
  let phaseUntil = 0; // ms timestamp when the current timed phase ends
  let round = 0;
  let winnerName = null;
  let animalPool = [...ANIMALS];

  function takeAnimal() {
    if (animalPool.length === 0) animalPool = [...ANIMALS];
    const i = (Math.random() * animalPool.length) | 0;
    return animalPool.splice(i, 1)[0];
  }

  function spawnBody() {
    const a = Math.random() * Math.PI * 2;
    const r = Math.random() * SPAWN_R;
    const x = Math.cos(a) * r;
    const y = Math.sin(a) * r;
    const body = Bodies.circle(x, y, PLAYER_R, {
      frictionAir: 0.06, // top-down "ice-ish" damping so pushes carry
      friction: 0.02,
      restitution: 0.85, // bouncy shoves
      density: 0.001,
    });
    Composite.add(engine.world, body);
    return body;
  }

  function canJoin() {
    return (phase === "waiting" || phase === "countdown") && players.size < MAX_PLAYERS;
  }

  function addPlayer(id, name) {
    if (players.has(id)) return { ok: true };
    if (!canJoin()) {
      return { ok: false, reason: players.size >= MAX_PLAYERS ? "full" : "in-progress" };
    }
    const animal = takeAnimal();
    const body = spawnBody();
    players.set(id, {
      id, name: (name || "Player").slice(0, 12), animal, body,
      alive: true, dashReadyAt: 0, dashUntil: 0, input: { vx: 0, vy: 0 },
    });
    // enough players waiting -> start a countdown
    if (phase === "waiting" && players.size >= 2) startCountdown();
    return { ok: true, animal };
  }

  function removePlayer(id) {
    const p = players.get(id);
    if (!p) return;
    if (p.body) Composite.remove(engine.world, p.body);
    players.delete(id);
    if (phase === "playing") checkWin();
  }

  function setInput(id, d) {
    const p = players.get(id);
    if (!p || !p.alive) return;
    // clamp stick vector to unit circle
    let vx = Number(d.vx) || 0, vy = Number(d.vy) || 0;
    const m = Math.hypot(vx, vy);
    if (m > 1) { vx /= m; vy /= m; }
    p.input.vx = vx; p.input.vy = vy;
  }

  function dash(id) {
    const p = players.get(id);
    if (!p || !p.alive || phase !== "playing") return;
    const now = Date.now();
    if (now < p.dashReadyAt) return;
    let { vx, vy } = p.input;
    const m = Math.hypot(vx, vy);
    if (m < 0.1) return; // need a direction to dash
    vx /= m; vy /= m;
    Body.setVelocity(p.body, { x: vx * DASH_SPEED, y: vy * DASH_SPEED });
    p.dashReadyAt = now + DASH_COOLDOWN_MS;
    p.dashUntil = now + DASH_DURATION_MS;
    emit({ t: "dash", id });
  }

  function startCountdown() {
    phase = "countdown";
    phaseUntil = Date.now() + COUNTDOWN_MS;
    emit({ t: "phase", phase, until: phaseUntil });
  }

  function startRound() {
    round += 1;
    winnerName = null;
    // reset every current player to a fresh spawn, all alive
    for (const p of players.values()) {
      if (p.body) Composite.remove(engine.world, p.body);
      p.body = spawnBody();
      p.alive = true;
      p.input.vx = 0; p.input.vy = 0;
      p.dashReadyAt = 0; p.dashUntil = 0;
    }
    phase = "playing";
    phaseUntil = 0;
    emit({ t: "phase", phase, round });
  }

  function endRound(name) {
    phase = "roundover";
    winnerName = name;
    phaseUntil = Date.now() + ROUNDOVER_MS;
    emit({ t: "roundover", winner: name, until: phaseUntil });
  }

  function checkWin() {
    if (phase !== "playing") return;
    const alive = [...players.values()].filter((p) => p.alive);
    if (alive.length <= 1) {
      endRound(alive.length === 1 ? alive[0].name : null);
    }
  }

  function eliminate(p) {
    p.alive = false;
    if (p.body) { Composite.remove(engine.world, p.body); p.body = null; }
    emit({ t: "out", id: p.id, name: p.name });
    checkWin();
  }

  function emit(ev) { onEvent && onEvent(ev); }

  // ── main fixed-step loop ──
  const dtMs = 1000 / TICK_HZ;
  let lastSnap = 0;

  const loop = setInterval(() => {
    const now = Date.now();

    // phase transitions
    if (phase === "countdown" && now >= phaseUntil) startRound();
    else if (phase === "roundover" && now >= phaseUntil) {
      // next round: keep connected players, reopen joining
      if (players.size >= 2) startCountdown();
      else { phase = "waiting"; emit({ t: "phase", phase }); }
    }

    // apply movement forces (only while playing)
    if (phase === "playing") {
      for (const p of players.values()) {
        if (!p.alive || !p.body) continue;
        const boosting = now < p.dashUntil;
        // during a dash we let the set velocity ride; otherwise steer normally
        if (!boosting) {
          Body.applyForce(p.body, p.body.position, {
            x: p.input.vx * WALK_FORCE * p.body.mass,
            y: p.input.vy * WALK_FORCE * p.body.mass,
          });
        }
      }
    }

    Engine.update(engine, dtMs);

    // out-of-bounds check (body centre outside platform)
    if (phase === "playing") {
      for (const p of players.values()) {
        if (!p.alive || !p.body) continue;
        const { x, y } = p.body.position;
        if (Math.hypot(x, y) > ARENA_R) eliminate(p);
      }
    }

    // broadcast snapshot at SNAPSHOT_HZ
    if (now - lastSnap >= 1000 / SNAPSHOT_HZ) {
      lastSnap = now;
      onSnapshot && onSnapshot(snapshot());
    }
  }, dtMs);

  function snapshot() {
    const now = Date.now();
    return {
      phase, round, winner: winnerName,
      until: phaseUntil || 0,
      arenaR: ARENA_R, playerR: PLAYER_R,
      players: [...players.values()].map((p) => ({
        id: p.id, name: p.name, animal: p.animal, alive: p.alive,
        x: p.body ? Math.round(p.body.position.x) : 0,
        y: p.body ? Math.round(p.body.position.y) : 0,
        dashReady: now >= p.dashReadyAt,
      })),
    };
  }

  return {
    addPlayer, removePlayer, setInput, dash,
    snapshot, canJoin,
    get phase() { return phase; },
    get count() { return players.size; },
    stop() { clearInterval(loop); },
  };
}
