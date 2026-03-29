#!/usr/bin/env python3
"""Capture RAGPipe demo as optimized GIF."""

import subprocess, sys, io
from pathlib import Path
import numpy as np
from PIL import Image
import imageio.v3 as imageio

DEMO_PATH = "file:///tmp/ragpipe/demo/index.html"
OUTPUT = "/tmp/ragpipe/.github/demo.gif"
WIDTH = 400
HEIGHT = 270
FPS = 6
NUM_FRAMES = 20
PAGE_WAIT = 5

script = f"""
const {{ chromium }} = require('/opt/homebrew/lib/node_modules/playwright');

(async () => {{
    const browser = await chromium.launch();
    const page = await browser.newPage({{ viewport: {{ width: {WIDTH}, height: {HEIGHT} }} }});
    await page.goto('{DEMO_PATH}', {{ waitUntil: 'networkidle' }});
    await page.waitForTimeout({PAGE_WAIT * 1000});
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);

    for (let i = 0; i < {NUM_FRAMES}; i++) {{
        const maxScroll = await page.evaluate(() => document.body.scrollHeight - window.innerHeight);
        const scrollY = Math.floor((i / {NUM_FRAMES}) * maxScroll * 0.85);
        await page.evaluate((y) => window.scrollTo(0, y), scrollY);
        await page.waitForTimeout({1000 // FPS});
        const buffer = await page.screenshot({{ type: 'png' }});
        const header = Buffer.alloc(4);
        header.writeUInt32BE(buffer.length, 0);
        process.stdout.write(header);
        process.stdout.write(buffer);
    }}
    await browser.close();
}})();
"""

result = subprocess.run(["node", "-e", script], capture_output=True, timeout=120)
data = result.stdout
frames_raw = []
offset = 0
while offset + 4 <= len(data):
    length = int.from_bytes(data[offset : offset + 4], "big")
    offset += 4
    frames_raw.append(data[offset : offset + length])
    offset += length

print(f"Captured {len(frames_raw)} frames")

# Resize to 480x320 and quantize
frames = []
for fb in frames_raw:
    img = Image.open(io.BytesIO(fb)).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    frames.append(np.array(img))

# Global palette from samples
sample_idx = [int(i * len(frames) / min(5, len(frames))) for i in range(min(5, len(frames)))]
all_px = np.vstack([frames[i].reshape(-1, 3) for i in sample_idx])
total = len(all_px)
w = min(512, int(np.sqrt(total)))
h = (total + w - 1) // w
needed = w * h
if needed > total:
    all_px = np.vstack([all_px, np.zeros((needed - total, 3), dtype=np.uint8)])
combined = Image.fromarray(all_px[:needed].reshape(h, w, 3).astype(np.uint8))
palette = combined.quantize(colors=48, method=2)

optimized = []
for f in frames:
    q = Image.fromarray(f).quantize(palette=palette, dither=1)
    optimized.append(np.array(q.convert("RGB")))

# Deduplicate
deduped = [optimized[0]]
for i in range(1, len(optimized)):
    diff = np.mean(
        np.abs(np.array(deduped[-1], dtype=np.float32) - np.array(optimized[i], dtype=np.float32))
    )
    if diff > 2.0:
        deduped.append(optimized[i])

print(f"After dedup: {len(deduped)} frames")

imageio.imwrite(OUTPUT, deduped, duration=1000 / FPS, loop=0)
size_kb = Path(OUTPUT).stat().st_size / 1024
print(f"GIF: {OUTPUT} ({size_kb:.0f} KB, {len(deduped)} frames, {WIDTH}x{HEIGHT})")
