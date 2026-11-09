# Separat bezogene Werkzeuge und Modelle

Die MIT-Lizenz dieses Repositorys gilt für den Xelavie-VMAF-Check-Projektcode. Sie ersetzt nicht die Lizenzbedingungen der folgenden unabhängigen Projekte. Der native HDR-Worker bündelt statisch Netflix libvmaf, zimg und graphengine. Deren Lizenztexte und festgelegte Quellen stehen unter `bin/<Plattform>/licenses/`; der reproduzierbare Build steht unter `native/`. FFmpeg, dovi_tool, MKVToolNix, Mesa und Modelle werden separat bezogen.

| Projekt | Verwendung / Lizenzinformationen |
| --- | --- |
| [Netflix VMAF](https://github.com/Netflix/vmaf) | Metrik und Modelle; Lizenzdateien im Upstream-Repository beachten. |
| [FFmpeg](https://ffmpeg.org/legal.html) | Decodierung und Filter; Lizenz hängt von den Build-Optionen ab. Die automatisch gewählten BtbN-Pakete sind GPL-Builds. |
| [BtbN FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds) | Portable FFmpeg-/FFprobe-Distribution. |
| [dovi_tool](https://github.com/quietvoid/dovi_tool) | Dolby-Vision-Vorbereitung; Upstream-Lizenz beachten. |
| [libplacebo](https://code.videolan.org/videolan/libplacebo) | HDR-/DV-Verarbeitung innerhalb geeigneter FFmpeg-Builds. |
| [zimg](https://github.com/sekrit-twc/zimg) | Farbkonvertierung innerhalb geeigneter FFmpeg-Builds. |
| [graphengine](https://github.com/sekrit-twc/graphengine) | Abhängigkeit des im HDR-Worker gebündelten zimg; Lizenztext liegt beim Worker. |
| GCC-/MinGW-Laufzeit, unter Linux glibc | Statische Laufzeitanteile im nativen Worker. Lizenzhinweise einschließlich Laufzeitausnahmen liegen ebenfalls beim Worker; dessen Quelltext und Buildskript ermöglichen den Neubau. |
| [MKVToolNix](https://mkvtoolnix.download/) | Separater GPL-Download für die Profil-7-Arbeitskopie. |
| [Mesa](https://www.mesa3d.org/) / [build-mesa](https://github.com/mmozeiko/build-mesa) | Software-Vulkan/Lavapipe; unter Windows bei Bedarf separater, SHA256-geprüfter Download. |
| [uv](https://github.com/astral-sh/uv) | Voraussetzung für die uv-Installation; optional vorhandenes Werkzeug für die portable Variante. Wird nicht mitgeliefert oder automatisch installiert. |
| [Python](https://www.python.org/psf/license/) / [python-build-standalone](https://github.com/astral-sh/python-build-standalone) | Optional heruntergeladene Laufzeit. |

Für eine eigene Weiterverteilung dieser Komponenten gelten deren jeweilige Lizenz- und Quellenhinweise. Produkt- und Projektnamen bezeichnen die jeweiligen unabhängigen Projekte und implizieren keine Verbindung oder Zertifizierung.

## Mitgelieferter DV-Renderer ab nightly.10

`bin/<Plattform>/dv/xelavie-dv-render` ist ein separater GPL-FFmpeg-Prozess mit statischem libplacebo, zimg und Shader-Compiler; Windows enthält außerdem dav1d statisch, Linux liefert libdav1d.so.7 mit. Der Linux-Build enthält auch libvmaf. Die jeweiligen Lizenztexte stehen unter `dv/licenses`. Der ROI-Layer ist MIT-lizenziert. Vollständige zugehörige Quellarchive, Änderungen, Buildkonfigurationen und Rezepte: Release-Anhang `Xelavie-DV-Renderer-0.1.0-nightly.10-Source.tar.gz` und `native/dv/`. Die MIT-Lizenz des Python-Projekts ersetzt die Lizenzen dieser separaten Komponenten nicht.
