"""Offline metadata audit; no .env, backend calls, ledger connection or writes to admissions."""
import collections, copy, hashlib, importlib.util, json, socket, sys
from decimal import Decimal
from pathlib import Path
sys.dont_write_bytecode = True
def forbidden(*args, **kwargs): raise AssertionError('offline_audit_forbids_side_effect')
socket.socket.connect = forbidden
socket.create_connection = forbidden
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
h = load('sol_admission_audit_helpers', '/private/tmp/gio_prepare_scaling_sol_v1.py')
require, read, digest = h.require, h.read, h.digest
INDEX = {'path':'/private/tmp/gio-scaling-sol-native-admissions-v1/ready-index.json','sha256':'ba96f2c68641e9d2f6bc281e8657f068ee88691261c016c5069b34b9240946e2'}
sys.path.insert(0, str(h.R))
driver = load('sol_audit_native_driver', h.R/h.DRIVER_REL)
from autoresearch.taste.overnight.backends import DollarLedger, OpenAIResponsesBackend, RATES
from autoresearch.taste.overnight.consumer import prepare_payload
from autoresearch.taste.overnight.runner import cache_key
OpenAIResponsesBackend.complete = forbidden
class OfflineLedger(DollarLedger):
    def __init__(self): pass
    _connect = reserve = finish = summary = forbidden

