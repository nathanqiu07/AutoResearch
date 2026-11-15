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

Default: Qwen/Qwen3-30B-A3B (Nathan's dev target: MoE, 3B active, thinking on by default) on one H100.
Other models: MODEL=... GPU=H100:4 PARSER=deepseek_r1 modal deploy harness/modal_vllm.py
(PARSER picks vLLM's --reasoning-parser: qwen3 for Qwen3, deepseek_r1 for R1 distills,
kimi_k2 for Kimi K2 thinking models where your vLLM version has it).
Petri auditor (non-thinking, tool calls, long context), as a second app:
    APP=autoresearch-auditor MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 GPU=H100:4 PARSER=none \
      MAX_MODEL_LEN=65536 modal deploy harness/modal_vllm.py
Stop: modal app stop autoresearch-vllm   (and autoresearch-auditor)
"""
import os
import subprocess
import threading

import modal

MODEL = os.environ.get("MODEL", "Qwen/Qwen3-30B-A3B")
GPU = os.environ.get("GPU", "H100:1")
PARSER = os.environ.get("PARSER", "qwen3")
TOOL_PARSER = os.environ.get("TOOL_PARSER", "hermes")
MAX_LEN = os.environ.get("MAX_MODEL_LEN", "32768")
N_GPU = int(GPU.split(":")[1]) if ":" in GPU else 1
APP = os.environ.get("APP", "autoresearch-vllm")   # a second server (e.g. the Petri auditor) needs its own app name

image = (
    modal.Image.debian_slim(python_version="3.12")
    # vllm 0.10.1.1 asks for transformers>=4.55 with no upper bound; 5.x removed
    # all_special_tokens_extended, which its tokenizer cache reads (auditor crash-looped 2026-11-14)
    .pip_install("vllm==0.10.1.1", "transformers==4.55.4", "huggingface_hub[hf_transfer]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "MODEL": MODEL, "GPU": GPU, "PARSER": PARSER,
          "TOOL_PARSER": TOOL_PARSER, "MAX_MODEL_LEN": MAX_LEN, "APP": APP})
)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
app = modal.App(APP)


def serve_command(model=MODEL, n_gpu=N_GPU, parser=PARSER, tool_parser=TOOL_PARSER, max_len=MAX_LEN, key="$KEY"):
    return ["vllm", "serve", model, "--served-model-name", model, "--host", "0.0.0.0", "--port", "8000",
            "--tensor-parallel-size", str(n_gpu), "--max-model-len", str(max_len),
            *(["--reasoning-parser", parser] if parser and parser != "none" else []),   # raw CoT -> reasoning_content
            "--enable-auto-tool-choice", "--tool-call-parser", tool_parser,   # Petri targets call tools
            "--api-key", key]


@app.function(image=image, gpu=GPU, volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
              secrets=[modal.Secret.from_name("vllm-key")], timeout=24 * 60 * 60, scaledown_window=15 * 60,
              max_containers=1)   # extra load queues; never a second GPU container (cost the ledger can't see)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=8000, startup_timeout=30 * 60)
def serve():
    proc = subprocess.Popen(serve_command(key=os.environ["VLLM_API_KEY"]))
    threading.Thread(target=exit_when_done, args=(proc,), daemon=True).start()


@app.function(image=image, volumes={"/root/.cache/huggingface": hf_cache}, cpu=4, memory=8192, timeout=3 * 60 * 60)
def download(model: str = MODEL) -> str:
    """Fetch the weights into the hf-cache volume on a CPU container (cents an hour), so the GPUs never
    sit billed through a first-time download (2026-11-14: ~25 min of 4xH100 for the auditor's 220 GiB).
    Already-cached files are only checked. scripts/c2_pilot.sh runs it before every deploy."""
    from huggingface_hub import snapshot_download
    path = snapshot_download(model, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.tiktoken",
                                                    "*.jinja", "*.py"])
    hf_cache.commit()
    print(f"weights for {model} ready in the hf-cache volume: {path}", flush=True)
    return path


EXIT_MARKER = "vllm exited with code"   # scripts/c2_pilot.sh watches the app log for this


def exit_when_done(proc, _exit=os._exit):
    """End the container as soon as vLLM exits. Without this, a vLLM that dies at startup (a bad
    dependency pin, out of memory) leaves Modal waiting startup_timeout (30 min) for a port that
    never opens, with every GPU billed (2026-11-14: the auditor crash-looped for 12 min)."""
    code = proc.wait()
    print(f"{EXIT_MARKER} {code}; stopping the container", flush=True)
    _exit(1)


if __name__ == "__main__":
    print(" ".join(serve_command()))
