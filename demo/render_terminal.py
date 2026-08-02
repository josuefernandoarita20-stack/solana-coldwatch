#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
import re
import textwrap

ROOT = Path(__file__).parent
TRANSCRIPT = ROOT / "live-transcript.txt"
OUT = ROOT / "terminal-frames"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1280, 720


def load_font(size):
    for path in (
        "/System/Library/Fonts/Supplemental/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT = load_font(20)
SMALL = load_font(15)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def clean_lines():
    raw = TRANSCRIPT.read_text(errors="replace")
    raw = ANSI.sub("", raw).replace("ð§", "TOOL")
    lines = []
    for line in raw.splitlines():
        line = line.rstrip().replace("\r", "")
        if not line:
            lines.append("")
            continue
        indent = len(line) - len(line.lstrip())
        wrapped = textwrap.wrap(
            line.strip(), width=96 - indent, break_long_words=True,
            break_on_hyphens=False,
        ) or [""]
        lines.extend((" " * indent) + part for part in wrapped)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def color(line):
    upper = line.upper()
    if line.startswith("$") or line.lstrip().startswith("method:") or line.lstrip().startswith("[Y]es"):
        return "#facc15"
    if any(token in upper for token in ("COLDWATCH", "REAL AGENT RUN", "SAFETY TESTS")):
        return "#67e8f9"
    if any(token in upper for token in ("PASS", "LIVE TOOL RESULT", "... OK", "RAN 4 TESTS", "MODE:")):
        return "#4ade80"
    if "PROMPT-INJECTION" in upper or "UNTRUSTED MESSAGE" in upper:
        return "#fb7185"
    if "FAILED" in upper:
        return "#fb7185"
    if line.startswith("TOOL"):
        return "#c084fc"
    if line.startswith("I do not comply"):
        return "#a7f3d0"
    if line.startswith("github.com"):
        return "#67e8f9"
    return "#dbeafe"


def duration_frames(line):
    upper = line.upper()
    if not line:
        return 3
    if "COLDWATCH —" in upper:
        return 14
    if any(token in upper for token in ("ARCHITECTURE", "REAL AGENT RUN", "LIVE TOOL RESULT", "PROMPT-INJECTION", "SAFETY TESTS", "PASS —")):
        return 10
    if line.startswith("I do not comply") or line.startswith("Please ensure"):
        return 18
    if line.startswith("$ zeroclaw"):
        return 12
    if line.startswith("TOOL") or "[Y]es" in line:
        return 9
    if line.startswith("test_"):
        return 4
    return 6


def render(visible, index):
    image = Image.new("RGB", (W, H), "#050b16")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 20, 1256, 700), radius=18, fill="#020617", outline="#23324a", width=2)
    draw.rounded_rectangle((24, 20, 1256, 68), radius=18, fill="#111827")
    draw.rectangle((24, 50, 1256, 68), fill="#111827")
    for x, c in ((50, "#fb7185"), (74, "#facc15"), (98, "#4ade80")):
        draw.ellipse((x, 36, x + 12, 48), fill=c)
    draw.text((134, 33), "coldwatch — live ZeroClaw session", font=SMALL, fill="#cbd5e1")
    draw.text((1015, 33), "● REC  REAL RUN", font=SMALL, fill="#fb7185")

    y = 88
    for line in visible[-25:]:
        draw.text((50, y), line, font=FONT, fill=color(line))
        y += 24
    draw.text((1020, 674), "watch-only • no secrets", font=SMALL, fill="#64748b")
    path = OUT / f"terminal-{index:03d}.png"
    image.save(path, optimize=True)
    return path.name


lines = clean_lines()
timeline = []
visible = []
for index, line in enumerate(lines):
    visible.append(line)
    timeline.append({"file": render(visible, index), "frames": duration_frames(line)})

timeline.insert(0, {"file": timeline[0]["file"], "frames": 10})
timeline[-1]["frames"] += 55
(OUT / "timeline.json").write_text(json.dumps(timeline, indent=2))
total_frames = sum(item["frames"] for item in timeline)
print(f"Rendered {len(lines)} terminal states — {total_frames / 10:.1f} seconds")
