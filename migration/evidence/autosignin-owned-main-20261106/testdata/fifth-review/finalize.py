from pathlib import Path
import json,hashlib,subprocess,datetime
P=Path('/Users/accidia/projects/light-media-plugins');H=Path('/Users/accidia/projects/light-media');r=P/'work/autosignin-owned-main-20261106-r5';w=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[r/'builds.json',r/'driver-overlay.json',r/'empty-main-bundle.json',r/'empty-main-actual/command.json',r/'empty-main-actual/actual-main.stdout',r/'empty-main-actual/actual-main.stderr',r/'empty-main-actual/runtime/evidence/observations.jsonl',r/'empty-main-actual/runtime/evidence/host-1.log',r/'empty-main-actual/runtime/evidence/host-2.log',P/'work/autosignin-real-integration-20261106/autosignin_owned_site_main_test.go',P/'tests/integration/testhost_main_test.go',P/'tests/integration/pluginuninstall_helpers_test.go',P/'work/independent-owned-main-r4-review-20261106/fixed-primary-facts.json',P/'work/migration-20261105/source-snapshot/autosignin/__init__.py',H/'internal/app/plugin_original_uninstall.go',H/'internal/app/plugin_original_install.go',H/'internal/app/plugin_original_reset.go',H/'internal/app/plugin_original_lifecycle.go']
binary=[]
for row in json.loads((r/'builds.json').read_text()):
 n=row['name'];b=json.loads((r/(n+'-before.json')).read_text());a=json.loads((r/(n+'-after.json')).read_text());assert b==a and row['exit']==0 and row['stable'];inputs.extend(r/(n+'-'+v+'.json')for v in ['before','after']);p=r/n;assert sha(p)==row['sha256'];info=subprocess.check_output(['go','version','-m',str(p)]);(w/(n+'-buildinfo.txt')).write_bytes(info);ls=subprocess.run(['lsof','-Fpn','--',str(p)],capture_output=True);assert ls.returncode in [0,1];(w/(n+'-lsof.stdout')).write_bytes(ls.stdout);(w/(n+'-lsof.stderr')).write_bytes(ls.stderr);binary.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'buildinfo_sha256':hashlib.sha256(info).hexdigest(),'local_lsof_exit':ls.returncode,'local_lsof_no_handles':not bool(ls.stdout),'inputs':len(b),'before_after_equal':True});inputs.append(p)
assert binary[0]['sha256']=='a4524236b3bad3462f640958ad56a170759558d69ff038ce56953ba38f648918'and binary[1]['sha256']=='b0a9a175e3b6d61b1a9158d4638f9a3c6639291f93879da11f5cbf157e5c6963'and binary[2]['sha256']=='4114b0d78934ac7c69daecb157ad1607db3e7e765436c0292b8eb166e14696d9'
(w/'binary-readback.json').write_text(json.dumps(binary,indent=2)+'\n')
driver=P/'work/autosignin-real-integration-20261106/autosignin_owned_site_main_test.go';(w/'r5-driver.go.txt').write_bytes(driver.read_bytes());assert json.loads((r/'driver-before.json').read_text())[str(driver)]==sha(driver)
rows=[json.loads(x)for x in(r/'empty-main-actual/runtime/evidence/observations.jsonl').read_text().splitlines()];pids=[x for x in rows if x['event']=='pui_worker_pids'];expected=[{'AutoSignIn':2680611,'AutoSignIncopy':2680669},{'AutoSignIn':2680611,'AutoSignIncopy':2680669},{},{'AutoSignIn':2680707,'AutoSignIncopy':2680715},{'AutoSignIncopy':2680715},{'AutoSignIn':2680727,'AutoSignIncopy':2680715},{'AutoSignIn':2680765,'AutoSignIncopy':2680715},{'AutoSignIn':2680765},{}];assert [x['value']for x in pids]==expected
labels=['clone_two_workers','save_keeps_workers','cold_stop_no_workers','cold_new_workers','ordinary_uninstall_clone_survives','reinstall_base_new_clone_same','reset_base_new_clone_same','clone_uninstall_base_survives','final_uninstall_no_workers'];stages=[{'stage':s,**x}for s,x in zip(labels,pids)];unique=sorted({pid for x in pids for pid in x['value'].values()});assert len(unique)==6
starts=[x for x in rows if x['event']=='main_start'];exits=[x for x in rows if x['event']=='main_exit'];assert [x['value']['pid']for x in starts]==[2680553,2680696]and[x['value']['pid']for x in exits]==[2680553,2680696]and all(x['value']['error']=='<nil>'for x in exits)
http=[x for x in rows if x['event']=='http'];peer=next(x for x in rows if x['event']=='owned_peer_observations');att=[x for x in peer['value']if x['path']=='/attendance.php'];assert len(att)==1 and att[0]['method']=='GET'and att[0]['cookie']=='owned_session=synthetic'and att[0]['ua']=='Owned-ASI/1'
complete=next(x for x in rows if x['event']=='asi_owned_site_once_complete');joined=next(x for x in rows if x['event']=='asi_all_workers_joined');assert joined['value']['observed_workers']==6 and joined['value']['base_code_retained']and joined['value']['clone_code_removed']and peer['at']>exits[-1]['at'];assert complete['value']['attendance_delay_seconds']>=2.9 and complete['value']['cold_no_replay_observation_ms']==3500

