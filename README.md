# KI statt Überstunden

Bildfabrik für den Instagram-Kanal @ki.statt.ueberstunden.

- `posts/*.json`: ein Beitrag pro Datei (Titel, Folien, Eingabe, Beitragstext)
- `python3 build.py`: rendert die Karussell-Bilder (1080 × 1350) und baut die Seite nach `docs/`
- `docs/index.html`: öffentliche Sammlung der Eingaben (Link im Profil)
- `docs/studio.html`: Galerie zum Herunterladen der Bilder und Kopieren der Beitragstexte

Folientypen: `cover`, `text`, `liste`, `eingabe`, `schluss`.
GitHub Pages: Branch `main`, Ordner `/docs`, Domain ki.micana.de.
