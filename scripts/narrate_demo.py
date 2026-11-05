"""Builds docs/demo.mp4: a narrated recording of the real Streamlit app.

Narration is synthesized locally with Kokoro (open weights TTS, Apache 2.0,
voice af_heart) via the kokoro-onnx package. Steps:

  1. pip install kokoro-onnx soundfile
     Download kokoro-v1.0.onnx and voices-v1.0.bin from
     https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0)
     into a folder, and pass it as MODEL_DIR below.
  2. python scripts/narrate_demo.py tts MODEL_DIR WORK_DIR
  3. streamlit run app.py  (no MODEL_API_KEY, so stub mode), then
     node scripts/record_narrated.js . WORK_DIR/rec WORK_DIR/durations.json docs/narration.json
  4. python scripts/narrate_demo.py mux WORK_DIR docs/demo.mp4
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARRATION = ROOT / "docs" / "narration.json"


def tts(model_dir: Path, work: Path, voice: str = "af_heart") -> None:
    import soundfile as sf
    from kokoro_onnx import Kokoro

    k = Kokoro(str(model_dir / "kokoro-v1.0.onnx"), str(model_dir / "voices-v1.0.bin"))
    work.mkdir(parents=True, exist_ok=True)
    durations = {}
    for name, text in json.loads(NARRATION.read_text(encoding="utf-8")):
        audio, sr = k.create(text, voice=voice, speed=1.0, lang="en-us")
        sf.write(work / f"{name}.wav", audio, sr)
        durations[name] = round(len(audio) / sr, 3)
        print(name, durations[name])
    (work / "durations.json").write_text(json.dumps(durations, indent=1))


def mux(work: Path, out: Path) -> None:
    video = next((work / "rec").glob("*.webm"))
    marks = json.loads((work / "rec" / "marks.json").read_text())
    vdur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]).decode())
    off = max(0.0, vdur - marks["end"])
    inputs, filt = ["-i", str(video)], []
    for i, mk in enumerate(marks["marks"], start=1):
        inputs += ["-i", str(work / f"{mk['name']}.wav")]
        ms = int((mk["t"] + off) * 1000)
        filt.append(f"[{i}:a]aresample=48000,adelay={ms}|{ms}[a{i}]")
    n = len(marks["marks"])
    filt.append("".join(f"[a{i}]" for i in range(1, n + 1))
                + f"amix=inputs={n}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[aout]")
    filt.append(f"[0:v]fps=30,format=yuv420p,fade=t=in:st=0:d=0.6,fade=t=out:st={vdur - 1:.2f}:d=1.0[vout]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", "-t", f"{vdur:.2f}", "-movflags", "+faststart", str(out)],
                   check=True)
    print("wrote", out)


if __name__ == "__main__":
    if sys.argv[1] == "tts":
        tts(Path(sys.argv[2]), Path(sys.argv[3]))
    elif sys.argv[1] == "mux":
        mux(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit(__doc__)
