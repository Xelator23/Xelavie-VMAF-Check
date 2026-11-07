# Installation: herunterladen, prüfen, lokal starten

Xelavie VMAF Check ist portabel. Es benötigt keinen Installer mit Administratorrechten und keinen Befehl wie `curl ... | bash` oder `irm ... | iex`.

Die Schritte sind getrennt: **Archiv herunterladen → SHA256 prüfen → entpacken → lokalen Starter aufrufen.** Dadurch kann heruntergeladener Skripttext nicht schon während des Downloads ausgeführt werden.

## 1. Passendes Paket herunterladen

Öffne das [Nightly-Release](https://github.com/Xelator23/Xelavie-VMAF-Check/releases/tag/nightly) im Browser und speichere das Windows-ZIP oder Linux-TAR.GZ in einem neuen, leeren Ordner. Verwende die Release-Pakete, nicht die automatisch von GitHub angebotenen „Source code“-Archive für die folgenden Prüfsummen.

Die folgenden **festen Referenzhashes gelten ausschließlich für `0.1.0-nightly.1`**, veröffentlicht am 7. November 2026:

| Paket | SHA256 |
| --- | --- |
| Windows ZIP | `0c8c151ad54c35f486375d39bd9ff6db687cd95b32c36e4dcaca0c7057e79cd5` |
| Linux TAR.GZ | `92dabc4b13af93b4d7426265418bd849401b1cfbb9abb5781e8ef1cd316b07b1` |

Bei einer Abweichung **nicht starten**. Der Tag `nightly` kann später einen anderen Stand bezeichnen; ein anderes Paket braucht seinen eigenen, geprüften Referenzhash.

## 2. Windows: prüfen und entpacken

Öffne PowerShell in dem Ordner mit dem heruntergeladenen ZIP. Dieser Block führt die Anwendung noch nicht aus:

```powershell
$ErrorActionPreference = 'Stop'
$archive = '.\Xelavie-VMAF-Check-0.1.0-nightly.1-Windows.zip'
$expected = '0c8c151ad54c35f486375d39bd9ff6db687cd95b32c36e4dcaca0c7057e79cd5'
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) {
    throw 'SHA256 stimmt nicht. Paket nicht ausführen.'
}
Expand-Archive -LiteralPath $archive -DestinationPath '.\geprueft'
Write-Host 'SHA256 stimmt. Paket nach .\geprueft entpackt.'
```

Danach kannst du die Dateien ansehen und den lokalen Starter getrennt aufrufen:

```powershell
.\geprueft\Xelavie-VMAF-Check\vmaf-check.cmd
```

## 3. Linux: prüfen und entpacken

Öffne ein Terminal im Ordner mit dem heruntergeladenen TAR.GZ. Dieser Block läuft in einer Subshell und entpackt ausschließlich bei passender Prüfsumme:

```sh
(
    set -eu
    archive='Xelavie-VMAF-Check-0.1.0-nightly.1-Linux.tar.gz'
    expected='92dabc4b13af93b4d7426265418bd849401b1cfbb9abb5781e8ef1cd316b07b1'
    actual=$(sha256sum -- "$archive")
    if [ "${actual%% *}" != "$expected" ]; then
        printf '%s\n' 'SHA256 stimmt nicht. Paket nicht ausführen.' >&2
        exit 1
    fi
    mkdir geprueft
    tar -xzf "$archive" -C geprueft
    printf '%s\n' 'SHA256 stimmt. Paket nach ./geprueft entpackt.'
)
```

Danach kannst du die Dateien ansehen und den lokalen Starter getrennt aufrufen:

```sh
sh ./geprueft/Xelavie-VMAF-Check/vmaf-check.sh
```

Kein `sudo` nötig. Existiert `geprueft` bereits, verwende für diese Anleitung einen neuen, leeren Downloadordner.

## Was passiert beim Start?

Die vorhandene Komfortfunktion zum Nachladen bleibt erhalten:

- **Python:** Vorhandenes Python 3.10+ wird bevorzugt. Fehlt es, lädt der Starter ein uv-Archiv einer festgelegten Version, prüft dessen im Starter hinterlegten SHA256 und entpackt es erst danach. uv beschafft anschließend Python. Es wird kein aus dem Netz geladener Shell-Skriptstrom ausgeführt.
- **FFmpeg/FFprobe und dovi_tool:** Archive werden über HTTPS geladen, gegen den SHA256-Digest der GitHub-Release-Metadaten geprüft und danach entpackt.
- **VMAF-Modelle:** JSON-Dateien werden über HTTPS geladen. Ihr Hash wird protokolliert; er wird derzeit nicht gegen einen fest eingebauten erwarteten Modellhash geprüft.
- Die HTTPS-Zertifikatsprüfung bleibt aktiviert. Systemtreiber werden nicht installiert.

Eine Prüfsumme ist **keine digitale Herausgebersignatur**. Wenn Archiv und Referenzhash aus derselben kompromittierten Quelle kommen, genügt dieser Vergleich nicht als Schutz. Die festen Hashes oben verhindern auch nicht, dass ein bereits verändertes README falsche Hashes liefert. GitHub-Konto und Upstream-Projekte bleiben Teil der Vertrauenskette.

## Optional: ohne automatische Downloads

Installiere Python und geeignete Werkzeuge über deine selbst gewählten vertrauenswürdigen Quellen, prüfe sie und halte ein passendes VMAF-Modell lokal bereit. Unter Linux kannst du für Python die Paketverwaltung deiner Distribution nutzen. Ein normales Distributions-FFmpeg enthält möglicherweise nicht alle benötigten VMAF-/HDR-/DV-Funktionen.

Starte dann direkt mit `--no-download`, beispielsweise für einen SDR-Vergleich:

```sh
python3 vmaf_check.py "/mnt/originale/Film.mkv" "/mnt/encodes/Film.mkv" --no-download --ffmpeg "/opt/ffmpeg/bin/ffmpeg" --ffprobe "/opt/ffmpeg/bin/ffprobe" --model "/opt/vmaf/vmaf_v0.6.1.json" --percent 25
```

Unter Windows entsprechend `python` und Windows-Pfade verwenden. Für eine P7-Konvertierung ist zusätzlich ein lokales `--dovi-tool` erforderlich. Diesen Offline-Modus über den direkten Aufruf nutzen; `--cli` und `--ui` lassen sich derzeit nicht mit zusätzlichen Starteroptionen kombinieren.

Weitere Bedienung: [README](README.md) · [technische Anleitung](ANLEITUNG.txt).
