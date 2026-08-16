#!/usr/bin/env python3
"""Download an explicit allow-list at immutable revisions; never snapshots or .pt."""
import argparse, json
from pathlib import Path
from huggingface_hub import hf_hub_download
from safetensors import safe_open
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import config

def fetch(repo,revision,filename,root):
    assert len(revision)==40 and all(c in "0123456789abcdef" for c in revision)
    if filename.endswith(".pt"): raise RuntimeError(".pt запрещён")
    target=root/repo
    return Path(hf_hub_download(repo_id=repo,revision=revision,filename=filename,local_dir=target))
def fetch_cache(repo,revision,filename,root):
    """Populate the standard HF cache that Vocos.from_pretrained reads offline."""
    assert len(revision)==40
    return Path(hf_hub_download(repo_id=repo,revision=revision,filename=filename,cache_dir=root))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--model-dir",type=Path,default=config.MODEL_DIR); args=ap.parse_args()
    files=[fetch(config.MODEL_REPO,config.MODEL_REVISION,f,args.model_dir) for f in (config.CHECKPOINT_FILE,config.VOCAB_FILE)]
    files += [fetch_cache(config.VOCODER_REPO,config.VOCODER_REVISION,f,args.model_dir) for f in config.VOCODER_FILES]
    ckpt=files[0]
    if ckpt.stat().st_size < 1_000_000_000: raise RuntimeError("checkpoint подозрительно мал")
    with safe_open(ckpt,framework="pt",device="cpu") as sf:
        if not list(sf.keys()): raise RuntimeError("пустой safetensors")
    if files[1].stat().st_size < 1000: raise RuntimeError("vocab подозрительно мал")
    manifest={"model_repository":config.MODEL_REPO,"model_revision":config.MODEL_REVISION,"variant":config.MODEL_VARIANT,"files":[{"path":str(x),"bytes":x.stat().st_size} for x in files]}
    (args.model_dir/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
