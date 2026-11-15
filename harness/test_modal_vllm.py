"""harness/modal_vllm.py without Modal calls. Run in the Petri env:
    $AUTORESEARCH_PETRI_PYTHON -m unittest harness/test_modal_vllm.py
"""
import contextlib
import io
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modal_vllm as mv  # noqa: E402


class FakeProc:
    def __init__(self, code):
        self.code = code

    def wait(self):
        return self.code


class ModalVllmTest(unittest.TestCase):
    def test_container_exits_and_logs_the_marker_when_vllm_dies(self):
        exits, out = [], io.StringIO()
        with contextlib.redirect_stdout(out):
            mv.exit_when_done(FakeProc(1), _exit=exits.append)
        self.assertEqual(exits, [1])
        self.assertIn(f"{mv.EXIT_MARKER} 1", out.getvalue())

    def test_pilot_watches_for_the_same_marker(self):
        pilot = (Path(__file__).resolve().parents[1] / "scripts" / "c2_pilot.sh").read_text()
        self.assertIn(mv.EXIT_MARKER, pilot)

    def test_transformers_is_pinned_below_5(self):
        # vllm 0.10.1.1 reads tokenizer.all_special_tokens_extended, which transformers 5 removed
        src = Path(mv.__file__).read_text()
        pin = re.search(r'"transformers==(\d+)\.', src)
        self.assertIsNotNone(pin, "transformers must be pinned in the vLLM image")
        self.assertLess(int(pin.group(1)), 5)

    def test_server_never_scales_past_one_gpu_container(self):
        # parallel audits can exceed max_inputs; a second container would double the GPU bill unseen by the
        # pilot's ledger (it counts one container) and wait out a fresh model load
        src = Path(mv.__file__).read_text()
        self.assertRegex(src, r"max_containers=1\b")

    def test_serve_command_omits_reasoning_parser_for_none(self):
        cmd = mv.serve_command(model="m", n_gpu=4, parser="none", max_len=65536, key="k")
        self.assertNotIn("--reasoning-parser", cmd)
        self.assertEqual(cmd[cmd.index("--tensor-parallel-size") + 1], "4")


if __name__ == "__main__":
    unittest.main()