def nodes(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from nodes(v)
 elif isinstance(x,list):
  for v in x:yield from nodes(v)
def success(page):
 for tr in nodes(page):
  if tr.get('component')!='tr':continue
  cells=tr.get('content',[])
  if len(cells)<3:continue
  if not any(n.get('text')=='Owned ASI source peer'and n.get('props',{}).get('class')=='autosignin-site-name'for n in nodes(cells[0])):continue
  if any(n.get('component')=='VChip'and n.get('text')=='签到成功'and n.get('props',{}).get('color')=='success'for n in nodes(cells[1]))and any(n.get('props',{}).get('title')=='11月6日 签到成功'for n in nodes(cells[2])):return True
 return False
want=[{'component':'VAlert','props':{'class':'mt-4','prepend-icon':'mdi-information','text':'暂无签到数据','type':'info','variant':'tonal'}}];pages=[]
for x in http:
 if not x['value']['path'].endswith('/page'):continue
 page=x['value']['response']['data']['page'];ok=success(page);empty=page==want
 if ok or empty:pages.append({'at':x['at'],'path':x['value']['path'],'successful_named_today_row':ok,'source_exact_empty':empty})
base=[x for x in pages if x['path']=='/api/plugins/AutoSignIn/page'];assert len(base)==4 and all(x['successful_named_today_row']for x in base[:3])and base[-1]['source_exact_empty'];assert any('copy/page'in x['path']and x['source_exact_empty']for x in pages)
config_gets=[x for x in http if x['value']['method']=='GET'and x['value']['path']=='/api/plugins/AutoSignIn'];configs=[x['value']['response']['data']for x in config_gets];assert len(configs)==4 and configs[0]==configs[1]==configs[2]and configs[0]['onlyonce']is False and configs[-1]=={}
metadata=json.loads((w/'owned-metadata.stdout').read_text());assert not metadata['owned_executable_processes']and not any(metadata['recorded_pid_exists'].values())and not metadata['plugin_value_counts']and metadata['installed']==[['AutoSignIn',0],['AutoSignIncopy',0]]and metadata['code']['AutoSignIn']['exists']and not metadata['code']['AutoSignIncopy']['exists']
command=json.loads((r/'empty-main-actual/command.json').read_text());assert command['exit']==0 and '--- PASS:'in(r/'empty-main-actual/actual-main.stdout').read_text()and '--- SKIP:'not in(r/'empty-main-actual/actual-main.stdout').read_text()
reinstall=next(x for x in http if x['value']['path']=='/api/plugins/install'and x['at']>pids[4]['at']);end=datetime.datetime.fromisoformat(peer['at'].replace('Z','+00:00'));begin=datetime.datetime.fromisoformat(reinstall['at'].replace('Z','+00:00'));reinstall_tail=(end-begin).total_seconds()
summary={'command':command,'pid_stages':stages,'unique_workers':unique,'main_start':starts,'main_exit':exits,'config_reads':config_gets,'page_observations':pages,'all_physical_peer':peer,'completion':complete,'all_joined':joined,'post_owned_metadata':metadata,'reinstall_observation_tail_seconds':reinstall_tail,'limits':['OS process stages are the necessary Go SDK adaptation of original per-instance objects; MP does not require one Python OS process per plugin.','Only the synthetic fixture config and rendered same-day successful history retention are established.','Post-cold physical no-replay is observed for3500ms; reinstall tail is less than3seconds and is not a second independent3-second wait. Successful-day dedup can suppress HTTP even if sign_in is entered.','Reset leaves clone PID unchanged; this fixture clone starts empty and does not prove preservation of independently seeded clone KV/files.','Code checks are directory existence/Lstat, not byte-equivalence of all package files.']}
(w/'actual-review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
plan={'release_safe_now':all(x['local_lsof_no_handles']for x in binary)and not metadata['owned_executable_processes'],'performed_cleanup':False,'retain_before_cleanup':['all raw stdout/stderr/observations/logs, original FAILs, commands/env/before-after input manifests','binary SHA/buildinfo/recipes and this independent review seal','one Root-selected current H/P binary pair only if next gate needs reuse'],'owned_remote_root':'/home/admin/light-media-plugins-root-asi-owned-20261106-r5','marker':'light-media-plugins/root-asi-owned/20261106/owned-only','eligible':['r5 redundant local/remote driver executable','r5 synthetic runtime DB/auth keys/site data/owned base package and tmp directory after preserving existing sanitized evidence','r5 local/remote host+worker duplicates if Root retains no active reuse dependency'],'guards':['verify exact own marker/path/no symlink before removal','match expected binary SHA and no process/open handle; do not touch production NAS containers/directories','leave frozen original evidence bytes and prior failure history intact'],'note':'Root owns cleanup execution and can keep one current binary pair for immediate next tests; no test artifacts need remain for this review.'}
(w/'cleanup-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
manifest=[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(set(inputs))];(w/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(w/'review.md').write_text(f'''# Independent R5 bounded acceptance

Actual R5 passes14.74seconds (command wall14.77s), no skipped root. Host b0a9a175 and worker a4524236 match R4 byte-for-byte; only driver4114b0d7 changes. All three build before/after snapshots are equal (P worker/driver4015, H host16707 recorded inputs). This review reads the actual raw, exact test/helper source, compiled binary hashes/buildinfo and one post-run marked owned-root metadata query; no Main rerun, compilation, source/SDK/ledger edit or deployment is performed. Current local commit03f39c4 does not replace those actual binary/input bindings.

## Observed lifecycle

| Stage | Base worker | Clone worker | Actual checked effect |
| --- | --- | --- | --- |
| Clone then once config save |2680611|2680669|Two workers/code directories; save retains both PIDs.|
| Cold stop/start |2680707|2680715|Both old workers joined; no workers while stopped; Main2680553 cleanly exits and2680696 starts.|
| Ordinary base uninstall |absent|2680715|Old base joined; both code directories retained; clone remains.|
| Same-repo reinstall |2680727|2680715|New base; exact saved false-once config and successful same-day source page restored; clone remains.|
| Base reset |2680765|2680715|Old base joined; new base default config{{}}/exact empty page; clone worker unchanged.|
| Clone uninstall |2680765|absent|Clone joined and its code directory removed; base/code remain.|
| Final ordinary uninstall |absent|absent|Base joined; ordinary code directory remains. Both Main/worker final joins complete.|

The pui_worker_pids records are reuse of a generic /proc/readlink observer, not PluginUnInstall business execution. Six distinct worker PIDs are all included in final waitDead checks, followed by actual Main clean exit before the final physical peer record. code() reads actual Lstat paths; these effects are supported by bound test assertions plus a post-run read-only metadata check, not uninstall HTTP acknowledgement alone.

Source linkage remains installed ASI270ae0 init82-134, generic1856-1916, __do histories1648-1738, page759-771/1441-1529; fixed MP8a83efe endpoint install576-624, reset739-761, uninstall992-1030 and manager stop156-190/reload641-651. Target H plugin_original_config/reset/lifecycle/install/uninstall and P autosignin/plugin/config/page implement the corresponding actions. Original object replacement becomes Go SDK worker replacement; this OS process adaptation is explicit.

## Functional evidence and limits

There is exactly one physical GET /attendance.php at3.036474844seconds, with the exact synthetic Cookie and Owned-ASI/1 UA. Host site.updated's three homepage/favicon observations remain separate. The named base success chip and11月6日 success dot appear before cold, after cold and after ordinary reinstall; clone retains source-exact empty state. Same false-once config survives cold and ordinary uninstall/reinstall. Reset then produces config{{}} and exact empty page. Ordinary retained=true and clone retained=false flags agree with fixed source policy.

Post-cold no additional attendance is observed for3500ms. Reinstall has only {reinstall_tail:.3f}seconds of remaining observed tail before reset/final shutdown, so it is not another independent3-second no-replay test; original successful-day dedup also prevents using no HTTP as proof sign_in never ran. The retained history evidence concerns this fixture's config and rendered successful-day record, not every unseeded plugin KV or file. Reset proves base replacement and unchanged clone PID; an empty clone provides no separate seeded clone-data retention test. Lstat verifies code presence/removal, not every code file's byte identity. Whole AutoSignIn, realPT, browser/OCR/UI, updates or23-instance completion remain outside this acceptance.

## Final readback and cleanup

A read-only query of the exact marked own R5 root finds installed flags0/0, no plugin_values in either synthetic namespace, ordinary code present, clone code absent, no own executable process and all eight recorded Main/worker PIDs absent. No DB/private payload/key is exported. Binary SHA/buildinfo are preserved; local lsof finds no open handles. This review needs no ELF or runtime retained. Root may release redundant r5 driver and synthetic runtime after preserving raw/recipes/hashes; keep one current H/P pair only if the next gate will reuse it. cleanup-plan.json lists exact own root, marker and guards. No cleanup is executed here and no production NAS artifact is included.
''')
assert all(sha(Path(x['path']))==x['sha256']for x in manifest)
files=[p for p in sorted(w.iterdir())if p.is_file()and p.name!='seal.json'];seal={'schema':1,'scope':'finite actual R5 native Main synthetic generic/once/history/clone/cold/reset/ordinary retain/reinstall and Go SDK process stages','new_Main_runs':0,'new_builds':0,'source_or_ledger_mutations':False,'files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size}for p in files],'input_count':len(manifest),'cleanup_release_safe':plan['release_safe_now']};(w/'seal.json').write_text(json.dumps(seal,indent=2)+'\n');print(json.dumps({'seal':str(w/'seal.json'),'sha256':sha(w/'seal.json'),'files':len(files),'inputs':len(manifest),'cleanup_release_safe':plan['release_safe_now']},ensure_ascii=False))
