from pathlib import Path
import hashlib,json,gzip,copy
p=Path('/Users/accidia/projects/light-media-plugins');a=p/'work/autosignin-command-update-main-20261107';w=Path(__file__).resolve().parent;root=a/'actual-r2';ev=root/'owned-r4/runtime/evidence';events=[json.loads(l)for l in(ev/'observations.jsonl').read_text().splitlines()];sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
launch=p/'work/independent-command-update-launch-r2-review-20261107';assert sha(launch/'seal.json')=='7531464dca3d47cc0398394b1893b48c4da1e99ff2b0b9829bf05acc82ed00e8';driver=(launch/'reviewed/driver.go').read_text();assert hashlib.sha256(driver.encode()).hexdigest()=='d87067940fc58353a3e86984bc6430502bafafd3a95df14208c3ae01c1f9c694'
command=json.loads((root/'attempt5/command.json').read_text());outer=json.loads((a/'remote-v2-command.json').read_text());assert command['exit']==outer['exit']==0 and command['exception']is outer['exception']is None and command['owned_container_remaining']is False and command['bundle_unchanged']is True;assert outer['stdin_sha256']=='91f4f095485ca08d1fc2408b2fec0de258f367695169e4053d4cec33208aec1c'and outer['uploaded_only_changed']==['bin/driver']
assert command['verified_container_id']=='fd686003562b7288d5999a484587be1acbea30e5990e8fb9155e94e5b19db4d3';assert all(x['exit']==0 and not x['stdout'].strip()for x in command['final_container_checks']);live=json.loads((root/'attempt5/live-inspect.json').read_text());net=json.loads((root/'attempt5/live-network.stdout').read_text());assert live['Id']==command['verified_container_id']and live['User']=='1000:1000'and live['NetworkMode']=='none'and live['ReadonlyRootfs'];assert net['uid']==1000 and len(net['ipv4_routes'].splitlines())==1 and all(l.split(':')[0].strip()=='lo'for l in net['interfaces'].splitlines()if':'in l)
assert '--- PASS: TestAutoSignInActualMainCommandsUpdateTimerShutdown (25.33s)'in(root/'attempt5/actual.stdout').read_text();assert not(root/'attempt5/actual.stderr').read_bytes()
# Current no-production-change runtime file maps are independently equal to saved build.
inputs=json.loads((a/'before-build-inputs.json').read_text());assert inputs==json.loads((a/'after-build-inputs.json').read_text())==json.loads((a/'after-runtime-inputs.json').read_text());assert len(inputs)==7064;assert json.loads((a/'runtime-binding.stdout').read_text())=={'stable':True,'inputs':7064,'binaries_stable':True}
get=lambda name:[e for e in events if e['event']==name]
http=[e for e in events if e['event']=='http'];data=lambda e:e['value']['response']['data']
commands=[e for e in http if e['value']['method']=='POST'and e['value']['path']=='/api/message/web'];assert len(commands)==4
stages=[]
for i,start in enumerate(commands):
 end=commands[i+1]['at']if i+1<len(commands)else get('ordinary_Web_broadcast_complete')[0]['at'];reads=[e for e in http if start['at']<e['at']<end and e['value']['path']=='/api/message/web?count=100'];rows=data(reads[-1]);counts={'incoming':0,'start':0,'complete':0}
 for row in rows:
  assert row['channel']=='Web'and row['userid']=='category-owned'
  if row['action']==0:assert row['source']=='category-owned'and row['text']=='/site_signin';counts['incoming']+=1
  else:
   assert row['action']==1 and row['source']is None
   if row['title']=='开始站点签到 ...':counts['start']+=1
   elif row['title']=='站点签到完成！':counts['complete']+=1
   else:raise AssertionError(row)
 stages.append({'command':i+1,'history_count':len(rows),'counts':counts,'at':reads[-1]['at']})
assert [s['history_count']for s in stages]==[3,8,13,16];assert [s['counts']for s in stages]==[{'incoming':1,'start':1,'complete':1},{'incoming':2,'start':3,'complete':3},{'incoming':3,'start':5,'complete':5},{'incoming':4,'start':7,'complete':5}]
logs=[]
for f in sorted(ev.glob('host-*.log')):
 for line in f.read_text().splitlines():
  try:r=json.loads(line)
  except:continue
  logs.append(r)
