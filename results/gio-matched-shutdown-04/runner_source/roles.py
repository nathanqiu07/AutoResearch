"""Native Inspect role factory, shared by future runner and offline transport checks.
Constructing models does not generate text. No Modal or fallback model path.
"""
from inspect_ai.model import GenerateConfig, get_model
from preflight import AUDITOR, TARGET, routing

def roles(api_key=None, openai_key=None):
    common=dict(max_retries=0, timeout=120, cache=False)
    return {
      'auditor':get_model('openrouter/'+AUDITOR, api_key=api_key, max_retries=0, memoize=False,
          provider=routing('auditor'), config=GenerateConfig(max_tokens=4096,temperature=0.7,**common)),
      'target':get_model('openrouter/'+TARGET, api_key=api_key, max_retries=0, memoize=False,
          provider=routing('target'), reasoning_enabled=True,
          config=GenerateConfig(max_tokens=16384,temperature=0.7,**common)),
      'judge':get_model('openai/gpt-5.1', api_key=openai_key, max_retries=0, memoize=False,
          config=GenerateConfig(max_tokens=32000,reasoning_effort='high',**common))}
