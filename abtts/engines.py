"""Thin wrappers around mlx-audio TTS models.

The audiobook workflow uses Qwen3-TTS only. The MOSS-TTS presets remain for the research
scripts in scripts/ (benchmarks and the first A/B test).

Every engine exposes the same call: synth(text, seed) -> (mono float32 numpy, sample_rate).
Parameter names follow mlx-audio 0.6.1 (mlx_audio/tts/models/moss_tts/moss_tts.py and
mlx_audio/tts/models/qwen3_tts/qwen3_tts.py).
"""

from __future__ import annotations

import gc
from dataclasses import dataclass, field
from pathlib import Path

import mlx.core as mx
import numpy as np

# Recommended decoding settings from each model card.
# MOSS-TTS v1.5 (8B delay) and Local-Transformer v1.5 both list 1.7 / 0.8 / 25 / 1.0.
# Qwen3-TTS-12Hz-1.7B-Base generation_config.json: temperature 0.9, top_k 50, top_p 1.0,
# repetition_penalty 1.05.
MODEL_PRESETS = {
    "moss8b": {
        "repo": "luisarn/MOSS-TTS-v1.5-MLX-8bit",
        "family": "moss",
        "sampling": {
            "audio_temperature": 1.7,
            "audio_top_p": 0.8,
            "audio_top_k": 25,
            "audio_repetition_penalty": 1.0,
        },
    },
    "moss8b-bf16": {
        "repo": "OpenMOSS-Team/MOSS-TTS-v1.5",
        "family": "moss",
        "sampling": {
            "audio_temperature": 1.7,
            "audio_top_p": 0.8,
            "audio_top_k": 25,
            "audio_repetition_penalty": 1.0,
        },
    },
    "mosslocal": {
        "repo": "mlx-community/MOSS-TTS-Local-Transformer-v1.5-8bit",
        "family": "moss",
        "sampling": {
            "audio_temperature": 1.7,
            "audio_top_p": 0.8,
            "audio_top_k": 25,
            "audio_repetition_penalty": 1.0,
        },
    },
    "qwen3": {
        "repo": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
        "family": "qwen3",
        "sampling": {
            "temperature": 0.9,
            "top_k": 50,
            "top_p": 1.0,
            "repetition_penalty": 1.05,
        },
    },
    "qwen3-custom": {
        "repo": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16",
        "family": "qwen3",
        "sampling": {
            "temperature": 0.9,
            "top_k": 50,
            "top_p": 1.0,
            "repetition_penalty": 1.05,
        },
    },
    "qwen3-design": {
        "repo": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
        "family": "qwen3",
        "sampling": {
            "temperature": 0.9,
            "top_k": 50,
            "top_p": 1.0,
            "repetition_penalty": 1.05,
        },
    },
}

# MOSS emits 12.5 audio tokens per second (model card). English narration runs
# roughly 14-16 characters per second, so this budget leaves 2x headroom.
MOSS_TOKENS_PER_SECOND = 12.5
CHARS_PER_SECOND_FLOOR = 7.0


@dataclass
class Voice:
    """How the narrator voice is specified.

    ref_audio/ref_text clone a voice. speaker picks a Qwen3 CustomVoice preset.
    instruct is a style prompt (Qwen3 CustomVoice) or a voice description (Qwen3 VoiceDesign).
    With nothing set, MOSS uses its own default voice.
    """

    ref_audio: str | None = None
    ref_text: str | None = None
    speaker: str | None = None
    instruct: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class Engine:
    model: str
    voice: Voice = field(default_factory=Voice)
    sampling: dict = field(default_factory=dict)
    language: str = "English"
    repo: str | None = None
    _tts: object = None

    def __post_init__(self):
        preset = MODEL_PRESETS.get(self.model, {})
        self.repo = self.repo or preset.get("repo") or self.model
        self.family = preset.get("family") or ("qwen3" if "qwen3" in self.repo.lower() else "moss")
        self.sampling = {**preset.get("sampling", {}), **(self.sampling or {})}

    def load(self):
        if self._tts is None:
            from mlx_audio.tts import load

            self._tts = load(self.repo, lazy=True)
        return self._tts

    @property
    def sample_rate(self) -> int:
        return int(self.load().sample_rate)

    def max_tokens_for(self, text: str) -> int:
        seconds = max(len(text) / CHARS_PER_SECOND_FLOOR, 4.0) + 3.0
        return int(seconds * MOSS_TOKENS_PER_SECOND)

    def synth(self, text: str, seed: int) -> tuple[np.ndarray, int]:
        tts = self.load()
        mx.random.seed(int(seed))
        if self.family == "moss":
            kwargs = dict(
                text=text,
                language=self.language,
                max_tokens=self.max_tokens_for(text),
                **self.sampling,
            )
            if self.voice.ref_audio:
                kwargs["ref_audio"] = str(Path(self.voice.ref_audio).expanduser())
            results = tts.generate(**kwargs)
        else:
            kwargs = dict(
                text=text,
                lang_code=self.language.lower(),
                # Chunks never contain newlines; keep the whole chunk as one segment.
                split_pattern="\n\n\n",
                **self.sampling,
            )
            if self.voice.ref_audio:
                kwargs["ref_audio"] = str(Path(self.voice.ref_audio).expanduser())
                if self.voice.ref_text:
                    kwargs["ref_text"] = self.voice.ref_text
            if self.voice.speaker:
                kwargs["voice"] = self.voice.speaker
            if self.voice.instruct:
                kwargs["instruct"] = self.voice.instruct
            results = tts.generate(**kwargs)

        pieces = [to_mono(np.array(r.audio, dtype=np.float32)) for r in results]
        audio = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        mx.clear_cache()
        return audio, int(tts.sample_rate)

    def unload(self):
        self._tts = None
        gc.collect()
        mx.clear_cache()


def to_mono(audio: np.ndarray) -> np.ndarray:
    """MOSS Local v1.5 returns stereo; everything downstream is mono."""
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        channel_axis = 1 if audio.shape[1] <= 2 else 0
        return audio.mean(axis=channel_axis).astype(np.float32)
    return audio.reshape(-1).astype(np.float32)
