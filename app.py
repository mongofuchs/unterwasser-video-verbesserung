import os
import tempfile

import cv2
import gradio as gr
import numpy as np

from enhance_video import enhance_video

TITLE = "Automatische Unterwasser-Videoverbesserung"
DESCRIPTION = (
    "Laed dein Unterwasservideo hoch und erhalte eine Version mit korrigierten Farben: "
    "Weissabgleich gegen Gruen-/Blau-Stich, Histogramm-Stretching, CLAHE-Kontrast und "
    "Saettigung. Alles laeuft lokal auf deinem Rechner, ohne Cloud, kostenlos."
)


def run(video, strength, denoise, compare, progress=gr.Progress()):
    if not video:
        raise gr.Error("Bitte zuerst ein Video hochladen.")

    out_dir = tempfile.mkdtemp(prefix="uwv_")
    output_path = os.path.join(out_dir, "verbessert.mp4")
    state = {"preview": None}

    def on_progress(frac):
        progress(frac, desc="Verarbeite Frames")

    def on_preview(pair):
        original, enhanced = pair
        original = cv2.resize(original, (960, int(960 * original.shape[0] / original.shape[1])))
        enhanced = cv2.resize(enhanced, (original.shape[1], original.shape[0]))
        state["preview"] = cv2.cvtColor(
            np.hstack([original, enhanced]), cv2.COLOR_BGR2RGB
        )

    enhance_video(
        video,
        output_path,
        strength=float(strength),
        denoise=bool(denoise),
        compare=bool(compare),
        progress_callback=on_progress,
        preview_callback=on_preview,
    )
    return output_path, state["preview"]


with gr.Blocks(title=TITLE) as demo:
    gr.Markdown(f"# {TITLE}\n{DESCRIPTION}")
    with gr.Row():
        with gr.Column():
            video_in = gr.Video(label="Unterwasservideo")
            strength = gr.Slider(0.5, 2.5, value=1.0, step=0.1,
                                 label="Verbesserungsstaerke")
            denoise = gr.Checkbox(value=False,
                                  label="Rauschreduzierung (langsamer)")
            compare = gr.Checkbox(value=False,
                                  label="Vergleichsvideo (Original | Verbessert)")
            button = gr.Button("Video verbessern", variant="primary")
        with gr.Column():
            video_out = gr.Video(label="Ergebnis")
            image_out = gr.Image(label="Vorschau: Original | Verbessert")

    button.click(run, inputs=[video_in, strength, denoise, compare],
                 outputs=[video_out, image_out])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
