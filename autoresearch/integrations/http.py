import json
import time
import urllib.error
import urllib.request


def post_json(url, body, headers, timeout=60, retries=3):
    data = json.dumps(body).encode()
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"content-type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"{url} -> HTTP {e.code}: {e.read()[:300]!r}")
