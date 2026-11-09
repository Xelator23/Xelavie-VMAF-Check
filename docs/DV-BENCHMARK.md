# Direkter Vergleich mit nightly.9

Gleicher realer P7/P10-Filmausschnitt, 288 Frames (12,012 s), 25 % = 72 bewertete Bilder; 1920×802; CPU-Mesa; VMAF-Threads 2, Mesa automatisch. P7 als P8.1 ohne Enhancement Layer. Pro Plattform drei abwechselnde Paare, Median. Werkzeuge/Modelle vorhanden, identische feste Crops, keine Download- oder automatische Crop-Suchzeit.

| Messung | nightly.9 | Optimiert | Weniger Zeit |
| --- | ---: | ---: | ---: |
| Windows Messphase | 24,547 s | 13,812 s | 43,73 % |
| Windows Vorbereitung + Messung | 31,360 s | 19,937 s | 36,43 % |
| Linux Messphase | 66,996 s | 35,040 s | 47,70 % |
| Linux Vorbereitung + Messung | 75,093 s | 41,655 s | 44,53 % |

Windows i7-13700KF, Mesa 26.2.6/LLVM 23; Ubuntu-Builder mit 8 vCPUs, Mesa 25.2.8/LLVM 20. Kein Vergleich der Betriebssystemgeschwindigkeit auf gleicher Hardware.

Mittlerer VMAF Windows 87,181492 → 87,180751, Linux 87,181543 → 87,180778. Maximaler Einzelbildunterschied 0,015171 / 0,014590. Wiederholungen je Variante identisch, gleiche Frames und Nachbarbilder. 100-%-Kontrolle (72 Frames, ein Paar): 42,05 % / 46,70 % weniger Messzeit. Kein Vollfilmtest oder Echtzeitversprechen.

Zusätzliche vorherige Profiltests: P5/P8.1/P8.4/P10/P7-Kompatibilität, 15 Paarungen mit 100/50/25 %, plus Farbverläufe. Größter Einzelbildunterschied bei den Verlaufsmustern 0,051003 Punkte. Der Schnellpfad ist eine experimentelle Näherung; diese beobachteten Werte sind keine allgemeine Fehlergarantie. Kritische Pixel nutzen den vollständigen ursprünglichen Umrechnungsweg. Andere Inhalte können abweichen. Für klassische Farbberechnung `--dv-renderer classic`.