def audit():
    require(h.ref(h.R/h.DRIVER_REL)['sha256'] == h.DRIVER_SHA, 'frozen_driver_changed')
    driver.verify_runtime(h.R, h.COMMIT)
    index = read(INDEX); plan = read(h.PLAN); policy = read(index['policy'])
    deny = read(policy['unknown_request_denylist'])['identity_denylists']
    counts = []; records = []; jobids = []; leases = []
    require([a['block'] for a in index['admissions']] == h.BLOCKS, 'block_order')
    for admission, block in zip(index['admissions'], plan['tranches'][0]['batches']):
        batch = read(admission['prepared']); evidence = read(admission['evidence']); raw = read(admission['raw_batch'])
        require(batch['max_workers'] == 2 and batch['ledger'] == policy['ledger'] and batch['deadline'] == h.DEADLINE, 'batch_policy')
        require(len(batch['jobs']) == len(block['jobs']) == len(evidence['mapping']) == admission['jobs'], 'exact_job_count')
        require(not (h.B/'receipts'/batch['batch_id']/'execution').exists(), 'batch_started')
        subtotal = Decimal(0); requests = 0
        for packet_ref, row, mapping in zip(batch['jobs'], block['jobs'], evidence['mapping']):
            draft = read(row['packet']); packet = read(packet_ref)
            require(mapping['original_draft'] == row['packet'] and mapping['requests'] == row['requests'], 'evidence_order')
            require(draft['lease'] is None and 'job_id' not in draft['manifest'] and draft['manifest']['allocation']['authorization_source'] is None, 'original_draft_not_null')
            normalized = copy.deepcopy(packet)
            for key in ('profile','release'):
                require(Path(packet[key]['path']).read_bytes() == Path(draft[key]['path']).read_bytes(), 'snapshot_not_byte_identical')
                require(packet[key]['sha256'] == draft[key]['sha256'], 'source_pin_change')
                normalized[key] = draft[key]
            expected = h.bind(draft, index['policy'], index['predecessor'])
            require(normalized == expected, 'scientific_fields_changed')
            require(read(mapping['packet']) == expected, 'evidence_packet_changed')
            prepared = driver._prepare_packet(packet, batch, OfflineLedger())
            jid = packet['manifest']['job_id']; jobids.append(jid); leases.append(packet['lease']['lease_id'])
            require(not (h.B/'lease'/(jid+'.json')).exists() and not (h.B/'output'/jid).exists(), 'claimed_or_started')
            require(packet['backend']['model'] == 'gpt-6-sol' and packet['backend']['reasoning'] == 'medium' and packet['backend']['timeout'] == 60, 'settings_change')
            require(packet['config']['settings'] == {'temperature':0.0,'max_tokens':8192}, 'consumer_settings')
            require(packet['lease']['owner'] == 'gio-overnight-00' and packet['lease']['expires_at'] == h.DEADLINE, 'lease_scope')
            require(len(prepared['items']) == len(row['requests']) == packet['backend']['max_calls'], 'item_count')
            cost = Decimal(0)
            for item, pin in zip(prepared['items'], row['requests']):
                payload = prepare_payload(prepared['profile'], item['context'], item['options'], prepared['config'])
                body = {'model':'gpt-6-sol','instructions':payload['system'],'input':payload['prompt'],'max_output_tokens':8192,'reasoning':{'effort':'medium'},'store':False,'service_tier':'default','prompt_cache_options':{'mode':'implicit','ttl':'30m'}}
                wire = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
                endpoint_hash = hashlib.sha256(json.dumps({'endpoint':'https://api.openai.com/v1/responses','body':body},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                require(digest(body) == pin['request_sha256'] and endpoint_hash == pin['endpoint_body_sha256'] and hashlib.sha256(wire).hexdigest() == pin['wire_bytes_sha256'], 'actual_wire_pin_mismatch')
                require(item['item_id'] == pin['item_id'] and digest(item) == pin['item_sha256'] and item['option_order_id'] == pin['option_order_id'], 'item_pin_mismatch')
                require(len(wire)+1024 == pin['input_bound'], 'input_bound_mismatch')
                rates = [Decimal(v) for v in RATES['gpt-6-sol']]
                price = (Decimal(len(wire)+1024)*rates[0]+Decimal(8192)*rates[1])/Decimal(1000000)
                require(price == Decimal(pin['max_usd']), 'price_bound_mismatch'); cost += price
                require(pin['request_sha256'] not in deny['body_compact_json_sha256'] and endpoint_hash not in deny['endpoint_body_sorted_json_sha256'], 'unknown_collision')
                settings = dict(prepared['config']['settings'], system=payload['system'])
                require(cache_key(draft['manifest'],payload['prompt'],settings) == pin['draft_cache_key'], 'draft_cache_pin_mismatch')
                key = cache_key(packet['manifest'],payload['prompt'],settings)
                require(not (Path(batch['roots']['cache'])/(key+'.json')).exists(), 'existing_native_cache')
                records.append({'block':block['block'],'job_id':jid,'item_id':item['item_id'],'request_sha256':pin['request_sha256'],'endpoint_body_sha256':endpoint_hash,'wire_bytes_sha256':pin['wire_bytes_sha256'],'native_cache_key':key})
                requests += 1
            require(cost <= Decimal(str(packet['backend']['max_usd'])), 'job_cost_too_small')
            subtotal += Decimal(str(packet['backend']['max_usd']))
        require(subtotal == Decimal(block['max_usd']) and requests == admission['calls'], 'batch_count_or_cost')
        counts.append({'block':block['block'],'jobs':admission['jobs'],'requests':requests,'max_usd':str(subtotal)})
    require(len(jobids) == len(set(jobids)) == len(set(leases)) == 62 and len(records) == 140, 'duplicate_identity')
    require(len({r['native_cache_key'] for r in records}) == 140, 'cache_alias')
    by_hash = collections.defaultdict(list)
    for r in records: by_hash[r['request_sha256']].append(r)
    pairs = [rows for rows in by_hash.values() if len(rows)>1]
    require(len(by_hash) == 139 and len(pairs) == 1 and len(pairs[0]) == 2, 'unexpected_repeat')
    require([r['block'] for r in pairs[0]] == ['lexical_retrieval','semantic_retrieval'] and pairs[0][0]['item_id'] == pairs[0][1]['item_id'], 'repeat_scope')
    require(pairs[0][0]['request_sha256'] == plan['duplicates'][0]['request_sha256'], 'unplanned_repeat')
    return {'schema_version':'sol-admission-independent-replay-v1','state':'pass','index':INDEX,'runtime_commit':h.COMMIT,'blocks':counts,'jobs':62,'requests':140,'distinct_wire_bodies':139,'distinct_native_cache_keys':140,'all_source_and_profile_files_byte_identical':True,'all_scientific_fields_unchanged':True,'actual_body_endpoint_and_wire_bytes_pins_verified':140,'unknown_identity_collisions':0,'global_claims_and_results_absent':True,'existing_native_cache_files':0,'same_input_pair':pairs[0],'no_api_or_env_or_ledger_access':True,'records_sha256':digest(records)}
if __name__ == '__main__':
    result = audit(); destination = Path('/private/tmp/gio-scaling-sol-independent-review-v1')
    destination.mkdir(exist_ok=True)
    print(h.canonical(h.write(destination/'admission-replay.json',result)))
