import os
import tempfile

import cv2
import gradio as gr
import numpy as np

from enhance_video import enhance_video

TITLE = "Unterwasser-Videoverbesserung"
DESCRIPTION = (
    "Achte auf deinen nächsten Tauchgang: Lade dein Unterwasservideo hoch und erhalte "
    "eine Version mit korrigierten Farben – Weissabgleich gegen Grün-/Blau-Stich, "
    "Histogramm-Stretching, CLAHE-Kontrast und Sättigung. Alles läuft lokal auf deinem "
    "Rechner, ohne Cloud, kostenlos."
)

HEADER_HTML = """
<div class="ocean-scene">
  <div class="rays"></div>
  <div class="bubble b1"></div><div class="bubble b2"></div>
  <div class="bubble b3"></div><div class="bubble b4"></div>
  <div class="bubble b5"></div><div class="bubble b6"></div>
  <span class="fish f1" style="animation-delay: 0s;  top: 30%;">🐠</span>
  <span class="fish f2" style="animation-delay: -8s; top: 55%; font-size: 34px;">🐡</span>
  <span class="fish f3" style="animation-delay: -16s; top: 18%; font-size: 22px;">🐟</span>
  <span class="fish f4" style="animation-delay: -4s; top: 72%; font-size: 26px;">🦈</span>
  <span class="fish f5" style="animation-delay: -21s; top: 42%; font-size: 38px;">🐬</span>
  <div class="monster m1" style="animation-delay: -3s;  top: 64%; font-size: 46px;">🦑</div>
  <div class="monster m2" style="animation-delay: -15s; top: 82%; font-size: 42px;">🐙</div>
  <div class="monster m3" style="animation-delay: -9s;  top: 10%; font-size: 52px;">🐋</div>
  <div class="monster m4" style="animation-delay: -20s; top: 44%; font-size: 44px;">🦕</div>
  <div class="diver">🤿</div>
  <div class="seabed">
    <span class="coral c1">🪸</span>
    <span class="coral c2">🌿</span>
    <span class="coral c3">🪸</span>
    <span class="coral c4">🐚</span>
    <span class="coral c5">🪸</span>
    <span class="coral c6">🦀</span>
  </div>
  <div class="scene-title">
    <h1>🤿 {title}</h1>
    <p>Corals, Fische &amp; Farben – dein Video in echtem Riff-Look</p>
  </div>
</div>
""".format(title=TITLE)

FOOTER_HTML = """
<div class="ocean-footer">🫧 Läuft zu 100% lokal auf deinem Rechner – kein Cloud-Atemzug &middot; 🐠
Nur OpenCV &amp; ffmpeg &middot; 🐚 Kostenlos &amp; quelloffen</div>
"""

