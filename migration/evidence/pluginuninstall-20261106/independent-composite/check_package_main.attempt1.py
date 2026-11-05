from pathlib import Path
import json,hashlib,collections
root=Path('/Users/accidia/projects/light-media-plugins');out=Path(__file__).resolve().parent;work=root/'work/migration-20261105/pluginuninstall-packaging-20261106';sha=lambda b:hashlib.sha256(b).hexdigest();raw=work/'package-main-harvest';m=json.loads((raw/'manifest.json').read_text());assert len(m['files'])==6
for r in m['files']:p=raw/r['path'];assert sha(p.read_bytes())==r['sha256'] and p.stat().st_size==r['bytes']
cmd=json.loads((raw/'package-main-1-command.json').read_text());assert cmd['exit_code']==0
obs=[json.loads(l) for l in (raw/'package-main-1/runtime/evidence/observations.jsonl').read_text().splitlines()];complete=next(r['value'] for r in obs if r['event']=='pui_canonical_package_complete');assert complete['canonical_zip_sha256']=='45865b1b617ae5eee8916f2ebf6da147c25ce0b608bc76dc8abee5641be9fc8d' and complete['verified_installed_members']==7 and complete['all_workers_joined']==3
assert complete['clone_config_KV_retained'] and complete['base_independent'] and complete['canonical_platform_clone_source_removed']
bind=json.loads((work/'package-main-driver-binding.json').read_text());assert bind['before']==bind['after']
for p,h in bind['before'].items():assert sha((root/p).read_bytes())==h,p
# Verify raw input pins, not solely the test's descriptive completion field.
assert '8305d765055b80f80bdcdc7ad8cfc14857da24c5abcccd54d9ec4e1c6b65fd7b' in json.dumps(cmd)
report={'raw_manifest_sha256':sha((raw/'manifest.json').read_bytes()),'raw_files':6,'main_exit':0,'main_reported_seconds':3.46,'driver_source_sha256':sha((root/'tests/integration/pluginuninstall_package_main_test.go').read_bytes()),'driver_reproduction_binding_sha256':sha((work/'package-main-driver-binding.json').read_bytes()),'driver_bound_inputs':len(bind['before']),'observations':len(obs),'event_counts':dict(collections.Counter(r['event'] for r in obs)),'completion':complete,'host_sha256':'8305d765055b80f80bdcdc7ad8cfc14857da24c5abcccd54d9ec4e1c6b65fd7b','classification':'independently read source-derived driver assertions and original actual Main ZIP observations; reviewer did not rerun Main'}
(out/'canonical-main-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
