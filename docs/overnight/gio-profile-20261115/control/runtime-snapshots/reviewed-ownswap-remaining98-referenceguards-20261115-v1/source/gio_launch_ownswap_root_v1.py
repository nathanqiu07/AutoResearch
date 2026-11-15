import hashlib,importlib.util,os,subprocess,sys
from pathlib import Path
p=Path('/private/tmp/gio_diagnostic_runtime_envelope_ownswap_v1.py');assert hashlib.sha256(p.read_bytes()).hexdigest()=='f5efb857ca9b3954250acd620bf5c5f51ac1b7f6111b8424a7c52aeb5a49c10c'
i=Path('/private/tmp/gio-profile-20261115-coordinator/ownswap-execution-v1/envelope.json');sha='e03ec8a8fd8476d7eb62826d35b8fd286d725e2e59635013b1362bd647f7d0ea';assert hashlib.sha256(i.read_bytes()).hexdigest()==sha
phase1=Path('/Users/giordanorogers/.codex/worktrees/gio-overnight-pilot-runtime/AutoResearch-overnight-control');sys.path.insert(0,str(phase1));sys.dont_write_bytecode=True
s=importlib.util.spec_from_file_location('credential_parser',phase1/'docs/overnight/gio-profile-20261115/control/run_batch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
env=dict(os.environ);env.update(m.read_credentials('/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/.env'))
r=subprocess.run([sys.executable,'-B',str(p),'--envelope',str(i),'--envelope-sha256',sha],env=env);sys.exit(r.returncode)
