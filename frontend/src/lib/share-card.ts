const CARD_W = 600;
const CARD_H = 340;
const BG = '#0f1117';
const SURFACE = '#1a1d27';
const MUTED = '#8b8fa3';
const WHITE = '#f0f0f5';
const PRIMARY = '#f59e0b';
const GREEN = '#4ade80';
const RED = '#f87171';

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawBadge(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  color: string,
) {
  ctx.font = '600 13px Inter, system-ui, sans-serif';
  const w = ctx.measureText(text).width + 20;
  const h = 26;
  ctx.globalAlpha = 0.15;
  ctx.fillStyle = color;
  roundRect(ctx, x - w / 2, y, w, h, 13);
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.fillText(text, x, y + 17);
}

function drawWatermark(ctx: CanvasRenderingContext2D) {
  ctx.font = '500 11px Inter, system-ui, sans-serif';
  ctx.fillStyle = MUTED;
  ctx.globalAlpha = 0.5;
  ctx.textAlign = 'center';
  ctx.fillText('lazyfantasy.app', CARD_W / 2, CARD_H - 14);
  ctx.globalAlpha = 1;
}

function createCanvas(): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const canvas = document.createElement('canvas');
  canvas.width = CARD_W;
  canvas.height = CARD_H;
  const ctx = canvas.getContext('2d')!;
  // Background
  ctx.fillStyle = BG;
  roundRect(ctx, 0, 0, CARD_W, CARD_H, 20);
  ctx.fill();
  return [canvas, ctx];
}

function toBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error('Canvas toBlob failed'))),
      'image/png',
    );
  });
}

export interface UpcomingCardInput {
  team1: string;
  team2: string;
  startTime: string;
  venue?: string;
}

export async function generateUpcomingCard(input: UpcomingCardInput): Promise<Blob> {
  const [canvas, ctx] = createCanvas();

  // VS divider line
  ctx.strokeStyle = '#2a2d3a';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(CARD_W / 2, 50);
  ctx.lineTo(CARD_W / 2, 200);
  ctx.stroke();

  // Team names
  ctx.font = '700 42px Inter, system-ui, sans-serif';
  ctx.fillStyle = WHITE;
  ctx.textAlign = 'center';
  ctx.fillText(input.team1, CARD_W * 0.25, 140);
  ctx.fillText(input.team2, CARD_W * 0.75, 140);

  // VS badge
  ctx.font = '700 16px Inter, system-ui, sans-serif';
  ctx.fillStyle = MUTED;
  ctx.textAlign = 'center';
  ctx.fillText('VS', CARD_W / 2, 140);

  // Date
  const date = new Date(input.startTime);
  const dateStr = date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
  ctx.font = '500 14px Inter, system-ui, sans-serif';
  ctx.fillStyle = MUTED;
  ctx.fillText(dateStr, CARD_W / 2, 220);

  // Venue
  if (input.venue) {
    ctx.font = '400 12px Inter, system-ui, sans-serif';
    ctx.fillStyle = MUTED;
    ctx.globalAlpha = 0.7;
    ctx.fillText(input.venue, CARD_W / 2, 244);
    ctx.globalAlpha = 1;
  }

  // Badge
  drawBadge(ctx, 'Predictions Open', CARD_W / 2, 270, PRIMARY);

  drawWatermark(ctx);

  return toBlob(canvas);
}

export interface ResultCardInput {
  team1: string;
  team2: string;
  winner: string;
  points: number;
  categories: { label: string; correct: boolean }[];
}

export async function generateResultCard(input: ResultCardInput): Promise<Blob> {
  const [canvas, ctx] = createCanvas();

  // Match header
  ctx.font = '600 18px Inter, system-ui, sans-serif';
  ctx.fillStyle = MUTED;
  ctx.textAlign = 'center';
  ctx.fillText(`${input.team1} vs ${input.team2}`, CARD_W / 2, 45);

  // Winner
  ctx.font = '700 14px Inter, system-ui, sans-serif';
  ctx.fillStyle = PRIMARY;
  ctx.fillText(`${input.winner} won`, CARD_W / 2, 72);

  // Points — big number
  ctx.font = '800 72px Inter, system-ui, sans-serif';
  ctx.fillStyle = WHITE;
  ctx.fillText(`${input.points}`, CARD_W / 2 - 20, 160);

  ctx.font = '500 22px Inter, system-ui, sans-serif';
  ctx.fillStyle = MUTED;
  ctx.textAlign = 'left';
  ctx.fillText('/100', CARD_W / 2 + 45, 160);

  // Points bar
  const barX = 80;
  const barW = CARD_W - 160;
  const barY = 185;
  const barH = 8;
  roundRect(ctx, barX, barY, barW, barH, 4);
  ctx.fillStyle = '#2a2d3a';
  ctx.fill();
  if (input.points > 0) {
    const fillW = (input.points / 100) * barW;
    roundRect(ctx, barX, barY, fillW, barH, 4);
    ctx.fillStyle = PRIMARY;
    ctx.fill();
  }

  // Category results
  const startY = 220;
  const gap = 30;
  ctx.textAlign = 'left';

  input.categories.forEach((cat, i) => {
    const y = startY + i * gap;
    const x = 100;

    // Icon
    ctx.font = '16px Inter, system-ui, sans-serif';
    ctx.fillStyle = cat.correct ? GREEN : RED;
    ctx.fillText(cat.correct ? '✓' : '✗', x, y);

    // Label
    ctx.font = '500 14px Inter, system-ui, sans-serif';
    ctx.fillStyle = cat.correct ? WHITE : MUTED;
    ctx.fillText(cat.label, x + 28, y);
  });

  // Correct count on right side
  const correctCount = input.categories.filter((c) => c.correct).length;
  ctx.textAlign = 'right';
  ctx.font = '600 14px Inter, system-ui, sans-serif';
  ctx.fillStyle = MUTED;
  ctx.fillText(
    `${correctCount}/${input.categories.length} correct`,
    CARD_W - 100,
    startY + ((input.categories.length - 1) * gap) / 2,
  );

  drawWatermark(ctx);

  return toBlob(canvas);
}
