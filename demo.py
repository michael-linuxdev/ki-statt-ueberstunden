#!/usr/bin/env python3
"""Test-Format: Reel, das Vorher und Nachher in einem Chat zeigt (statt der Eingabe).

Rendert für jeden Beitrag mit dem Feld "demo" ein Video nach docs/reels/NNN-demo.mp4.
Aufruf:  python3 demo.py
"""
import json
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

import build

FPS = 30
VORLAGE = build.ROOT / "demo.html"


def main():
    posts = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((build.ROOT / "posts").glob("*.json"))]
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception:
            browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(VORLAGE.as_uri())
        page.evaluate("document.fonts.ready")
        for post in posts:
            if "demo" not in post:
                continue
            d = {**post["demo"], "stempel": post["stempel"], "kanal": build.KANAL}
            ziel = build.DOCS / "reels" / f"{post['nr']:03d}-demo.mp4"
            sekunden = page.evaluate("d => dauer(d)", d)
            ff = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS), "-i", "-",
                 "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest", "-c:v", "libx264", "-preset",
                 "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k",
                 "-movflags", "+faststart", str(ziel)], stdin=subprocess.PIPE)
            for i in range(int(sekunden * FPS)):
                page.evaluate("([d, t]) => zeige(d, t)", [d, i / FPS])
                ff.stdin.write(page.screenshot(type="jpeg", quality=92))
            ff.stdin.close()
            if ff.wait() != 0:
                raise SystemExit(f"ffmpeg ist bei Nr. {post['nr']} gescheitert")
            print(f"Nr. {post['nr']}: {sekunden:.1f} s, {ziel.name}")
        browser.close()


if __name__ == "__main__":
    main()
