#!/bin/bash
set -e
ORIGINAL_DIR=$(pwd)

cleanup() {
    deactivate || true
    cd "$ORIGINAL_DIR" || true
}
trap cleanup EXIT

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment for applio..."
    python3.12 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    echo "NVIDIA GPU detected. Installing CUDA torch..."
    python -m pip install --upgrade torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128
fi

python install.py

echo Installation for applio complete