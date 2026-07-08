import argparse

from fastapi import FastAPI, UploadFile, File, Form, Response
import numpy as np
import os
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from pydantic import BaseModel

from rvc.lib.tools.prerequisites_download import prequisites_download_pipeline
from rvc.realtime.core import VoiceChanger

app = FastAPI()

vc = None
audio_buffer = np.array([], dtype=np.float32)
config_file: str = "api_config.json"
result_queue = asyncio.Queue()

class RVCConfig(BaseModel):
    model_path: str = ""
    index_path: str = ""
    f0_method: str = "fcpe"
    sid: int = 0
    index_rate: float = 0.5
    protect: float = 0.5
    f0_up_key: int = 0
    read_chunk_size: int = 128
    extra_convert_size: float = 0.3

def load_config(path: str) -> RVCConfig:
    if os.path.exists(path):
        with open(path, "r") as f:
            return RVCConfig(**json.load(f))
    return RVCConfig()
current_config = load_config(config_file)

executor = ThreadPoolExecutor(max_workers=1)

# Configuration for the RVC model
RVC_CHUNK_SIZE = 128


def initialize_vc(config: RVCConfig):
    global vc

    vc = VoiceChanger(
        read_chunk_size=config.read_chunk_size,
        cross_fade_overlap_size=0.05,
        extra_convert_size=config.extra_convert_size,
        model_path=config.model_path,
        index_path=config.index_path,
        f0_method=config.f0_method,
        sid=config.sid,
        embedder_model="contentvec",
        silent_threshold=-60,
    )
    return vc

def initialize_config(path: str):
    global current_config, config_file
    config_file = path
    current_config = load_config(config_file)
    return current_config


@app.on_event("startup")
async def startup_event():
    global vc, current_config

    prequisites_download_pipeline(True, True, True)

    if current_config.model_path and current_config.index_path:
        try:
            initialize_vc(current_config)
        except Exception as e:
            print(f"Failed to initialize VC on startup: {e}")


@app.get("/settings")
async def get_settings():
    return current_config


@app.patch("/settings")
async def update_settings(
    model_path: Optional[str] = Form(None),
    index_path: Optional[str] = Form(None),
    f0_method: Optional[str] = Form(None),
    sid: Optional[int] = Form(None),
    index_rate: Optional[float] = Form(None),
    protect: Optional[float] = Form(None),
    f0_up_key: Optional[int] = Form(None),
    read_chunk_size: Optional[int] = Form(None),
    extra_convert_size: Optional[float] = Form(None),
):
    global current_config

    needs_reinit = (
        model_path or
        index_path or
        current_config.read_chunk_size != read_chunk_size or
        current_config.extra_convert_size != extra_convert_size
    )

    update_data = {
        k: v for k, v in locals().items()
        if k in RVCConfig.model_fields and v is not None
    }

    current_config = current_config.model_copy(update=update_data)

    os.makedirs(os.path.dirname(config_file) or ".", exist_ok=True)
    with open(config_file, "w") as f:
        f.write(current_config.model_dump_json())

    if needs_reinit:
        initialize_vc(current_config)

    return {"status": "settings updated", "config": current_config}


@app.post("/process-audio")
async def process_audio(waveform: UploadFile = File(...)):
    global audio_buffer, vc, current_config

    if vc is None:
        return Response(content=b"VC not initialized", status_code=400)

    # 2 seconds at 48000 sample rate
    MAX_BUFFER_SAMPLES = 48000 * 2

    audio_bytes = await waveform.read()
    new_chunk = np.frombuffer(audio_bytes, dtype=np.float32)
    
    audio_buffer = np.concatenate([audio_buffer, new_chunk])
    if len(audio_buffer) > MAX_BUFFER_SAMPLES:
        audio_buffer = audio_buffer[-MAX_BUFFER_SAMPLES:]
    
    chunk_size = current_config.read_chunk_size * 128

    while len(audio_buffer) >= chunk_size:
        process_chunk = audio_buffer[:chunk_size]
        audio_buffer = audio_buffer[chunk_size:]

        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            executor,
            process_and_queue,
            loop,
            process_chunk,
            current_config,
        )

    if not result_queue.empty():
        out = await result_queue.get()
        return Response(content=out.tobytes(), media_type="application/octet-stream")
    else:
        return Response(content=b"", media_type="application/octet-stream")

def process_and_queue(loop, chunk, config):
    out, _, _ = vc.on_request(chunk, config.f0_up_key, config.index_rate, config.protect)
    loop.call_soon_threadsafe(result_queue.put_nowait, out)


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Applio server")
    parser.add_argument("--config", default="api_config.json", help="Config file path")
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--model-path", help="Initial model path")
    parser.add_argument("--index-path", help="Initial index path")
    args = parser.parse_args()

    initialize_config(args.config)

    if args.model_path:
        current_config.model_path = args.model_path
    if args.index_path:
        current_config.index_path = args.index_path

    os.makedirs(os.path.dirname(config_file) or ".", exist_ok=True)
    with open(config_file, "w") as f:
        f.write(current_config.model_dump_json())

    uvicorn.run(app, host="127.0.0.1", port=args.port)

