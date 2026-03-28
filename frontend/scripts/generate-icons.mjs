import sharp from 'sharp';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const svgPath = join(__dirname, '../public/icon.svg');
const svg = readFileSync(svgPath);

const sizes = [
  { size: 512, out: join(__dirname, '../public/icons/icon-512x512.png') },
  { size: 192, out: join(__dirname, '../public/icons/icon-192x192.png') },
  { size: 32,  out: join(__dirname, '../src/app/favicon.png') },
];

for (const { size, out } of sizes) {
  await sharp(svg)
    .resize(size, size)
    .png()
    .toFile(out);
  console.log(`✓ ${size}x${size} → ${out}`);
}