for i,start in enumerate(commands):
 end=commands[i+1]['at']if i+1<len(commands)else get('ordinary_Web_broadcast_complete')[0]['at'];starts=[r for r in logs if start['at']<r.get('time','')<end and r.get('event')=='plugin_message'and r.get('message')=='收到命令，开始站点签到 ...'];consumers=sorted(r['plugin_instance_id']for r in starts);assert consumers==(['AutoSignIn']if i==0 else['AutoSignIn','AutoSignIncmd']);stages[i]['actual_log_consumers']=consumers
 counts=[r for r in logs if r.get('event')=='plugin_message'and r.get('message')=='开始站点签到：Owned ASI source peer，地址：[URL]'and r.get('time','')<end];stages[i]['cumulative_attendance_operations']=len(counts)
assert [r['cumulative_attendance_operations']for r in stages]==[2,4,6,6]
peer=get('owned_HTTPS_peer')[0]['value'];assert len(peer['wire'])==7 and all(x=={'cookie':'owned_session=synthetic','host':'hhanclub.net','method':'GET','path':'/attendance.php','ua':'Owned-ASI/1'}for x in peer['wire'])
for request in peer['proxy_requests']:
 assert request['method']=='CONNECT'and request['host']=='hhanclub.net:443'or request['method']=='GET'and request['host']=='127.0.0.1:42431'and request['uri'].startswith('http://127.0.0.1:42431/')
# Source-derived page operations read independently from actual raw trees.
def walk(v):
 if isinstance(v,dict):
  yield v
  for x in v.values():yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
def success(page):
 for r in walk(page):
  if r.get('component')!='tr':continue
  cells=r.get('content',[])
  if len(cells)<3 or not any(x.get('text')=='Owned ASI source peer'and x.get('props',{}).get('class')=='autosignin-site-name'for x in walk(cells[0])):continue
  if any(x.get('component')=='VChip'and x.get('text')=='签到成功'and x.get('props',{}).get('color')=='success'for x in walk(cells[1]))and any(x.get('props',{}).get('class')=='autosignin-dot autosignin-dot--success'for x in walk(cells[2])):return True
 return False
