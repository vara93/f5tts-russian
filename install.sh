#!/usr/bin/env bash
set -Eeuo pipefail
trap 'rc=$?; echo "ОШИБКА: строка $LINENO, команда: $BASH_COMMAND (код $rc)" >&2; exit $rc' ERR
[[ $EUID -eq 0 ]] || { echo 'Запустите: sudo bash install.sh' >&2; exit 1; }
exec > >(tee -a /var/log/f5tts-russian-install.log) 2>&1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd); ALLOW_CIDR=""
while (($#)); do case "$1" in --allow-cidr) [[ $# -ge 2 ]] || { echo 'Нет CIDR'; exit 2; }; ALLOW_CIDR=$2; shift 2;; *) echo "Неизвестный параметр: $1"; exit 2;; esac; done
source /etc/os-release
[[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 26.04 ]] || { echo "Требуется Ubuntu 26.04; обнаружено ${PRETTY_NAME:-неизвестно}"; exit 1; }
[[ $(uname -m) == x86_64 ]] || { echo 'Поддерживается только amd64/x86_64'; exit 1; }
if ss -H -ltn 'sport = :80' 2>/dev/null | grep -q .; then echo 'Порт 80 уже занят; установка ничего не останавливает:'; ss -ltnp 'sport = :80'; exit 1; fi
ram=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo); disk=$(df -Pm /opt 2>/dev/null | awk 'NR==2{print $4}' || df -Pm / | awk 'NR==2{print $4}'); cpus=$(nproc)
((ram>=8192)) || echo "ПРЕДУПРЕЖДЕНИЕ: RAM ${ram} МБ; рекомендуется 8 ГБ+"
((disk>=8000)) || echo "ПРЕДУПРЕЖДЕНИЕ: свободно ${disk} МБ; рекомендуется 8 ГБ+"
((cpus>=4)) || echo "ПРЕДУПРЕЖДЕНИЕ: CPU-потоков $cpus; синтез будет медленным"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends nginx ffmpeg libsndfile1 libgomp1 curl ca-certificates git build-essential pkg-config ufw iproute2
UV_VERSION=0.8.11
curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
uv python install 3.11.13
id f5tts >/dev/null 2>&1 || useradd --system --home-dir /var/lib/f5tts-russian --shell /usr/sbin/nologin f5tts
install -d -o f5tts -g f5tts -m 0750 /opt/f5tts-russian /var/lib/f5tts-russian/{models,huggingface,tmp} /etc/f5tts-russian
find "$ROOT" -maxdepth 1 -type f \( -name '*.py' -o -name '*.json' -o -name '*.toml' -o -name 'uv.lock' -o -name '.python-version' -o -name '*.md' \) -exec install -o root -g root -m 0644 {} /opt/f5tts-russian/ \;
install -d -o root -g root -m 0755 /opt/f5tts-russian/scripts
install -o root -g root -m 0755 "$ROOT"/scripts/* /opt/f5tts-russian/scripts/
uv venv --python 3.11.13 /opt/f5tts-russian/.venv
UV=/opt/f5tts-russian/.venv/bin/python
uv pip install --python "$UV" --index-url https://download.pytorch.org/whl/cpu torch==2.7.1+cpu torchaudio==2.7.1+cpu torchcodec==0.5
uv pip install --python "$UV" f5-tts==1.1.22 gradio==5.35.0 fastapi==0.115.12 uvicorn==0.34.3 huggingface-hub==0.33.1 safetensors==0.5.3 vocos==0.1.0 soundfile==0.13.1 numpy==1.26.4
if uv pip list --python "$UV" | grep -Eiq '^(nvidia-|.*cuda|.*rocm)'; then echo 'Обнаружены запрещённые CUDA/ROCm-пакеты'; exit 1; fi
HF_HOME=/var/lib/f5tts-russian/huggingface "$UV" /opt/f5tts-russian/scripts/download_models.py --model-dir /var/lib/f5tts-russian/models
chown -R f5tts:f5tts /var/lib/f5tts-russian; chmod -R go-rwx /var/lib/f5tts-russian
threads=$(( cpus>8 ? 8 : cpus )); printf 'OMP_NUM_THREADS=%s\nMKL_NUM_THREADS=%s\nF5TTS_DATA_DIR=/var/lib/f5tts-russian\n' "$threads" "$threads" >/etc/f5tts-russian/environment
install -o root -g root -m 0644 "$ROOT/systemd/f5tts-russian.service" /etc/systemd/system/f5tts-russian.service
install -o root -g root -m 0644 "$ROOT/nginx/f5tts-russian.conf" /etc/nginx/sites-available/f5tts-russian
ln -sfn /etc/nginx/sites-available/f5tts-russian /etc/nginx/sites-enabled/f5tts-russian
[[ ! -L /etc/nginx/sites-enabled/default ]] || rm /etc/nginx/sites-enabled/default
nginx -t; systemctl daemon-reload; systemctl enable --now f5tts-russian nginx; systemctl reload nginx
if ufw status | grep -q '^Status: active'; then
  if [[ -n $ALLOW_CIDR ]]; then ufw allow from "$ALLOW_CIDR" to any port 80 proto tcp comment 'F5-TTS Russian'; else echo 'UFW активен; порт не открыт. При необходимости: ufw allow from ВАША_СЕТЬ to any port 80 proto tcp'; fi
fi
echo 'Ожидание загрузки модели (до 20 минут)...'; ready=0
for _ in {1..120}; do if curl -fsS --max-time 5 http://127.0.0.1:7860/readyz >/dev/null; then ready=1; break; fi; sleep 10; done
((ready)) || { systemctl status f5tts-russian --no-pager || true; journalctl -u f5tts-russian -n 80 --no-pager || true; echo 'Модель не готова за 20 минут'; exit 1; }
"$UV" /opt/f5tts-russian/scripts/smoke_test.py
echo 'Готовые URL:'; ip -4 -o addr show scope global | awk '{print "  http://" $4}' | sed 's#/.*##'