OCEAN_CSS = """
:root {
  --deep-1: #051d2e;
  --deep-2: #08344f;
  --deep-3: #0d4d6e;
  --aqua: #4dd6ff;
  --aqua-soft: rgba(77, 214, 255, 0.18);
  --coral: #ff7f50;
  --sand: #ffd166;
  --shell: #f6e7cf;
  --ink: #e8f6ff;
}

/* ---------- Szene ---------- */
.ocean-scene {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  min-height: 230px;
  background: linear-gradient(180deg, #0a86b4 0%, #086a9c 18%, var(--deep-3) 55%, var(--deep-1) 100%);
  border: 1px solid var(--aqua-soft);
  box-shadow: inset 0 0 60px rgba(0, 20, 35, 0.55), 0 10px 30px rgba(0, 0, 0, 0.35);
  margin-bottom: 6px;
}
.ocean-scene .scene-title { position: relative; z-index: 5; text-align: center; padding: 34px 20px 56px; }
.ocean-scene .scene-title h1 {
  margin: 0; color: var(--ink); font-size: 2em; letter-spacing: 0.02em;
  text-shadow: 0 2px 14px rgba(0, 30, 50, 0.8), 0 0 24px rgba(77, 214, 255, 0.35);
}
.ocean-scene .scene-title p { margin: 6px 0 0; color: #bfe6f5; }

/* Lichtstrahlen */
.rays {
  position: absolute; inset: -20%; z-index: 1; pointer-events: none; opacity: 0.5;
  background:
    linear-gradient(115deg, transparent 38%, rgba(255,255,255,0.10) 40%, transparent 43%),
    linear-gradient(115deg, transparent 58%, rgba(255,255,255,0.08) 60%, transparent 63%),
    linear-gradient(105deg, transparent 74%, rgba(255,255,255,0.06) 76%, transparent 80%);
  animation: rays-drift 9s ease-in-out infinite alternate;
}
@keyframes rays-drift { from { transform: translateX(-3%) skewX(-2deg); } to { transform: translateX(3%) skewX(2deg); } }

/* Blasen steigen auf */
.bubble {
  position: absolute; bottom: -30px; z-index: 2; border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle at 32% 28%, rgba(255,255,255,0.85), rgba(255,255,255,0.12) 62%, rgba(255,255,255,0.04));
  box-shadow: inset 0 0 6px rgba(255,255,255,0.4), 0 0 8px rgba(120,220,255,0.25);
  animation: rise 11s ease-in infinite;
}
.bubble.b1 { left: 6%;  width: 14px; height: 14px; animation-duration: 9s;  }
.bubble.b2 { left: 18%; width: 8px;  height: 8px;  animation-delay: -4.5s; }
.bubble.b3 { left: 34%; width: 18px; height: 18px; animation-delay: -2.5s; animation-duration: 13s; }
.bubble.b4 { left: 58%; width: 10px; height: 10px; animation-delay: -7s;  }
.bubble.b5 { left: 76%; width: 16px; height: 16px; animation-delay: -1s;  animation-duration: 10s; }
.bubble.b6 { left: 90%; width: 7px;  height: 7px;  animation-delay: -5.5s; }
@keyframes rise {
  0%   { transform: translateY(0) translateX(0) scale(0.6); opacity: 0; }
  12%  { opacity: 0.9; }
  50%  { transform: translateY(-120px) translateX(10px) scale(1); }
  100% { transform: translateY(-245px) translateX(-8px) scale(1.15); opacity: 0; }
}

/* Fische schwimmen durch */
.fish { position: absolute; z-index: 3; left: -70px; font-size: 28px; pointer-events: none;
        filter: drop-shadow(0 4px 6px rgba(0, 20, 40, 0.5));
        animation: swim 26s linear infinite; }
@keyframes swim {
  0%   { transform: translateX(0) rotate(2deg); }
  45%  { transform: translateX(58vw) rotate(-3deg) translateY(-14px); }
  100% { transform: translateX(118vw) rotate(2deg); }
}

/* Tiefseekreaturen mit Leuchtorgan-Schimmer, schwimmen von rechts */
.monster {
  position: absolute; z-index: 3; right: -110px; pointer-events: none;
  filter: drop-shadow(0 0 14px rgba(0, 255, 210, 0.55)) drop-shadow(0 6px 10px rgba(0, 20, 40, 0.6));
  animation: swim-rtl 44s linear infinite;
}
@keyframes swim-rtl {
  0%   { transform: translateX(0) scaleX(-1) translateY(0); }
  45%  { transform: translateX(-62vw) scaleX(-1) translateY(-16px); }
  100% { transform: translateX(-130vw) scaleX(-1) translateY(6px); }
}

/* Taucher schwebt */
.diver {
  position: absolute; z-index: 4; right: 8%; bottom: 34%; font-size: 40px; pointer-events: none;
  filter: drop-shadow(0 6px 10px rgba(0, 20, 40, 0.6));
  animation: hover-dive 7s ease-in-out infinite alternate;
}
@keyframes hover-dive {
  from { transform: translateY(0) rotate(-8deg); }
  to   { transform: translateY(-18px) rotate(10deg); }
}

/* Meeresboden mit Korallen */
.seabed {
  position: absolute; bottom: 0; left: 0; right: 0; z-index: 4; height: 46px;
  background: linear-gradient(180deg, rgba(244, 225, 181, 0.06), rgba(20, 50, 70, 0.55));
  border-top: 2px solid rgba(244, 225, 181, 0.25);
  display: flex; align-items: flex-end; gap: 26px; padding: 0 5%;
  pointer-events: none;
}
.coral { font-size: 30px; transform-origin: bottom center; animation: sway 5s ease-in-out infinite alternate; }
.coral.c2 { font-size: 36px; animation-delay: -1.6s; }
.coral.c3 { animation-delay: -2.8s; }
.coral.c4 { animation-delay: -0.8s; transform-origin: 60% 90%; animation-duration: 7s; }
.coral.c5 { animation-delay: -3.6s; font-size: 26px; }
@keyframes sway {
  from { transform: rotate(-5deg); }
  to   { transform: rotate(6deg); }
}

/* ---------- Panels als Muschel-/Nacre-Karten ---------- */
.gr-panel, .block {
  background: linear-gradient(160deg, rgba(9, 45, 70, 0.82), rgba(6, 30, 48, 0.9)) !important;
  border: 1px solid rgba(120, 220, 255, 0.22) !important;
  box-shadow: 0 8px 26px rgba(0, 10, 20, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
  border-radius: 18px !important;
  color: var(--ink);
}
/* Perlmutt-Glanz oben */
.gr-panel::before, .block::before {
  content: ""; position: absolute; inset: 0; border-radius: 18px; pointer-events: none;
  background: linear-gradient(120deg, rgba(255,255,255,0.07) 0%, transparent 30%, transparent 70%, rgba(246, 231, 207, 0.05) 100%);
}

body, .gradio-container { background: linear-gradient(180deg, var(--deep-2), var(--deep-1)) !important; color: var(--ink) !important; }

label, .label-wrap, span.label { color: var(--ink) !important; }

/* ---------- Videofenster = Tauchmaske ---------- */
.mask-frame {
  border: 12px solid #101d29 !important;
  border-radius: 46% 46% 12% 12% / 46% 46% 8% 8% !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.55), inset 0 2px 14px rgba(150, 230, 255, 0.25),
              0 0 0 3px rgba(120, 200, 235, 0.35) !important;
  overflow: hidden !important;
  position: relative;
  background: #04121d;
}
.mask-frame::after {
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 42%; pointer-events: none;
  border-radius: 40% 40% 0 0 / 40% 40% 0 0;
  background: linear-gradient(118deg, transparent 46%, rgba(210, 240, 255, 0.10) 50%, transparent 56%);
}
.mask-frame video { width: 100% !important; height: auto !important; display: block; }
.mask-frame video::-webkit-media-controls-panel {
  background-image: linear-gradient(transparent, rgba(4, 18, 29, 0.92)) !important;
}
.mask-frame video::-webkit-media-controls-play-button,
.mask-frame video::-webkit-media-controls-mute-button,
.mask-frame video::-webkit-media-controls-toggle-closed-captions-button { opacity: 1; }
/* Gradio-Controls interaktiv lassen */
.mask-frame a, .mask-frame button, .mask-frame .icon-button {
  pointer-events: auto !important;
}
.mask-label { display: block; text-align: center; margin-bottom: 6px; color: var(--aqua); font-weight: 600; letter-spacing: 0.04em; }

/* ---------- 3D-Tauchtank-Button ---------- */
.btn-tank {
  background: linear-gradient(180deg, #ffd98a 0%, #ffb84d 45%, #f2a03d 100%) !important;
  color: #2b1a05 !important;
  border: 2px solid #d98f2b !important;
  border-radius: 16px !important;
  font-size: 1.15em !important;
  font-weight: 700 !important;
  letter-spacing: 0.03em;
  padding: 14px 18px !important;
  box-shadow:
    0 7px 0 #b87333,
    0 12px 24px rgba(0, 0, 0, 0.5),
    inset 0 3px 8px rgba(255, 255, 255, 0.65),
    inset 0 -4px 10px rgba(160, 90, 20, 0.45) !important;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.55);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.btn-tank:hover { filter: brightness(1.06); }
.btn-tank:active {
  transform: translateY(6px);
  box-shadow:
    0 1px 0 #b87333,
    0 4px 10px rgba(0, 0, 0, 0.45),
    inset 0 3px 8px rgba(255, 255, 255, 0.5),
    inset 0 -2px 6px rgba(160, 90, 20, 0.5) !important;
}

/* Sekundaere Elemente im Aqua-Look */
.btn-aux {
  background: linear-gradient(180deg, rgba(77, 214, 255, 0.16), rgba(77, 214, 255, 0.06)) !important;
  border: 1px solid rgba(120, 220, 255, 0.4) !important;
  color: var(--ink) !important;
  border-radius: 14px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 12px rgba(0, 20, 40, 0.4) !important;
}

/* Slider = Tiefenmesser */
input[type="range"] { accent-color: var(--coral); }

/* Footer */
.ocean-footer {
  text-align: center; padding: 14px; margin-top: 10px; color: #9fc9dd;
  border-top: 1px solid rgba(120, 220, 255, 0.18);
  font-size: 0.92em;
}
"""


