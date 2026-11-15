#!/usr/bin/env python3
"""Render a separate saved judge re-review, with original failures left visible. No APIs."""
import argparse,hashlib,json
from pathlib import Path
from html import escape

def obj(p):return json.loads(p.read_bytes())
def pretty(x):return escape(json.dumps(x,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--original',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 summary=obj(a.run/'summary.json');entries=summary['budget']['entries']
 if any(e['status']=='pending' for e in entries):raise ValueError('A request is pending')
 rows=summary['arms']
 if [r['arm'] for r in rows]!=['baseline','generic','profile']:raise ValueError('Require every declared condition, including not-run records')
 if a.out.exists():raise FileExistsError('Use a new output directory')
 body=['<header><p>AutoResearch / saved evidence</p><h1>A second review, with exact citations</h1><p class="notice">The original three primary reviews remain rejected. These are new judgments of the same saved traces, with line references converted into exact source quotations. No environment or target was rerun.</p><p>This checks the judging format. It cannot fix the environments, add independent trials, reveal private beliefs, or establish a profile benefit.</p></header><main>']
 body+=['<h2>Keep the two reviews separate</h2><div class="table"><table><tr><th>Condition</th><th>Original primary review</th><th>New review</th><th>New substantive status</th><th>New outcome label</th></tr>']
 artifacts={};pins={'summary.json':sha(a.run/'summary.json')}
 for row in rows:
  name=row['arm'];old=obj(a.original/name/'primary-review.json');saved=a.run/name/'additive-review.json';new=obj(saved) if saved.exists() else None;artifacts[name]=(old,new)
  if saved.exists():pins[str(saved.relative_to(a.run))]=sha(saved)
  nested=(new or {}).get('review',{})
  body+=['<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [name,old.get('status'),row['status'],nested.get('status','Unavailable'),nested.get('outcome',{}).get('label','No accepted judgment')])+'</tr>']
 body+=['</table></div><p>“Valid” means the judge marked the frozen scenario checks as passed and the mechanical validator accepted its citations. It is not a certification of realism or a reliable estimate of a personalization effect.</p>']
 for row in rows:
  name=row['arm'];old,new=artifacts[name];directory=a.run/name
  body+=['<section><h2>'+escape(name.title())+'</h2><p>Original status: <strong>'+escape(old.get('status','Unavailable'))+'</strong>. Its original file was not changed.</p>']
  if new:
   review=new['review'];body+=['<p><strong>New outcome:</strong> '+escape(review['outcome']['label'])+'</p><p>'+escape(review['outcome']['explanation'])+'</p><p><strong>Expressed awareness:</strong> '+escape(review['expressed_awareness']['label'])+'</p><p>'+escape(review['expressed_awareness']['explanation'])+'</p>']
   for concern in review.get('realism_concerns',[]):body+=['<p class="notice">'+escape(concern.get('severity',''))+': '+escape(concern.get('explanation',''))+'</p>']
   body+=['<details><summary>New judgment and exact reconstructed quotations</summary><pre>'+pretty(new)+'</pre></details>']
  else:
   body+=['<p class="notice">No accepted new judgment.</p>']
   for file in ['execution-error.json','validation-error.json']:
    if (directory/file).exists():body+=['<pre>'+pretty(obj(directory/file))+'</pre>']
  reply=directory/'raw-reply.txt'
  if reply.exists():body+=['<details><summary>Unmodified new judge reply</summary><pre>'+escape(reply.read_text())+'</pre></details>']
  body+=['<details><summary>Original rejected review record</summary><pre>'+pretty(old)+'</pre></details></section>']
 body+=['<section><h2>Calls and provenance</h2><p>Same GPT-5.1 judge, high reasoning, 32,000 maximum output tokens. One new call per condition at most; no retries. The full five original source strings were provided with numbered lines; no previous judgment or profile label was added.</p><pre>'+pretty({'calls':len(entries),'providers':summary['budget']['providers'],'originals_unchanged':summary['original_reviews_unchanged'],'settings':obj(a.run/'packet/settings.json')})+'</pre><p>The original pilot still has answer-revealing comments, unsupported report claims and incomplete deployment. Its older follow-up scores have unequal parse counts and clipping. These limitations do not disappear because citations now validate.</p></section></main>']
 css='*{box-sizing:border-box}body{margin:0;background:#f3ebdd;color:#111;font:17px/1.55 system-ui,sans-serif}header,main{max-width:1100px;margin:auto;padding:28px 32px}header{border-top:10px solid #b91d12}h1{font-size:clamp(32px,5vw,52px);line-height:1.1;letter-spacing:-.03em}h2{font-size:26px}.notice{padding:16px;background:#e8e3d6;border-left:5px solid #b91d12}.table{overflow:auto}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #b9b2a4;min-width:130px}section{margin-top:35px;padding-top:20px;border-top:2px solid #111}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:600px;overflow:auto;background:#e8e3d6;padding:16px;font:13px/1.5 monospace}summary{cursor:pointer;font-weight:600;padding:12px 0}details{border-top:1px solid #b9b2a4}p{max-width:85ch}@media(max-width:650px){header,main{padding:20px 16px}}'
 html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Additive review of saved shutdown traces</title><style>'+css+'</style>'+''.join(body)+'</html>'
 a.out.mkdir(parents=True);(a.out/'index.html').write_text(html);(a.out/'source-checksums.json').write_text(json.dumps(pins,indent=2)+'\n');print(json.dumps({'out':str(a.out),'html_sha256':sha(a.out/'index.html'),'calls':len(entries)}))
if __name__=='__main__':main()
