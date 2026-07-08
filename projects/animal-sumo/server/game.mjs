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

const { Engine, World, Bodies, Body, Composite, Events } = Matter;

// ── World tunables (pixels; the big screen scales to fit) ──
export const ARENA_R = 360; // platform radius
const PLAYER_R = 30; // animal ball radius
const SPAWN_R = ARENA_R * 0.6; // ring on which players spawn
const WALK_FORCE = 0.0016; // per-tick force from stick (scaled by body mass)
// dash is now charge-based: a tap gives a short shove, holding winds up a
// stronger lunge (A+B combined, per owner). Speed scales with charge time.
const DASH_SPEED_MIN = 11; // tap dash
const DASH_SPEED_MAX = 21; // full charge dash
const DASH_TAP_MS = 150; // below this = pure tap (min speed)
const DASH_CHARGE_MAX_MS = 700; // hold this long (or more) = max speed
const DASH_COOLDOWN_MS = 900;
const DASH_DURATION_MS = 220; // how long the dash "shove" boost lasts
const HIT_IMPULSE = 9; // extra shove given to a victim hit by a dasher
const HITSTOP_MS = 90; // brief freeze-frame feel on a dash hit
const MAX_PLAYERS = 8;
const COUNTDOWN_MS = 3000;
const ROUNDOVER_MS = 5000;
const TICK_HZ = 60;
const SNAPSHOT_HZ = 30; // network broadcast rate (raised for smoother public play)
const BOT_FILL_TO = 4; // auto-fill with AI bots up to this many players
const HEARTBEAT_TIMEOUT_MS = 30000; // drop humans silent this long (zombie cleanup)

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
  let botSeq = 1;

  // dash-hit shove + hitstop: when a dashing body touches another player, the
  // victim gets an extra impulse along the contact normal and both feel a brief
  // freeze (hitstop) for punch. Runs off Matter's collisionStart.
  Events.on(engine, "collisionStart", (evt) => {
    if (phase !== "playing") return;
    const now = Date.now();
    for (const pair of evt.pairs) {
      const A = bodyOwner(pair.bodyA), B = bodyOwner(pair.bodyB);
      if (!A || !B) continue;
      const aDash = now < A.dashUntil, bDash = now < B.dashUntil;
      if (aDash === bDash) continue; // need exactly one attacker
      const atk = aDash ? A : B, vic = aDash ? B : A;
      const dx = vic.body.position.x - atk.body.position.x;
      const dy = vic.body.position.y - atk.body.position.y;
      const d = Math.hypot(dx, dy) || 1;
      Body.setVelocity(vic.body, {
        x: vic.body.velocity.x + (dx / d) * HIT_IMPULSE,
        y: vic.body.velocity.y + (dy / d) * HIT_IMPULSE,
      });
      atk.hitstopUntil = now + HITSTOP_MS;
      vic.hitstopUntil = now + HITSTOP_MS;
      emit({ t: "hit", x: Math.round(vic.body.position.x), y: Math.round(vic.body.position.y) });
    }
  });
  function bodyOwner(body) {
    for (const p of players.values()) if (p.body === body) return p;
    return null;
  }

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
      restitution: 0.6, // shoves that carry but don't fling wildly
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
    // a joining human takes an idle bot's slot if we're at capacity-by-bots
    const bot = [...players.values()].find((p) => p.bot);
    if (bot && players.size >= MAX_PLAYERS) removePlayer(bot.id);
    const animal = takeAnimal();
    const body = spawnBody();
    players.set(id, {
      id, name: (name || "Player").slice(0, 12), animal, body, bot: false,
      alive: true, dashReadyAt: 0, dashUntil: 0, dashStart: 0, hitstopUntil: 0,
      lastInputAt: Date.now(), input: { vx: 0, vy: 0 },
    });
    // a lone human is enough: fill with bots, then start
    if (phase === "waiting") { fillBots(); if (players.size >= 2) startCountdown(); }
    return { ok: true, animal };
  }

  // add an AI bot (server-driven fake player; has a body, no WS connection)
  function addBot() {
    if (players.size >= MAX_PLAYERS) return;
    const id = `bot${botSeq++}`;
    const animal = takeAnimal();
    const body = spawnBody();
    const names = ["野毛子", "莽撞王", "毛团子", "小霸王", "摹鱼手", "矮壮士", "宠儿", "毛腿"];
    players.set(id, {
      id, name: names[(Math.random() * names.length) | 0], animal, body, bot: true,
      alive: true, dashReadyAt: 0, dashUntil: 0, dashStart: 0, hitstopUntil: 0,
      lastInputAt: Date.now(), input: { vx: 0, vy: 0 },
    });
  }

  // top up with bots so a lone human (or none) can still start a match
  function fillBots() {
    if (phase === "playing") return;
    while (players.size < BOT_FILL_TO) addBot();
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
    p.lastInputAt = Date.now();
    // clamp stick vector to unit circle
    let vx = Number(d.vx) || 0, vy = Number(d.vy) || 0;
    const m = Math.hypot(vx, vy);
    if (m > 1) { vx /= m; vy /= m; }
    p.input.vx = vx; p.input.vy = vy;
  }

  // charge dash: press starts the wind-up, release fires with speed scaled by
  // how long it was held (tap = short shove, hold = strong lunge).
  function dashDown(id) {
    const p = players.get(id);
    if (!p || !p.alive || phase !== "playing") return;
    p.lastInputAt = Date.now();
    if (Date.now() < p.dashReadyAt) return;
    if (!p.dashStart) p.dashStart = Date.now();
  }
  function dashUp(id) {
    const p = players.get(id);
    if (!p || !p.alive || phase !== "playing" || !p.dashStart) return;
    fireDash(p, Date.now() - p.dashStart);
    p.dashStart = 0;
  }
  function fireDash(p, heldMs) {
    const now = Date.now();
    if (now < p.dashReadyAt) { p.dashStart = 0; return; }
    let { vx, vy } = p.input;
    const m = Math.hypot(vx, vy);
    if (m < 0.1) return; // need a direction to dash
    vx /= m; vy /= m;
    // map hold time -> speed
    const t = Math.max(0, Math.min(1, (heldMs - DASH_TAP_MS) / (DASH_CHARGE_MAX_MS - DASH_TAP_MS)));
    const speed = DASH_SPEED_MIN + (DASH_SPEED_MAX - DASH_SPEED_MIN) * t;
    Body.setVelocity(p.body, { x: vx * speed, y: vy * speed });
    p.dashReadyAt = now + DASH_COOLDOWN_MS;
    p.dashUntil = now + DASH_DURATION_MS;
    emit({ t: "dash", id: p.id, power: t });
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
      p.dashReadyAt = 0; p.dashUntil = 0; p.dashStart = 0; p.hitstopUntil = 0;
      p.lastInputAt = Date.now();
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

  // ── bot AI: set each bot's input (and maybe dash) like a phone would ──
  function botThink(now) {
    const alive = [...players.values()].filter((p) => p.alive && p.body);
    for (const b of alive) {
      if (!b.bot) continue;
      const bx = b.body.position.x, by = b.body.position.y;
      const distC = Math.hypot(bx, by);
      // near the edge -> steer back toward centre (self-preservation)
      if (distC > ARENA_R * 0.66) {
        const d = distC || 1;
        b.input.vx = -bx / d; b.input.vy = -by / d;
        continue;
      }
      // else chase nearest opponent
      let foe = null, best = Infinity;
      for (const o of alive) {
        if (o === b) continue;
        const dd = Math.hypot(o.body.position.x - bx, o.body.position.y - by);
        if (dd < best) { best = dd; foe = o; }
      }
      if (!foe) { b.input.vx = 0; b.input.vy = 0; continue; }
      const dx = foe.body.position.x - bx, dy = foe.body.position.y - by;
      const d = Math.hypot(dx, dy) || 1;
      b.input.vx = dx / d; b.input.vy = dy / d;
      // close & dash ready -> lunge (mid difficulty: react with a small chance)
      if (best < PLAYER_R * 4 && now >= b.dashReadyAt && Math.random() < 0.06) {
        fireDash(b, DASH_TAP_MS + Math.random() * 400);
      }
    }
  }

  // ── main fixed-step loop ──
  const dtMs = 1000 / TICK_HZ;
  let lastSnap = 0;

  const loop = setInterval(() => {
    const now = Date.now();

    // phase transitions
    if (phase === "countdown" && now >= phaseUntil) startRound();
    else if (phase === "roundover" && now >= phaseUntil) {
      // next round: keep connected players, top up bots, reopen joining
      fillBots();
      if (players.size >= 2) startCountdown();
      else { phase = "waiting"; emit({ t: "phase", phase }); }
    }

    // heartbeat cleanup: drop humans who've gone silent (zombie WS)
    for (const p of [...players.values()]) {
      if (!p.bot && now - p.lastInputAt > HEARTBEAT_TIMEOUT_MS) removePlayer(p.id);
    }

    // drive AI bots (simple: seek centre when near edge, else chase nearest foe
    // and dash when lined up & close)
    if (phase === "playing") botThink(now);

    // apply movement forces (only while playing)
    if (phase === "playing") {
      for (const p of players.values()) {
        if (!p.alive || !p.body) continue;
        if (now < p.hitstopUntil) continue; // frozen by hitstop
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
        id: p.id, name: p.name, animal: p.animal, alive: p.alive, bot: !!p.bot,
        x: p.body ? Math.round(p.body.position.x) : 0,
        y: p.body ? Math.round(p.body.position.y) : 0,
        dashReady: now >= p.dashReadyAt,
      })),
    };
  }

  return {
    addPlayer, removePlayer, setInput, dashDown, dashUp,
    snapshot, canJoin,
    get phase() { return phase; },
    get count() { return players.size; },
    stop() { clearInterval(loop); },
  };
}
