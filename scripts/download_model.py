"""Explicit small-model install; the running application never downloads models."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Download a local faster-whisper model. tiny.en ≈75 MB; base.en ≈145 MB.")
parser.add_argument("--model", choices=["tiny.en", "base.en", "tiny", "base"], default="tiny.en")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
print(f"Downloading {args.model} into models/. English tiny.en is about 75 MB, base.en about 145 MB.", flush=True)
from huggingface_hub import snapshot_download
path = snapshot_download(f"Systran/faster-whisper-{args.model}", local_dir=root / "models" / f"faster-whisper-{args.model}",
    allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.*", "preprocessor_config.json"])
print(f"Model ready at {path}. Set NEUAURA_WHISPER_MODEL_PATH in .env if you chose a different model.")
