# unterwasser-video-verbesserung
Tauch Videos zum leben erwecken mit allen Farben ....

Automatisches Tool zur lokalen Verbesserung von Unterwasservideos.
Pro Frame kombinieren:

- **Histogramm-Stretching** pro Farbkanal (reduziert Gruen-/Blauschleier)
- **Weissabgleich** (Gray-World mit begrenzten Gains)
- **CLAHE** auf dem Helligkeitskanal (Kontrast in trueben Regionen)
- **Saettigungs-Boost** fuer natuerlichere Farben

Die Ausgabe wird als H.264-MP4 mit erhaltener Audiospur geschrieben.
Keine Cloud, keine Modelle, keine Kosten – nur OpenCV und ein
mitgelieferter ffmpeg-Build via `imageio-ffmpeg`.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Start

```powershell
python app.py
```

Danach im Browser oeffnen: http://127.0.0.1:7860

(Linux/macOS: `.venv/bin/activate` statt `.venv\Scripts\Activate.ps1`.)

## Bedienung

1. Video hochladen (z. B. `.mp4`, `.mov`, `.avi`)
2. Verbesserungsstaerke waehlen (1.0 = Standard; hoehere Werte gegen starke Schleier)
3. Optional: Rauschreduzierung (langsam, dafuer sauberer) oder Vergleichsvideo
   (Original | Verbessert nebeneinander)
4. „Video verbessern“ klicken – Ergebnis und Vorher-/Nachher-Vorschau erscheinen
   auf der rechten Seite

Lange Videos koennen einige Minuten dauern (Faustregel: 2–5x Videolaenge bei
hoher Aufloesung; Rauschreduzierung deutlich laenger).
