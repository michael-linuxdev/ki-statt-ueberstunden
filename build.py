#!/usr/bin/env python3
"""Baut aus posts/*.json die Karussell-Bilder und die Webseite in docs/.

Aufruf:  python3 build.py
Braucht: playwright (Python) und einen Chrome/Chromium.
"""
import html
import json
import shutil
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
FONTS = DOCS / "fonts"
KANAL = "ki.statt.ueberstunden"
DOMAIN = "ki.micana.de"

# Farben: Kugelschreiber-Blau, Textmarker-Gelb, Papier, Stempel-Rot
TINTE, MARKER, PAPIER, LINIE, STEMPEL = "#17277A", "#FFE84D", "#FFFFFF", "#DCE2F4", "#D8342A"


def e(text):
    return html.escape(text, quote=True)


def absatz(text):
    return "".join(f"<p>{e(t)}</p>" for t in text.split("\n\n"))


def font_css(basis):
    return f"""
@font-face {{ font-family: Bitter; src: url('{basis}/Bitter.ttf'); font-weight: 100 900; }}
@font-face {{ font-family: Fira; src: url('{basis}/FiraSans-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: Fira; src: url('{basis}/FiraSans-Medium.ttf'); font-weight: 500; }}
@font-face {{ font-family: Fira; src: url('{basis}/FiraSans-Bold.ttf'); font-weight: 700; }}
"""


SLIDE_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: 1080px; height: 1350px; }}
body {{ background: {PAPIER}; color: {TINTE}; font-family: Fira, sans-serif; position: relative; overflow: hidden; }}
.rand {{ position: absolute; left: 0; top: 0; bottom: 0; width: 28px; background: {TINTE}; }}
.kopfzeile {{ position: absolute; left: 100px; right: 80px; top: 70px; display: flex;
  justify-content: space-between; font-size: 30px; font-weight: 500; }}
.fuss {{ position: absolute; left: 100px; right: 80px; bottom: 64px; display: flex;
  justify-content: space-between; align-items: baseline; font-size: 30px; font-weight: 500;
  border-top: 3px solid {TINTE}; padding-top: 22px; }}
.inhalt {{ position: absolute; left: 100px; right: 80px; top: 190px; bottom: 190px;
  display: flex; flex-direction: column; justify-content: center; }}
h1 {{ font-family: Bitter, serif; font-weight: 800; font-size: 112px; line-height: 1.22; letter-spacing: -1.5px; }}
h1 span, .schluss span {{ background: {MARKER}; padding: 2px 14px; margin-left: -14px;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; }}
h2 {{ font-family: Bitter, serif; font-weight: 800; font-size: 68px; line-height: 1.15; margin-bottom: 56px; }}
.text p {{ font-size: 52px; line-height: 1.38; margin-bottom: 34px; }}
ul {{ list-style: none; }}
li {{ font-size: 46px; line-height: 1.34; padding: 30px 0 30px 70px; border-top: 3px solid {LINIE}; position: relative; }}
li:last-child {{ border-bottom: 3px solid {LINIE}; }}
li::before {{ content: ""; position: absolute; left: 4px; top: 44px; width: 34px; height: 34px; background: {MARKER};
  border: 3px solid {TINTE}; }}
.zettel {{ border-left: 10px solid {MARKER}; padding: 6px 0 6px 38px; }}
.zettel p {{ font-size: 39px; line-height: 1.5; font-weight: 500; margin-bottom: 44px; }}
.zettel p:last-child {{ margin-bottom: 0; }}
.stempel {{ position: absolute; right: 90px; bottom: 230px; transform: rotate(-7deg); color: {STEMPEL};
  border: 7px solid {STEMPEL}; border-radius: 14px; padding: 18px 34px; font-family: Bitter, serif;
  font-weight: 800; font-size: 54px; opacity: .92; }}
