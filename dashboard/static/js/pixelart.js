/**
 * SpecAgent — 8-bit Office Visualization Engine
 *
 * Draws a retro pixel-art office scene on an HTML Canvas.
 * Five agent characters (Speck, Arch, Cody, Tess, Rex) sit at desks and
 * animate based on their current status.
 *
 * Pixel scale: each logical pixel = SCALE canvas pixels (4px default).
 */

const SCALE = 4;  // logical px → canvas px

// ─────────────────────────────────────────────────────────────────────────────
// 8-bit colour palette (index → hex)
// ─────────────────────────────────────────────────────────────────────────────
const PAL = {
  // Shared
  T:    null,           // transparent
  BLK:  '#0a0a0a',
  WHT:  '#f8f8f8',
  DGR:  '#3a4060',      // dark grey / floor
  MGR:  '#525878',      // mid grey / wall
  LGR:  '#8a90aa',      // light grey
  WD1:  '#8b5e3c',      // wood dark
  WD2:  '#c48a5e',      // wood mid
  SKN:  '#f5c48a',      // skin
  SKN2: '#e0a870',      // skin shadow
  BLU:  '#4a6cf7',      // accent blue
  GRN:  '#2ecc71',
  RED:  '#e74c3c',
  YEL:  '#f1c40f',
  PUR:  '#9b59b6',
  ORN:  '#e67e22',
  CYN:  '#00d2d3',
  // Desk colours
  DSKF: '#c48a5e',
  DSKD: '#8b5e3c',
  // Monitor
  MON:  '#1a1a2e',
  SCR:  '#0a2040',
  SCRA: '#4a6cf7',      // active screen glow
  // Plant
  PLT1: '#27ae60',
  PLT2: '#1e8449',
  PLT3: '#8b5e3c',
  // Coffee machine
  CF1:  '#888',
  CF2:  '#aaa',
  // Background wall
  WAL:  '#1a1e2e',
  FLR:  '#141720',
  // Carpet
  CAR:  '#2a1e3a',
  // Character colours per agent
  // Speck (Spec) — blue wizard
  SP1:  '#2c3e7a',  SP2:  '#4a6cf7',
  // Arch — grey engineer
  AR1:  '#6a7a8a',  AR2:  '#e8e8e8',
  // Cody (Coder) — dark hoodie
  CO1:  '#1a1a2e',  CO2:  '#4a6cf7',
  // Tess (Tester) — green jacket
  TE1:  '#2d7a2d',  TE2:  '#5caf5c',
  // Rex (Reviewer) — red flannel
  RE1:  '#8b2020',  RE2:  '#c04040',
};

// ─────────────────────────────────────────────────────────────────────────────
// Tiny pixel-drawing helpers
// ─────────────────────────────────────────────────────────────────────────────
let _ctx;

function px(x, y, color) {
  if (!color || color === PAL.T) return;
  _ctx.fillStyle = color;
  _ctx.fillRect(x * SCALE, y * SCALE, SCALE, SCALE);
}

function rect(x, y, w, h, color) {
  if (!color || color === PAL.T) return;
  _ctx.fillStyle = color;
  _ctx.fillRect(x * SCALE, y * SCALE, w * SCALE, h * SCALE);
}

