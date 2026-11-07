# uv und Git einrichten

Diese Anleitung bereitet Windows oder Linux für die direkte Installation von Xelavie VMAF Check aus GitHub vor. **Du installierst die Voraussetzungen einmal selbst. VMAF Check installiert uv und Git nicht automatisch.**

Führe nur den Abschnitt für dein Betriebssystem aus. Die Befehle laden Pakete über Paketverwaltungen; sie führen keinen heruntergeladenen Shell-Skriptstrom aus.

## Bereits installiert?

Öffne PowerShell unter Windows oder ein Terminal unter Linux:

```sh
uv --version
git --version
```

Zeigen beide Befehle eine Versionsnummer, kannst du direkt zu [VMAF Check installieren](#vmaf-check-installieren) springen.

## Windows 10 / 11

Öffne PowerShell und prüfe, ob WinGet vorhanden ist:

```powershell
winget --version
```

Falls WinGet fehlt, installiere beziehungsweise aktualisiere **App-Installer von Microsoft** über den Microsoft Store und öffne PowerShell erneut. [Microsoft-Anleitung](https://learn.microsoft.com/en-us/windows/package-manager/winget/)

Installiere die fehlenden Programme einzeln:

```powershell
winget install --id astral-sh.uv -e --source winget
winget install --id Git.Git -e --source winget
```

Die Installationsprogramme können eine Windows-Berechtigungsabfrage anzeigen. Schließe danach das Terminal vollständig und öffne ein neues PowerShell-Fenster.

Diese Paketnamen sind in den offiziellen Anleitungen dokumentiert: [uv über WinGet](https://docs.astral.sh/uv/getting-started/installation/#winget), [Git für Windows](https://git-scm.com/install/windows).

## Linux

Wähle **eine** der folgenden Varianten passend zu deiner Distribution.

### Debian / Ubuntu

Git und pipx kommen aus der Paketverwaltung. pipx installiert uv anschließend in einer eigenen Benutzerumgebung:

```sh
sudo apt update
sudo apt install git pipx
pipx install uv
pipx ensurepath
```

Öffne danach ein neues Terminal. Für `pipx install uv` ist kein `sudo` nötig.

Falls deine Distributionsversion das Paket `pipx` nicht anbietet, folge der [offiziellen pipx-Anleitung](https://pipx.pypa.io/latest/how-to/install-pipx.html). Der Weg `pipx install uv` wird auch von [Astral dokumentiert](https://docs.astral.sh/uv/getting-started/installation/#pypi). Git empfiehlt unter Linux die [Paketverwaltung der Distribution](https://git-scm.com/install/linux).

### Fedora

```sh
sudo dnf install git uv
```

uv ist als [Fedora-Paket](https://packages.fedoraproject.org/pkgs/uv/uv/index.html) verfügbar. Öffne anschließend ein neues Terminal.

### Arch Linux

```sh
sudo pacman -Syu git uv
```

Dieser Befehl aktualisiert auch dein Arch-System. uv liegt im offiziellen [Extra-Repository](https://archlinux.org/packages/extra/x86_64/uv/). Öffne anschließend ein neues Terminal.

### Andere Distributionen

Installiere Git über die [passende Paketverwaltung](https://git-scm.com/install/linux). Für uv nutze ein Paket deiner Distribution oder vorhandenes pipx mit `pipx install uv`. Weitere Möglichkeiten nennt die [offizielle uv-Anleitung](https://docs.astral.sh/uv/getting-started/installation/), darunter direkte Release-Downloads. Die hier beschriebenen Wege benötigen keine Pipe in eine Shell.

## Installation prüfen

Im **neu geöffneten** Terminal:

```sh
uv --version
git --version
```

Beide Befehle müssen eine Versionsnummer ausgeben. Ein GitHub-Konto und eine Git-Konfiguration mit Name oder E-Mail sind zum Installieren unseres öffentlichen Projekts nicht erforderlich.

## VMAF Check installieren

Für Windows und Linux gilt derselbe Befehl. Als normaler Benutzer ausführen, ohne `sudo`:

```sh
uv tool install git+https://github.com/Xelator23/Xelavie-VMAF-Check.git
xelavie-vmaf-check
```

Das installiert den aktuellen Entwicklungsstand. Der Start bietet die Auswahl zwischen CLI und UI. Für eine feste Nightly-Version, Updates und die portablen Downloads siehe die [Installationsanleitung](INSTALLATION.md).

## Wenn ein Befehl nicht gefunden wird

| Meldung / Situation | Nächster Schritt |
| --- | --- |
| `winget` fehlt | App-Installer von Microsoft installieren/aktualisieren und PowerShell neu öffnen. |
| `uv` fehlt nach Installation mit pipx | `pipx ensurepath` ausführen und Terminal neu öffnen; falls nötig ab- und wieder anmelden. |
| `uv` oder `git` fehlt nach WinGet | Terminal vollständig schließen und neu öffnen; gegebenenfalls die übergeordnete Terminal-App oder den Editor ebenfalls neu starten. |
| Git ist vorhanden, wird aber nicht gefunden | Unter Windows `Get-Command git`, unter Linux `command -v git` prüfen. Git muss im PATH des Terminals verfügbar sein, in dem uv läuft. |
| `xelavie-vmaf-check` fehlt nach erfolgreicher Installation | `uv tool update-shell` ausführen und Terminal neu öffnen. [uv-Dokumentation](https://docs.astral.sh/uv/guides/tools/) |

## uv und Git aktuell halten

Nutze denselben Installationsweg auch für Updates:

| Installation | Aktualisierung |
| --- | --- |
| Windows / WinGet | `winget upgrade --id astral-sh.uv -e --source winget` und `winget upgrade --id Git.Git -e --source winget` |
| Debian/Ubuntu: uv über pipx | `pipx upgrade uv` |
| Debian/Ubuntu: Git über apt | `sudo apt update`, anschließend `sudo apt install --only-upgrade git` |
| Fedora | `sudo dnf upgrade git uv` |
| Arch Linux | `sudo pacman -Syu` (vollständiges Systemupdate) |

Bei Installation über eine Paketverwaltung wird uv über diese aktualisiert, statt über `uv self update`. [uv-Updatehinweise](https://docs.astral.sh/uv/getting-started/installation/#upgrading-uv)

Zurück zur [README](README.md) · [VMAF-Installationsanleitung](INSTALLATION.md)
