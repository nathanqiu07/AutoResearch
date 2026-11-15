"""One frozen, explicitly authorized exploratory P8 swap; no general bypass.

The caller supplies exact evidence bytes, so validation is independent of paths
and repeated by the runner before its claim. This is cooperative coordinator
authorization, not a signature or a replacement for native lease/budget checks.
"""
import json
import re

from .contracts import (ProfileArtifact, digest, sha256_bytes, source_manifest,
                        validate_documents)

BINDING_SHA256 = '67e921d89f19815881119ad880cb04f0db1aa36e6fc3b36b39da82a9cb1a2e5a'
ORIGIN_SHA = 'f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca'
STUDY = 'exploratory-own-versus-swapped-p8-v1'
PEOPLE = ('chris_olah', 'neel_nanda')
RELEASE_SCOPE = 'Tier A primary descriptive; Tier B separately reported secondary; no confirmation panel'
PACKET_REFS = {'profile_source_release': 'donor_release',
               'assignment_binding': 'binding', 'assignment_authority': 'authority'}
EVIDENCE_KEYS = {'binding', 'authority', 'target_release', 'donor_release', 'profile'}
ITEM_FIELDS = {'item_id', 'researcher_id', 'context', 'options', 'option_order_id'}


def _require(condition, reason):
    if not condition:
        raise ValueError('cross-subject assignment: ' + reason)


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate evidence field')
        result[key] = value
    return result


def _json(raw):
    _require(type(raw) is bytes, 'immutable evidence bytes required')
    try:
        return json.loads(raw, object_pairs_hook=_object,
                          parse_constant=lambda _: _require(False, 'nonfinite evidence'))
    except (TypeError, UnicodeError, json.JSONDecodeError):
        raise ValueError('cross-subject assignment: invalid evidence JSON') from None


def declarations(binding):
    """Derive the two hash-only declarations, excluding root authority SHA."""
    _require(binding.get('schema_version') == 'exploratory-own-versus-swapped-p8-feasibility-binding-v1'
             and binding.get('frozen_runtime') == ORIGIN_SHA
             and binding.get('primary_config_id') == 'P8-c8192-explicit-only'
             and binding.get('execution_authorized') is False
             and binding.get('final_test_authorized') is False, 'wrong frozen evaluator binding')
    rows = binding['swapped_prospective_bindings']
    _require(isinstance(rows, list) and len(rows) == 28, 'exact 28 prospective slots required')
    result = []
    for target in PEOPLE:
        selected = [row for row in rows if row['target_researcher_id'] == target]
        _require(len(selected) == 14, 'exact 14 ordered target items required')
        first = selected[0]
        donor = next(person for person in PEOPLE if person != target)
        common = ('donor_researcher_id', 'target_researcher_id', 'donor_fit_release',
                  'true_donor_profile', 'true_donor_profile_id', 'true_donor_documents_hash',
                  'true_donor_source_manifest_hash', 'target_release', 'target_bundle_sha256',
                  'target_items_sha256')
        _require(all(row['donor_researcher_id'] == donor and
                     all(row[k] == first[k] for k in common) for row in selected),
                 'inconsistent donor/target assignment')
        ordered = [dict(item_id=row['target_item_id'], item_sha256=row['target_item_sha256'],
                        option_order_id=row['target_option_order_id']) for row in selected]
        _require(len({row['item_id'] for row in ordered}) == 14, 'duplicate target slot')
        result.append(dict(schema_version='declared-cross-subject-p8-v1', study=STUDY,
            condition='swapped', binding_sha256=BINDING_SHA256, donor_researcher_id=donor,
            target_researcher_id=target, profile_origin_code_sha=ORIGIN_SHA,
            donor_profile_id=first['true_donor_profile_id'],
            donor_profile_file_sha256=first['true_donor_profile']['sha256'],
            donor_release_sha256=first['donor_fit_release']['sha256'],
            donor_documents_hash=first['true_donor_documents_hash'],
            donor_source_manifest_hash=first['true_donor_source_manifest_hash'],
            target_release_sha256=first['target_release']['sha256'],
            target_bundle_sha256=first['target_bundle_sha256'],
            target_items_sha256=first['target_items_sha256'], ordered_items=ordered))
    return result