.stempel small {{ display: block; font-family: Fira, sans-serif; font-size: 26px; font-weight: 500; }}
.schluss {{ font-family: Bitter, serif; font-weight: 800; font-size: 84px; line-height: 1.28; }}
.schluss + p {{ font-size: 44px; line-height: 1.4; margin-top: 60px; }}
ol {{ list-style: none; counter-reset: schritt; }}
ol li {{ counter-increment: schritt; }}
ol li::before {{ content: counter(schritt); background: {MARKER}; border: 0; width: 52px; height: 52px; top: 30px;
  left: 0; font-family: Bitter, serif; font-weight: 800; font-size: 34px; display: grid; place-items: center; }}
.hinweis {{ font-size: 40px; line-height: 1.4; margin-top: 48px; font-weight: 500; }}
"""


def slide_html(post, slide, i, n, basis):
    typ = slide["typ"]
    stempel = ""
    if typ == "cover":
        inhalt = f"<h1><span>{e(post['titel'])}</span></h1>"
        stempel = f"<div class='stempel'><small>Nr. {post['nr']}</small>{e(post['stempel'])}</div>"
    elif typ == "text":
        inhalt = f"<h2>{e(slide['kopf'])}</h2><div class='text'>{absatz(slide['text'])}</div>"
    elif typ == "liste":
        punkte = "".join(f"<li>{e(p)}</li>" for p in slide["punkte"])
        inhalt = f"<h2>{e(slide['kopf'])}</h2><ul>{punkte}</ul>"
    elif typ == "eingabe":
        inhalt = f"<h2>{e(slide['kopf'])}</h2><div class='zettel'>{absatz(post['eingabe'])}</div>"
    elif typ == "schluss":
        if post["eingabe"]:
            bild = next(k for k, x in enumerate(post["slides"], 1) if x["typ"] == "eingabe")
            inhalt = (f"<h2>So kopierst du die Eingabe</h2><ol>"
                      f"<li>Wisch zurück zu Bild {bild} und mach einen Screenshot.</li>"
                      f"<li>Öffne den Screenshot in deinen Fotos.</li>"
                      f"<li>Halte den Finger auf den Text und wähle „Kopieren“.</li></ol>"
                      f"<p class='hinweis'>Speichere den Beitrag, damit du ihn wiederfindest.</p>")
        else:
            inhalt = ("<div class='schluss'><span>Schick das jemandem, der alles einfügt.</span></div>"
                      "<p>Mehr KI fürs Büro, ehrlich getestet:<br>folge @" + KANAL + "</p>")
    else:
        raise ValueError(f"Unbekannter Folientyp: {typ}")
    weiter = "weiterwischen" if i < n else ""
    return f"""<!doctype html><html lang="de"><meta charset="utf-8">
<style>{font_css(basis)}{SLIDE_CSS}</style>
<body><div class="rand"></div>
<div class="kopfzeile"><span>{e(post['format'])}</span><span>{i} / {n}</span></div>
<div class="inhalt">{inhalt}</div>{stempel}
<div class="fuss"><span>@{KANAL}</span><span>{weiter}</span></div>
</body></html>"""


PROFIL_HTML = """<!doctype html><html><meta charset="utf-8"><style>{fonts}
* {{ margin: 0; }} body {{ width: 1080px; height: 1080px; background: {tinte}; display: grid; place-items: center; }}
div {{ font-family: Bitter, serif; font-weight: 900; font-size: 430px; color: {tinte}; background: {marker};
  padding: 0 60px; line-height: 1.12; transform: rotate(-4deg); letter-spacing: -8px; }}
