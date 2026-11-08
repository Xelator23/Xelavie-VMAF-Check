# HDR-/DV-Prüfstand für nightly.9

Geprüft am 8. November 2026 unter Windows x64 und Ubuntu x86_64. Dies sind Kurztests, keine abgeschlossene HDR-/DV-Vollfilmvalidierung und keine Dolby-Zertifizierung.

- 113 Regressionstests: Windows vollständig erfolgreich; Linux erfolgreich mit einem übersprungenen Windows-Test.
- Portable Pakete und installiertes Wheel: nativer Worker startet, CLI-Version/Hilfe, UI-Dateien, Einstellungen und Lebenszyklus des Hintergrunddienstes geprüft.
- Native HDR-Konvertierung: gültige PQ-Bildpaare erfolgreich gemessen; unbekannte Farbangaben werden abgelehnt. Ein fehlendes zimg gilt ausdrücklich als Fehler.
- Synthetische HDR10-, HLG-, DV-P5/P8.1- und P8.1/P10-Fälle mit 100 %, 50 % und 25 % erfolgreich geprüft.
- Vollständiger CLI-Ablauf mit synthetischem P7/P10-Paar: MKVToolNix-Remux, HDR-Vorabtest, Frameprüfung und Ergebnisbericht erfolgreich auf beiden Plattformen.
- Echter P7-MEL-/AV1-P10-Filmausschnitt: zeitlich abgeglichene Bilder bei 100 % und 50 % sowie 72 Eingangsframes / 18 bewertete Frames bei 25 %. Optimierter und vollständiger Aufbereitungsweg liefern innerhalb jeder Plattform exakt gleiche Frame-Merkmale, VMAF-Werte und gepoolte Metriken.

Mesa Lavapipe auf der CPU; unter Windows Mesa 26.2.6, unter Linux Mesa 25.2.8. FFmpeg mit libplacebo 7.387.0; der Linux-Medientest verwendet einen passenden lokalen FFmpeg-Build und eine portable Mesa-Laufzeit. Systempakete und beliebige ältere FFmpeg-Builds sind damit nicht automatisch validiert.

Unterschiedliche Betriebssysteme, Mesa-/FFmpeg-Versionen und Hardware können unterschiedliche Werte erzeugen. Für reproduzierbare Vergleiche dieselbe Pipeline und dieselben protokollierten Versionen/Modelle verwenden. Profil 7 wird als P8.1-Kompatibilitätsvergleich ohne vollständige FEL-Rekonstruktion bewertet.

Die 25-%-Optimierung behält die für Bewegungsmerkmale nötigen Referenznachbarn bei. Sie ist keine Zusage für 75 % weniger Laufzeit. Das 4K-DV-Rendering auf der CPU bleibt teuer. Die zuletzt untersuchten alternativen Vulkan-Upload-/Downloadpfade werden nicht ausgeliefert.
