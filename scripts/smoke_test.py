#!/usr/bin/env python3
import importlib, json, sys, urllib.request
mods={m:importlib.import_module(m).__version__ if hasattr(importlib.import_module(m),"__version__") else "ok" for m in ("torch","torchaudio","torchcodec","gradio","f5_tts")}
import torch
assert not torch.cuda.is_available(),"CUDA неожиданно доступна"
assert "+" in "молок+о"
for endpoint in ("healthz","readyz"):
    with urllib.request.urlopen(f"http://127.0.0.1:7860/{endpoint}",timeout=10) as r: assert r.status==200
print(json.dumps({"imports":mods,"torch":torch.__version__,"cuda":torch.cuda.is_available(),"status":"ok"},ensure_ascii=False))