pages=[e for e in http if e['value']['path'].endswith('/page')];basepages=[e for e in pages if e['value']['path']=='/api/plugins/AutoSignIn/page'];clonepages=[e for e in pages if e['value']['path']=='/api/plugins/AutoSignIncmd/page'];assert len(basepages)==7 and len(clonepages)==4
assert success(data(basepages[0]))and success(data(basepages[1]));empty=[{'component':'VAlert','props':{'type':'info','text':'暂无签到数据','variant':'tonal','class':'mt-4','prepend-icon':'mdi-information'}}];assert data(basepages[2])['page']==empty and data(basepages[5])['page']==empty
pending=json.loads((p/'work/independent-command-main-attempt4-review-20261107/source-oracle.json').read_text())['rows'][0]['page'];assert data(clonepages[0])['page']==pending
assert all(success(data(e))for e in clonepages[1:]);assert success(data(basepages[-1]))
# Actual CLI result counters, guarded identity/form and default/source once lifecycle.
cli=[e['value']for e in get('native_source_CLI')];assert [e['state']for e in cli]==['validated','ready','imported','already_imported'];assert [e['writes']for e in cli]==[0,0,2,0]and all(e['jobs_queued']==e['external_calls']==0 and e['sites']==1 for e in cli)
form=next(data(e)for e in http if e['value']['path']=='/api/plugins/AutoSignIn/form');assert any(x.get('model')=='sign_sites'and any(i.get('value')==501 and i.get('title')=='Owned ASI source peer'for i in x.get('items',[])if isinstance(i,dict))for x in walk(form));assert get('private_init_waited')[0]['value']=={'observed_block_ms':200,'source_stop_wait':True}
update=get('same_version_force_update_complete')[0]['value'];assert update['version']=='2.9.15'and update['before_sha256']=='2b77bc3db6c80ff67314a68daa0df90b1595e99ab2bc658ca80cfaafd6a251a0'and update['after_sha256']=='e38f19188cfbfe4b295893b9707c1ba8ee77117880ffdcfb7952e77bf0108f36';assert update['base_pid_before']==122 and update['base_pid_after']==136 and update['clone_pid_unchanged']==115
pidmaps=[e['value']for e in get('pui_worker_pids')];assert pidmaps==[{'AutoSignIn':82},{'AutoSignIn':100},{'AutoSignIn':122,'AutoSignIncmd':115},{'AutoSignIn':136,'AutoSignIncmd':115},{'AutoSignIn':143,'AutoSignIncmd':115},{},{'AutoSignIn':161,'AutoSignIncmd':167},{'AutoSignIn':161},{}]
# Hot/cold executable assertions and physical code existence are in exact executed driver,
# not a new claim that those every-read values were separately logged.
for needle in ['fileHash(t, fmt.Sprintf("/proc/%d/exe", newPIDs[id])) != activeDigest','fileHash(t, fmt.Sprintf("/proc/%d/exe", afterColdPIDs[id])) != activeDigest','observer.code(clone, false)','observer.code(id, true)','observer.waitDead(oldPIDs[id])'] :assert needle in driver
assert len(get('main_start'))==len(get('main_exit'))==4 and all(e['value']['error']=='<nil>'for e in get('main_exit'))
removed=next(e for e in http if e['value']['method']=='DELETE'and e['value']['path'].startswith('/api/sites/manage/'));afterdelete=next(data(e)for e in http if e['at']>removed['at']and e['value']['path']=='/api/plugins/AutoSignIn'and e['value']['method']=='GET');assert afterdelete['enabled']is False and afterdelete['sign_sites']==[]
ack={e['value']['path']:data(e)for e in http if e['value']['method']=='DELETE'and e['value']['path'].startswith('/api/plugins/')};assert ack['/api/plugins/AutoSignIncmd']['data_retained']is False and ack['/api/plugins/AutoSignIn']['data_retained']is True
stop=get('public_timer_global_shutdown_complete')[0]['value'];assert stop['first_enter_ms']==3640 and stop['observed_stop_wait_ms']==200 and stop['cold_additional_attendance']==0;assert len(data([e for e in http if e['value']['path']=='/api/message/web?count=100'][-1]))==16
notifications=[r for r in logs if r.get('event')=='notification_failed'];assert len(notifications)==12
# Preserve all actual files exactly; no DB/config/private keys are read.
files=[]
for f in sorted(root.rglob('*')):
 if f.is_file():
  dest=w/'raw'/f.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(f.read_bytes());files.append({'path':str(f),'sha256':sha(f),'bytes':f.stat().st_size})
for n in ['remote-v2-command.json','builds-current.json','bundle-bom.json','runtime-binding.stdout','before-build-inputs.json','after-build-inputs.json','after-runtime-inputs.json']:
 f=a/n;dest=w/'bindings'/n;dest.parent.mkdir(exist_ok=True);dest.write_bytes(f.read_bytes())
result={'classification':'actual Linux Go Main finite command/update/reset/delete/uninstall and cooperative timer-stop outcome; globaldrain causality NOT accepted','events':len(events),'Main_pass_seconds':25.33,'wrapper_seconds':command['seconds'],'wrapper_owned_remaining':False,'BOM_stable':True,'recorded_runtime_input_files':7064,'stages':stages,'physical_attendance_total':7,'CLI':cli,'update':update,'PID_snapshots':pidmaps,'hot_cold_proc_executable_hash_assertions_executed':True,'base_code_retained_clone_code_removed_assertions_executed':True,'ordinary_site_delete_effect':afterdelete,'uninstall_ack':ack,'public_timer_outcome_raw_unmodified':stop,'globaldrain_causality':'unverified: no actual stopping/drain-entry observation; code backup/HTTP shutdown can consume the200ms before revocation, so natural completion may precede the bug','globaldrain_bug_cleared':False,'external_notification_delivery':'not accepted;12 notification_failed logs coexist with correct persisted Web messages','source_reruns':0,'new_Main_runs':0,'new_App_runs':0,'true_writes':0,'ledger_writes':0,'raw_bindings':files}
(w/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['events','Main_pass_seconds','wrapper_seconds','stages','physical_attendance_total','PID_snapshots','globaldrain_causality','globaldrain_bug_cleared']},ensure_ascii=False,indent=2))
