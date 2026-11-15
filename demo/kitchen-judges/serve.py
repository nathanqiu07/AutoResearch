"""Run the judges' copy of Profile Kitchen: David's studio server, serving this folder's frontend.

    python3 demo/kitchen-judges/serve.py            # then open http://127.0.0.1:8790/#/judges

The "Build your agent" and "Results" pages run entirely in the browser (no API calls, no cost).
The rest of the app is the original Profile Kitchen; pick the offline backend there to stay free.
Profiles judges create go to a scratch root (data/judges_researchers) so the team's are untouched.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from autoresearch.studio import server  # noqa: E402

server.STATIC = os.path.join(HERE, "static")

if __name__ == "__main__":
    args = sys.argv[1:] or ["--port", "8790", "--root", "data/judges_researchers"]
    server.main(args)
