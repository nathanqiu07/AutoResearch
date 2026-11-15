import io
import json
import unittest
from unittest.mock import patch
from autoresearch.taste.paper_backend import PaperOpenAILLM

class PaperBackendTests(unittest.TestCase):
    def test_embedding_usage_and_alignment(self):
        data={'data':[{'index':1,'embedding':[.5]*256},{'index':0,'embedding':[.1]*256}], 'usage':{'prompt_tokens':10}}
        with patch.dict('os.environ',{'OPENAI_API_KEY':'fixture'}), patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
            llm=PaperOpenAILLM(max_usd=.01)
            self.assertEqual(llm.embed(['a','b'])[0][0],.1)
            self.assertEqual(llm.budget.calls,1)
            self.assertAlmostEqual(llm.spent_usd,.0000002)
            self.assertEqual(llm.reserved_usd,0)
    def test_failed_embedding_holds_reservation_and_does_not_retry(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':'fixture'}), patch('urllib.request.urlopen',side_effect=OSError('hidden')) as network:
            llm=PaperOpenAILLM(max_usd=.01)
            with self.assertRaisesRegex(RuntimeError,'reservation retained'):llm.embed(['a'])
            self.assertGreater(llm.reserved_usd,0)
            self.assertEqual(network.call_count,1)
    def test_cap_prevents_network(self):
        with patch('urllib.request.urlopen') as network:
            with self.assertRaisesRegex(RuntimeError,'budget'):PaperOpenAILLM(max_usd=1e-10).embed(['a'])
            network.assert_not_called()
    def test_invalid_usage_cannot_reduce_budget(self):
        for invalid in [-1,float('nan'),'10',True]:
            data={'usage':{'prompt_tokens':invalid},'data':[]}
            with patch.dict('os.environ',{'OPENAI_API_KEY':'fixture'}), patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
                llm=PaperOpenAILLM(max_usd=.01)
                with self.assertRaises(RuntimeError):llm.embed(['a'])
                self.assertEqual(llm.spent_usd,0)
                self.assertEqual(llm.budget.input_tokens,0)
                self.assertGreater(llm.reserved_usd,0)
    def test_predictions_require_strict_json_schema(self):
        from tests.test_taste_backends import OpenAIBackendTests
        with patch.dict('os.environ',{'OPENAI_API_KEY':'fixture'}), patch('urllib.request.urlopen',return_value=OpenAIBackendTests().response(output=[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'{"probabilities":[0.7,0.3],"rationale":"test"}'}]}])) as network:
            llm=PaperOpenAILLM(max_usd=.01)
            llm.complete('Return JSON\nINPUT_JSON:\n{"options":["A","B"]}')
            body=json.loads(network.call_args.args[0].data)
            self.assertEqual(body['text']['format']['type'],'json_schema')
            self.assertTrue(body['text']['format']['strict'])
            self.assertEqual(body['text']['format']['schema']['properties']['probabilities']['maxItems'],2)
    def test_retry_only_failures_and_record_each_attempt(self):
        valid='{"probabilities":[0.7,0.3],"rationale":"reason"}'
        llm=PaperOpenAILLM(max_request_attempts=3)
        with patch('autoresearch.taste.backends.OpenAILLM.complete',side_effect=[RuntimeError('transport'),valid]) as call, patch('time.sleep'):
            result=llm.complete('JSON\nINPUT_JSON:\n{"options":["a","b"]}')
        self.assertEqual(result,valid)
        self.assertEqual(call.call_count,2)
        self.assertEqual(len(llm.retry_events),1)
