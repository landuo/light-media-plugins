from pathlib import Path
import json,hashlib,subprocess
r=Path.cwd();p=r/'work/migration-20261105/sdk98-impact-20261105';commit=subprocess.check_output(['git','rev-parse','16c572e'],text=True).strip();origin=json.loads(subprocess.check_output(['git','show',commit+':SDK_ORIGIN.json']));assert len(origin['files'])==95
cur=json.loads((r/'SDK_ORIGIN.json').read_text());assert hashlib.sha256((r/'SDK_ORIGIN.json').read_bytes()).hexdigest()=='40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875'
snapshot=p/'sdk95';snapshot.mkdir(exist_ok=True);replace={};bindings={}
for f in origin['files']:
 raw=subprocess.check_output(['git','show',commit+':'+f['path']]);assert hashlib.sha256(raw).hexdigest()==f['sha256'];target=snapshot/f['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);replace[str(r/f['path'])]=str(target);bindings[f['path']]=f['sha256']
added=[f['path'] for f in cur['files']if f['path']not in bindings]
for path in added:replace[str(r/path)]=''
(p/'sdk95-git-binding.json').write_text(json.dumps({'classification':'one shared test-only complete SDK95 Gitblob snapshot; no per-plugin SDK/framework copies','commit':commit,'Origin_sha256':hashlib.sha256(subprocess.check_output(['git','show',commit+':SDK_ORIGIN.json'])).hexdigest(),'files':bindings,'excluded_new':added},indent=2)+'\n')
paths=['plugins/torrenttransfer/protocol_budget_test.go','cmd/torrent-transfer/main_test.go','cmd/site-statistic/main_test.go','cmd/site-statistic/lifecycle_test.go']
for variant in ['95','98']:
 v=p/('variant'+variant);v.mkdir(exist_ok=True);m=dict(replace)if variant=='95'else{}
 for path in paths:
  src=r/path;raw=src.read_text();rep=raw.replace('../../work/migration-20261105/torrenttransfer/sdk-observations',str(v/'tt-observations')).replace('../../work/migration-20261105/torrenttransfer',str(v/'tt-cmd')).replace('../../work/migration-20261105/sitestatistic-preparation',str(v/'site-observations'))
  dst=v/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(rep);m[str(src)]=str(dst)
 (p/('overlay'+variant+'.json')).write_text(json.dumps({'Replace':m},indent=2)+'\n')
print({'old_commit':commit,'old_count':95,'new_count':len(cur['files']),'excluded':added})
