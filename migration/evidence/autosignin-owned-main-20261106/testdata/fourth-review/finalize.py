from pathlib import Path
import json,hashlib,datetime,subprocess
P=Path('/Users/accidia/projects/light-media-plugins');H=Path('/Users/accidia/projects/light-media');MP=Path('/Users/accidia/projects/MoviePilot');w=Path(__file__).resolve().parent;r4=P/'work/autosignin-owned-main-20261106-r4';old=P/'work/source-ocr-value-domain-20261106';plan=P/'work/source-ocr-json-production-tests-plan-20261106';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[r4/'builds.json',r4/'driver-overlay.json',r4/'empty-main-bundle.json',r4/'empty-main-actual/command.json',r4/'empty-main-actual/actual-main.stdout',r4/'empty-main-actual/actual-main.stderr',r4/'empty-main-actual/runtime/evidence/observations.jsonl',r4/'empty-main-actual/runtime/evidence/host-1.log',r4/'empty-main-actual/runtime/evidence/host-2.log',P/'work/autosignin-real-integration-20261106/autosignin_owned_site_main_test.go',P/'tests/integration/testhost_main_test.go',P/'tests/integration/pluginuninstall_helpers_test.go',plan/'plan.json',plan/'actual-application.json',P/'plugins/autosignin/source_ocr_value_domain_test.go',P/'work/migration-20261105/source-snapshot/autosignin/__init__.py',H/'internal/app/plugin_original_uninstall.go',H/'internal/app/plugin_original_reset.go',H/'internal/app/plugin_original_lifecycle.go',H/'internal/app/plugin_original_install.go']
for n in ['worker','host','driver']:
 b=json.loads((r4/(n+'-before.json')).read_text());a=json.loads((r4/(n+'-after.json')).read_text());assert a==b
 paths.extend(r4/(n+'-'+v+'.json')for v in ['before','after'])
for row in json.loads((r4/'builds.json').read_text()):
 assert row['exit']==0 and row['stable'];p=r4/row['name'];assert sha(p)==row['sha256']
 paths.append(p)
app=json.loads((plan/'actual-application.json').read_text());assert sha(plan/'actual-application.json').startswith('00ad899d')
expected=(old/'value_domain_test.go').read_text()
for item in json.loads((plan/'plan.json').read_text())['necessary_test_edits']:
 assert expected.count(item['before'])==1;expected=expected.replace(item['before'],item['after'])
assert expected==(P/'plugins/autosignin/source_ocr_value_domain_test.go').read_text()
checks=[]
for row in app['rows']:
 p=P/row['target'];assert sha(p)==row['sha256'];paths.append(p)
 if row['target'].endswith('.json'):
  assert p.read_bytes()==Path(row['source']).read_bytes();paths.append(Path(row['source']))
 checks.append({'target':str(p),'sha256':sha(p),'equal_reported_byte':True,'expected_edits':4 if p.suffix=='.go'else 0})
