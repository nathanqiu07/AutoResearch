"""Reasoning target on Modal (WS C2, PLAN 12.3 item 5).

Serves an open-weight reasoning model with vLLM behind an OpenAI-compatible URL.
`--reasoning-parser` splits the raw chain of thought into `reasoning_content`,
which autoresearch's OpenAICompatLLM reads into `Sample.reasoning` for the A1
(verbalized-awareness) judge. Tool calling is on, so the same endpoint can be
the Petri target. Scales to zero after 15 idle minutes.

    pip install modal && modal setup
    modal secret create vllm-key VLLM_API_KEY=<any long random string>
    modal deploy harness/modal_vllm.py
    # prints https://<workspace>--autoresearch-vllm-serve.modal.run
    export OPENAI_COMPAT_BASE_URL=https://<workspace>--autoresearch-vllm-serve.modal.run/v1
    export OPENAI_COMPAT_API_KEY=<the same random string>
    export MODAL_BASE_URL=$OPENAI_COMPAT_BASE_URL MODAL_API_KEY=$OPENAI_COMPAT_API_KEY   # Inspect ids openai-api/modal/...
    python3 scripts/c2_smoke_target.py --n 5          # paid: needs the user's OK (AGENTS.md rule 5)

Default: Qwen/Qwen3-32B (dense, open reasoning model, raw thinking) on one H100.
Other models: MODEL=... GPU=H100:4 PARSER=deepseek_r1 modal deploy harness/modal_vllm.py
(PARSER picks vLLM's --reasoning-parser: qwen3 for Qwen3, deepseek_r1 for R1 distills,
kimi_k2 for Kimi K2 thinking models where your vLLM version has it).
Stop: modal app stop autoresearch-vllm
"""
import os
import subprocess

import modal

MODEL = os.environ.get("MODEL", "Qwen/Qwen3-32B")
GPU = os.environ.get("GPU", "H100:1")
PARSER = os.environ.get("PARSER", "qwen3")
TOOL_PARSER = os.environ.get("TOOL_PARSER", "hermes")
MAX_LEN = os.environ.get("MAX_MODEL_LEN", "32768")
N_GPU = int(GPU.split(":")[1]) if ":" in GPU else 1

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.10.1.1", "huggingface_hub[hf_transfer]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "MODEL": MODEL, "GPU": GPU, "PARSER": PARSER,
          "TOOL_PARSER": TOOL_PARSER, "MAX_MODEL_LEN": MAX_LEN})
)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
app = modal.App("autoresearch-vllm")


def serve_command(model=MODEL, n_gpu=N_GPU, parser=PARSER, tool_parser=TOOL_PARSER, max_len=MAX_LEN, key="$KEY"):
    return ["vllm", "serve", model, "--served-model-name", model, "--host", "0.0.0.0", "--port", "8000",
            "--tensor-parallel-size", str(n_gpu), "--max-model-len", str(max_len),
            "--reasoning-parser", parser,                                     # raw CoT -> reasoning_content
            "--enable-auto-tool-choice", "--tool-call-parser", tool_parser,   # Petri targets call tools
            "--api-key", key]


@app.function(image=image, gpu=GPU, volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
              secrets=[modal.Secret.from_name("vllm-key")], timeout=24 * 60 * 60, scaledown_window=15 * 60)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=8000, startup_timeout=30 * 60)
def serve():
    subprocess.Popen(serve_command(key=os.environ["VLLM_API_KEY"]))


if __name__ == "__main__":
    print(" ".join(serve_command()))
