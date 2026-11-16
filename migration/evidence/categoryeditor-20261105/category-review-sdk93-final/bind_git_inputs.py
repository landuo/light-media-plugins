from pathlib import Path
import json,hashlib,subprocess
R=Path(__file__).resolve().parent;root=R.parents[2];host=Path('/Users/accidia/projects/light-media')
origin=json.loads((root/'SDK_ORIGIN.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest();rows=[]
for item in origin['files']:
 commit=item.get('source_commit',origin['source_commit']);objectid=commit+':'+item['source_path'];blob=subprocess.check_output(['git','show',objectid],cwd=host);target=(root/item['path']).read_bytes();assert sha(blob)==item['source_sha256'],objectid
 expected=blob
 if item['changes']:
  assert item['changes']==['module_import_relocation'],item
  for relocation in origin['allowed_changes']:expected=expected.replace(relocation['from'].encode(),relocation['to'].encode())
 assert expected==target,item['path'];assert sha(target)==item['sha256'],item['path']
 rows.append({'path':item['path'],'source_path':item['source_path'],'commit':commit,'git_blob_oid':subprocess.check_output(['git','rev-parse',objectid],cwd=host,text=True).strip(),'source_sha256':sha(blob),'target_sha256':sha(target),'exact_with_declared_import_relocation':True})
report={'kind':'actual local host Git blobs, not worktree file assumptions or remote/push claims','host_repository':str(host),'origin_sha256':sha((root/'SDK_ORIGIN.json').read_bytes()),'origin_head_source_commit':origin['source_commit'],'files':rows,'count':len(rows),'no_host_product_edits':True}
(R/'sdk93-git-binding.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'files':len(rows),'commits':sorted(set(x['commit'] for x in rows)),'all_exact':True}))
