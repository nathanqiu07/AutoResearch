import importlib.util
import os
import unittest

spec = importlib.util.spec_from_file_location(
    "build_pipeline_diagram",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "build_pipeline_diagram.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class PipelineDiagramTest(unittest.TestCase):
    def test_committed_docs_match_generator(self):
        stale = [str(p.relative_to(build.ROOT)) for p, text in build.outputs().items()
                 if not p.exists() or p.read_text() != text]
        self.assertEqual(stale, [], "run python3 scripts/build_pipeline_diagram.py and commit the result")


if __name__ == "__main__":
    unittest.main()