</style><body><div>KI</div></body></html>"""


SITE_CSS = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: {PAPIER}; color: {TINTE}; font-family: Fira, system-ui, sans-serif;
  font-size: 18px; line-height: 1.5; border-left: 10px solid {TINTE}; }}
main {{ max-width: 680px; margin: 0 auto; padding: 28px 20px 80px; }}
header p {{ margin: 0 0 6px; font-weight: 500; }}
h1 {{ font-family: Bitter, serif; font-weight: 800; font-size: clamp(38px, 10vw, 60px); line-height: 1.25;
  letter-spacing: -.5px; margin: 0 0 18px; }}
h1 span {{ background: {MARKER}; padding: 1px 8px; margin-left: -8px;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; }}
h2 {{ font-family: Bitter, serif; font-weight: 800; font-size: 26px; line-height: 1.25; margin: 0 0 6px; }}
article {{ border-top: 3px solid {TINTE}; padding: 26px 0 30px; margin-top: 28px; }}
.meta {{ display: flex; justify-content: space-between; font-weight: 500; margin-bottom: 8px; }}
.rot {{ color: {STEMPEL}; }}
.zettel {{ background: repeating-linear-gradient({PAPIER} 0 29px, {LINIE} 29px 31px); border-left: 5px solid {MARKER};
  padding-left: 16px; margin: 16px 0; white-space: pre-wrap; line-height: 31px; font-weight: 500; }}
button, .knopf {{ font: inherit; font-weight: 700; color: {PAPIER}; background: {TINTE}; border: 0; border-radius: 6px;
  padding: 13px 20px; min-height: 48px; cursor: pointer; text-decoration: none; display: inline-block; }}
button.hell {{ background: {MARKER}; color: {TINTE}; }}
button:focus-visible, a:focus-visible {{ outline: 3px solid {STEMPEL}; outline-offset: 3px; }}
a {{ color: {TINTE}; }}
.reihe {{ display: flex; gap: 12px; overflow-x: auto; padding: 4px 0 14px; scroll-snap-type: x mandatory; }}
.reihe img {{ height: 300px; width: auto; border: 2px solid {LINIE}; scroll-snap-align: start; }}
.knoepfe {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; }}
pre {{ white-space: pre-wrap; font: inherit; font-size: 16px; background: #F3F5FC; padding: 14px; border-radius: 6px; }}
footer {{ margin-top: 50px; border-top: 3px solid {LINIE}; padding-top: 18px; font-size: 16px; }}
"""

KOPIER_JS = """
document.addEventListener('click', async (ev) => {
  const b = ev.target.closest('[data-kopiere]');
  if (b) {
    const text = document.getElementById(b.dataset.kopiere).textContent;
    try { await navigator.clipboard.writeText(text); b.textContent = 'Kopiert'; }
    catch { b.textContent = 'Kopieren hat nicht geklappt, bitte Text markieren'; }
    return;
  }
  const t = ev.target.closest('[data-teile]');
  if (t) {
    const urls = t.dataset.teile.split(',');
    try {
      const files = await Promise.all(urls.map(async (u, i) => {
        const blob = await (await fetch(u)).blob();
        return new File([blob], (i + 1) + '.png', { type: 'image/png' });
      }));
      if (navigator.canShare && navigator.canShare({ files })) { await navigator.share({ files }); }
      else { t.textContent = 'Teilen geht hier nicht, bitte Bilder einzeln lang antippen'; }
    } catch (err) { if (err.name !== 'AbortError') t.textContent = 'Teilen hat nicht geklappt'; }
  }
});
"""


def seite(titel, body, beschreibung):
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title><meta name="description" content="{e(beschreibung)}">
<link rel="icon" href="profilbild.png">
<style>{font_css('fonts')}{SITE_CSS}</style></head>
<body><main>{body}</main><script>{KOPIER_JS}</script></body></html>
"""


def index_html(posts):
    teile = [f"""<header><p>@{KANAL}</p>
<h1><span>KI statt Überstunden</span></h1>
<p>Fertige Eingaben für ChatGPT, Claude und Co. Kopieren, eigene Angaben eintragen, früher gehen.</p></header>"""]
    for p in sorted(posts, key=lambda p: -p["nr"]):
        if not p["eingabe"]:
            continue
        teile.append(f"""<article id="nr{p['nr']}">
