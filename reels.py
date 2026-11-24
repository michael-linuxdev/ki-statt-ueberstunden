#!/usr/bin/env python3
"""Baut zu jedem Beitrag ein Reel (1080 x 1920, MP4) nach docs/reels/.

Aufbau: Aufhänger (Problem in einem Satz) -> Eingabe -> so kopierst du sie.
Beiträge ohne Eingabe zeigen statt der Eingabe ihre Listen und Texte.

Aufruf:  python3 reels.py          nur fehlende oder geänderte Reels
         python3 reels.py --alle   alle neu
Braucht: playwright, ffmpeg. Danach build.py aufrufen.
"""
import json
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

from playwright.sync_api import sync_playwright

import build

FPS = 30
REELS = build.DOCS / "reels"
VORLAGE = build.ROOT / "reel.html"


def daten(post):
    """Was die Vorlage für ein Reel braucht."""
    assert post.get("aufhaenger"), f"Nr. {post['nr']}: Feld 'aufhaenger' fehlt"
    kopf = next((s.get("kopf", "") for s in post["slides"] if s["typ"] == "eingabe"), "")
    return {
        "nr": post["nr"], "aufhaenger": post["aufhaenger"], "stempel": post["stempel"],
        "eingabe": post["eingabe"], "kopf": kopf, "kanal": build.KANAL,
        "schluss": post.get("schluss", ""),
        "szenen": [s for s in post["slides"] if s["typ"] in ("liste", "text")],
    }


def rendere(aufgabe):
    datei, ziel = aufgabe
    post = json.loads(Path(datei).read_text(encoding="utf-8"))
    d = daten(post)
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception:
            browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(VORLAGE.as_uri())
        page.evaluate("document.fonts.ready")
        sekunden = page.evaluate("d => dauer(d)", d)
        ff = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS), "-i", "-",
             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(ziel)],
            stdin=subprocess.PIPE)
        eng = False
        for i in range(int(sekunden * FPS)):
            page.evaluate("([d, t]) => zeige(d, t)", [d, i / FPS])
            if i % 15 == 0:
                eng = eng or page.evaluate("passtNicht()")
            ff.stdin.write(page.screenshot(type="jpeg", quality=92))
        ff.stdin.close()
        ok = ff.wait() == 0
        browser.close()
    if not ok:
        return f"Nr. {post['nr']}: ffmpeg gescheitert"
    return f"Nr. {post['nr']:>2}: {sekunden:4.1f} s{'  ACHTUNG: Text passt nicht ganz' if eng else ''}"


def main():
    alle = "--alle" in sys.argv
    REELS.mkdir(parents=True, exist_ok=True)
    aufgaben = []
    for f in sorted((build.ROOT / "posts").glob("*.json")):
        nr = json.loads(f.read_text(encoding="utf-8"))["nr"]
        ziel = REELS / f"{nr:03d}.mp4"
        neuer = max(f.stat().st_mtime, VORLAGE.stat().st_mtime)
        if alle or not ziel.exists() or ziel.stat().st_mtime < neuer:
            aufgaben.append((str(f), ziel))
    with Pool(2) as pool:
        for zeile in pool.imap(rendere, aufgaben):
            print(zeile, flush=True)
    print(f"{len(aufgaben)} Reels gebaut.")


if __name__ == "__main__":
    main()
