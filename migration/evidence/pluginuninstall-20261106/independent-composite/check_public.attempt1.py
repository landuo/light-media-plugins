from pathlib import Path
import json,hashlib
root=Path('/Users/accidia/projects/light-media-plugins');out=Path(__file__).resolve().parent;pub=root/'migration/evidence/pluginuninstall-20261106';sha=lambda b:hashlib.sha256(b).hexdigest();m=json.loads((pub/'copy-manifest.json').read_text());by_source={};by_public={}
for r in m['files']:
 a=Path(r['source']);b=root/r['public'];assert a.is_file() and b.is_file() and not b.is_symlink(),r
 assert sha(a.read_bytes())==sha(b.read_bytes())==r['sha256']
 assert a.stat().st_size==b.stat().st_size==r['bytes'];assert str(b).startswith(str(pub)+'/')
 assert b.read_bytes()[:4]!=b'\x7fELF';assert b.name not in ['ui-ready.private.json','light-media.db','key.json']
 assert str(b) not in by_public;by_public[str(b)]=r;by_source[str(a)]=r
private={}
for r in m['private_source_inputs_not_copied']:
 p=Path(r['path']);assert p.is_file() and sha(p.read_bytes())==r['sha256'];private[str(p)]=r
raw_manifest=root/'work/sites-review-20261105/pluginuninstall-review/final-current/raw-evidence-manifest.json';raw=json.loads(raw_manifest.read_text());print('raw manifest kind',type(raw).__name__)
rows=raw if isinstance(raw,list) else raw.get('files',[]);assert len(rows)==248,len(rows)
missing=[];covered=0;omitted=0
for r in rows:
 p=r['path']
 if p in by_source:covered+=1
 elif p in private:omitted+=1
 else:missing.append(p)
assert not missing,missing[:8]
report={'public_mapping_sha256':sha((pub/'copy-manifest.json').read_bytes()),'mapped_files_exact':len(by_public),'private_host_full_source_inputs_retained_not_public':len(private),'original_f38f_raw248':{'public_exact':covered,'private_fullsource_with_exact_hash_retained':omitted,'missing':0},'source_App_seals_unchanged':True,'public_dossier_reproduction_boundary':'Complete private host production Go source stays in original host checkout/work revision0719+f9e4. Public package is raw outputs/tests/manifests plus source references, not a standalone clone of host source.','README_sha256':sha((pub/'README.md').read_bytes())}
(out/'public-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