function drawSprite(sprite, ox, oy) {
  const rows = sprite.length;
  const cols = sprite[0].length;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const c = sprite[row][col];
      if (c) px(ox + col, oy + row, c);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Background: office walls, floor, carpet
// ─────────────────────────────────────────────────────────────────────────────
function drawBackground(W, H) {
  // Wall
  rect(0, 0, W, H * 0.45, PAL.WAL);
  // Floor
  rect(0, H * 0.45, W, H * 0.55, PAL.FLR);
  // Carpet strip
  rect(2, H * 0.44, W - 4, H * 0.56, PAL.CAR);

  // Wall baseboard
  rect(0, H * 0.43, W, 2, PAL.DGR);

  // Wall decorations — banner
  const bx = Math.floor(W / 2) - 15, by = 3;
  rect(bx, by, 30, 8, PAL.BLU);
  rect(bx + 1, by + 1, 28, 6, PAL.DGR);

  // Window on the wall
  const wx = 3, wy = 4;
  rect(wx, wy, 18, 12, PAL.DGR);
  rect(wx + 1, wy + 1, 16, 10, '#1a3a6a');
  // window panes
  rect(wx + 8, wy + 1, 1, 10, PAL.DGR);
  rect(wx + 1, wy + 5, 16, 1, PAL.DGR);
  // sun
  rect(wx + 3, wy + 2, 4, 4, '#f5d060');

  // Clock
  const cx2 = W - 12, cy2 = 5;
  rect(cx2, cy2, 8, 8, PAL.LGR);
  rect(cx2 + 1, cy2 + 1, 6, 6, PAL.MGR);
  rect(cx2 + 3, cy2 + 1, 1, 3, PAL.WHT);  // clock hands
  rect(cx2 + 3, cy2 + 3, 2, 1, PAL.WHT);
}

// ─────────────────────────────────────────────────────────────────────────────
// Desk with monitor
// ─────────────────────────────────────────────────────────────────────────────
function drawDesk(dx, dy, screenColor) {
  // Desk top
  rect(dx, dy, 26, 4, PAL.DSKF);
  rect(dx, dy + 3, 26, 1, PAL.DSKD);
  // Legs
  rect(dx + 1, dy + 4, 2, 6, PAL.DSKD);
  rect(dx + 23, dy + 4, 2, 6, PAL.DSKD);

  // Monitor base
  rect(dx + 10, dy - 1, 6, 1, PAL.DGR);
  rect(dx + 11, dy - 5, 1, 4, PAL.DGR);
  // Monitor bezel
  rect(dx + 6, dy - 12, 14, 10, PAL.BLK);
  rect(dx + 7, dy - 11, 12, 8, screenColor || PAL.SCR);

  // Keyboard
  rect(dx + 5, dy, 12, 2, PAL.LGR);
  rect(dx + 5, dy + 1, 12, 1, PAL.MGR);

  // Coffee mug on desk
  rect(dx + 20, dy - 3, 3, 3, PAL.WD2);
  rect(dx + 21, dy - 3, 1, 3, PAL.SKN);
}

// ─────────────────────────────────────────────────────────────────────────────
// Plants
// ─────────────────────────────────────────────────────────────────────────────
function drawPlant(px2, py) {
  // Pot
  rect(px2, py + 5, 6, 4, PAL.WD1);
  rect(px2 + 1, py + 6, 4, 3, PAL.WD2);
  // Soil
  rect(px2 + 1, py + 5, 4, 1, PAL.BLK);
  // Leaves
  px(px2 + 2, py + 4, PAL.PLT2);
  rect(px2 + 1, py + 2, 4, 3, PAL.PLT1);
  px(px2, py + 3, PAL.PLT2);
  px(px2 + 4, py + 3, PAL.PLT2);
  rect(px2 + 2, py, 2, 2, PAL.PLT2);
}

// ─────────────────────────────────────────────────────────────────────────────
// Coffee machine
// ─────────────────────────────────────────────────────────────────────────────
function drawCoffeeMachine(mx, my) {
  rect(mx, my, 8, 12, PAL.DGR);
  rect(mx + 1, my + 1, 6, 4, PAL.MGR);    // display
  rect(mx + 2, my + 2, 4, 2, PAL.BLU);    // screen
  rect(mx + 2, my + 6, 2, 2, PAL.RED);    // button
  rect(mx + 5, my + 6, 2, 2, PAL.GRN);
  rect(mx + 3, my + 9, 2, 1, PAL.LGR);    // spout
  rect(mx + 3, my + 10, 2, 3, PAL.CF2);   // cup
}

// ─────────────────────────────────────────────────────────────────────────────
// Character sprites (idle frame 0 and 1, working, thinking, celebrating)
// Each sprite is a 10 wide × 18 tall logical-pixel grid.
// ─────────────────────────────────────────────────────────────────────────────

// ── Generic character builder ──
// body = shirt colour, pants = pants colour, hair = hair colour, acc = accessory
function buildChar(body, pants, hair, acc, frame, state) {
  const S = PAL.SKN, S2 = PAL.SKN2;
  const idle = frame % 2;

  // Frames are 10x18
  const sprite = Array.from({ length: 18 }, () => Array(10).fill(null));

  const set = (r, c, color) => { if (r >= 0 && r < 18 && c >= 0 && c < 10) sprite[r][c] = color; };
  const row = (r, cs, ce, color) => { for (let c = cs; c <= ce; c++) set(r, c, color); };

  // Hair
  row(0, 3, 6, hair);
  row(1, 2, 7, hair);

  // Head
  row(2, 2, 7, S);
  set(2, 2, S2); set(2, 7, S2);
  row(3, 2, 7, S);
  row(4, 2, 7, S);
  // Eyes
  set(3, 3, PAL.BLK); set(3, 6, PAL.BLK);
  // Mouth
  set(4, 4, PAL.BLK); set(4, 5, PAL.BLK);

  // Neck
  set(5, 4, S); set(5, 5, S);

  // Body / shirt
  row(6, 2, 7, body);
  row(7, 2, 7, body);
  row(8, 2, 7, body);
  // Shirt shading
  set(6, 2, PAL.BLK); set(6, 7, PAL.BLK);

  // Arms
  if (state === 'working') {
    // Both arms forward (typing)
    row(7, 0, 1, S);
    row(7, 8, 9, S);
    row(8, 0, 1, body);
    row(8, 8, 9, body);
  } else if (state === 'celebrating') {
    // Arms raised
    set(6, 0, body); set(5, 0, S);
    set(6, 9, body); set(5, 9, S);
    set(5, 1, S); set(5, 8, S);
  } else {
    // Idle — arms down
    set(7, 1, body); set(8, 1, S);
    set(7, 8, body); set(8, 8, S);
  }

  // Pants
  row(9, 3, 6, pants);
  row(10, 3, 6, pants);

  // Legs
  set(11, 3, pants); set(11, 6, pants);
  set(12, 3, pants); set(12, 6, pants);

  // Shoes
  set(13, 2, PAL.BLK); set(13, 3, PAL.BLK);
  set(13, 6, PAL.BLK); set(13, 7, PAL.BLK);

  // Accessory layer
  if (acc === 'glasses') {
    set(3, 3, '#88ccff'); set(3, 6, '#88ccff');
    set(3, 4, PAL.LGR); set(3, 5, PAL.LGR);
  }
  if (acc === 'hardhat') {
    row(0, 2, 7, PAL.YEL);
    row(1, 1, 8, PAL.YEL);
    set(1, 1, PAL.WD2); set(1, 8, PAL.WD2);
  }
  if (acc === 'hoodie') {
    set(0, 3, body); set(0, 4, body); set(0, 5, body); set(0, 6, body);
    set(1, 2, body); set(1, 7, body);
    set(2, 2, body); set(2, 7, body);
  }
  if (acc === 'clipboard') {
    set(7, 0, PAL.WHT); set(8, 0, PAL.WHT);
    set(7, 1, PAL.LGR); set(8, 1, PAL.LGR);
  }
  if (acc === 'coffee') {
    set(8, 9, PAL.WD2); set(8, 8, PAL.WD2);
    set(7, 9, PAL.WHT);
  }

  // Idle bobbing (frame 1 shifts down 1px if idle)
  if (state === 'idle' && idle === 1) {
    sprite.unshift(Array(10).fill(null));
    sprite.pop();
  }

  return sprite;
}

// Per-agent character definitions
const AGENT_CHARS = {
  spec:      { body: PAL.SP1, pants: PAL.SP2, hair: PAL.YEL, acc: 'glasses' },
  architect: { body: PAL.AR1, pants: PAL.DGR, hair: PAL.WD1, acc: 'hardhat' },
  coder:     { body: PAL.CO1, pants: PAL.CO2, hair: PAL.BLK, acc: 'hoodie' },
  tester:    { body: PAL.TE1, pants: PAL.DGR, hair: '#c0402a', acc: 'clipboard' },
  reviewer:  { body: PAL.RE1, pants: PAL.DGR, hair: PAL.LGR, acc: 'coffee' },
};

// ─────────────────────────────────────────────────────────────────────────────
// Thought / status bubble
// ─────────────────────────────────────────────────────────────────────────────
function drawBubble(bx, by, status) {
  if (status === 'idle' || !status) return;
  const icon = {
    thinking: '?',
    working: '…',
    awaiting_hitm: '!',
    celebrating: '★',
    error: '✗',
  }[status] || '';
  if (!icon) return;

  // Small thought bubble
  rect(bx + 1, by - 5, 6, 5, PAL.WHT);
  // Connector dots
  px(bx + 1, by, PAL.WHT);
  px(bx + 2, by - 1, PAL.WHT);
  // Icon inside (drawn as colour block — pixel text not practical at this scale)
  const iconColor = {
    thinking: PAL.YEL,
    working: PAL.BLU,
    awaiting_hitm: PAL.ORN,
    celebrating: PAL.GRN,
    error: PAL.RED,
  }[status] || PAL.BLK;
  rect(bx + 2, by - 4, 4, 3, iconColor);
}

// ─────────────────────────────────────────────────────────────────────────────
// Full scene renderer
// ─────────────────────────────────────────────────────────────────────────────
const DESK_POSITIONS = [
  { dx: 2,  dy: 62 },   // Speck — far left
  { dx: 35, dy: 62 },   // Arch
  { dx: 68, dy: 62 },   // Cody  — centre
  { dx: 101, dy: 62 },  // Tess
  { dx: 134, dy: 62 },  // Rex   — far right
];

const AGENT_KEYS = ['spec', 'architect', 'coder', 'tester', 'reviewer'];

let _agentStates = {};   // filled from app.js
let _frame = 0;
let _rafId = null;
let _canvas = null;

function setAgentStates(statesMap) {
  _agentStates = statesMap;
}

function getScreenColor(agentKey) {
  const status = (_agentStates[agentKey] || {}).status;
  if (status === 'working') return PAL.SCRA;
  if (status === 'celebrating') return PAL.GRN;
  if (status === 'error') return PAL.RED;
  return PAL.SCR;
}

function renderScene() {
  if (!_canvas) return;
  const ctx = _canvas.getContext('2d');
  _ctx = ctx;

  const LW = Math.floor(_canvas.width / SCALE);   // logical width  (200)
  const LH = Math.floor(_canvas.height / SCALE);  // logical height (105)

  ctx.clearRect(0, 0, _canvas.width, _canvas.height);

  drawBackground(LW, LH);

  // Plants at corners
  drawPlant(LW - 10, 30);
  drawPlant(25, 28);

  // Coffee machine left of first desk
  drawCoffeeMachine(0, 33);

  // Desks + characters
  for (let i = 0; i < 5; i++) {
    const key = AGENT_KEYS[i];
    const { dx, dy } = DESK_POSITIONS[i];
    const agentState = _agentStates[key] || {};
    const status = agentState.status || 'idle';
    const charDef = AGENT_CHARS[key];

    const screenColor = getScreenColor(key);
    drawDesk(dx, dy, screenColor);

    // Character sits ~4px above desk top
    const cx = dx + 8, cy = dy - 16;
    const sprite = buildChar(
      charDef.body, charDef.pants, charDef.hair, charDef.acc,
      _frame, status,
    );
    drawSprite(sprite, cx, cy);

    // Status bubble above character
    drawBubble(cx + 4, cy, status);

    // Name tag
    // (rendered natively as canvas text for readability)
    ctx.font = `bold ${SCALE * 2}px monospace`;
    ctx.fillStyle = '#8b92b5';
    ctx.textAlign = 'center';
    ctx.fillText(key.charAt(0).toUpperCase() + key.slice(1), (dx + 13) * SCALE, (dy + 12) * SCALE);
  }

  // Scoreboard on far right wall
  drawScoreboard(LW - 30, 10);

  _frame++;
}

function drawScoreboard(bx, by) {
  rect(bx, by, 28, 22, PAL.DGR);
  rect(bx + 1, by + 1, 26, 20, PAL.BLK);
  // "SPEC AGENT" title
  _ctx.font = `bold ${SCALE * 1.5}px monospace`;
  _ctx.fillStyle = PAL.BLU;
  _ctx.textAlign = 'left';
  _ctx.fillText('SPECAGENT', (bx + 2) * SCALE, (by + 5) * SCALE);

  const active = Object.values(_agentStates).filter(a => a.status === 'working').length;
  const done   = Object.values(_agentStates).filter(a => a.status === 'celebrating').length;

  _ctx.fillStyle = PAL.GRN;
  _ctx.fillText(`ACTIVE: ${active}`, (bx + 2) * SCALE, (by + 10) * SCALE);
  _ctx.fillStyle = PAL.YEL;
  _ctx.fillText(`DONE:   ${done}`, (bx + 2) * SCALE, (by + 15) * SCALE);
}

// ─────────────────────────────────────────────────────────────────────────────
// Animation loop
// ─────────────────────────────────────────────────────────────────────────────
let _lastTick = 0;
const FRAME_INTERVAL = 400; // ms per animation frame (slow = 8-bit feel)

function animLoop(ts) {
  _rafId = requestAnimationFrame(animLoop);
  if (ts - _lastTick >= FRAME_INTERVAL) {
    renderScene();
    _lastTick = ts;
  }
}

function startPixelArt(canvas) {
  _canvas = canvas;
  if (_rafId) cancelAnimationFrame(_rafId);
  _rafId = requestAnimationFrame(animLoop);
}

function stopPixelArt() {
  if (_rafId) cancelAnimationFrame(_rafId);
  _rafId = null;
}

// Export
window.PixelArt = { start: startPixelArt, stop: stopPixelArt, setAgentStates };
