# Changelog

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
