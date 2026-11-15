#!/bin/bash
# usage: map_one.sh <index into selection.json>
set -u
W=/Users/ethancai/Projects/Ongoing/AutoResearch/experiments/taste_petri/profiles/_work
i=$1
read -r slug file out < <(python3 -c "
import json;s=json.load(open('$W/selection.json'))[$i];print(s['slug'],s['file'],'$W/map/'+s['slug']+'/'+s['file'][:-4]+'.json')")
mkdir -p "$(dirname $out)"
[ -s "$out" ] && exit 0
python3 - "$i" > "$W/tmp_$i.txt" <<'PY'
import json,re,sys
W="/Users/ethancai/Projects/Ongoing/AutoResearch/experiments/taste_petri/profiles/_work"
s=json.load(open(W+"/selection.json"))[int(sys.argv[1])]
txt=open(s["path"],errors="ignore").read()
m=re.search(r"\n#+\s*References\s*\n|\nReferences\n",txt)
if m and m.start()>len(txt)*0.4: txt=txt[:m.start()]
txt=txt[:160000]
name=s["slug"].replace("_"," ").title()
p=open(W+"/map_prompt.txt").read().replace("{NAME}",name).replace("{TITLE}",s["title"]).replace("{DATE}",s["publishedDate"] or "undated").replace("{KIND}",s["kind"]).replace("{POS}",s["author_position"])
print(p+txt)
PY
cd /private/tmp/claude-501/-Users-ethancai-Projects-Ongoing-AutoResearch/414d2fe3-0b7c-4161-aca0-f3ceaeffeb26/scratchpad/run
claude -p --model sonnet --tools "" --strict-mcp-config --no-session-persistence --setting-sources "" \
  --system-prompt "You are a careful research-taste extraction assistant. Output only JSON." --output-format json \
  < "$W/tmp_$i.txt" > "$out.raw" 2> "$out.err"
echo "$(date +%H:%M:%S) map sonnet $slug $file exit=$?" >> "$W/calls.log"
python3 -c "
import json,re,sys
r=json.load(open('$out.raw'))['result']
r=r[r.find('{'):r.rfind('}')+1]
json.dump(json.loads(r),open('$out','w'),indent=1)
" && rm -f "$out.raw" "$out.err" "$W/tmp_$i.txt"