def _release(body, person):
    _require(isinstance(body, dict) and body.get('schema_version') == 'released-development-v2'
             and body.get('scope') == RELEASE_SCOPE and body.get('researcher_id') == person,
             'original target-only development release required')
    _require(not any(k in body for k in ('approved_peer_sources', 'peer_policy', 'parent_releases')),
             'peer derivative is not a swap source')
    docs = body['sources']['documents']
    sources = source_manifest(docs)
    _require(body['sources']['source_manifest'] == sources and
             body['sources']['allowed_source_manifest_hash'] == digest(sources), 'source manifest mismatch')
    validate_documents(docs, dict(researcher_id=person, allowed_sources=sources,
                                 allowed_source_manifest_hash=digest(sources)))
    items = body['items']
    _require(isinstance(items, list) and len(items) == 14 and digest(items) == body['items_sha256'],
             'full original target panel required')
    _require(all(isinstance(i, dict) and set(i) == ITEM_FIELDS and i['researcher_id'] == person
                 for i in items), 'label-free target fields required')
    _require(all(isinstance(i['item_id'], str) and i['item_id'] for i in items)
             and len({i['item_id'] for i in items}) == 14, 'unique target IDs required')
    return docs


def validate_assignment(manifest, config, profile, items, documents, evidence=None):
    """Return the verified declaration, or None for an ordinary unmodified job."""
    if 'profile_assignment' not in manifest:
        _require(evidence is None, 'evidence without declaration')
        return None
    try:
        return _validate_assignment(manifest, config, profile, items, documents, evidence)
    except (KeyError, TypeError, IndexError, AttributeError):
        raise ValueError('cross-subject assignment: malformed declaration or evidence') from None


