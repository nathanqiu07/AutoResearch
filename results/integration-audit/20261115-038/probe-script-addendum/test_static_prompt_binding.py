#!/usr/bin/env python3
"""Small synthetic controls for AST-only literal extraction; no retained imports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit038_literal_reader', Path(__file__).with_name('static_prompt_binding.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class LiteralControls(unittest.TestCase):
    def test_utf8_and_escaped_newline(self):
        result = reader.prompt_literal(b'PROMPT = "synthetic \\u03bb\\n"\n')
        expected = 'synthetic \u03bb\n'.encode('utf-8')
        self.assertEqual(result['utf8_bytes'], len(expected))
        self.assertEqual(result['sha256'], hashlib.sha256(expected).hexdigest())

    def test_dynamic_expression_is_rejected_without_execution(self):
        with self.assertRaisesRegex(ValueError, 'literal string'):
            reader.prompt_literal(b'PROMPT = definitely_not_executed()\n')

    def test_ambiguous_reassignment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'one module-level'):
            reader.prompt_literal(b'PROMPT = "first"\nPROMPT = "second"\n')


if __name__ == '__main__':
    unittest.main()
