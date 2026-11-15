"""Small live integration check: saved taste -> proposal -> choice -> environment -> score.

Uses current checkout's research code with an explicit saved-model runtime checkout.
No training data, validation data, or held-out data are loaded.
"""
import argparse
from dataclasses import asdict
import getpass
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--taste-runtime', type=Path, required=True)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-usd', type=float, default=1.)
    p.add_argument('--check-only', action='store_true')
    p.add_argument('--resume-from', type=Path, help='reuse saved proposals/advice after an abstention')
    args = p.parse_args()
    if not 0 < args.max_usd <= 1:
        p.error('this smoke runner is capped at $1 total')
    # Only the taste package comes from the model's runtime; research modules stay current.
    import autoresearch.taste
    autoresearch.taste.__path__.insert(0, str(args.taste_runtime.resolve() / 'autoresearch' / 'taste'))
    from autoresearch.llm import Budget
    from autoresearch.taste.backends import OpenAILLM
    from autoresearch.taste.paper_backend import PaperOpenAILLM
    from autoresearch.research.advisor import TasteAdvisor, load_user_model
    from autoresearch.research.ideas import Proposer
    from autoresearch.research.measure import Measurer, Models, METRIC_INFLATION

    worker = OpenAILLM(budget=Budget(max_calls=40, max_seconds=600), max_usd=args.max_usd * .8)
    preference = PaperOpenAILLM(budget=Budget(max_calls=8, max_seconds=600),
                               max_usd=args.max_usd * .2, max_request_attempts=3)
    model, source = load_user_model(str(args.model_dir), None, llm=preference)
    advisor = TasteAdvisor(model, source=source)
    principles = advisor.principles()
    if not principles:
        raise ValueError('this smoke requires a model with extracted principles')
    revision = lambda path: subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
    report = dict(status='preflight', research_revision=revision(ROOT),
                  taste_revision=revision(args.taste_runtime), source=source,
                  model_sha256=hashlib.sha256((args.model_dir/'usermodel.json').read_bytes()).hexdigest(),
                  principles=principles, model=worker.label, seed=20261115,
                  limits={'worker_usd':worker.max_usd,'preference_usd':preference.max_usd},
                  limitations=['Single sample per arm; no causal or significance claim.',
                              'All roles use GPT-6 Luna, not the configured Tinker target or independent judge.',
                              'Default awareness probes are uncalibrated for this model.',
                              'Tool-less single-turn environment, not the Petri multi-turn harness.',
                              'Researcher labels were AI-inferred; confidence is not calibrated.',
                              'This exercises proposal, advisor, generation and scoring, not the full accept/confirm loop.'],
                  heldout_accessed=False)
    if args.check_only:
        print(json.dumps(report, indent=2)); return
    if args.output.exists():
        raise ValueError('output already exists; preserve previous runs')
    args.output.mkdir(parents=True)
    if not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = getpass.getpass('OpenAI API key (hidden): ')
    trace = args.output/'requests.jsonl'
    model.trace_path = args.output/'preference.jsonl'
    preference.retry_path = str(args.output/'preference-retries.jsonl')
    preference.recovery_path = str(args.output/'preference-envelopes.jsonl')
    original = worker.complete
    def logged(prompt, **kwargs):
        entry = dict(prompt=prompt, settings=kwargs)
        try:
            text = original(prompt, **kwargs); entry['response']=text; return text
        except Exception as e:
            entry['error']=str(e); raise
        finally:
            with trace.open('a') as f: f.write(json.dumps(entry)+'\n')
    worker.complete = logged
    def save():
        report['budgets']=[worker.cost_summary(),preference.cost_summary()]
        report['calls'] = worker.budget.calls + preference.budget.calls
        report['advisor_errors']=advisor.errors
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    try:
        sc = METRIC_INFLATION
        proposer = Proposer(worker, None, random.Random(20261115),
                            taste_text='Researcher preference principles:\n'+'\n'.join(principles))
        if args.resume_from:
            prior = json.loads(args.resume_from.read_text())
            if prior['model_sha256'] != report['model_sha256'] or prior.get('advisor_errors'):
                raise ValueError('resume model mismatch or prior advisor error')
            for key in ('proposals','proposal_gate_rejections','advice','taste_scores'):
                report[key] = prior[key]
            report['resumed_from_sha256'] = hashlib.sha256(args.resume_from.read_bytes()).hexdigest()
        else:
            ideas = proposer.propose(sc.goal, sc.probe, [], set(), [], [], k=2, setting=sc.setting)
            report['proposals']=[i.to_dict() for i in ideas]
            report['proposal_gate_rejections']=proposer.gated
            if len(ideas)!=2 or any(i.origin!='llm' for i in ideas):
                raise ValueError('expected two live-generated proposals; library fallback is not a successful smoke')
            scores, advice = advisor.d1_scores(sc.goal+'\n'+sc.setting+'\n'+sc.probe,
                                              [i.text for i in ideas], [i.features for i in ideas])
            report.update(advice=asdict(advice), taste_scores=scores)
            if advisor.errors:
                raise ValueError('advisor prediction failed')
        advice = report['advice']
        index = advice['choice'] if advice['usable'] and advice['choice'] is not None else 0
        report['selection_source'] = 'user_model' if advice['usable'] else 'first_proposal_fallback_after_abstention'
        selected = report['proposals'][index]
        report['selected']=selected; save()
        print('Selected (%s): %s' % (report['selection_source'], selected['text']), flush=True)
        measurer = Measurer(Models(worker, worker, worker), scenario=sc, workers=1, mode='dev')
        report['samples']={}
        for arm, interventions in [('baseline',[]), ('icai',[selected['text']])]:
            sample = measurer.sample(interventions, seed=20261115)
            row = sample.to_dict(); row['response']=sample.response
            row['setting_check']=proposer.env_setting_check(sample.env,sc.setting)
            report['samples'][arm]=row; save()
            print(arm, 'score=',sample.score,'behavior=',sample.behavior,'error=',sample.error,flush=True)
            if sample.behavior=='error' or not sample.env.get('user') or not row['setting_check'][0]:
                raise ValueError('sample failed generation, scoring, or setting check; see report')
        report['status']='complete'
    except Exception as exc:
        report.update(status='failed', error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        save()
        print(json.dumps({'status':report['status'],'calls':report['calls'],'budgets':report['budgets']},indent=2))

if __name__=='__main__': main()
