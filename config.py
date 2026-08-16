"""Immutable deployment configuration."""
from pathlib import Path
import os

APP_VERSION = "1.0.0"
MODEL_REPO = "Misha24-10/F5-TTS_RUSSIAN"
# Full immutable HF commit, deliberately never `main`.
MODEL_REVISION = "d2e518f738e36a44fc4c799f943f70e243a70e13"
MODEL_VARIANT = "F5TTS_v1_Base_v2"
MODEL_CONFIG = "F5TTS_v1_Base"
CHECKPOINT_FILE = "F5TTS_v1_Base_v2/model_last_inference.safetensors"
VOCAB_FILE = "F5TTS_v1_Base/vocab.txt"
VOCODER_REPO = "charactr/vocos-mel-24khz"
VOCODER_REVISION = "0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21"
VOCODER_FILES = ("config.yaml", "pytorch_model.bin")
DATA_DIR = Path(os.getenv("F5TTS_DATA_DIR", "/var/lib/f5tts-russian"))
MODEL_DIR = Path(os.getenv("F5TTS_MODEL_DIR", DATA_DIR / "models"))
TMP_DIR = Path(os.getenv("F5TTS_TMP_DIR", DATA_DIR / "tmp"))
CHECKPOINT_PATH = MODEL_DIR / MODEL_REPO / CHECKPOINT_FILE
VOCAB_PATH = MODEL_DIR / MODEL_REPO / VOCAB_FILE
VOCODER_DIR = MODEL_DIR / VOCODER_REPO
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_REFERENCE_SECONDS = 60.0
MIN_REFERENCE_SECONDS = 1.0
SAMPLE_RATE = 24_000
PREPARED_REFERENCE = ("Сегодня ранним утром я вышел к реке. Воздух был прохладным, над водой плыл лёгкий "
 "туман, а вдалеке тихо звонили колокола. Я остановился, улыбнулся и сказал: «Как же хорошо, когда впереди новый день!»")
