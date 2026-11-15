"""Prospective morning structural checks around the unchanged native runtime.

The builder replacement is scoped to one run_arm call in a single-threaded
runner process. It changes no saved run, model, seed, target tool or judge.
"""
from contextlib import contextmanager
import json
import os

import run_matched as _legacy
from scripts.gio_recovery.scenario_check import check_environment


@contextmanager
def structural_setup_guard():
    """Record every proposed setup; reject hard failures before world mutation."""
    original_builder = _legacy.build_task

    def build_task(*args, **kwargs):
        task, world = original_builder(*args, **kwargs)
        original_configure = world.configure
        report_path = world.output_dir/'structural-setup-reports.jsonl'
        attempt = 0

        def configure(files, workspace_note, entrypoint=''):
            nonlocal attempt
            report = check_environment(files, workspace_note, entrypoint)
            attempt += 1
            record = {'attempt': attempt, 'phase': 'before_world_configure', 'report': report}
            with report_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n')
                stream.flush()
                os.fsync(stream.fileno())
            if report['hard_failures']:
                failures = json.dumps(report['hard_failures'], ensure_ascii=False, sort_keys=True)
                raise ValueError('Structural setup rejected: '+failures)
            return original_configure(files, workspace_note, entrypoint)

        world.configure = configure
        return task, world

    _legacy.build_task = build_task
    try:
        yield
    finally:
        _legacy.build_task = original_builder


def run_arm(arm, packet, out, settings, parent):
    """Use the established run unchanged, with one pre-target structural hook."""
    with structural_setup_guard():
        return _legacy.run_arm(arm, packet, out, settings, parent)
