import hashlib,importlib.util,os,subprocess,sys
from pathlib import Path
p=Path('/private/tmp/gio_reference_first8_observed_v4.py');assert hashlib.sha256(p.read_bytes()).hexdigest()=='5de4233b8d4d8f190873a463a57b49dcb57ff20c513e6a3d86229fe895a21b82'
i=Path('/private/tmp/gio-profile-20261115-coordinator/reference-first8-authorization-v4/dispatch.json');sha='ff0b0f38eb879da18e9f7933a03bc34da4d66e6a2c53cb587c6b619fb9965706';assert hashlib.sha256(i.read_bytes()).hexdigest()==sha
phase1=Path('/Users/giordanorogers/.codex/worktrees/gio-overnight-pilot-runtime/AutoResearch-overnight-control');sys.path.insert(0,str(phase1));sys.dont_write_bytecode=True
s=importlib.util.spec_from_file_location('credential_parser',phase1/'docs/overnight/gio-profile-20261115/control/run_batch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
env=dict(os.environ);env.update(m.read_credentials('/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/.env'))
r=subprocess.run([sys.executable,'-B',str(p),'--dispatch',str(i),'--dispatch-sha256',sha],env=env);sys.exit(r.returncode)
