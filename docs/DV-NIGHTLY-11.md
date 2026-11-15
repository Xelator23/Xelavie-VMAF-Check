# Dolby-Vision-Messung auf der CPU

Der Vergleich verwendet einen 60,14 Sekunden langen Ausschnitt von *Masters of the Universe*. Das 4K-HEVC-Original wurde aus Dolby Vision Profil 7 nach 8.1 vorbereitet. Der 1080p-AV1-Encode enthält Profil 10. Das HDR-Modell bewertet bei 100 % alle 1.442 Bilder auf einem Prüfraster von 1.920 × 802 Pixeln. Referenz ist der vorherige private Stand mit optimiertem Auto-Crop.

## Vollständiger Auftrag mit verifiziertem Crop aus dem Arbeitsordner

Pro System und Build liegen zwei vollständige Läufe vor. Die Tabelle zeigt deren Mittel. Die Messzeit umfasst Dekodierung, Bildverarbeitung und Bewertung. Die Gesamtzeit enthält zusätzlich Vorbereitung und Abschluss. Der spätere Schutz vor der Wiederverwendung eines fehlgeschlagenen Rendervorgangs ist im endgültigen Erstlauf mitgeprüft.

| System | Stand | Vorbereitung | Messung | Gesamt | Mess-FPS |
|---|---|---:|---:|---:|---:|
| Windows | Bisher | 4,6 s | 102,3 s | 106,9 s | 14,10 |
| Windows | Optimiert | 3,7 s | 97,3 s | 101,1 s | 14,82 |
| Ubuntu, 8 vCPU | Bisher | 4,4 s | 290,4 s | 294,8 s | 4,97 |
| Ubuntu, 8 vCPU | Optimiert | 3,2 s | 271,3 s | 274,6 s | 5,31 |

## Erster Auftrag mit leerem Crop-Speicher

Die Vorbereitung wurde pro Stand einmal separat bis zum Start der Vollmessung gemessen. Ein weiterer vollständiger Erstlauf prüfte den endgültigen Build. Unter Ubuntu stammt diese Zeit aus einer durchgehenden Wiederholung am 14. November. Werkzeuge und Modell lagen bereits lokal vor. Die Zeit für die erstmalige Balkensuche schwankt mit der Rechnerlast.

| System | Vorbereitung bisher | Vorbereitung optimiert | Endgültiger Build, Vorbereitung | Endgültiger Build, Messung | Endgültiger Build, gesamt |
|---|---:|---:|---:|---:|---:|
| Windows | 58,6 s | 55,9 s | 55,8 s | 99,9 s | 155,8 s |
| Ubuntu, 8 vCPU | 143,9 s | 135,8 s | 170,2 s | 343,2 s | 513,4 s |

## Was der Renderer spart

Wenn alle Teilstücke der Dolby-Vision-Kurve ihren Eingangswert unverändert ausgeben, genügen für diesen Schritt die beiden vorgeschriebenen Wertebegrenzungen. Die Entscheidung prüft alle Teilstücke und Farbkomponenten. Matrizen, PQ-Umrechnung und nachfolgende Farbberechnungen laufen weiter.

Für geeignete, direkt aufeinanderfolgende P010-Bilder prüft der Renderer die Helligkeits- und Farbebenen byteweise. Er vergleicht auch Bildformat, Farbkennzeichnung und die unterstützten Metadaten einschließlich RPU. Stimmen sie überein, wird das bereits gerenderte Bild mit den aktuellen Bildzeitstempeln weitergegeben. Filmkorn, unbekannte Zusatzdaten und zeitabhängige Effekte schließen diese Wiederverwendung aus. Fehlgeschlagene Renderoperationen liefern keinen Cache-Eintrag. Die VMAF-Bewertung behält jedes vorgesehene Bild und seine zeitlichen Nachbarn.

## Gegenprobe an einer zweiten Filmstelle

Der zweite Ausschnitt zeigt eine bewegte Filmszene. Jede Variante lief zweimal in umgekehrter Reihenfolge. Die Zahlen umfassen hier den Start der Decoder und die Messung des Ausschnitts.

| System | Anteil | Verarbeitete Bilder | Bisher | Optimiert |
|---|---:|---:|---:|---:|
| Windows | 100 % | 240 | 14,34 s | 14,49 s |
| Windows | 50 % | 96 | 6,28 s | 6,22 s |
| Windows | 25 % | 240 | 9,74 s | 9,75 s |
| Ubuntu, 8 vCPU | 100 % | 240 | 38,09 s | 38,00 s |
| Ubuntu, 8 vCPU | 50 % | 96 | 15,60 s | 15,51 s |
| Ubuntu, 8 vCPU | 25 % | 240 | 25,89 s | 25,83 s |

## Prüfung der Ergebnisse

- Windows. VMAF-Mittelwert 85,969078. Alle Merkmale und alle Einzelbild-Scores der 1.442 Filmbilder stimmen mit dem vorherigen privaten Build überein. Auf 396 weiteren Ausgabebildern wurden alle 16-Bit-Ebenen per SHA-256 verglichen. Abgedeckt sind P5, P8.1, P8.4, P10, vorbereitetes P7 und reale Filmstellen. Bei 24 synthetischen Bildern mit konstanten Pixeln führten gleichbleibende DV-Metadaten zu 22 Wiederverwendungen. Wechselnde Metadaten alle vier Bilder ergaben 17. Beide Bildfolgen stimmen byteweise mit der bisherigen Ausgabe überein.
- Ubuntu, 8 vCPU. VMAF-Mittelwert 85,969068. Alle Merkmale und alle Einzelbild-Scores der 1.442 Filmbilder stimmen mit dem vorherigen privaten Build überein. Auf 396 weiteren Ausgabebildern wurden alle 16-Bit-Ebenen per SHA-256 verglichen. Abgedeckt sind P5, P8.1, P8.4, P10, vorbereitetes P7 und reale Filmstellen. Bei 24 synthetischen Bildern mit konstanten Pixeln führten gleichbleibende DV-Metadaten zu 22 Wiederverwendungen. Wechselnde Metadaten alle vier Bilder ergaben 17. Beide Bildfolgen stimmen byteweise mit der bisherigen Ausgabe überein.

Referenz-Crop, Encode-Crop, Prüfraster und Stichproben stimmen überein. Die Prüfsumme der P7-Vorbereitung ist identisch. Die Funktionstests und der native Regressionstest mit wechselnden DV-Metadaten liefen auf beiden Plattformen durch. Die Gleichheitsprüfung bezieht sich jeweils auf den bisherigen Build derselben Plattform.

Die separate Übergabe von Referenz und Encode über zwei Betriebssystem-Pipes wurde ebenfalls geprüft. In den vollständigen Läufen brachte sie auf keiner Plattform einen belastbaren Zeitgewinn. Der private Build verwendet deshalb den bisherigen Transport.

Die Dauer hängt vom Material und Rechner ab. Die beiden geprüften Ausschnitte erlauben keine belastbare Hochrechnung auf einen vollständigen Film. Das Ziel einer Gesamtzeit innerhalb der Filmlaufzeit bleibt offen.
