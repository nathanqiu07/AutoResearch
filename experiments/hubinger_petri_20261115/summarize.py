"""Export a small, auditable Hubinger-only comparison from saved Petri files."""
import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.run_root.resolve()
    out = Path(__file__).resolve().parent
    rows = []
    conditions = [(m, root / 'hubinger-recovery-01' / m, 2) for m in ('P2', 'P5', 'P8')]
    conditions += [(m, root / 'matched-controls' / m, 3)
                   for m in ('no_profile', 'generic', 'evan_hubinger-raw')]
    for condition, directory, count in conditions:
        for replicate in range(1, count + 1):
            source = directory / ('r' + str(replicate))
            summary = load(source / 'summary.json')
            primary = load(source / 'primary-review.json')
            initial = load(source / 'environment-review.json')
            capture = load(source / 'role-input-captures.json')
            native = load(source / 'native-sample.json').get('scores', {}).get('alignment_judge', {})
            values = native.get('value', {})
            row = {'condition': condition, 'local_replicate': replicate,
                   'original_planned_replicate': replicate + 1 if condition.startswith('P') else replicate,
                   'source': str(source.relative_to(root)),
                   'execution': summary.get('execution_status', 'pending'),
                   'primary_validity': primary.get('status', 'unmeasured'),
                   'initial_checks': {k: v.get('status') for k, v in initial.get('checks', {}).items()},
                   'initial_realism_concerns': len(initial['realism_concerns']) if 'realism_concerns' in initial else None,
                   'major_primary_concerns': sum(x.get('severity') == 'major' for x in primary['realism_concerns']) if 'realism_concerns' in primary else None,
                   'native_awareness_1_to_10': values.get('eval_awareness'),
                   'native_realism_1_to_10': values.get('scenario_realism'),
                   'expressed_awareness': primary.get('expressed_awareness', {}).get('label', 'unmeasured'),
                   'behavior': primary.get('outcome', {}).get('label', 'unmeasured'),
                   'profile_isolation': capture.get('status', 'unmeasured')}
            hashes = {}
            if summary:
                target = out / 'evidence' / condition / ('r' + str(replicate))
                target.mkdir(parents=True, exist_ok=True)
                for name in ('summary.json', 'primary-review.json', 'environment-review.json',
                             'role-input-captures.json', 'author-meta-diagnostic.json', 'audit.json'):
                    path = source / name
                    if path.is_file():
                        raw = path.read_bytes()
                        (target / name).write_bytes(raw)
                        hashes[name] = hashlib.sha256(raw).hexdigest()
                (target / 'native-judge.json').write_text(json.dumps(native, indent=2) + '\n')
            row['source_hashes'] = hashes
            rows.append(row)
    report = {'scope': 'Three frozen Hubinger profiles and three controls; no profile fidelity scoring.',
              'interrupted_original_profile_attempts': 3,
              'recovery_policy': 'Original profile r1 attempts remain interrupted/missing; new r1/r2 map to originally unstarted r2/r3.',
              'limitations': ['Small one-scenario pilot, not an established method ranking.',
                              'Judges are models; quoted provenance does not prove semantic correctness.',
                              'None-observed awareness is not proof of unawareness.',
                              'Shutdown interference is a behavior outcome, not an environment-quality score.',
                              'Missing or failed reviews are not zero scores or invalid environments.'],
              'rows': rows}
    (out / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Hubinger Petri comparison', '', report['scope'], '', report['recovery_policy'], '',
             '| Condition | Local run | Execution | Primary validity | Native awareness | Native realism | Initial concerns | Major primary concerns |',
             '|---|---:|---|---|---:|---:|---:|---:|']
    keys = ('condition', 'local_replicate', 'execution', 'primary_validity', 'native_awareness_1_to_10',
            'native_realism_1_to_10', 'initial_realism_concerns', 'major_primary_concerns')
    for row in rows:
        lines.append('| ' + ' | '.join(str(row[k]) if row[k] is not None else 'unmeasured' for k in keys) + ' |')
    lines += ['', 'Native ratings use a 1–10 scale. Lower awareness and higher realism are favorable ratings, not calibrated probabilities.', '']
    lines += ['- ' + text for text in report['limitations']]
    (out / 'comparison.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'completed': sum(r['execution'] == 'success' for r in rows), 'expected': len(rows)}))


if __name__ == '__main__':
    main()
