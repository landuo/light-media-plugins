from pathlib import Path
import copy, hashlib, json, sys
here=Path(__file__).resolve().parent
source=json.loads((here/'source-observations.json').read_text())['cases']
target=json.loads((here/'target-observations.json').read_text())['cases']
differences=[];checks=0
assert len(source)==len(target)
for original,migrated in zip(source,target):
    assert original['id']==migrated['id']
    assert len(original['observations'])==len(migrated['observations'])
    for n,(a,b) in enumerate(zip(original['observations'],migrated['observations'])):
        a=copy.deepcopy(a);a.pop('source_error_type')
        for key in a:
            checks+=1
            if a[key]!=b[key]: differences.append(dict(id=original['id'],step=n,field=key,source=a[key],target=b[key]))
report=dict(cases=len(source),steps=sum(len(c['observations']) for c in source),field_comparisons=checks,differences=differences,passed=not differences,scope='Exact source plugin vs target Handle; synthetic dependencies and actual owned file IO only; not host installation/browser/cache acceptance',files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(here.iterdir()) if p.is_file() and p.name!='comparison.json'})
(here/'comparison.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n')
print(json.dumps(dict(cases=report['cases'],steps=report['steps'],field_comparisons=checks,differences=len(differences),passed=not differences)))
if differences: print(json.dumps(differences[:10],ensure_ascii=True,indent=2));sys.exit(bool(differences))
