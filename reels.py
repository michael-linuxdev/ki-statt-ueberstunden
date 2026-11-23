#!/usr/bin/env python3
"""Baut zu jedem Beitrag ein Reel (1080 x 1920, MP4) nach docs/reels/.

Die Bilder des Karussells bauen sich Element für Element auf.

Aufruf:  python3 reels.py          nur fehlende oder geänderte Reels
         python3 reels.py --alle   alle neu
Braucht: playwright, Pillow, ffmpeg.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

import build

FPS = 30
BLENDE = 8  # Bilder pro Überblendung
REEL_CSS = """
html, body { height: 1920px; }
.kopfzeile { top: 250px; }
.fuss { display: none; }
.inhalt { top: 350px; bottom: 540px; }
"""
# Zerlegt ein Bild in die Teile, die nacheinander erscheinen
TEILE_JS = """(() => {
  const i = document.querySelector('.inhalt');
  const teile = [...i.querySelectorAll('h1, .stempel, h2, li, .text p, .zettel, .hinweis, .schluss, .schluss + p')];
  window.__teile = teile;
  return teile.map(t => [t.matches('.zettel') ? 'eingabe' : t.tagName, t.innerText.length]);
})()"""


def dauer(art, zeichen, letzter):
    """Standzeit eines Teils in Sekunden."""
    if art == "eingabe":
        return 4.0
    sek = 0.45 + zeichen / 55
    return sek + (0.8 if letzter else 0)




def schluss_reel(markup):
    return (markup.replace("Wisch zurück zu Bild", "Halte das Video bei Bild")
            .replace("und mach einen Screenshot.", "an und mach einen Screenshot."))


def baue(post, page, tmp, ziel):
    basis = build.FONTS.resolve().as_uri()
    n = len(post["slides"])
    bilder = []  # (Datei, Sekunden)
    for i, s in enumerate(post["slides"], 1):
        markup = build.slide_html(post, s, i, n, basis).replace("</style>", REEL_CSS + "</style>")
        if s["typ"] == "schluss":
            markup = schluss_reel(markup)
        quelle = Path(tmp) / "slide.html"
        quelle.write_text(markup, encoding="utf-8")
        page.goto(quelle.as_uri())
        page.evaluate("document.fonts.ready")
        page.evaluate(build.H1_ANPASSEN)
        if page.evaluate(build.PASST_NICHT):
            raise SystemExit(f"Text passt nicht ins Reel: Nr. {post['nr']}, Bild {i}")
        teile = page.evaluate(TEILE_JS)
        for k in range(1, len(teile) + 1):
            page.evaluate("k => window.__teile.forEach((t, j) => t.style.visibility = j < k ? '' : 'hidden')", k)
            datei = Path(tmp) / f"{i:02d}-{k:02d}.png"
            page.screenshot(path=str(datei))
            art, zeichen = teile[k - 1]
            bilder.append((datei, dauer(art, zeichen, k == len(teile))))
    bilder[-1] = (bilder[-1][0], bilder[-1][1] + 1.0)

    ziel.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
         "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(ziel)],
        stdin=subprocess.PIPE)
    vorher = None
    sekunden = 0.0
    for datei, sek in bilder:
        bild = Image.open(datei).convert("RGB")
        if vorher is not None:
            for b in range(1, BLENDE + 1):
                ff.stdin.write(Image.blend(vorher, bild, b / (BLENDE + 1)).tobytes())
        roh = bild.tobytes()
        for _ in range(round(sek * FPS)):
            ff.stdin.write(roh)
        sekunden += sek + BLENDE / FPS
        vorher = bild
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit(f"ffmpeg ist bei Nr. {post['nr']} gescheitert")
    return sekunden


def main():
    alle = "--alle" in sys.argv
    reels = build.DOCS / "reels"
    posts = [(f, json.loads(f.read_text(encoding="utf-8"))) for f in sorted((build.ROOT / "posts").glob("*.json"))]
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
        try:
            browser = pw.chromium.launch()
        except Exception:
            browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        for f, post in posts:
            ziel = reels / f"{post['nr']:03d}.mp4"
            if not alle and ziel.exists() and ziel.stat().st_mtime > f.stat().st_mtime:
                continue
            sek = baue(post, page, tmp, ziel)
            print(f"Nr. {post['nr']:>2}: {sek:4.1f} s, {ziel.stat().st_size / 1e6:.1f} MB", flush=True)
        browser.close()


if __name__ == "__main__":
    main()
