#!/usr/bin/env bash
set -u
echo '=== ОС ==='; cat /etc/os-release; uname -a
echo '=== Ресурсы ==='; free -h; nproc; df -h /opt /var/lib/f5tts-russian 2>/dev/null
echo '=== Python и пакеты ==='; /opt/f5tts-russian/.venv/bin/python --version 2>&1; uv pip list --python /opt/f5tts-russian/.venv/bin/python 2>/dev/null | awk 'NR==1 || /^(f5-tts|torch |torchaudio|torchcodec|gradio|vocos)/'
echo '=== Модель ==='; cat /var/lib/f5tts-russian/models/manifest.json 2>/dev/null || true
echo '=== Сервисы ==='; systemctl --no-pager --full status f5tts-russian nginx 2>&1 || true
echo '=== Порты ==='; ss -ltnp 2>&1 | sed -n '1p;/\(:80\|:7860\)/p'
echo '=== Журнал ==='; journalctl -u f5tts-russian -n 50 --no-pager 2>&1 || true
echo '=== Probes ==='; curl -fsS --max-time 5 http://127.0.0.1:7860/healthz || true; echo; curl -fsS --max-time 5 http://127.0.0.1:7860/readyz || true; echo
echo '=== CUDA/NVIDIA Python-пакеты ==='; uv pip list --python /opt/f5tts-russian/.venv/bin/python 2>/dev/null | awk 'BEGIN{IGNORECASE=1}/cuda|nvidia|rocm/' || true
echo '=== Права ==='; namei -l /opt/f5tts-russian /var/lib/f5tts-russian /etc/f5tts-russian 2>&1 || true
