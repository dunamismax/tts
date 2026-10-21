"""Download model weights into the normal Hugging Face cache.

Usage: uv run python scripts/download_models.py [core|fast|moss|bf16|all]

core is everything the workflow uses (Qwen3-TTS + Whisper, about 15 GB). fast is the
optional 8-bit Qwen3-TTS Base (about 3 GB). moss and bf16
are the MOSS-TTS models from the original comparison; they are no longer used.
"""

import sys

from huggingface_hub import snapshot_download

CORE = [
    "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
    "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16",
    "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
    "mlx-community/whisper-large-v3-turbo-asr-fp16",
]
MOSS = [
    "luisarn/MOSS-TTS-v1.5-MLX-8bit",
    "OpenMOSS-Team/MOSS-Audio-Tokenizer",
    "mlx-community/MOSS-TTS-Local-Transformer-v1.5-8bit",
    "OpenMOSS-Team/MOSS-Audio-Tokenizer-v2",
]
BF16 = ["OpenMOSS-Team/MOSS-TTS-v1.5"]
FAST = ["mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"]

GROUPS = {"core": CORE, "fast": FAST, "moss": MOSS, "bf16": BF16, "all": CORE + FAST + MOSS + BF16}

if __name__ == "__main__":
    group = sys.argv[1] if len(sys.argv) > 1 else "core"
    for repo in GROUPS[group]:
        print(f"Downloading {repo} ...", flush=True)
        path = snapshot_download(repo)
        print(f"  -> {path}", flush=True)
    print("done", flush=True)