def _validate_assignment(manifest, config, profile, items, documents, evidence):
    assignment = manifest['profile_assignment']
    _require(isinstance(assignment, dict) and isinstance(evidence, dict)
             and set(evidence) == EVIDENCE_KEYS, 'exact declaration and evidence required')
    _require(all(type(value) is bytes for value in evidence.values()), 'immutable evidence bytes required')
    hashes = {key: sha256_bytes(value) for key, value in evidence.items()}
    _require(hashes['binding'] == BINDING_SHA256, 'unapproved evaluator binding')
    binding = _json(evidence['binding'])
    expected = declarations(binding)
    core = {k: v for k, v in assignment.items() if k != 'authority_sha256'}
    _require(core in expected and set(assignment) == set(core) | {'authority_sha256'},
             'declaration differs from exact frozen assignment')
    for key, field in (('authority', 'authority_sha256'), ('profile', 'donor_profile_file_sha256'),
                       ('donor_release', 'donor_release_sha256'), ('target_release', 'target_release_sha256')):
        _require(hashes[key] == assignment[field], 'evidence file hash mismatch')
    authority = _json(evidence['authority'])
    _require(set(authority) == {'schema_version', 'state', 'authority', 'scope', 'binding_sha256',
                'runtime_code_sha', 'assignment_sha256s', 'max_calls', 'final_test_authorized'},
             'exact root authority fields required')
    runtime = manifest['code_sha']
    _require(isinstance(runtime, str) and re.fullmatch('[0-9a-f]{40}', runtime)
             and runtime != ORIGIN_SHA, 'explicit successor runtime required')
    _require(authority['schema_version'] == 'own-swapped-p8-authorization-v1'
             and authority['state'] == 'authorized' and isinstance(authority['authority'], str)
             and authority['authority'].strip() and authority['scope'] == STUDY
             and authority['binding_sha256'] == BINDING_SHA256 and authority['runtime_code_sha'] == runtime
             and authority['assignment_sha256s'] == sorted(digest(a) for a in expected)
             and type(authority['max_calls']) is int and authority['max_calls'] == 28
             and authority['final_test_authorized'] is False, 'root authority does not adopt both exact assignments')
    _require(manifest['campaign_id'] == 'gio-profile-20261115'
             and manifest['deadline'] == '2026-11-15T17:00:00Z'
             and manifest['stage'] == 'dev' and manifest['kind'] == 'predict'
             and manifest['method_id'] == 'P8' and type(manifest['personalization_cap']) is int
             and manifest['personalization_cap'] == 8192 and type(manifest['replicate_id']) is int
             and manifest['replicate_id'] == 0, 'only the frozen development P8 condition is permitted')
    _require(manifest['allocation']['authorization_source'] == hashes['authority']
             and manifest['allocation']['cost_mode'] == 'priced_api'
             and type(manifest['allocation']['max_calls']) is int and manifest['allocation']['max_calls'] == 14,
             'exact per-target allocation authority and 14-call ceiling required')
    donor = _json(evidence['donor_release'])
    target = _json(evidence['target_release'])
    donor_docs = _release(donor, assignment['donor_researcher_id'])
    _release(target, assignment['target_researcher_id'])
    _require(documents == donor_docs and digest(documents) == assignment['donor_documents_hash']
             and manifest['documents_hash'] == assignment['donor_documents_hash']
             and donor['sources']['allowed_source_manifest_hash'] == assignment['donor_source_manifest_hash']
             and manifest['source_manifest_hash'] == assignment['donor_source_manifest_hash'],
             'honest donor source provenance required')
    saved = ProfileArtifact.from_dict(_json(evidence['profile']))
    _require(isinstance(profile, ProfileArtifact) and saved.to_dict() == profile.to_dict()
             and profile.profile_id == assignment['donor_profile_id'] and profile.code_sha == ORIGIN_SHA
             and profile.researcher_id == assignment['donor_researcher_id']
             and profile.documents_hash == assignment['donor_documents_hash']
             and profile.allowed_source_manifest_hash == assignment['donor_source_manifest_hash']
             and profile.status == 'complete' and profile.method_id == 'P8'
             and profile.personalization_cap == 8192 and type(profile.replicate_id) is int
             and profile.replicate_id == 0 and profile.config.get('evidence_policy') == 'explicit-only',
             'unchanged complete original donor profile required')
    validate_documents(documents, profile.config)
    _require(items == target['items'] and digest(items) == assignment['target_items_sha256']
             and target['target_bundle_sha256'] == assignment['target_bundle_sha256'], 'target panel differs')
    _require([dict(item_id=i['item_id'], item_sha256=digest(i), option_order_id=i['option_order_id'])
              for i in items] == assignment['ordered_items'], 'target item/order differs')
    settings = binding['consumer_and_settings']
    _require(manifest['consumer'] == settings['consumer'] and config.get('settings') == settings['settings'],
             'consumer identity or settings differs from original condition')
    from .consumer import PROMPT_VERSION, implementation_hash, prepare_payload
    expected_config = dict(method_implementation_hash=profile.method_implementation_hash,
        renderer_implementation_hash=implementation_hash(), profile_prompt_version=profile.prompt_version,
        consumer_prompt_version=PROMPT_VERSION, settings=settings['settings'])
    _require(config == expected_config, 'exact original prediction config required')
    for item in items:
        prepare_payload(profile, item['context'], item['options'], config)
    return assignment


def validate_assignment_batch(jobs, max_total_attempts):
    """The declared intervention is exactly two complementary 14-item jobs."""
    assigned = [j['manifest'].get('profile_assignment') for j in jobs]
    if not any(a is not None for a in assigned):
        return
    _require(len(assigned) == 2 and all(isinstance(a, dict) for a in assigned),
             'both assignments, without mixed ordinary jobs, are required')
    _require({a['target_researcher_id'] for a in assigned} == set(PEOPLE)
             and len({a['authority_sha256'] for a in assigned}) == 1
             and type(max_total_attempts) is int and max_total_attempts == 28,
             'exact complementary 28-slot batch required')
