# KI statt Überstunden

Bildfabrik für den Instagram-Kanal @ki.statt.ueberstunden.

- `posts/*.json`: ein Beitrag pro Datei (Titel, Folien, Eingabe, Beitragstext)
- `python3 build.py`: rendert die Karussell-Bilder (1080 × 1350) und baut die Seite nach `docs/`
- `python3 reels.py`: rendert zu jedem Beitrag ein Reel (1080 × 1920, MP4) nach `docs/reels/`; danach `build.py` erneut aufrufen
- `docs/index.html`: öffentliche Sammlung der Eingaben (Link im Profil)
- `docs/studio.html`: Redaktionsplan mit Bildern zum Herunterladen, Beitragstexten und Abhaken
- `REDAKTIONSPLAN.md`: derselbe Plan als Tabelle (wird von `build.py` erzeugt)

Rhythmus: Montag, Mittwoch, Freitag. Jeder Beitrag trägt sein Datum im Feld `datum`.

Folientypen: `cover`, `text`, `liste`, `eingabe`, `schluss`.
GitHub Pages: Branch `main`, Ordner `/docs`, Domain ki.micana.de.
