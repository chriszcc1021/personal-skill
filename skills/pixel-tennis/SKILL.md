---
name: pixel-sprite-animation
description: "Pixel art sprite animation for HTML5 Canvas games. Covers sprite sheet design, frame animation controller, character animation states, and game juice. Use when building or upgrading pixel-style 2D games with smooth character animations."
license: MIT
metadata:
  version: "1.0.0"
  domain: game-dev
  triggers: pixel art, sprite animation, sprite sheet, pixel game, canvas game animation
---

# Pixel Sprite Animation

Pixel art sprite animation for HTML5 Canvas 2D games. Single-file, zero-dependency.

## 1 · Sprite Sheet Standard

### Size & Layout

```
Recommended character size: 32×32px or 48×48px per frame
Sheet layout: rows = actions, columns = frames

     F0    F1    F2    F3    F4    F5
R0  [idle ][idle ][idle ][idle ]
R1  [run  ][run  ][run  ][run  ][run  ][run  ]
R2  [fh   ][fh   ][fh   ][fh   ]        ← forehand
R3  [bh   ][bh   ][bh   ][bh   ]        ← backhand
R4  [serve][serve][serve][serve]
R5  [cele ][cele ][cele ][cele ]        ← celebrate
R6  [hurt ][hurt ]
```