def run(video, strength, denoise, compare, progress=gr.Progress()):
    if not video:
        raise gr.Error("Benötigt Ausrüstung: bitte zuerst ein Video hochladen. 🤿")

    out_dir = tempfile.mkdtemp(prefix="uwv_")
    output_path = os.path.join(out_dir, "verbessert.mp4")
    state = {"preview": None}

    def on_progress(frac, desc=None):
        progress(frac, desc=desc or "Verarbeite Frames")

    def on_preview(pair):
        original, enhanced = pair
        original = cv2.resize(original, (960, int(960 * original.shape[0] / original.shape[1])))
        enhanced = cv2.resize(enhanced, (original.shape[1], original.shape[0]))
        state["preview"] = cv2.cvtColor(
            np.hstack([original, enhanced]), cv2.COLOR_BGR2RGB
        )

    try:
        enhance_video(
            video,
            output_path,
            strength=float(strength),
            denoise=bool(denoise),
            compare=bool(compare),
            progress_callback=on_progress,
            preview_callback=on_preview,
        )
    except RuntimeError as e:
        detail = str(e).strip().splitlines()[-3:]
        raise gr.Error("Tauchgang abgebrochen (ffmpeg): " + " | ".join(detail))
    except OSError as e:
        raise gr.Error(f"Video konnte nicht verarbeitet werden: {e}")
    except Exception as e:
        raise gr.Error(f"Unerwarteter Tauchunfall: {type(e).__name__} – {str(e)[-200:]}")

    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise gr.Error("Ergebnisvideo fehlt oder ist leer – bitte Konsole prüfen.")
    return output_path, state["preview"]


