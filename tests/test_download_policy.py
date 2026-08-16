from pathlib import Path
import config
def test_model_allowlist():
    assert config.CHECKPOINT_FILE.endswith(".safetensors")
    assert not config.CHECKPOINT_FILE.endswith(".pt")
    assert len(config.MODEL_REVISION)==40
    assert config.MODEL_VARIANT == "F5TTS_v1_Base_v2"
def test_vocoder_allowlist(): assert set(config.VOCODER_FILES)=={"config.yaml","pytorch_model.bin"}
