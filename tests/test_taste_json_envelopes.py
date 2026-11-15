import json
import unittest
from unittest.mock import patch
from autoresearch.taste.paper_backend import PaperOpenAILLM

class EnvelopeTests(unittest.TestCase):
    def test_consensus_decision_can_be_recovered_but_raw_is_retained(self):
        raw='{"probabilities":[0.75,0.25],"rationale":"first"} <style></style> {"probabilities":[0.75,0.25],"rationale":"second"}'
        llm=PaperOpenAILLM()
        with patch('autoresearch.taste.backends.OpenAILLM.complete',return_value=raw):
            result=llm.complete('Return JSON\nINPUT_JSON:\n{"options":["A","B"]}')
        self.assertEqual(json.loads(result)['probabilities'],[.75,.25])
        self.assertEqual(llm.recoveries[0]['raw_response'],raw)
    def test_conflicting_decisions_remain_an_error(self):
        raw='{"probabilities":[0.75,0.25],"rationale":"first"} {"probabilities":[0.6,0.4],"rationale":"second"}'
        llm=PaperOpenAILLM()
        with patch('autoresearch.taste.backends.OpenAILLM.complete',return_value=raw):
            with self.assertRaisesRegex(ValueError,'conflicting'):llm.complete('Return JSON\nINPUT_JSON:\n{"options":["A","B"]}')
    def test_conflicting_principles_remain_an_error(self):
        llm=PaperOpenAILLM()
        with patch('autoresearch.taste.backends.OpenAILLM.complete',return_value='{"principles":["a"]} {"principles":["b"]}'):
            with self.assertRaisesRegex(ValueError,'conflicting'):llm.complete('Return JSON\nINPUT_JSON:\n{"generation_style":"positive"}')