(w/'regular-tests-byte-review.json').write_text(json.dumps({'application_sha256':sha(plan/'actual-application.json'),'test_original_sha256':sha(old/'value_domain_test.go'),'actual_test_sha256':sha(P/'plugins/autosignin/source_ocr_value_domain_test.go'),'exact_four_plan_edits':True,'rows':checks,'executed_by_this_review':False,'scope':'regular test relocation bytes only; no default network fixture introduced'},indent=2)+'\n')
rows=[json.loads(x)for x in(r4/'empty-main-actual/runtime/evidence/observations.jsonl').read_text().splitlines()]
def nodes(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from nodes(v)
 elif isinstance(x,list):
  for v in x:yield from nodes(v)
def site_rows(page):
 out=[]
 for row in nodes(page):
  if row.get('component')!='tr':continue
  cells=row.get('content',[])
  if len(cells)<3:continue
  if not any(n.get('props',{}).get('class')=='autosignin-site-name'and n.get('text')=='Owned ASI source peer'for n in nodes(cells[0])):continue
  out.append({'chips':[n for n in nodes(cells[1])if n.get('component')=='VChip'],'first_day':[n.get('props')for n in nodes(cells[2])if n.get('component')=='span'],'records':[n.get('text')for n in nodes(cells[0])if n.get('props',{}).get('class')=='autosignin-site-meta']})
 return out
starts=[x for x in rows if x['event']=='main_start'];exits=[x for x in rows if x['event']=='main_exit'];assert len(starts)==len(exits)==2 and starts[0]['value']['pid']!=starts[1]['value']['pid']and all(x['value']['error']=='<nil>'for x in exits)
http=[x for x in rows if x['event']=='http'];page_events=[]
want=[{'component':'VAlert','props':{'type':'info','text':'暂无签到数据','variant':'tonal','class':'mt-4','prepend-icon':'mdi-information'}}]
for x in http:
 v=x['value']
 if not v['path'].endswith('/page'):continue
 page=v['response']['data']['page'];sr=site_rows(page);stats=[]
 for n in nodes(page):
  cls=n.get('props',{}).get('class','')
  if n.get('component')=='div'and(isinstance(cls,str)and cls.split()and cls.split()[0]=='autosignin-stat'):
   stats.append([m['text']for m in nodes(n)if isinstance(m.get('text'),str)])
 if page==want or any(c['text']=='签到成功'for r in sr for c in r['chips']):page_events.append({'at':x['at'],'path':v['path'],'empty_exact':page==want,'site_rows':sr,'stats':stats})
clone=next(x for x in page_events if 'copy/page'in x['path']);assert clone['empty_exact']
base=[x for x in page_events if x['path']=='/api/plugins/AutoSignIn/page'];assert len(base)==3 and base[-1]['empty_exact']
for x in base[:2]:assert any(c.get('text')=='签到成功'and c.get('props',{}).get('color')=='success'for r in x['site_rows']for c in r['chips'])and any(d.get('title')=='11月6日 签到成功'for r in x['site_rows']for d in r['first_day'])
peer=next(x for x in rows if x['event']=='owned_peer_observations');business=[x for x in peer['value']if x['path']=='/attendance.php'];assert len(business)==1 and business[0]['method']=='GET'and business[0]['cookie']=='owned_session=synthetic'and business[0]['ua']=='Owned-ASI/1'
complete=next(x for x in rows if x['event']=='asi_owned_site_once_complete');assert complete['value']['attendance_delay_seconds']>=2.9 and complete['value']['cold_no_replay_observation_ms']==3500
commands=json.loads((r4/'empty-main-actual/command.json').read_text());assert commands['exit']==0 and '--- PASS: TestAutoSignInActualMainOwnedSiteOnceAndClone' in(r4/'empty-main-actual/actual-main.stdout').read_text()
metadata=json.loads((w/'owned-metadata.stdout').read_text());assert metadata['installations']==[['AutoSignIn','AutoSignIn','2.9.15',0],['AutoSignIncopy','AutoSignIn','2.9.15',0]]and metadata['plugin_value_counts']==[]and metadata['code']['AutoSignIn']['exists']and not metadata['code']['AutoSignIncopy']['exists']and not metadata['owned_executable_processes']and not any(metadata['recorded_main_pid_exists'].values())
summary={'actual_command':commands,'main_starts':starts,'main_exits':exits,'worker_pid_snapshots_in_r4':0,'successful_and_empty_pages':page_events,'all_physical_peer':peer,'completion_record':complete,'post_main_stop_owned_metadata':metadata,'uninstall_ack':[x for x in http if x['value']['path'].endswith('/uninstall')],'scope':'finite native Main synthetic generic attendance/once/same-day visible history/empty-clone/cold/page reset; no full AutoSignIn/PID chronology/code-byte data equivalence'}
(w/'actual-review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
fixed='8a83efeacd3e26b82be495e17d50146e31c96a60';facts=[]
for name,spans in [('app/api/endpoints/plugin.py',[(576,624),(739,761),(992,1030)]),('app/core/plugin.py',[(156,190),(634,651),(1905,1999)])]:
 b=subprocess.check_output(['git','show',fixed+':'+name],cwd=MP);lines=b.decode().splitlines();facts.append({'commit':fixed,'path':name,'sha256':hashlib.sha256(b).hexdigest(),'snippets':[{'lines':[a,z],'text':'\n'.join(lines[a-1:z])}for a,z in spans]})
(w/'fixed-primary-facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n')
# Pin the exact Root-owned test text that this finite readback inspected; future r5 edits do not rewrite it.
(w/'r4-driver.go.txt').write_text((P/'work/autosignin-real-integration-20261106/autosignin_owned_site_main_test.go').read_text())
paths=sorted(set(paths));manifest=[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}for p in paths];(w/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
report='''# Independent R4 bounded acceptance and remaining observation gaps

R4 actually passes the single owned Main test in12.65seconds with host b0a9a175, true AutoSignIn worker a4524236 and test-only driver f56e825b. The three build snapshots are equal before/after (worker/driver4015, host16707; broad recorded boundaries). Binary SHA values are read and compared here; the driver patch remains test-only. R1/R2/R3 failures are not reclassified or deleted. This review does not run the test again or edit true source, SDK or ledger.

## Accepted finite behavior

| Original/source behavior | Target | Actual evidence |
| --- | --- | --- |
| Installed ASI init82-134: onlyonce schedules3seconds and saves false before execution; generic1856-1916 GET attendance.php confirms login+signin. | P plugin/config and sdk source transport; H ordinary plugin config/init/host source chain. | Config GET onlyonce=false; exactly one physical GET /attendance.php with correct Cookie/UA; driver delay3.024286912s. All four physical requests are retained; the other homepage/favicon calls are host site.updated, not plugin attendance. |
| ASI __do1648-1738 result/history and page675-759/1441-1529. | P autosignin histories and page. | Before cold and after cold the named source row has exact success chip/icon and11月6日 success dot, and its distinct login row is also successful. Current-day selected site is1. This verifies rendered persisted history, not every raw plugin KV byte. |
| Clone1905-1999 copies only nonempty config, disables it, separate KV; page759-771 empty condition. | H clone namespace; P empty page. | Clone created before base config; actual clone config{} and source-exact empty VAlert despite base successful history. It does not verify all configured-clone forms/files/isolation or worker PID separation. |
| Stop/start reload and no one-shot replay with persisted false flag. | H actual executable and same owned data-dir. | Main PID2677045 cleanly exits, then2677101 starts same host bytes and loads same config+success page. Recorder has no further attendance through3.5second no-replay window. This is bounded absence of physical attendance; successful-day dedup can also suppress visits, so it does not independently prove sign_in was never entered. |
| Reset739-761: compensation, stop, force config/data delete, reload/register. | H reset/config/lifecycle and P default state. | Reset call is followed by actual GET config{} and exact empty page. Own post-test read-only DB shows no plugin_values in either namespace, supporting final removal of these synthetic values. The test does not record reset worker PID transition. |

## PID and uninstall evidence limits

There are exactly two recorded Main PIDs and no worker PID snapshots in R4. The logs do not reveal plugin worker PIDs. Consequently R4 cannot retroactively prove that save retained the same worker, clone had another PID, cold joined both old workers, reset replaced one worker, or uninstall stopped each process at its operation boundary. Those require contemporaneous /proc/readlink observations; post-Main-stop absence is only cleanup evidence.

I made one minimal read-only query of the marked own R4 directory after Main stopped: SQLite mode=ro/query_only, metadata counts only, code Lstat and /proc executable paths only under this exact owned root. Both installed flags are0; both plugin_values namespaces are empty; ordinary AutoSignIn code directory remains, clone directory is absent; no executable under the own root and neither recorded Main PID remains. No runtime DB/key/private config payload is copied. These final states supplement the two uninstall acknowledgements, but do not recover the missing operation-time worker states.

Fixed plugin.py992-1030 explicitly deletes code/config/data only for clones. Ordinary uninstall retains them, then stops and clears the in-memory object/class. H plugin_original_uninstall.go matches. Thus data_retained=true is a policy flag, not evidence that reset left rows, and ordinary code presence is expected. Do not require all code directories to disappear. A minimal next observation can reuse existing puiMain pids/readlink, waitDead and code helpers; no new runtime framework is necessary. This readback does not count a PUI business test.

## R5 source preconditions (static, not run)

Source supports ordinary base uninstall/reinstall between cold/no-replay and reset: use the same ID and valid compatible same-version repo; retain saved onlyonce=false, future Dec31 cron and managed source ID. Uninstall keeps this fixture's config and successful-day history/code. stop156-184 removes memory class, so non-force reinstall must supply a nonempty valid repo (install576-624), then installed-list update, reload/init and register. Restored false once must not schedule an immediate job, and the existing success page can reappear without another attendance. Check retained config plus this visible source history, not all unseeded plugin data. Keep clone PID/config/code unchanged. After final ordinary base uninstall code must remain; clone code must disappear. OS PID replacement/isolation is the Go SDK process adaptation of original object identity, not a literal MP multi-process contract.

The existing puiMain pids helper only reads executable paths under s.dir/plugin-packages and registers every seen PID in allPIDs; its map stores one PID per instance. Initialize puiMain with the current mainHost and an empty allPIDs map, use only pids/code/waitDead, capture pre-operation nonzero PIDs and wait for them after stop/reset/uninstall, then check expected surviving/new instances. Reusing this observer is narrower than adding an observer plugin or general framework. Current R4 has not supplied those future observations.

## Regular JSON pure test relocation

application00ad899d is byte-correct: all three oracle files equal the frozen raw bytes4df6b454/1a93d372/f4d59537; the new Go test filec67d2a53 equals original39806e1f with exactly the four planned filename/path replacements. No semantic assertion or source expected value changed. The test remains one file/three functions and local file reads only; actualSDK/App fixture, bridge and14 HDSky flows were not placed into default tests. This review verifies bytes and path existence, not a new execution of relocated permanent tests. See regular-tests-byte-review.json.

Accepted scope is the finite generic/once/visible-history/empty-clone/cold/reset functional slice and documented final metadata. Whole AutoSignIn, real PT, browser/OCR/UI, update, complete scheduling, operation-time worker lifecycle and broader23-instance acceptance are not signed by R4.
'''
(w/'review.md').write_text(report)
assert all(sha(Path(x['path']))==x['sha256']for x in manifest)
files=[p for p in sorted(w.iterdir())if p.is_file()and p.name!='seal.json'];seal={'schema':1,'scope':'independent actual R4 bounded readback + regular JSON test relocation bytes + static R5 lifecycle preconditions','new_Main_runs':0,'new_builds':0,'production_edits':False,'input_count':len(manifest),'files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size}for p in files]};(w/'seal.json').write_text(json.dumps(seal,indent=2)+'\n');print(json.dumps({'seal':str(w/'seal.json'),'sha256':sha(w/'seal.json'),'files':len(files),'inputs':len(manifest)},ensure_ascii=False))