<div class="meta"><span>Eingabe Nr. {p['nr']}</span><span class="rot">{e(p['stempel'])}</span></div>
<h2>{e(p['titel'])}</h2>
<div class="zettel" id="e{p['nr']}">{e(p['eingabe'])}</div>
<button data-kopiere="e{p['nr']}">Eingabe kopieren</button></article>""")
    teile.append(f"""<footer><p>Gib keine Namen, Kundendaten oder Passwörter in ein KI-Werkzeug ein
und prüfe jedes Ergebnis, bevor du es verwendest.</p>
<p><a href="https://www.instagram.com/{KANAL}/">@{KANAL} auf Instagram</a></p></footer>""")
    return seite("KI statt Überstunden: Eingaben zum Kopieren", "".join(teile),
                 "Fertige KI-Eingaben für den Büroalltag zum Kopieren.")


def studio_html(posts):
    teile = ["""<header><p>Nur für dich</p><h1><span>Studio</span></h1>
<p>Bilder aufs Handy holen, Text kopieren, in Instagram als Karussell posten.</p></header>"""]
    for p in sorted(posts, key=lambda p: -p["nr"]):
        n = len(p["slides"])
        ordner = f"slides/{p['nr']:03d}"
        bilder = "".join(f'<a href="{ordner}/{i}.png" download="{p["nr"]:03d}-{i}.png">'
                         f'<img src="{ordner}/{i}.png" alt="Bild {i} von {n}" loading="lazy"></a>'
                         for i in range(1, n + 1))
        urls = ",".join(f"{ordner}/{i}.png" for i in range(1, n + 1))
        teile.append(f"""<article>
<div class="meta"><span>Nr. {p['nr']}, {e(p['format'])}</span><span>{n} Bilder</span></div>
<h2>{e(p['titel'])}</h2>
<div class="reihe">{bilder}</div>
<div class="knoepfe"><button data-teile="{urls}">Alle Bilder teilen oder sichern</button>
<button class="hell" data-kopiere="c{p['nr']}">Beitragstext kopieren</button></div>
<pre id="c{p['nr']}">{e(p['caption'])}</pre></article>""")
    teile.append('<footer><p><a href="profilbild.png" download>Profilbild herunterladen</a></p></footer>')
    return seite("Studio", "".join(teile), "Interne Galerie").replace(
        "<title>", '<meta name="robots" content="noindex"><title>')


def main():
    posts = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((ROOT / "posts").glob("*.json"))]
    nummern = [p["nr"] for p in posts]
    assert len(nummern) == len(set(nummern)), "Doppelte Beitragsnummer"

    slides_dir = DOCS / "slides"
    shutil.rmtree(slides_dir, ignore_errors=True)
    basis = FONTS.resolve().as_uri()

    with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
        try:
            browser = pw.chromium.launch()
        except Exception:
            browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1080, "height": 1350})

        def render(markup, ziel):
            quelle = Path(tmp) / "slide.html"
            quelle.write_text(markup, encoding="utf-8")
            page.goto(quelle.as_uri())
            page.evaluate("document.fonts.ready")
            zu_hoch = page.evaluate(
                "(() => { const i = document.querySelector('.inhalt');"
                " return i ? i.scrollHeight > i.clientHeight + 1 : false; })()")
            if zu_hoch:
                raise SystemExit(f"Text passt nicht auf das Bild: {ziel}. Bitte kürzen.")
            ziel.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(ziel))

        for p in posts:
            n = len(p["slides"])
            for i, s in enumerate(p["slides"], 1):
                render(slide_html(p, s, i, n, basis), slides_dir / f"{p['nr']:03d}" / f"{i}.png")
        page.set_viewport_size({"width": 1080, "height": 1080})
        render(PROFIL_HTML.format(fonts=font_css(basis), tinte=TINTE, marker=MARKER), DOCS / "profilbild.png")
        browser.close()

    (DOCS / "index.html").write_text(index_html(posts), encoding="utf-8")
    (DOCS / "studio.html").write_text(studio_html(posts), encoding="utf-8")
    (DOCS / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print(f"{len(posts)} Beiträge gebaut.")


if __name__ == "__main__":
    main()
