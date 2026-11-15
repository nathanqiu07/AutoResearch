#!/usr/bin/env python3
"""Stand-in for `codex exec --json --output-last-message FILE -` that calls the OpenAI
Responses API directly with the same model Codex used (gpt-6-astra, high reasoning).
Used after the ChatGPT Codex plan hit its usage limit mid-build."""
import json, os, random, sys, time, urllib.error, urllib.request

MODEL = os.environ.get('SHIM_MODEL', 'gpt-6-astra')
EFFORT = os.environ.get('SHIM_EFFORT', 'high')


def emit(event):
    print(json.dumps(event), flush=True)


def main():
    args = sys.argv[1:]
    out = args[args.index('--output-last-message') + 1]
    prompt = sys.stdin.read()
    emit({'type': 'thread.started', 'shim': 'openai-responses-api', 'model': MODEL, 'reasoning': EFFORT})
    body = json.dumps({'model': MODEL, 'input': prompt, 'reasoning': {'effort': EFFORT},
                       'max_output_tokens': 128000}).encode()
    headers = {'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'], 'Content-Type': 'application/json'}
    last = None
    data = None
    for attempt in range(15):
        try:
            req = urllib.request.Request('https://api.openai.com/v1/responses', data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=2300) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            last = f'HTTP {e.code}: {e.read()[:500]!r}'
            if e.code not in (408, 409, 429, 500, 502, 503, 504):
                break
        except Exception as e:
            last = repr(e)
        print(f'retry {attempt + 1}: {last}', file=sys.stderr, flush=True)
        time.sleep(min(60, 5 * 2 ** attempt) + random.uniform(0, 15))
    if not data or data.get('status') != 'completed':
        emit({'type': 'error', 'message': last if not data else json.dumps(data)[:2000]})
        return 1
    text = ''.join(c.get('text', '') for o in data.get('output', []) if o.get('type') == 'message'
                   for c in o.get('content', []) if c.get('type') == 'output_text')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    u = data.get('usage', {})
    emit({'type': 'turn.completed', 'response_id': data.get('id'), 'model': data.get('model'),
          'usage': {'input_tokens': u.get('input_tokens'),
                    'cached_input_tokens': (u.get('input_tokens_details') or {}).get('cached_tokens'),
                    'output_tokens': u.get('output_tokens'),
                    'reasoning_output_tokens': (u.get('output_tokens_details') or {}).get('reasoning_tokens')}})
    return 0 if text.strip() else 1


if __name__ == '__main__':
    sys.exit(main())
