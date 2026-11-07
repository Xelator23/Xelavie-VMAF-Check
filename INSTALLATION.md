# Installation: uv direkt aus GitHub oder Portable

Beide Varianten verwenden dieselbe CLI, UI, Warteschlange und gespeicherte Konfiguration. uv wird **nicht mitgeliefert und nicht automatisch installiert**.

- **Portable:** Python 3.10+ oder bereits installiertes uv im PATH erforderlich.
- **uv direkt aus GitHub:** uv und Git müssen bereits installiert sein. Prüfen mit `uv --version` und `git --version`.
- **Optionales Wheel:** Bereits installiertes uv erforderlich; Git wird dafür nicht benötigt.

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
uv tool install "git+https://github.com/Xelator23/Xelavie-VMAF-Check.git@v0.1.0-nightly.2"
```

uv richtet eine eigene Python-Umgebung ein und kann bei Bedarf eine passende Python-Version beschaffen. Falls der Startbefehl nicht gefunden wird: `uv tool update-shell` ausführen und das Terminal neu öffnen. Direkter Start: `xelavie-vmaf-check --ui` oder `xelavie-vmaf-check --cli`.

### Updates

Beende vorher laufende Prüfungen und die UI. Für den neuesten Stand des Standardbranches:

```sh
uv tool install --reinstall --refresh git+https://github.com/Xelator23/Xelavie-VMAF-Check.git
```

Bei einer Installation über einen Versionstag bleibst du auf diesem Stand. Um auf ein anderes Release zu wechseln, `--reinstall` verwenden und den gewünschten Tag hinter `@` angeben. Der Befehl ohne Tag wechselt zum aktuellen Entwicklungsstand.

Deinstallation: `uv tool uninstall xelavie-vmaf-check`. Einstellungen und Ergebnisse bleiben in ihren Benutzer-/Arbeitsordnern erhalten.

## Alternative: Portable oder Wheel herunterladen

Die folgenden Download- und Prüfsummenschritte gelten für die Release-Pakete. Für die oben beschriebene Git-Installation ist kein manueller Archiv- oder Wheel-Download nötig.

### 1. Dateien herunterladen

Öffne [Release 0.1.0-nightly.2](https://github.com/Xelator23/Xelavie-VMAF-Check/releases/tag/v0.1.0-nightly.2) und lade `SHA256SUMS.txt` sowie eines dieser Pakete in einen neuen, leeren Ordner:

| Variante | Datei |
| --- | --- |
| Windows portable | `Xelavie-VMAF-Check-0.1.0-nightly.2-Windows.zip` |
| Linux portable | `Xelavie-VMAF-Check-0.1.0-nightly.2-Linux.tar.gz` |
| uv für Windows und Linux | `xelavie_vmaf_check-0.1.0.dev2-py3-none-any.whl` |

Die automatisch von GitHub angebotenen „Source code“-Archive sind andere Dateien. Diese Anleitung verwendet die ausdrücklich aufgeführten Release-Pakete. Es wird kein heruntergeladener Skripttext direkt an eine Shell weitergereicht.

### 2. Prüfsumme kontrollieren

### Windows / PowerShell

Setze `$package` auf genau die heruntergeladene Datei (ZIP oder Wheel):

```powershell
$package = 'Xelavie-VMAF-Check-0.1.0-nightly.2-Windows.zip'
$entries = @(Get-Content -LiteralPath '.\SHA256SUMS.txt' | Where-Object { $_ -match ('^[0-9a-f]{64}  ' + [regex]::Escape($package) + '$') })
if ($entries.Count -ne 1) { throw 'Keine eindeutige SHA256 für dieses Paket.' }
$expected = $entries[0].Substring(0,64)
$actual = (Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'SHA256 stimmt nicht. Paket nicht ausführen.' }
Write-Host 'SHA256 stimmt.'
```

### Linux

Setze `package` auf die heruntergeladene Datei (TAR.GZ oder Wheel):

```sh
(
  set -eu
  package='Xelavie-VMAF-Check-0.1.0-nightly.2-Linux.tar.gz'
  expected=$(awk -v file="$package" '$2 == file {print $1}' SHA256SUMS.txt)
  [ "${#expected}" -eq 64 ] || { echo 'Keine eindeutige SHA256 für dieses Paket.' >&2; exit 1; }
  printf '%s  %s\n' "$expected" "$package" | sha256sum --check -
)
```

**Nur nach erfolgreicher Prüfung fortfahren.**

### 3a. Portable starten

Windows:

```powershell
Expand-Archive -LiteralPath '.\Xelavie-VMAF-Check-0.1.0-nightly.2-Windows.zip' -DestinationPath '.\geprueft'
.\geprueft\Xelavie-VMAF-Check\vmaf-check.cmd
```

Linux:

```sh
mkdir geprueft && tar -xzf Xelavie-VMAF-Check-0.1.0-nightly.2-Linux.tar.gz -C geprueft && sh ./geprueft/Xelavie-VMAF-Check/vmaf-check.sh
```

Fehlt Python, darf nur vorhandenes uv Python beschaffen. Fehlen beide Voraussetzungen, zeigt der Starter einen Hinweis und beendet sich.

### 3b. Optionales Wheel mit vorhandenem uv installieren

Nach erfolgreicher Prüfung des **Wheels** unter Windows oder Linux:

```sh
uv tool install --python 3.12 ./xelavie_vmaf_check-0.1.0.dev2-py3-none-any.whl
xelavie-vmaf-check
```

Der Start bietet die gewohnte Auswahl CLI/UI. `xelavie-vmaf-check --ui` und `xelavie-vmaf-check --cli` starten die jeweilige Oberfläche direkt. Falls der Befehl nicht gefunden wird, `uv tool update-shell` ausführen und ein neues Terminal öffnen.

Die Python-Paketversion `0.1.0.dev2` entspricht `0.1.0-nightly.2`. Es gibt aktuell **keine Veröffentlichung auf PyPI**. Bei dieser optionalen Variante wird der Pfad zur Wheel-Datei verwendet; alternativ ist die direkte GitHub-Installation oben möglich.

### Updates der Downloadpakete und Deinstallation

Laufende Prüfungen und UI vorher beenden. Neues Wheel und zugehörige Prüfsummen aus dem gewünschten Release herunterladen, prüfen, anschließend (DATEINAME ersetzen):

```sh
uv tool install --reinstall --python 3.12 ./DATEINAME.whl
```

`uv tool upgrade xelavie-vmaf-check` ist für diese lokale Wheel-Installation nicht der Updateweg. Zur Deinstallation:

```sh
uv tool uninstall xelavie-vmaf-check
```

Einstellungen, Warteschlange und Ergebnisdateien bleiben erhalten. Beide Installationsvarianten nutzen dieselben Benutzer-Einstellungen; nicht gleichzeitig mit derselben Warteschlange starten. Portable Updates werden in einen neuen Programmordner entpackt.

## Was passiert beim Start?

Die vorhandene Komfortfunktion zum Nachladen bleibt erhalten:

- **Python/uv:** Die portable Variante bevorzugt Python 3.10+. Fehlt Python, darf der Starter nur ein bereits installiertes uv verwenden. uv kann dann Python 3.12 in seinen Benutzerverzeichnissen beschaffen. Fehlen beide, endet der Start mit einem verständlichen Hinweis. **uv selbst wird nie automatisch installiert oder heruntergeladen.**
- **FFmpeg/FFprobe und dovi_tool:** Archive werden über HTTPS geladen, gegen den SHA256-Digest der GitHub-Release-Metadaten geprüft und danach entpackt.
- **VMAF-Modelle:** JSON-Dateien werden über HTTPS geladen. Ihr Hash wird protokolliert; er wird derzeit nicht gegen einen fest eingebauten erwarteten Modellhash geprüft.
- Die HTTPS-Zertifikatsprüfung bleibt aktiviert. Systemtreiber werden nicht installiert.

Eine Prüfsumme ist **keine digitale Herausgebersignatur**. Wenn Archiv und Referenzhash aus derselben kompromittierten Quelle kommen, genügt dieser Vergleich nicht als Schutz. GitHub-Konto und Upstream-Projekte bleiben Teil der Vertrauenskette.

## Optional: ohne automatische Downloads

Installiere Python und geeignete Werkzeuge über deine selbst gewählten vertrauenswürdigen Quellen, prüfe sie und halte ein passendes VMAF-Modell lokal bereit. Unter Linux kannst du für Python die Paketverwaltung deiner Distribution nutzen. Ein normales Distributions-FFmpeg enthält möglicherweise nicht alle benötigten VMAF-/HDR-/DV-Funktionen.

Starte dann direkt mit `--no-download`, beispielsweise für einen SDR-Vergleich:

```sh
python3 vmaf_check.py "/mnt/originale/Film.mkv" "/mnt/encodes/Film.mkv" --no-download --ffmpeg "/opt/ffmpeg/bin/ffmpeg" --ffprobe "/opt/ffmpeg/bin/ffprobe" --model "/opt/vmaf/vmaf_v0.6.1.json" --percent 25
```

Unter Windows entsprechend `python` und Windows-Pfade verwenden. Für eine P7-Konvertierung ist zusätzlich ein lokales `--dovi-tool` erforderlich. Diesen Offline-Modus über den direkten Aufruf nutzen; `--cli` und `--ui` lassen sich derzeit nicht mit zusätzlichen Starteroptionen kombinieren.

Weitere Bedienung: [README](README.md) · [technische Anleitung](ANLEITUNG.txt).
