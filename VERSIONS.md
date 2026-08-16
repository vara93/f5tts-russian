# Зафиксированные версии и основания выбора

| Компонент | Версия / immutable revision |
|---|---|
| CPython (uv-managed) | 3.11.13 |
| uv | 0.8.11 |
| F5‑TTS | 1.1.22 |
| PyTorch CPU / torchaudio CPU | 2.7.1+cpu / 2.7.1+cpu |
| TorchCodec | 0.5 |
| Gradio | 5.35.0 |
| FastAPI / Uvicorn | 0.115.12 / 0.34.3 |
| Russian model | `Misha24-10/F5-TTS_RUSSIAN@d2e518f738e36a44fc4c799f943f70e243a70e13` |
| Vocos | `charactr/vocos-mel-24khz@0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21` |

Основной файл — `F5TTS_v1_Base_v2/model_last_inference.safetensors`, vocabulary — `F5TTS_v1_Base/vocab.txt`. Это конфигурация F5TTS v1 Base (DiT 1024, 22 слоя, 16 голов), поэтому API получает `model="F5TTS_v1_Base"`; вариант v2 относится к обученному checkpoint, а не к имени архитектуры. v2 выбран из-за полной разметки ударений, поддержки ручного `+` и безопасного inference-safetensors. `.pt` русской модели запрещены политикой загрузчика.

F5‑TTS 1.1.22 закреплён вместе с его актуальным `F5TTS` API: `infer()` поддерживает `nfe_step`, `cfg_strength`, `sway_sampling_coef`, `cross_fade_duration`, `target_rms`, `speed`, `seed`, `remove_silence` и `fix_duration`. UI намеренно не навязывает `fix_duration`. Torch/Torchaudio ставятся первыми исключительно из официального CPU index, а проверка установки отвергает пакеты NVIDIA/CUDA/ROCm. TorchCodec 0.5 согласован с Torch 2.7; FFmpeg остаётся системным декодером и нормализатором.

Указанные HF SHA являются полными неизменяемыми ревизиями. Установщик использует `hf_hub_download` отдельно для четырёх разрешённых файлов, затем приложение включает `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` и `local_files_only=True`.

> Среда разработки могла не иметь сетевого доступа; перед производственным обновлением ревизии и совместимость повторно проверяются целевой адресной загрузкой и smoke-тестом установщика, а не заменяются веткой `main`.
