"""Offline, single-model F5-TTS inference and input validation."""
from __future__ import annotations
import json, os, random, re, subprocess, threading, time, uuid, wave
from collections import deque
from pathlib import Path
from typing import Any
import config

RUSSIAN_VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
ALLOWED_AUDIO = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}

def validate_stress(text: str) -> tuple[bool, str]:
    """Keep text intact and require every plus to precede a Russian vowel."""
    if not text or not text.strip(): return False, "Введите текст для синтеза."
    bad = [str(i + 1) for i, ch in enumerate(text) if ch == "+" and (i + 1 == len(text) or text[i + 1] not in RUSSIAN_VOWELS)]
    if bad: return False, "Знак + должен стоять непосредственно перед русской гласной (позиции: " + ", ".join(bad) + ")."
    return True, "Разметка ударений корректна."

def load_presets(path: Path | str | None = None) -> dict[str, str]:
    p = Path(path) if path else Path(__file__).with_name("presets.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data or not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k,v in data.items()):
        raise ValueError("presets.json должен быть непустым объектом строк")
    return data

def probe_audio(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file() or p.suffix.lower() not in ALLOWED_AUDIO: raise ValueError("Допустимы WAV, MP3, FLAC, OGG и M4A.")
    if p.stat().st_size > config.MAX_UPLOAD_BYTES: raise ValueError("Аудиофайл превышает 100 МБ.")
    cmd = ["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=sample_rate,channels:format=duration","-of","json",str(p)]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=20)
    meta = json.loads(result.stdout); stream = meta["streams"][0]
    duration = float(meta["format"]["duration"])
    if duration < config.MIN_REFERENCE_SECONDS or duration > config.MAX_REFERENCE_SECONDS:
        raise ValueError("Длительность референса должна быть от 1 до 60 секунд.")
    return {"duration": duration, "sample_rate": int(stream["sample_rate"]), "channels": int(stream["channels"]), "size": p.stat().st_size}

def normalize_audio(path: str) -> tuple[str, dict[str, Any], str]:
    meta = probe_audio(path); config.TMP_DIR.mkdir(parents=True, exist_ok=True)
    out = config.TMP_DIR / f"ref-{uuid.uuid4().hex}.wav"
    subprocess.run(["ffmpeg","-nostdin","-v","error","-i",path,"-vn","-ac","1","-ar",str(config.SAMPLE_RATE),"-c:a","pcm_s16le","-y",str(out)], check=True, timeout=90)
    warnings=[]
    if meta["duration"] < 3: warnings.append("референс короче 3 с")
    if meta["duration"] > 20: warnings.append("референс длиннее рекомендуемых 20 с")
    detect = subprocess.run(["ffmpeg","-nostdin","-i",str(out),"-af","volumedetect","-f","null","-"], capture_output=True, text=True, timeout=30)
    m = re.search(r"mean_volume: ([-\d.]+) dB", detect.stderr); mx = re.search(r"max_volume: ([-\d.]+) dB", detect.stderr)
    if m and float(m.group(1)) < -35: warnings.append("очень тихая запись")
    if mx and float(mx.group(1)) >= -0.1: warnings.append("возможно клиппирование")
    return str(out), meta, ("Предупреждение: " + "; ".join(warnings) if warnings else "Референс принят.")

class TTSEngine:
    def __init__(self): self.lock=threading.Lock(); self.ready=False; self.tts=None
    def load(self):
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        if not config.CHECKPOINT_PATH.is_file() or not config.VOCAB_PATH.is_file(): raise FileNotFoundError("Файлы русской модели не установлены")
        from f5_tts.api import F5TTS
        self.tts = F5TTS(model=config.MODEL_CONFIG, ckpt_file=str(config.CHECKPOINT_PATH), vocab_file=str(config.VOCAB_PATH), vocoder_name="vocos", local_files_only=True, device="cpu", hf_cache_dir=str(config.MODEL_DIR))
        self.ready=True
    def synthesize(self, ref_file: str, ref_text: str, gen_text: str, params: dict[str,Any]) -> dict[str,Any]:
        ok,msg=validate_stress(gen_text)
        if not ok: raise ValueError(msg)
        if not ref_text.strip(): raise ValueError("Точная расшифровка референса обязательна.")
        normalized,_,_=normalize_audio(ref_file)
        seed = int(params.get("seed", -1)); seed = random.randint(0,2**31-1) if seed < 0 else seed
        out=config.TMP_DIR/f"result-{uuid.uuid4().hex}.wav"; started=time.monotonic()
        kwargs={k:params[k] for k in ("target_rms","cross_fade_duration","sway_sampling_coef","cfg_strength","nfe_step","speed","fix_duration","remove_silence") if k in params}
        try:
            with self.lock:
                wav,sr,_=self.tts.infer(ref_file=normalized,ref_text=ref_text,gen_text=gen_text,seed=seed,file_wave=str(out),**kwargs)
            elapsed=time.monotonic()-started
            with wave.open(str(out),"rb") as w: duration=w.getnframes()/w.getframerate()
            return {"path":str(out),"elapsed":elapsed,"duration":duration,"rtf":elapsed/duration if duration else 0,"seed":seed,"params":kwargs,"text":gen_text}
        finally: Path(normalized).unlink(missing_ok=True)

def cleanup_tmp(max_age=86400):
    config.TMP_DIR.mkdir(parents=True,exist_ok=True); cutoff=time.time()-max_age
    for p in config.TMP_DIR.iterdir():
        if p.is_file() and p.stat().st_mtime < cutoff: p.unlink(missing_ok=True)