with gr.Blocks(title=TITLE) as demo:
    gr.HTML(HEADER_HTML)
    with gr.Row():
        with gr.Column():
            gr.HTML('<span class="mask-label">🫧 Ausrüstung</span>')
            video_in = gr.Video(label="Unterwasservideo hochladen", show_label=False,
                                 elem_classes="mask-frame")
            strength = gr.Slider(0.5, 2.5, value=1.0, step=0.1,
                                 label="🎚 Atemregler – Verbesserungsstärke")
            denoise = gr.Checkbox(value=False,
                                  label="🐚 Muschel-Filter – Rauschreduzierung (langsam, dafür sauber)",
                                  elem_classes="btn-aux")
            compare = gr.Checkbox(value=False,
                                  label="🥽 Vergleichsmaske (Original | Verbessert)",
                                  elem_classes="btn-aux")
            button = gr.Button("🤿 Abtauchen & Video verbessern", variant="primary",
                               elem_classes="btn-tank")
        with gr.Column():
            gr.HTML('<span class="mask-label">🪸 Fundstücke</span>')
            video_out = gr.Video(label="Ergebnis", show_label=False,
                                  elem_classes="mask-frame")
            image_out = gr.Image(label="Vorschau: Original | Verbessert", show_label=False,
                                 elem_classes="mask-frame")
    gr.HTML(FOOTER_HTML)

    button.click(run, inputs=[video_in, strength, denoise, compare],
                 outputs=[video_out, image_out])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860,
                css=OCEAN_CSS, theme=gr.themes.Soft(
                    primary_hue="orange", secondary_hue="cyan", neutral_hue="slate"))
