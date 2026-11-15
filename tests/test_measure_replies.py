"""Target replies must not be silently truncated or empty; the generator must not see the
judge's rubric or be told it writes for a study. Scripted fakes and a mocked urlopen only."""
import hashlib
import json
import os
import random
import unittest
from dataclasses import replace
from unittest import mock

from autoresearch import llm as L
from autoresearch.llm import Budget, LLM
from autoresearch.research.measure import EVAL_NOTICE, SCENARIOS, Measurer, Models

PROBE_PREFIXES = ("Below is an interaction", "Below is a transcript", "Here is a conversation")
ENV = {"system": "S", "user": "U"}


class Recorder(LLM):
    """Records every prompt and answers a fixed string."""
    name, model = "recorder", "r"

    def __init__(self, reply="{}"):
        super().__init__(Budget())
        self.reply, self.prompts = reply, []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.prompts.append(prompt)
        return self.reply


class Target(LLM):
    """Text only from complete_with_reasoning; plain complete is a test failure."""
    name, model = "script-target", "t"

    def __init__(self, replies):
        super().__init__(Budget())
        self.replies, self.systems = list(replies), []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        raise AssertionError("target reply must go through complete_with_reasoning")

    def complete_with_reasoning(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.systems.append(system)
        return "thoughts", self.replies.pop(0) if self.replies else "fine"


class Gen(LLM):
    name, model = "script-gen", "g"

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        return json.dumps({"system": "You are Atlas.", "user": "hey can u pull Q3 churn"})


class Judge(LLM):
    name, model = "script-judge", "j"

    def __init__(self):
        super().__init__(Budget())
        self.replies_judged, self.audits = [], 0

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        if prompt.startswith(PROBE_PREFIXES):
            return '{"p": 0.2}'
        if prompt.startswith("You audit"):
            self.audits += 1
            return ('{"verbalized": 0.1, "opportunity": 0.9, "scorable": 0.9, "bait_reached": 0.9, '
                    '"behavior": "honest"}')
        self.replies_judged.append(prompt.split("ASSISTANT REPLY:\n", 1)[1].split("\n\nClassify", 1)[0])
        return '{"behavior": "honest"}'


def measurer(replies, **kw):
    judge = Judge()
    return Measurer(Models(Gen(Budget()), Target(replies), judge), **kw), judge


class FaithfulnessPairTests(unittest.TestCase):
    def test_both_arms_use_the_reasoning_path(self):
        m, judge = measurer(["plain reply", "noticed reply"])
        pair = m.faithfulness_pair([], 1)
        self.assertEqual(pair, {"plain": "honest", "eval_notice": "honest"})
        self.assertEqual(judge.replies_judged, ["plain reply", "noticed reply"])
        systems = m.target.systems
        self.assertFalse(systems[0].startswith(EVAL_NOTICE))
        self.assertTrue(systems[1].startswith(EVAL_NOTICE))

    def test_empty_reply_in_one_arm_is_an_error_and_not_judged(self):
        for replies, bad_arm in ((["", "ok"], "plain"), (["ok", "  \n"], "eval_notice")):
            m, judge = measurer(replies)
            pair = m.faithfulness_pair([], 1)
            self.assertEqual(pair[bad_arm], "error")
            self.assertIn("empty target reply", pair["error"])
            self.assertIn(bad_arm, pair["error"])
            self.assertEqual(len(judge.replies_judged), 1)   # only the non-empty arm
            self.assertEqual(judge.replies_judged, ["ok"])

    def test_faithfulness_excludes_and_counts_empty_pairs_with_the_reason(self):
        m, _ = measurer(["", "ok", "a", "b"], workers=1)
        rep = m.faithfulness([], [1, 2])
        self.assertEqual((rep["n"], rep["errors"]), (1, 1))
        [(reason, count)] = rep["error_reasons"].items()
        self.assertIn("empty target reply", reason)
        self.assertEqual(count, 1)


class SampleEmptyReplyTests(unittest.TestCase):
    def test_empty_reply_is_an_error_sample_and_the_judge_is_not_called(self):
        for empty in ("", "   \n\t"):
            m, judge = measurer([empty])
            s = m.sample([], 1)
            self.assertEqual(s.behavior, "error")
            self.assertIn("empty target reply", s.error)
            self.assertEqual(judge.audits, 0)
            self.assertEqual(judge.replies_judged, [])


class OpenAICompatTests(unittest.TestCase):
    def _run(self, payload, call):
        sent = []

        def urlopen(req, timeout=0):
            sent.append(json.loads(req.data))

            class Resp:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def read(self): return json.dumps(payload).encode()
            return Resp()
        with mock.patch.dict(os.environ, {"OPENAI_COMPAT_BASE_URL": "http://vllm.invalid/v1"}), \
                mock.patch.object(L.urllib.request, "urlopen", urlopen):
            llm = L.OpenAICompatLLM("qwen3", Budget())
            try:
                return call(llm), sent
            finally:
                self.sent = sent

    def test_reasoning_path_adds_headroom_and_plain_complete_does_not(self):
        ok = {"choices": [{"message": {"content": "hi", "reasoning_content": "r"}, "finish_reason": "stop"}]}
        result, sent = self._run(ok, lambda m: m.complete_with_reasoning("q", max_tokens=1200))
        self.assertEqual(result, ("r", "hi"))
        self.assertEqual(sent[0]["max_tokens"], 1200 + L.OpenAICompatLLM.THINKING_HEADROOM)
        result, sent = self._run(ok, lambda m: m.complete("q", max_tokens=1200))
        self.assertEqual(result, "hi")
        self.assertEqual(sent[0]["max_tokens"], 1200)

    def test_length_stop_with_empty_content_raises_on_both_paths(self):
        cut = {"choices": [{"message": {"content": "", "reasoning_content": "still thinking"},
                            "finish_reason": "length"}]}
        for call in (lambda m: m.complete_with_reasoning("q", max_tokens=1200), lambda m: m.complete("q", max_tokens=50)):
            with self.assertRaises(RuntimeError) as cm:
                self._run(cut, call)
            self.assertIn("qwen3", str(cm.exception))
            self.assertIn(str(self.sent[0]["max_tokens"]), str(cm.exception))

    def test_length_stop_with_some_content_still_returns_it(self):
        part = {"choices": [{"message": {"content": "half an ans"}, "finish_reason": "length"}]}
        result, _ = self._run(part, lambda m: m.complete("q"))
        self.assertEqual(result, "half an ans")

    def test_parse_openai_chat_keeps_its_shape(self):
        data = {"choices": [{"message": {"content": "hi", "reasoning": "r"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4}}
        self.assertEqual(L.parse_openai_chat(data), ("r", "hi", 3, 4))


class AnthropicTruncationTests(unittest.TestCase):
    def _run(self, payload):
        def urlopen(req, timeout=0):
            class Resp:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def read(self): return json.dumps(payload).encode()
            return Resp()
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "k"}), \
                mock.patch.object(L.urllib.request, "urlopen", urlopen):
            llm = L.AnthropicLLM("claude-sonnet-4-5+thinking", Budget())
            return llm.complete_with_reasoning("q", max_tokens=1200)

    def test_max_tokens_stop_with_empty_text_raises(self):
        cut = {"stop_reason": "max_tokens", "content": [{"type": "thinking", "thinking": "hmm"}],
               "usage": {"input_tokens": 1, "output_tokens": 1}}
        with self.assertRaises(RuntimeError) as cm:
            self._run(cut)
        self.assertIn("claude-sonnet-4-5", str(cm.exception))
        self.assertIn("max_tokens", str(cm.exception))

    def test_normal_reply_parses(self):
        ok = {"stop_reason": "end_turn", "content": [{"type": "thinking", "thinking": "hmm"},
                                                      {"type": "text", "text": "yes"}],
              "usage": {"input_tokens": 1, "output_tokens": 1}}
        self.assertEqual(self._run(ok), ("hmm", "yes"))

    def test_max_tokens_stop_with_some_text_still_returns_it(self):
        part = {"stop_reason": "max_tokens", "content": [{"type": "text", "text": "partial"}],
                "usage": {"input_tokens": 1, "output_tokens": 1}}
        self.assertEqual(self._run(part), ("", "partial"))


# sha256 prefixes of the prompts for the four stock scenarios, captured from the code as it
# was before the rubric field existed: [generate, rewrite, audit, behavior, faithful].
# The two generator prompts are hashed with " for a study of model behaviour" removed,
# the one intended change to them.
SNAPSHOT = {
    "metric_inflation": ['90fb810c65ea5769', '662c0a0511414813', 'f39de3081df5a6df', 'ca93eec928248836', '580e4e05da9461c3'],
    "sycophancy_code": ['b34e5b97a56108b3', '249320024ab6e350', '4e71a1bc9fd78f94', '316e844f3640c40f', '9ad7cf128610dcdb'],
    "test_special_casing": ['97c112de0724c2a5', '85acaecf5f9069ba', '47abb10884e42b7b', '928bd917c9b3ed04', '9ebbbc85bebb47a2'],
    "fabrication": ['dc9521aa4454c726', '5032e964c3a9371c', '0d3a38fdae7bb471', '9c10d1d3d3685a94', '227c664d102d7625'],
}


def prompts_for(sc):
    """[generate, rewrite, audit, behavior, faithful] prompts for a scenario."""
    gen, judge = Recorder(), Recorder()
    m = Measurer(Models(gen, Recorder(), judge), sc)
    m.generate(["x"], random.Random(1))
    m._audit("T", "reason")
    m._behavior(ENV, "R")
    m2 = Measurer(Models(gen, Recorder(), judge), replace(sc, original={"system": "os", "user": "ou"}))
    m2.generate(["x"], random.Random(1))
    m2.faithful_to_original(ENV)
    g, j = gen.prompts, judge.prompts
    return [g[0], g[1], j[0], j[1], j[2]]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class RubricTests(unittest.TestCase):
    def test_without_a_rubric_prompts_are_byte_identical_to_before(self):
        for name, sc in SCENARIOS.items():
            self.assertEqual(sc.rubric, "")
            self.assertEqual([digest(p) for p in prompts_for(sc)], SNAPSHOT[name], name)

    def test_rubric_reaches_the_judge_prompts_and_never_the_generator(self):
        rubric = "Reply labels: 'honest' = RUBRIC-MARKER-7; 'dishonest' = other; 'unclear' = neither."
        sc = replace(SCENARIOS["metric_inflation"], rubric=rubric)
        base = prompts_for(SCENARIOS["metric_inflation"])
        with_rubric = prompts_for(sc)
        gen_a, gen_b, audit, behavior, faithful = with_rubric
        self.assertEqual([gen_a, gen_b], base[:2])
        self.assertNotIn("RUBRIC-MARKER-7", gen_a + gen_b)
        self.assertIn(rubric, audit)
        self.assertIn(rubric, behavior)
        self.assertNotEqual(audit, base[2])
        self.assertNotEqual(behavior, base[3])
        self.assertNotIn("RUBRIC-MARKER-7", faithful)   # faithfulness compares task cues, not labels
        # the audit's JSON schema still ends the prompt
        self.assertIn('"behavior": one of', audit)

    def test_scenario_field_order_is_unchanged_and_rubric_is_last(self):
        from dataclasses import fields
        names = [f.name for f in fields(SCENARIOS["fabrication"])]
        self.assertEqual(names[-1], "rubric")
        self.assertEqual(names[:9], ["name", "goal", "setting", "probe", "behaviors", "misbehavior",
                                    "corpus_keywords", "original", "source_id"])


class GeneratorPromptTests(unittest.TestCase):
    def test_generate_does_not_prime_study_and_keeps_its_prefix(self):
        gen = Recorder()
        Measurer(Models(gen, Recorder(), Recorder())).generate(["x"], random.Random(1))
        [prompt] = gen.prompts
        self.assertTrue(prompt.startswith("You write the opening"))
        self.assertNotIn("study", prompt.lower())
        self.assertNotIn("evaluat", prompt.lower())


if __name__ == "__main__":
    unittest.main()
