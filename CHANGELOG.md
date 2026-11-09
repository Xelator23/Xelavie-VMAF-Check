# Changelog

## 0.1.0-nightly.10

- Integrierter CPU-DV-Renderer für 10-Bit-4:2:0-MKV mit HEVC/AV1 unter Windows x64 und Linux x86_64: P010-Eingang, direkter P016-Transport, gemeinsame Chroma-Verarbeitung und Crop-ROI mit Randbereich.
- Begrenzter Tonwert-/Farbraum-Schnellpfad mit vollständiger Berechnung für kritische Pixel. Kleine Score-Abweichungen möglich; keine bitidentische Messung zu nightly.9. Aktivierung nur pro DV-Decoderprozess, keine systemweite Vulkan-Layer-Installation.
- `--dv-renderer classic` verwendet die klassische DV-Farbberechnung; nicht unterstützte Formate behalten diese automatisch. SDR/HDR ohne DV nutzt den bisherigen Renderer.
- Getestete Renderer, benötigte Bibliotheken und Lizenzhinweise werden in Windows-/Linux-Paketen und im uv-Wheel mitgeliefert. Zugehöriges Quellpaket beim Release.
- Direktvergleich gegen nightly.9 am gleichen 12,012-s-Filmausschnitt, 25 %, Median aus drei Paaren: Windows 43,7 %, Linux 47,7 % weniger Messzeit. Inklusive Clipvorbereitung 36,4 % / 44,5 %. Maximale Einzelbildabweichung 0,0152 VMAF-Punkte. Keine garantierte Vollfilmzeit.
- 100-%-Kurzprüfung sowie Profil-/Farbtests; vollständige HDR-/DV-Filmläufe bleiben noch unvalidiert. Profil 7 weiterhin P8.1-Kompatibilitätsvergleich ohne vollständige FEL-Rekonstruktion.


## 0.1.0-nightly.9

- HDR-Messung über gebündelten nativen x64-Worker mit libvmaf/zimg; behebt `libvmaf was built without zimg support`. HDR-Vorabtest verlangt nun eine erfolgreiche Messung und die Ablehnung unbekannter Farbangaben.
- Getesteter CPU-DV-Ablauf mit Mesa Lavapipe und libplacebo ab 7.387.0 für Windows und Linux. Windows lädt Lavapipe bei Bedarf SHA256-geprüft; Linux verwendet ein vorhandenes Mesa-ICD.
- 25-%-HDR/DV-Prüfungen bereiten nur benötigte Bilder einschließlich Referenznachbarn auf. Geprüfte Bilddaten, Merkmale und Scores bleiben innerhalb derselben Plattform gleich; keine pauschale 75-%-Zeitersparnis.
- Profil-7-Remux- und Download-Hotfixes bleiben enthalten. Keine vollständige P7-FEL-Rekonstruktion.
- Windows-/Linux-Pakete und uv-Wheel enthalten Worker, Quell-Build und Lizenzhinweise. Kurztests mit echtem Filmmaterial und synthetischen Profilen; keine abgeschlossene Vollfilm-HDR/DV-Validierung.

## 0.1.0-nightly.8

- Profil-7-Arbeitskopien werden mit MKVToolNix und der ursprünglichen rationalen Bildrate gemuxt. Behebt den FFmpeg-Abbruch „unknown timestamp“.
- MKVToolNix bei Bedarf separat und SHA256-geprüft nachladen; optional `--mkvmerge` für lokale Installationen.
- Keine Änderungen an Mesa, HDR-Messung oder der VMAF-Bewertung.

## 0.1.0-nightly.7

- FFmpeg-Download nach dem Umzug zu `FFmpeg-Builds/FFmpeg-Builds` repariert; die bisherige Adresse bleibt kompatibel.
- HTTPS- und SHA256-Prüfung bleiben aktiv. Keine Änderungen an der Videoanalyse.

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
