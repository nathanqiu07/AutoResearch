"""Serve an open model on Modal with vLLM, as an OpenAI-compatible endpoint the pipeline can call.

Default: Qwen3-235B-A22B-Instruct-2507 (FP8) on 4 x H100, with tool calling on, for the
auditor, the plain-agent rewriter, and (if OpenAI credits don't come through) the judges.
The Kimi target stays on Tinker. Run these from your laptop:

    pip install modal && modal setup
    modal secret create vllm-key VLLM_API_KEY=<any long random string>
    modal deploy modal_vllm.py
    # prints a URL like https://<workspace>--eval-aware-vllm-serve.modal.run
    export MODAL_BASE_URL=https://<workspace>--eval-aware-vllm-serve.modal.run/v1
    export MODAL_API_KEY=<the same random string>

Then in config.yaml use  openai-api/modal/Qwen/Qwen3-235B-A22B-Instruct-2507-FP8
The first request after idle waits for the model to load (several minutes on first deploy
while weights download into the volume, faster afterwards). It scales to zero after 15 idle
minutes, so it only bills while the pipeline is running. Stop it with: modal app stop eval-aware-vllm

To serve a smaller model instead (e.g. for a cheap test):
    MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507 GPU=H100:1 modal deploy modal_vllm.py
"""

import os
import subprocess

import modal

MODEL = os.environ.get("MODEL", "Qwen/Qwen3-235B-A22B-Instruct-2507-FP8")
GPU = os.environ.get("GPU", "H100:4")
N_GPU = int(GPU.split(":")[1]) if ":" in GPU else 1

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.10.1.1", "huggingface_hub[hf_transfer]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "MODEL": MODEL, "GPU": GPU})
)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
app = modal.App("eval-aware-vllm")


@app.function(
    image=image,
    gpu=GPU,
    volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
    secrets=[modal.Secret.from_name("vllm-key")],
    timeout=24 * 60 * 60,
    scaledown_window=15 * 60,
)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=8000, startup_timeout=30 * 60)
def serve():
    cmd = [
        "vllm", "serve", MODEL,
        "--served-model-name", MODEL,
        "--host", "0.0.0.0", "--port", "8000",
        "--tensor-parallel-size", str(N_GPU),
        "--max-model-len", "65536",
        "--enable-auto-tool-choice", "--tool-call-parser", "hermes",  # Petri's auditor needs tool calls
        "--api-key", os.environ["VLLM_API_KEY"],
    ]
    subprocess.Popen(cmd)
