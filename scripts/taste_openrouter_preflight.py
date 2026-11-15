import getpass,json,time,urllib.request,urllib.error,hashlib
from pathlib import Path
MODEL='nvidia/nemotron-3-ultra-550b-a55b:free'
import argparse
parser=argparse.ArgumentParser(description='Two free OpenRouter calls; no paid auditor or judge.')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
out=args.output;out.mkdir(parents=True,exist_ok=False)
key=getpass.getpass('OpenRouter key (hidden): ')
report={'model':MODEL,'status':'started','requests':[],'scope':'two free target calls only; no auditor or paid judge'}
def call(path,body=None,auth=True):
 headers={'Content-Type':'application/json'}
 if auth:headers['Authorization']='Bearer '+key
 req=urllib.request.Request('https://openrouter.ai/api/v1/'+path,data=json.dumps(body).encode() if body else None,headers=headers)
 start=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=120) as r: data=json.load(r)
 except urllib.error.HTTPError as e:raise RuntimeError('OpenRouter HTTP '+str(e.code)) from None
 return data,time.monotonic()-start
try:
 data,_=call('key')
 account=data.get('data',{})
 report['free_quota']=account.get('free_model_daily_requests')
 report['is_free_tier']=account.get('is_free_tier')
 ep,_=call('models/'+MODEL+'/endpoints',auth=False)
 (out/'endpoint-metadata.json').write_text(json.dumps(ep,indent=2))
 ends=ep['data']['endpoints']
 assert any(float(e['pricing']['prompt'])==0 and float(e['pricing']['completion'])==0 and 'reasoning' in e['supported_parameters'] and 'tools' in e['supported_parameters'] for e in ends)
 messages=[{'role':'system','content':'You are an assistant answering questions about a fictional shop. Use the supplied tool for inventory facts. Be brief.'},{'role':'user','content':'We have 7 pending orders for notebooks. Check stock, then tell me whether we can fill them and how many notebooks will remain.'}]
 tool={'type':'function','function':{'name':'lookup_stock','description':'Look up the stock count for an item in a fictional shop.','parameters':{'type':'object','properties':{'item':{'type':'string'}},'required':['item'],'additionalProperties':False}}}
 common={'model':MODEL,'reasoning':{'enabled':True,'exclude':False},'provider':{'order':['nvidia'],'allow_fallbacks':False,'require_parameters':True,'max_price':{'prompt':0,'completion':0}},'max_tokens':4096,'temperature':0.6,'tools':[tool]}
 for index in range(2):
  body={**common,'messages':messages,'tool_choice':'required' if index==0 else 'none'}
  (out/f'request-{index+1}.json').write_text(json.dumps(body,indent=2))
  data,elapsed=call('chat/completions',body)
  (out/f'response-{index+1}.json').write_text(json.dumps(data,indent=2))
  if data.get('error'):raise RuntimeError('Endpoint returned error; raw response saved')
  msg=data['choices'][0]['message'];r=msg.get('reasoning') or msg.get('reasoning_content') or ''
  details=msg.get('reasoning_details',[])
  report['requests'].append({'seconds':elapsed,'provider':data.get('provider'),'model':data.get('model'),'finish_reason':data['choices'][0]['finish_reason'],'reasoning_chars':len(r),'reasoning_detail_types':[d.get('type') for d in details],'usage':data.get('usage'),'tool_calls':len(msg.get('tool_calls') or []),'answer':msg.get('content')})
  print(json.dumps(report['requests'][-1]),flush=True)
  assert data['choices'][0]['finish_reason']!='length','output truncated'
  assert r.strip() or any(d.get('text','').strip() for d in details),'no readable reasoning'
  if index==0:
   calls=msg.get('tool_calls') or [];assert len(calls)==1 and calls[0]['function']['name']=='lookup_stock'
   messages.append({k:v for k,v in msg.items() if k in ('role','content','tool_calls','reasoning','reasoning_details')})
   messages.append({'role':'tool','tool_call_id':calls[0]['id'],'content':json.dumps({'item':'notebooks','in_stock':12})})
  else:assert msg.get('content','').strip(),'no final answer'
 report['status']='api_check_passed'
except Exception as e:
 report['status']='failed';report['error']=type(e).__name__+': '+str(e)
finally:
 (out/'report.json').write_text(json.dumps(report,indent=2));print('Status:',report['status'],flush=True)
