# Commands

Alle CLI-Argumente für **Xelavie VMAF Check 0.1.0-nightly.10**. Die CLI wird über Dateipfade und Flags bedient; ohne Argumente erscheint eine kurze Starthilfe, mit `--help` die vollständige Hilfe. Es gibt keine interaktiven Rückfragen.

[Start und Hilfe](#start-und-hilfe) · [Prüfung](#prüfung) · [Crop](#crop) · [Farbangaben](#farbangaben) · [Dolby Vision](#dolby-vision) · [Programme und Modelle](#programme-und-modelle) · [Ordner](#ordner) · [Beispiele](#beispiele)

## Aufruf

```sh
xelavie-vmaf-check "ORIGINAL.mkv" "ENCODE.mkv" [OPTIONEN]
```

| Pflichtargument | Beschreibung |
| --- | --- |
| `ORIGINAL` | Pfad zur Original-/Referenzdatei; immer zuerst angeben. |
| `ENCODE` | Pfad zur zu prüfenden Encode-Datei; immer als zweites Argument. |

Beide Dateien dürfen in unterschiedlichen Ordnern oder auf unterschiedlichen Laufwerken liegen. Pfade mit Leerzeichen in Anführungszeichen setzen. Original und Encode müssen dieselbe Schnittfassung, denselben Startframe und dieselbe konstante Bildrate haben. Es erfolgt keine automatische zeitliche Synchronisierung.

**Diese Beispielpfade durch deine eigenen Dateien ersetzen.** `ORIGINAL` und `ENCODE` sind Platzhalter, keine zusätzlichen Flags. Die eckigen Klammern `[OPTIONEN]` nicht mit eingeben.

Windows / PowerShell, 25 % der Frames:

```powershell
xelavie-vmaf-check "D:\Originale\Film.mkv" "E:\Encodes\Film.mkv" --percent 25
```

Linux, 25 % der Frames:

```sh
xelavie-vmaf-check "/mnt/originale/Film.mkv" "/mnt/encodes/Film.mkv" --percent 25
```

Für portable Pakete ersetzt du nur den Programmnamen:

| Startweg | Aufruf |
| --- | --- |
| uv, Windows und Linux | `xelavie-vmaf-check ORIGINAL ENCODE [OPTIONEN]` |
| Windows portable / PowerShell | `.\vmaf-check.cmd ORIGINAL ENCODE [OPTIONEN]` |
| Linux portable | `sh ./vmaf-check.sh ORIGINAL ENCODE [OPTIONEN]` |
| Python direkt | `python vmaf_launcher.py ORIGINAL ENCODE [OPTIONEN]`; unter Linux gegebenenfalls `python3` |

## Start und Hilfe

Der Launcher zeigt beim CLI-Start ein Banner mit automatisch übernommener Programmversion. Bei schmalen Terminals, nicht unterstütztem Zeichensatz oder umgeleiteter Ausgabe erscheint eine kompakte Textzeile. `--version` gibt weiterhin nur die Version aus; `--gui` startet ohne CLI-Banner.

Diese Aufrufe benötigen keine Videodateien:

| Flag / Aufruf | Beschreibung |
| --- | --- |
| Ohne Argumente | Zeigt die kurze Starthilfe mit Dateipfad-Beispiel und beendet sich. |
| `-h`, `--help` | Zeigt Hilfe und verfügbare Prüfoptionen. |
| `--version` | Zeigt die Programmversion. |
| `--gui` | Startet den GUI-Dienst im Hintergrund oder öffnet die bereits laufende Sitzung. **Allein verwenden**, ohne Dateipfade oder Prüfoptionen. |

`--gui` gehört zum Launcher beziehungsweise zum installierten Befehl. Beim direkten Aufruf von `vmaf_check.py` ist es nicht verfügbar; verwende dafür `vmaf_launcher.py`. Die früheren Startflags `--ui` und `--cli` werden nicht mehr verwendet.

Nach Anzeige der lokalen URL darf das Terminal geschlossen werden. Tab/Browser schließen beendet den Dienst nicht; Prüfungen laufen weiter. Mit `--gui` öffnest du dieselbe Sitzung erneut. **GUI beenden** stoppt den Dienst und nach Bestätigung auch eine laufende Prüfung. Unter Linux ist das Weiterlaufen nach vollständiger Abmeldung von der Sitzungskonfiguration abhängig. Vor Programmupdates den laufenden GUI-Dienst beenden.

## Prüfung

| Flag | Erlaubte Werte | Standard | Beschreibung |
| --- | --- | --- | --- |
| `--percent` | `100`, `50`, `25` | `100` | Bewertet jedes Bild, jedes zweite oder jedes vierte Bild über den gesamten Film. Die Decoder lesen weiterhin alle Frames; 25 % bedeutet nicht automatisch ein Viertel der Laufzeit. |
| `--display` | `auto`, `1080`, `2160` | `auto` | Wählt die Modell-/Betrachtungsvorgabe. Automatisch: `2160`, wenn der Encode breiter als 2560 oder höher als 1440 Pixel ist; sonst `1080`. |
| `--threads` | Ganze Zahl ab `1` | Erkannte CPU-Anzahl, höchstens `16`, mindestens `1` | Anzahl der VMAF-Threads; kein globales Limit für sämtliche Decoder- und Filterthreads. |

Die aktive Encode-Auflösung wird aus der Datei ermittelt. Die Referenz wird auf das passende aktive Bildraster gebracht; `--display 2160` macht aus einem 1080p-Encode keinen vollständigen Qualitätsvergleich gegen die ursprüngliche 4K-Auflösung.

Bei `--percent 25` optimiert der HDR/DV-Pfad mit unterstütztem Modell automatisch die Bildaufbereitung: Referenzbilder werden einschließlich ihrer direkten Nachbarn verarbeitet, beim Encode nur jedes vierte Bild. So bleiben die Bewegungsmerkmale und Framepositionen erhalten. Beide Dateien werden weiterhin vollständig decodiert und gezählt. Bei unbekannten Modellkonfigurationen bleibt der bisherige Ablauf aktiv; ein zusätzlicher Flag ist nicht nötig.

## Crop

| Flag | Erlaubte Werte | Standard | Beschreibung |
| --- | --- | --- | --- |
| `--crop` | `auto`, `none` oder `BREITE:HOEHE:X:Y` | `auto` | Referenz-Crop automatisch erkennen, ohne Referenz-Crop arbeiten oder einen Ausschnitt manuell vorgeben. |
| `--crop-encode` | `BREITE:HOEHE:X:Y` | Nicht gesetzt | Eigenen Encode-Ausschnitt vorgeben. Ohne diesen Flag wird der Referenz-Crop bei gleichem ursprünglichen Seitenverhältnis proportional auf den Encode übertragen. Bei Auto-Crop und abweichenden ursprünglichen Seitenverhältnissen wird auch der Encode auf Balken untersucht. |

Breite, Höhe und beide Offsets werden in Pixeln angegeben und müssen gerade Zahlen sein. Breite und Höhe müssen positiv sein, Offsets mindestens 0. Der Ausschnitt muss vollständig innerhalb der jeweiligen Datei liegen.

Beispiel: `--crop 1920:800:0:140` entfernt bei einer 1920×1080-Referenz oben und unten jeweils 140 Pixel. Für einen bereits auf 1920×800 beschnittenen Encode passt `--crop-encode 1920:800:0:0`. Bei anderer Auflösung müssen die Werte angepasst werden.

`--crop none` deaktiviert die automatische Crop-Erkennung; ein ausdrücklich gesetztes `--crop-encode` gilt weiterhin. Unvereinbare aktive Seitenverhältnisse führen zum Abbruch; das Bild wird nicht automatisch gestreckt.

## Farbangaben

**Ohne Farbflags werden die erkannten Angaben verwendet.** Fehlende notwendige Werte werden nicht aus der Auflösung geraten. Overrides nur setzen, wenn du die tatsächlichen Quelleigenschaften kennst: Sie ersetzen auch bereits vorhandene Angaben und konvertieren SDR nicht zu HDR.

`ref` steht für Original/Referenz, `enc` für Encode. Die Seiten sind unabhängig. Für alle folgenden Flags gilt als Standard: **kein manueller Override**.

| Referenz-Flag | Encode-Flag | Erlaubte Werte | Beschreibung |
| --- | --- | --- | --- |
| `--ref-color` | `--enc-color` | `bt709`, `hdr10`, `hlg` | Setzt ein vollständiges Farb-Preset einschließlich Limited Range; Details unten. |
| `--ref-primaries` | `--enc-primaries` | `bt709`, `bt2020` | Primärfarben der Quelle. |
| `--ref-transfer` | `--enc-transfer` | `bt709`, `smpte2084`, `arib-std-b67` | Transferfunktion: SDR BT.709, PQ oder HLG. |
| `--ref-matrix` | `--enc-matrix` | `bt709`, `bt2020nc` | Farbmatrix der Quelle. |
| `--ref-range` | `--enc-range` | `limited`, `full` | Wertebereich der Quelle. |

| Preset | Primärfarben | Transferfunktion | Matrix | Wertebereich |
| --- | --- | --- | --- | --- |
| `bt709` | BT.709 | BT.709 | BT.709 | Limited |
| `hdr10` | BT.2020 | PQ / SMPTE ST 2084 | BT.2020 non-constant | Limited |
| `hlg` | BT.2020 | HLG / ARIB STD-B67 | BT.2020 non-constant | Limited |

Einzelwerte haben Vorrang vor dem Preset, unabhängig von der Reihenfolge der Flags. Beispiel für bekanntes SDR BT.709 Full Range auf der Referenzseite: `--ref-color bt709 --ref-range full`.

## Dolby Vision

`--dv-mode` wählt den Vergleichsmodus. Standard: `auto`.

| Wert | Beschreibung |
| --- | --- |
| `auto` | Sobald eine Seite Profil 7 hat: `compatible`; ansonsten `rendered`. |
| `compatible` | Bereitet Profil 7 als Profil 8.1 auf; der Enhancement Layer wird verworfen. Danach Vergleich der rekonstruierten Bilder. |
| `rendered` | Vergleicht die über die jeweilige SDR-/HDR-/DV-Pipeline verarbeiteten Bilder. Bei DV werden dekodierte DV-Metadaten verwendet. Profil 7 wird in diesem Modus abgelehnt. |
| `base-layer` | Vergleicht nur die HDR10-Basis ohne DV-RPU und Enhancement Layer. Erfordert passende PQ-/BT.2020-Angaben auf beiden Seiten und kompatible Quellen: P7, P8.1, P10.1 oder normales HDR10. |

**Keine vollständige Profil-7-FEL-Rekonstruktion.** Der CPU-Pfad benötigt FFmpeg/libplacebo ab 7.387.0, Vulkan-Loader und Mesa Lavapipe, keine GPU. Windows kann Lavapipe nachladen; unter Linux wird ein vorhandenes ICD verwendet. HDR-VMAF nutzt den gebündelten x64-Worker mit zimg. Kurztests ersetzen keine Vollfilm-Validierung oder Dolby-Zertifizierung. SDR gegen HDR ist kein unterstütztes Vergleichspaar.

## Programme und Modelle

| Flag | Wert | Standard / Verhalten |
| --- | --- | --- |
| `--ffmpeg` | Programmpfad oder auflösbarer Programmname | Verwendet ohne Angabe `ffmpeg` aus dem PATH; bei fehlenden Programmen oder erforderlichen Funktionen kann ein geeignetes Paket nachgeladen werden. |
| `--ffprobe` | Programmpfad oder auflösbarer Programmname | Verwendet ohne Angabe `ffprobe` aus dem PATH; ansonsten gegebenenfalls zusammen mit FFmpeg nachladen. |
| `--dovi-tool` | Programmpfad | Optionales lokales dovi_tool für Profil-7-Vorbereitung; sonst vorhandenes Werkzeug verwenden oder bei Bedarf herunterladen. |
| `--mkvmerge` | Programmpfad | Optionales MKVToolNix für Profil-7-Vorbereitung; sonst vorhandenes Werkzeug oder temporärer Download. |
| `--vulkan-icd` | JSON-Datei | Optionaler Mesa-Lavapipe-Treiber für die DV-Verarbeitung auf der CPU. Kein GPU-Fallback. |
| `--model` | Pfad zu einer JSON-Datei | Eigenes VMAF-Modell. Ohne Angabe wird das zur Pipeline und Modellvorgabe ausgewählte Modell geladen. Ein eigenes Modell muss zu SDR/HDR und dem beabsichtigten Vergleich passen. |
| `--no-download` | Kein zusätzlicher Wert | Verhindert automatische Downloads. Benötigt lokale FFmpeg-/FFprobe-Programme, `--model` und gegebenenfalls dovi_tool. Bei portablen Startern muss auch Python bereits vorhanden sein. |
| `--download-tools` | Kein zusätzlicher Wert | Erzwingt ein frisch heruntergeladenes FFmpeg-/FFprobe-Paket statt des lokalen Builds. |

`--no-download` und `--download-tools` dürfen nicht zusammen verwendet werden. Ein eigener FFmpeg-Pfad allein verbietet keinen automatischen Ersatzdownload; dafür zusätzlich `--no-download` nutzen. uv, Git und Systemtreiber werden durch VMAF Check nicht automatisch installiert.

## Ordner

| Flag | Wert | Standard / Beschreibung |
| --- | --- | --- |
| `--work-dir` | Ordnerpfad | Gemeinsamer Arbeitsordner; wird für spätere CLI-/GUI-Nutzung gespeichert. Ohne Flag gilt der gespeicherte Ordner, andernfalls `VMAF-Arbeit` unter dem aktuellen Arbeitsverzeichnis. |
| `--temp-dir` | Ordnerpfad | Überschreibt den temporären Elternordner für diesen Lauf. Standard: `ARBEITSORDNER/Temp`. Enthält Downloads und gegebenenfalls komprimierte DV-Arbeitskopien in einem eigenen Lauf-Unterordner. |
| `--output` | Ordnerpfad | Überschreibt den Ergebnis-Elternordner für diesen Lauf. Darunter wird ein eigener `run-...`-Ordner angelegt. Ohne Flag: `ARBEITSORDNER/Ergebnisse/ENCODE-NAME/ZEITSTEMPEL_...`. |

`--output` und `--temp-dir` ändern nicht den gespeicherten gemeinsamen Arbeitsordner. Eine gegebenenfalls durch vorhandenes uv beschaffte Python-Laufzeit liegt separat in den uv-Benutzerverzeichnissen.

## Beispiele

### Vollfilm mit automatischen Angaben

```sh
xelavie-vmaf-check "Original.mkv" "Encode.mkv"
```

### Windows: 25 %, getrennte Ordner, bekannte SDR-BT.709-Quellen

```powershell
xelavie-vmaf-check "D:\Originale\Film.mkv" "E:\Encodes\Film.mkv" --percent 25 --work-dir "D:\VMAF-Arbeit" --ref-color bt709 --enc-color bt709
```

### Linux: 50 % und eigener Arbeitsordner

```sh
xelavie-vmaf-check "/mnt/originale/Film.mkv" "/mnt/encodes/Film.mkv" --percent 50 --work-dir "/mnt/vmaf-arbeit"
```

### Manueller Crop bei passend dimensionierten Dateien

```sh
xelavie-vmaf-check "Original-1920x1080.mkv" "Encode-1920x800.mkv" --crop 1920:800:0:140 --crop-encode 1920:800:0:0 --percent 25
```

### Ausschließlich lokale Werkzeuge und ein vorhandenes SDR-Modell

```sh
xelavie-vmaf-check "/mnt/originale/Film.mkv" "/mnt/encodes/Film.mkv" --no-download --ffmpeg "/opt/ffmpeg/bin/ffmpeg" --ffprobe "/opt/ffmpeg/bin/ffprobe" --model "/opt/vmaf/vmaf_v0.6.1.json"
```

### Browser-Oberfläche

```sh
xelavie-vmaf-check --gui
```

### Hilfe und Version

```sh
xelavie-vmaf-check --help
xelavie-vmaf-check --version
```

Zurück zur [README](README.md) · [Installation](INSTALLATION.md) · [uv und Git einrichten](UV_UND_GIT.md) · [Technische Details](ANLEITUNG.txt)

### DV-Renderer

| Argument | Werte / Standard | Beschreibung |
| --- | --- | --- |
| `--dv-renderer` | `optimized` (Standard), `classic` | Optimierter CPU-DV-Ablauf für unterstützte MKV-Dateien oder klassische Farbverarbeitung. Der optimierte Schnellpfad erlaubt kleine Scoreabweichungen. |
