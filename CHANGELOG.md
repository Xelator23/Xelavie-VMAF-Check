# Changelog

## 0.1.0-nightly.6

- `--gui` startet unter Windows und Linux im Hintergrund; das Terminal kann anschließend geschlossen werden.
- Ein erneuter GUI-Aufruf öffnet dieselbe Sitzung. Prozesssperre, Startdiagnosen und Wiederanlauf nach veralteten Sitzungsdaten ergänzt.
- „GUI beenden“ stoppt den Dienst und versucht den Browser-Tab zu schließen; bei Browserbeschränkungen erscheint ein Hinweis.
- Textmarkierungen bleiben bei automatischen Aktualisierungen erhalten. Unveränderte Texte werden nicht neu geschrieben; markierte Bereiche nach Ende der Auswahl aktualisiert.
- Ausrichtung der CHECK-Buchstaben im CLI-Banner korrigiert.
- Hintergrundstart, Wiederverbindung, Abbruch und installierte Pakete unter Windows und auf Ubuntu geprüft.

## 0.1.0-nightly.5

- Kompakte CLI-Starthilfe mit klarer Reihenfolge: Original/Remux zuerst, Encode danach.
- Konkrete Dateipfad-Beispiele für Windows und Linux, auch bei getrennten Ordnern und Laufwerken.
- Die vollständige Optionsliste erscheint erst mit `--help`; ohne Argumente wird keine Prüfung gestartet.
- Pflichtargumente in der Hilfe heißen jetzt `ORIGINAL` und `ENCODE`.
- README, Installationsanleitung und Commands zeigen die Filmangabe direkt am Einstieg.

## 0.1.0-nightly.4

- CLI-Startbanner mit VMAF-CHECK-Blockschrift, „by Xelavie“, Motto und Verlauf.
- Versionsnummer wird direkt aus dem Programm übernommen.
- Kompakte Ausgabe bei schmalen Terminals, nicht unterstützten Zeichensätzen und umgeleiteten Logs.
- `--version` bleibt eine einzelne Zeile; kein CLI-Banner beim GUI-Start.
- Vollständige Commands-Referenz ist nun auch im portablen Paket enthalten.

## 0.1.0-nightly.3

- CLI ist Standard und nimmt Original/Encode als Argumente sowie Einstellungen als Flags entgegen.
- Ohne Argumente erscheint die Hilfe; kein Auswahlmenü und keine interaktiven Rückfragen.
- Browser-Oberfläche ausschließlich mit `--gui`; bisherige Flags `--ui` und `--cli` entfallen.
- Windows-/Linux-Starter und uv-Befehl verwenden dasselbe Verhalten.
- Startanleitungen, Paketprüfung und Tests angepasst; uv/Git-Einrichtungsanleitung in den portablen Paketen enthalten.

## 0.1.0-nightly.2

- Portable Windows-/Linux-Pakete und zusätzlich ein installierbares Python-Wheel für uv.
- Gemeinsamer Befehl `xelavie-vmaf-check` mit derselben CLI, UI und gespeicherten Konfiguration.
- uv muss bereits installiert sein; kein automatischer uv-Download mehr, auch in den portablen Startern.
- Portable Starter nutzen Python 3.10+ oder vorhandenes uv für Python 3.12.
- Wheel mit UI-Dateien und Windows-Downloadhelfer; Installation wird unter Windows und Linux getestet.
- Python-Paketversion `0.1.0.dev2` entspricht der angezeigten Version `0.1.0-nightly.2`.

## 0.1.0-nightly.1

Erste öffentliche Vorabversion, veröffentlicht unter dem Tag `nightly`.
Die öffentlichen Versionsnummern beginnen neu; interne 6.x-Entwicklungsstände sind keine früheren öffentlichen Releases.

- Windows- und Linux-Starter mit optionalem Python-/Werkzeugdownload.
- Lokale Browser-UI mit Xelavie-Branding, Dashboard, Dateiauswahl, Warteschlange und Ergebnissen.
- Fortsetzen nach Auftragsfehlern, automatische Entfernung erfolgreicher Queue-Einträge, Ergebnisverwaltung.
- Interaktive CLI mit Farb-Presets, getrennten Quellordnern und Pfadnavigation; Windows-Livevorschau.
- Vollfilmprüfung mit 100/50/25 Prozent Frame-Sampling, Crop-Erkennung und Metadaten-Frameanzahl mit Scan-Fallback.
- SDR-/HDR-/HLG-Pipeline und explizite Dolby-Vision-Vergleichsmodi mit P7-Kompatibilitätsvergleich.
- Getrennte Zeitmessung für Vorbereitung, Messung und gesamten Job.
- Separate Windows-/Linux-Archive, Prüfsummen, Dokumentation und Demo-Bilder.

### Bekannte Grenzen

- HDR-/HLG-/DV-Videoläufe noch nicht vollständig validiert; keine vollständige P7-FEL-Rekonstruktion.
- Linux-Terminal und Python-Bootstrap noch nicht Ende-zu-Ende validiert.
- Keine automatische zeitliche Synchronisierung, keine SDR-gegen-HDR-Paarung.
- Automatisch geladene Upstream-Werkzeuge können sich ändern.

Der erste stabile Release ist als `v0.1.0` geplant.
