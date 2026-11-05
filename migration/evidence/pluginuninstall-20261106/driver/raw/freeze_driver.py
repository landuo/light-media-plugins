import pathlib,json,hashlib,subprocess
root=pathlib.Path('/Users/accidia/projects/light-media-plugins');r=root/'work/migration-20261105/pluginuninstall-main-driver-20261105'
def info(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
source=[root/'tests/integration/pluginuninstall_main_test.go',root/'tests/integration/pluginuninstall_helpers_test.go',root/'tests/integration/testhost_main_test.go',r/'probe/main.go',r/'probe/main_test.go',r/'plugin-version-2.2.1.go',r/'manifest-update-overlay.json',r/'run_checks.py',r/'source-map.md']
bind=json.load(open(r/'check-input-binding.json'));assert bind['all_inputs_stable'] and bind['before']==bind['after']
for rel,data in bind['after'].items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==data['sha256'],rel
commands=json.load(open(r/'commands.json'));assert len(commands)==14 and all(x['exit_code']==0 for x in commands)
private=json.load(open(root/'work/migration-20261105/pluginuninstall-20261105/private-files-final.json'))
assert len(private['files'])==18
assert all(hashlib.sha256(pathlib.Path(p['path']).read_bytes()).hexdigest()==p['sha256'] for p in private['files'])
assert hashlib.sha256((root/'SDK_ORIGIN.json').read_bytes()).hexdigest()=='40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875'
frozen=r/'frozen-driver-source';frozen.mkdir(exist_ok=False)
for p in source:
 target=frozen/(p.name if 'probe' not in p.parts else 'probe-'+p.name);target.write_bytes(p.read_bytes())
artifacts=[r/'pluginuninstall-main-linux.test',r/'owned-pui-fixture-linux',r/'plugin-uninstall-2.2.1-linux',root/'work/migration-20261105/pluginuninstall-20261105/plugin-uninstall-linux',root/'work/migration-20261105/shared-acceptance-inputs/mp-server-status-linux-amd64']
raw=[p for p in sorted(r.iterdir()) if p.is_file() and (p.suffix in ['.json','.jsonl','.stdout','.stderr','.md','.py'] or p.name.endswith('overlay.json')) and p.name!='freeze.json']
result={'classification':'driver frozen; ordinary Main, native permissions, cold states and browser NOT executed; coordinator requires newly reviewed host, superseded7a08 rejected','sources':[info(p) for p in source],'artifacts':[info(p) for p in artifacts],'commands':commands,'local':{'driver_normal':{'passed':29,'opt_in_Main_skipped':1,'failed':0},'driver_race':{'passed':29,'opt_in_Main_skipped':1,'failed':0},'owned_probe_normal':{'passed':1},'owned_probe_race':{'passed':1},'vets':2,'Linux_builds':3},'source_input_count':len(bind['before']),'SDK_ORIGIN':info(root/'SDK_ORIGIN.json'),'producer18_unchanged':True,'raw':[info(p) for p in raw],'expected_Main':{'new_reviewed_host_SHA':'required via PLUGINUNINSTALL_EXPECT_HOST_SHA256; coordinator final binding pending','port':36258,'uid':1000,'UI_barrier_minutes':50,'test_timeout_minutes':70,'network':'owned executable repositories; no MPS page/dashboard'},'preserved_harness_failures':['initial-driver-build-failure.json','probe-before-schema-fix.jsonl'],'executed_Main':False,'executed_NAS':False,'executed_browser':False}
(r/'freeze.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(info(r/'freeze.json'))
