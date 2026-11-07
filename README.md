![Xelavie VMAF Check – Compare · Analyze · Quality](xelavie-banner.png)

# Xelavie VMAF Check

**Lokale Videoqualitätsprüfung für Windows und Linux – mit CLI, Browser-UI und Warteschlange.**

Vergleiche einen Encode mit seiner Originaldatei über den gesamten Film. Xelavie VMAF Check organisiert FFmpeg, Modelle, Crop-Erkennung und Ergebnisberichte. Deine Videos bleiben auf deinem Rechner.

**Aktueller Stand: `0.1.0-nightly.3` · Release-Kanal: `nightly` · MIT-Lizenz**

Dies ist eine Vorabversion. Die erste stabile Veröffentlichung ist als `v0.1.0` vorgesehen. Echte SDR-Prüfungen unter Windows wurden durchgeführt; vollständige HDR-/HLG-/Dolby-Vision-Videoläufe sind noch nicht validiert.

## Installation über uv (Windows und Linux)

**uv oder Git noch nicht vorhanden?** → [uv und Git unter Windows und Linux installieren](UV_UND_GIT.md).

**Voraussetzung: uv und Git sind bereits installiert und im PATH erreichbar.** Prüfen mit `uv --version` und `git --version`. Wir liefern uv nicht mit und installieren es nicht automatisch. Eine Veröffentlichung auf PyPI ist für diesen Weg nicht erforderlich.

Direkt aus dem aktuellen Standardbranch installieren und starten:

```sh
uv tool install git+https://github.com/Xelator23/Xelavie-VMAF-Check.git
xelavie-vmaf-check
```

Ohne Versionszusatz wird der aktuelle Entwicklungsstand installiert. Für die konkret veröffentlichte Nightly stattdessen:

```sh
uv tool install "git+https://github.com/Xelator23/Xelavie-VMAF-Check.git@v0.1.0-nightly.3"
```

uv richtet eine eigene Python-Umgebung ein und kann bei Bedarf eine passende Python-Version beschaffen. Falls der Startbefehl nicht gefunden wird: `uv tool update-shell` ausführen und das Terminal neu öffnen. Die CLI erhält Original und Encode als Argumente, Einstellungen als Flags. Ohne Argumente wird die Hilfe angezeigt. Die Browser-Oberfläche startet ausschließlich mit `xelavie-vmaf-check --gui`.

### Updates

Beende vorher laufende Prüfungen und die UI. Für den neuesten Stand des Standardbranches:

```sh
uv tool install --reinstall --refresh git+https://github.com/Xelator23/Xelavie-VMAF-Check.git
```

Bei einer Installation über einen Versionstag bleibst du auf diesem Stand. Um auf ein anderes Release zu wechseln, `--reinstall` verwenden und den gewünschten Tag hinter `@` angeben. Der Befehl ohne Tag wechselt zum aktuellen Entwicklungsstand.

Deinstallation: `uv tool uninstall xelavie-vmaf-check`. Einstellungen und Ergebnisse bleiben in ihren Benutzer-/Arbeitsordnern erhalten.

## Portable und optionales Wheel

