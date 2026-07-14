from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

DEEPFILTER_VERSION = "0.5.6"
DEEPFILTER_BASE_URL = f"https://github.com/Rikorose/DeepFilterNet/releases/download/v{DEEPFILTER_VERSION}"

ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / "bin"
BIN_DIR.mkdir(exist_ok=True)

DEEPFILTER = ROOT / "deep-filter.exe"

FFMPEG = BIN_DIR / "ffmpeg.exe"
FFPROBE = BIN_DIR / "ffprobe.exe"

ARCH_ALIASES = {
    "amd64": "x86_64",
    "x86-64": "x86_64",
    "arm64": "aarch64",
}

DEEPFILTER_DOWNLOADS = {
    ("Windows", "x86_64"): f"deep-filter-{DEEPFILTER_VERSION}-x86_64-pc-windows-msvc.exe",
    ("Linux", "x86_64"): f"deep-filter-{DEEPFILTER_VERSION}-x86_64-unknown-linux-musl",
    ("Linux", "aarch64"): f"deep-filter-{DEEPFILTER_VERSION}-aarch64-unknown-linux-gnu",
    ("Linux", "armv7l"): f"deep-filter-{DEEPFILTER_VERSION}-armv7-unknown-linux-gnueabihf",
    ("Darwin", "x86_64"): f"deep-filter-{DEEPFILTER_VERSION}-x86_64-apple-darwin",
    ("Darwin", "aarch64"): f"deep-filter-{DEEPFILTER_VERSION}-aarch64-apple-darwin",
}


def download(url: str, output: Path):
    if shutil.which("curl"):
        subprocess.check_call(["curl", "-fL", url, "-o", str(output)])
    elif shutil.which("wget"):
        subprocess.check_call(["wget", "-O", str(output), url])
    else:
        raise RuntimeError("Neither curl nor wget was found.")


def download_deepfilter():
    system = platform.system()
    machine = ARCH_ALIASES.get(
        platform.machine().lower(),
        platform.machine().lower()
    )

    if DEEPFILTER.exists():
        print("DeepFilter already exists. Skipping download.")
        return

    try:
        filename = DEEPFILTER_DOWNLOADS[(system, machine)]
    except KeyError:
        raise RuntimeError(
            f"No DeepFilter binary for {system} ({machine})."
        )

    print(f"Downloading {filename}...")
    download(f"{DEEPFILTER_BASE_URL}/{filename}", DEEPFILTER)
    if system != "Windows":
        os.chmod(DEEPFILTER, 0o755)
    print("DeepFilter installation complete.")


def download_ffmpeg_windows():
    print("Starting ffmpeg download")
    subprocess.check_call(["winget","install", "FFmpeg (Essentials Build)"])


def download_ffmpeg_linux():
    print("Starting ffmpeg download")
    subprocess.check_call(["sudo", "apt-get", "install", "-y", "ffmpeg"])


def download_ffmpeg_macos():
    if not shutil.which("brew"):
        raise RuntimeError(
            "Please install Homebrew or install FFmpeg manually and set on PATH."
        )

    print("Starting ffmpeg download")
    subprocess.check_call(["brew", "install", "ffmpeg"])


def install_ffmpeg():
    if shutil.which("ffmpeg"):
        print("FFmpeg already installed.")
        return

    system = platform.system()

    if system == "Windows":
        download_ffmpeg_windows()
    elif system == "Linux":
        download_ffmpeg_linux()
    elif system == "Darwin":
        download_ffmpeg_macos()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
    
    print("FFmpeg installation complete.")


def main():
    download_deepfilter()
    install_ffmpeg()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        sys.exit(1)