- Export as single PNG → base64 inline → `new Image()` + `drawImage()`
- Transparent background (#00000000)
- All frames same size, no padding between frames
- Palette: ≤16 colors per character for authentic pixel look

### Action Frame Counts

| Action | Frames | FPS | Loop | Notes |
|--------|--------|-----|------|-------|
| idle | 4 | 4 | yes | Subtle breathing / bounce |
| run | 6 | 10 | yes | Contact-pass-contact cycle |
| forehand | 4 | 12 | no | Wind-up → contact → follow-through |
| backhand | 4 | 12 | no | Mirror of forehand |
| serve | 4 | 10 | no | Toss → reach → smash → land |
| celebrate | 4 | 6 | no | Fist pump or jump |
| hurt | 2 | 6 | no | Recoil |

## 2 · Animation Controller

```javascript
class SpriteAnimator {
  constructor(image, frameW, frameH, animations) {
    this.img = image;         // loaded Image object
    this.fw = frameW;         // frame width px
    this.fh = frameH;         // frame height px
    this.anims = animations;  // {name: {row, frames, fps, loop}}
    this.current = 'idle';
    this.frame = 0;
    this.timer = 0;
    this.done = false;        // true when non-loop anim finished
  }

  play(name) {
    if (this.current === name && !this.done) return;
    this.current = name;
    this.frame = 0;
    this.timer = 0;
    this.done = false;
  }

  update(dt) {  // dt in seconds
    const a = this.anims[this.current];
    if (!a || this.done) return;
    this.timer += dt;
    const spf = 1 / a.fps;
    while (this.timer >= spf) {
      this.timer -= spf;
      this.frame++;
      if (this.frame >= a.frames) {
        if (a.loop) { this.frame = 0; }
        else { this.frame = a.frames - 1; this.done = true; }
      }
    }
  }

  draw(ctx, x, y, scale, flipX) {
    const a = this.anims[this.current];
    if (!a) return;
    const sx = this.frame * this.fw;
    const sy = a.row * this.fh;
    const dw = this.fw * scale;
    const dh = this.fh * scale;
    ctx.save();
    ctx.translate(x, y);
    if (flipX) { ctx.scale(-1, 1); }
    ctx.imageSmoothingEnabled = false;  // crisp pixels!
    ctx.drawImage(this.img, sx, sy, this.fw, this.fh,
                  -dw/2, -dh/2, dw, dh);
    ctx.restore();
  }
}
```

### Usage

```javascript
const ANIMS = {
  idle:      { row: 0, frames: 4, fps: 4,  loop: true },
  run:       { row: 1, frames: 6, fps: 10, loop: true },
  forehand:  { row: 2, frames: 4, fps: 12, loop: false },
  backhand:  { row: 3, frames: 4, fps: 12, loop: false },
  serve:     { row: 4, frames: 4, fps: 10, loop: false },
  celebrate: { row: 5, frames: 4, fps: 6,  loop: false },
  hurt:      { row: 6, frames: 2, fps: 6,  loop: false },
};

const playerAnim = new SpriteAnimator(spriteImg, 48, 48, ANIMS);

// In game loop:
playerAnim.update(1/60);
playerAnim.draw(ctx, player.x, player.y, SCALE, player.facing < 0);
```

### State Machine Integration

```javascript
function updatePlayerAnimation() {
  const moving = Math.abs(player.vx) > 0.5 || Math.abs(player.vy) > 0.5;
  if (player.swinging > 0) {
    playerAnim.play(player.facing >= 0 ? 'forehand' : 'backhand');
  } else if (player.serving) {
    playerAnim.play('serve');
  } else if (moving) {
    playerAnim.play('run');
  } else {
    playerAnim.play('idle');
  }
}
```

## 3 · Pixel Animation Principles

### The 12 Pixel Rules

1. **Anticipation** — 1 frame wind-up before action (arm goes back before swing)
2. **Squash & Stretch** — Character squishes on land, stretches on jump (±1px)
3. **Smear Frames** — Motion blur via stretched intermediate frame (swing frame 2)
4. **Follow-Through** — Action continues 1-2 frames after contact
5. **Secondary Motion** — Hair / cape / ribbon lag behind main body by 1 frame
6. **Sub-pixel Shimmer** — Alternate edge pixels between frames for breathing effect
7. **Hold Frames** — Key poses hold 2-3 frames, transitions get 1 frame
8. **Contact Frame** — The hit frame is the most detailed, hold it longest
9. **Ease In/Out** — More frames near start/end of motion, fewer in middle
10. **Silhouette Test** — Each frame readable as solid black shape
11. **Color Flash** — White flash overlay on contact frame (1 frame)
12. **Exaggeration** — Bigger wind-up and follow-through than realistic

### Generating Sprite Sheets with AI

Use `image_generate` with precise prompts:

```
Prompt template:
"Pixel art sprite sheet, [SIZE]x[SIZE] per frame, [COLUMNS] columns x [ROWS] rows,
transparent background, [CHARACTER DESCRIPTION], 
row 1: idle animation 4 frames (subtle bounce),
row 2: run cycle 6 frames (side view),
row 3: [ACTION] 4 frames (wind-up to follow-through),
retro 16-bit style, limited palette [COLORS], 
each frame clearly separated, no anti-aliasing, crisp pixels"
```

After generation:
1. Inspect: frame alignment, consistent size, no anti-aliased edges
2. If misaligned: crop/adjust in code or re-generate
3. Convert to base64: `cat sprite.png | base64 -w0`
4. Embed: `const img = new Image(); img.src = 'data:image/png;base64,...';`

## 4 · Game Juice Checklist

### On Hit

- [ ] Hit stop (freeze 2-4 frames)
- [ ] Screen shake (3-6px, 3-5 frames)
- [ ] Zoom punch (scale 0.97→1.0 over 8 frames)
- [ ] Impact particles (6-8 white squares burst outward)
- [ ] Expanding ring (white circle, fade out over 10 frames)
- [ ] Radial lines (4 lines from impact point)
- [ ] Flash frame (character turns white for 1 frame)
- [ ] Sound: distinct per shot type (pitch variation)

### On Bounce

- [ ] Dust particles (4-6 small squares, spread & fade)
- [ ] Ball squash (flatten Y by 30% for 2 frames)
- [ ] Bounce sound (pitch = height)

### On Score

- [ ] Big text pop (scale 0→1.2→1.0 with bounce ease)
- [ ] Winner: character celebrate animation
- [ ] Loser: character hurt animation
- [ ] Screen flash (winner=green, loser=red, 0.1s)
- [ ] Confetti particles (winner only)

### On Charge

- [ ] Charge glow (expanding circle under character)
- [ ] Character vibrate (±1px random offset)
- [ ] Rising pitch sound loop
- [ ] Charge level particles (more at higher charge)

### Movement

- [ ] Run dust (small particles behind feet every 4 frames)
- [ ] Skid particles (on direction change)
- [ ] Shadow (ellipse under character, scales with jump height)

## 5 · Performance Rules

- `imageSmoothingEnabled = false` — always, for crisp pixel art
- Sprite sheet < 512×512px — fits in GPU texture cache
- Max 2 sprite sheets (player + opponent) — minimize draw calls
- Pre-render static elements to offscreen canvas
- Particle pool: reuse objects, don't create/destroy each frame
- requestAnimationFrame only — never setInterval for game loop
- Delta time: `const dt = (now - lastTime) / 1000` — frame-rate independent

## 6 · Court & Background Art

- Court: draw once to offscreen canvas, blit each frame
- Lines: 1px at game scale, anti-alias OFF
- Net: dithered pattern (checkerboard 1px)
- Audience: 1-2 row of 8×8 pixel blobs, random color, bob animation (±1px at 2fps)
- Scoreboard: pixel font (built-in or bitmap), not system font