Unter [Releases](https://github.com/Xelator23/Xelavie-VMAF-Check/releases/tag/v0.1.0-nightly.3) stehen weiterhin getrennte Pakete bereit:

| Variante | Download | Start |
| --- | --- | --- |
| Windows portable | `Xelavie-VMAF-Check-0.1.0-nightly.3-Windows.zip` | `vmaf-check.cmd` |
| Linux portable | `Xelavie-VMAF-Check-0.1.0-nightly.3-Linux.tar.gz` | `sh ./vmaf-check.sh` |
| Optional: uv ohne Git | `xelavie_vmaf_check-0.1.0.dev3-py3-none-any.whl` | `xelavie-vmaf-check` |

Portable benötigt Python 3.10+ oder bereits installiertes uv. Vor dem Entpacken beziehungsweise Installieren eines Release-Pakets dessen SHA256 gemäß [Installationsanleitung](INSTALLATION.md) prüfen. Kein `curl | bash`, kein `irm | iex` und keine Administratorrechte für das portable Paket.

Das Wheel ist eine zusätzliche Möglichkeit für Nutzer mit uv, aber ohne Git:

```sh
uv tool install --python 3.12 ./xelavie_vmaf_check-0.1.0.dev3-py3-none-any.whl
```

Wheel-Updates: neues Wheel herunterladen, prüfen und mit `uv tool install --reinstall --python 3.12 ./DATEINAME.whl` installieren. `0.1.0.dev3` ist die Python-Paketbezeichnung für `0.1.0-nightly.3`.

Alle Wege verwenden denselben Prüfcode und dieselbe UI. FFmpeg und Modelle werden bei Bedarf separat heruntergeladen; Treiber werden nicht installiert. Das Projekt ist noch nicht auf PyPI veröffentlicht: Der Installationsbefehl benötigt deshalb die GitHub-URL oder eine Wheel-Datei.

## Funktionen

- CLI über Dateipfade und Flags; lokale Browser-Oberfläche auf Wunsch mit `--gui`.
- Dashboard, Dateiauswahl, persistente Warteschlange und kompakte Ergebnisse.
- Fehlerhafte Aufträge halten die Warteschlange nicht auf; erfolgreiche verschwinden automatisch aus der Warteschlange und bleiben als Ergebnis erhalten.
- 100 %, 50 % oder 25 % der Frames über die gesamte Filmlänge bewerten.
- Auflösung und VMAF-Modell aus dem Encode ableiten; Referenz auf dessen aktives Bildraster skalieren.
- Automatische Erkennung schwarzer Balken, mit manuellen Crop-Optionen.
- Frameanzahl zunächst aus Videometadaten; vollständiger Scan nur bei fehlenden, ungültigen oder widersprüchlichen Angaben.
- SDR BT.709, HDR10/PQ und HLG-Pipeline; Dolby-Vision-Modi für Profile 5, 7, 8 und 10 mit dokumentierten Grenzen.
- Gemeinsamer, gespeicherter Arbeitsordner mit `Temp` und `Ergebnisse`.
- Fortschritt, Laufzeit, Restzeitschätzung sowie getrennte Vorbereitung und Messzeit. FPS beziehen sich nur auf die Messung.
- JSON-, CSV- und Protokolldateien; Ergebnisberichte können in der UI gelöscht werden.
- Original und Encode als getrennte Dateipfade; Farb-Overrides über Flags. Pfadvervollständigung übernimmt deine Shell.

## Beispielbilder

Die folgenden Bilder zeigen die echte UI mit **synthetischen Demodaten**. Die Werte sind keine Messnachweise. Die CLI-Abbildung ist eine beschriftete Beispieldarstellung.

### Dashboard

![Dashboard mit Demo-Statistik](docs/images/ui-dashboard.png)

### Warteschlange

![Warteschlange mit Demo-Fortschritt](docs/images/ui-queue.png)

### Dateiauswahl

![Dateiauswahl mit getrennten Quellordnern](docs/images/ui-files.png)

### CLI

![CLI-Pfadvorschau und Ergebnis – Beispielwerte](docs/images/cli-example.png)

## Schnellstart

Nach dem Herunterladen und Prüfen gemäß [Installationsanleitung](INSTALLATION.md), im entpackten Programmordner:

### Windows

Öffne PowerShell im entpackten Ordner. Ohne Argumente erscheint die Hilfe:

```powershell
.\vmaf-check.cmd
```

Direkter Start mit bekannten BT.709-Limited-Quellen:

```powershell
.\vmaf-check.cmd "D:\Originale\Film.mkv" "E:\Encodes\Film-1080p.mkv" --percent 25 --work-dir "D:\VMAF-Arbeit" --ref-color bt709 --enc-color bt709
```

### Linux

```sh
tar -xzf Xelavie-VMAF-Check-0.1.0-nightly.3-Linux.tar.gz
cd Xelavie-VMAF-Check
sh ./vmaf-check.sh
```

Direkter Start ohne Farb-Overrides:

```sh
sh ./vmaf-check.sh "/mnt/originale/Film.mkv" "/mnt/encodes/Film-1080p.mkv" --percent 25 --work-dir "/mnt/vmaf-arbeit"
```

`--gui` startet die Browser-Oberfläche und wird allein verwendet. Ohne Argumente oder mit `--help` erscheint die CLI-Hilfe. Es gibt keine Startauswahl und kein interaktives Eingabeformular. Ist Python 3.10+ vorhanden, geht auch `python vmaf_launcher.py` beziehungsweise `python3 vmaf_launcher.py`.

## Bedienung

**UI:** Unter „Dateiauswahl“ Original, Encode, Prüfanteil und Arbeitsordner setzen. „Prüfung starten“ startet die Warteschlange; „Zur Warteschlange“ reiht einen weiteren Vergleich ein. Wartende Aufträge können verschoben werden. „Abbrechen“ stoppt den aktuellen Lauf und pausiert die Warteschlange. Bei normalen Fehlern geht es automatisch weiter. Nach einem Neustart ist die Warteschlange zunächst pausiert.

Das Prüfprotokoll ist einklappbar und öffnet sich bei Fehlern. Fortschritt und Restzeit sind Arbeitsanzeigen, keine geschätzten VMAF-Scores. „UI beenden“ beendet den lokalen Dienst; allein das Schließen des Browser-Tabs beendet ihn nicht.

**CLI:** Die Reihenfolge ist `ORIGINAL ENCODE [Optionen]`. Pfade mit Leerzeichen in Anführungszeichen setzen. Fehlende Pflichtargumente oder ungültige Optionen führen zu einer Fehlermeldung und einem Fehlercode; es wird nichts interaktiv nachgefragt.

```sh
xelavie-vmaf-check "Original.mkv" "Encode.mkv" --percent 25
```

| Argument / Flag | Bedeutung |
| --- | --- |
| `ORIGINAL ENCODE` | Zwei Dateipfade, auch aus unterschiedlichen Ordnern/Laufwerken |
| `--percent 100`, `50` oder `25` | Prüfanteil; Standard: 100 % |
| `--work-dir "PFAD"` | Gemeinsamer Arbeitsordner für Temp und Ergebnisse |
| `--ref-color bt709 --enc-color bt709` | Bekannte SDR-BT.709-Limited-Quellwerte explizit setzen |
| `--ref-range full` / `--enc-range full` | Bekannten Full-Range-Wertebereich setzen |
| `--crop auto` | Automatische Balkenerkennung (Standard) |
| `--help` | Alle Prüfoptionen anzeigen |
| `--gui` | Browser-Oberfläche öffnen; separat verwenden |

Farbangaben bleiben ohne Overrides automatisch. Presets nur bei bekannten Quelleigenschaften setzen: Sie überschreiben vorhandene Angaben. Dateien und Optionen werden direkt an die Prüfung übergeben. Tab-Vervollständigung und Navigation erfolgen in deiner Shell, nicht in einem Formular der Anwendung.

Browser-Oberfläche starten:

```sh
xelavie-vmaf-check --gui
```

Portable unter Windows: `.\vmaf-check.cmd --gui`; unter Linux: `sh ./vmaf-check.sh --gui`.

## Vergleichsbedingungen und Grenzen

- Original und Encode brauchen dieselbe Schnittfassung, denselben Startframe und dieselbe konstante Bildrate. Es gibt keine automatische Synchronisierung oder Schnittkorrektur.
- 25 % bedeutet jedes vierte Bild über den **ganzen Film**; die Decoder lesen weiterhin alle Frames. Die Laufzeit sinkt daher nicht zwingend auf ein Viertel.
- Der Vergleich erfolgt auf der Zielauflösung des Encodes. Ein 1080p-Encode wird damit nicht als Wiedergabe auf einem gemeinsamen 4K-Raster bewertet.
- Crop ist eine Heuristik. Dunkle Szenen, Untertitel oder wechselnde Seitenverhältnisse können manuelle Einstellungen erfordern. Abweichende aktive Seitenverhältnisse werden nicht automatisch gestreckt.
- Fehlende Farbmetadaten werden nicht aus der Auflösung geraten. FFprobe liest Container/Bitstream; bleiben notwendige Angaben unbekannt, müssen bekannte Quellwerte angegeben werden. Ein Farb-Preset wandelt SDR nicht in HDR um. SDR gegen HDR ist ausgeschlossen.
- HLG wird unter einer festgelegten 1000-cd/m²-Normalisierung nach PQ umgerechnet. HDR10+ wird anhand seiner PQ-Bilder bewertet, nicht als dynamische HDR10+-Wiedergabe.
- Dolby Vision benötigt passende FFmpeg/libplacebo-Funktionen und ein funktionierendes Vulkan-Gerät samt Treiber. Profile 5/8/10 verwenden dekodierte DV-Metadaten; Profil 10 erfordert AV1.
- **Profil 7:** Im Automatikmodus erfolgt ein Kompatibilitätsvergleich nach P8.1-Konvertierung mit verworfenem Enhancement Layer. **Keine vollständige FEL-Rekonstruktion.** Ein hoher Score beweist keine gleichwertige vollständige P7-Wiedergabe. Die berücksichtigten Profilpaarungen 5/7/8/10 sind kein Nachweis erfolgreicher realer Videoläufe für jede Paarung.

Details zu Crop, Modellen, Farb-Overrides, Dolby-Vision-Modi und Offline-Betrieb stehen in [ANLEITUNG.txt](ANLEITUNG.txt).

## Voraussetzungen und Downloads

Windows benötigt PowerShell 5.1+. Linux benötigt eine passende glibc; Alpine/musl ist kein zugesichertes Ziel. Die automatischen Werkzeugdownloads berücksichtigen x64/ARM64, wobei die Verfügbarkeit passender Upstream-Builds entscheidend bleibt.

Die portablen Starter benötigen Python 3.10+ oder bereits installiertes `uv` im PATH. **uv wird weder mitgeliefert noch automatisch installiert.** Fehlt Python, kann vorhandenes uv Python 3.12 beschaffen; diese Laufzeit und ihr Cache liegen in den normalen uv-Benutzerverzeichnissen. Die Video-Arbeitsdateien verwenden weiterhin deinen gewählten Arbeitsordner.

FFmpeg/FFprobe, VMAF-Modelle und bei Bedarf `dovi_tool` werden automatisch geladen. HTTPS-Zertifikatsprüfung bleibt aktiv. Bei `--no-download` müssen alle benötigten Werkzeuge und das mit `--model` gewählte Modell lokal vorhanden sein. `--download-tools` erzwingt einen frischen FFmpeg-Build. Unterschiedliche Builds können Verhalten und Ergebnisse beeinflussen; Versionen und Modellhash werden protokolliert.

Die UI ist ausschließlich an `127.0.0.1` gebunden. Videos werden nicht hochgeladen. Berichte enthalten lokale Dateipfade – vor dem Teilen von Fehlerberichten persönliche Angaben entfernen.

## Entwicklung und Tests

Nur Python-Standardbibliothek, keine `pip`-Pakete erforderlich:

```sh
python -B -m unittest discover -s . -p "test_*.py" -v
```

Die Tests prüfen Offline-Logik, CLI, Crop-Entscheidungen, Farbmetadaten, Download-Verifikation, lokalen HTTP-Server, Warteschlange und Ergebnisverwaltung. Sie ersetzen keine echten HDR-/DV-Videoläufe. Die GitHub-Actions-Matrix prüft Windows und Linux mit Python 3.10 und 3.12.

Fehler und Verbesserungsvorschläge bitte über [Issues](https://github.com/Xelator23/Xelavie-VMAF-Check/issues) melden. Hilfreich sind Version, Betriebssystem, Vergleichsmodus und ein bereinigtes Protokoll.

## Lizenz und verwendete Projekte

Der Projektcode steht unter der [MIT-Lizenz](LICENSE). Separat heruntergeladene Programme und Modelle behalten ihre eigenen Lizenzen; siehe [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Basierend auf [Netflix VMAF](https://github.com/Netflix/vmaf), [FFmpeg](https://ffmpeg.org/), [BtbN FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds), [dovi_tool](https://github.com/quietvoid/dovi_tool), [libplacebo](https://code.videolan.org/videolan/libplacebo) und [uv](https://github.com/astral-sh/uv). Dies ist ein unabhängiges Projekt, keine Dolby-zertifizierte Prüflösung.
