from pathlib import Path
import collections, datetime, gzip, hashlib, json, shutil

P=Path('/Users/accidia/projects/light-media-plugins'); H=Path('/Users/accidia/projects/light-media')
A=P/'work/autosignin-command-update-main-20261107'; W=Path(__file__).resolve().parent
L=P/'work/independent-command-update-launch-r3-review-20261107'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def save(n,v):
 p=W/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def copy(p,n):
 q=W/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
assert sha(L/'seal.json')=='fcb4d5e5bbcca8ed987de4a826ec57c065e7297e8e1335337c5dcfc56638b643'
for r in load(L/'manifest.json'):
 assert sha(L/r['path'])==r['sha256'] and (L/r['path']).stat().st_size==r['bytes']
fixed=load(L/'verification.json')
for n,s in fixed['files'].items(): assert sha(A/n)==s,(n,sha(A/n),s)
bom=load(A/'bundle-bom.json')
for n in ['host','worker','worker-updated','cli','driver']:
 assert sha(A/n)==bom['bin/'+n]['sha256'] and (A/n).stat().st_size==bom['bin/'+n]['bytes'],n
before=load(A/'before-build-inputs.json');after=load(A/'after-build-inputs.json');runtime=load(A/'after-runtime-inputs.json')
assert before==after==runtime and len(before)==7064
embeds=load(A/'before-build-embeds.json');assert embeds==load(A/'after-build-embeds.json')==load(A/'after-runtime-embeds.json') and len(embeds)==811
map_paths=[]
for name in ['after-runtime-inputs.json','after-runtime-embeds.json','after-runtime-list-commands.json']:
 copy(A/name,'binding/'+name)
def objects(raw):
 d=json.JSONDecoder();s=raw.decode();i=0;out=[]
 while i<len(s):
  while i<len(s) and s[i].isspace():i+=1
  if i==len(s):break
  x,i=d.raw_decode(s,i);out.append(x)
 return out
stream=[]
fields=['GoFiles','CompiledGoFiles','TestGoFiles','XTestGoFiles','CgoFiles','CFiles','CXXFiles','MFiles','HFiles','FFiles','SFiles','SwigFiles','SwigCXXFiles','SysoFiles','EmbedFiles','TestEmbedFiles','XTestEmbedFiles']
for name in ['host','worker','worker-updated','cli','driver']:
 raw=(A/('after-runtime-'+name+'-list.json')).read_bytes()
 build=gzip.decompress((L/'lists'/('after-build-'+name+'-list.json.gz')).read_bytes())
 # Runtime list output can contain harmless metadata order differences; compare selected physical fields.
 overlay=load(A/('driver-overlay.json' if name=='driver' else 'updated-worker-overlay.json'))['Replace'] if name in ['driver','worker-updated'] else {}
 def select(data):
  rows={};n=set();es=set();packages=objects(data)
  for p in packages:
   for f in fields:
    for v in p.get(f,[]):
     x=Path(v);x=x if x.is_absolute() else Path(p['Dir'])/x;y=overlay.get(str(x),str(x));assert y in runtime,(name,f,y)
     rows.setdefault(p['ImportPath'],{}).setdefault(f,[]).append((str(x),y,runtime[y]));n.add(y)
     if 'Embed' in f:es.add(y)
  return rows,len(packages),len(n),len(es)
 selected,pk,paths,en=select(raw);assert selected==select(build)[0]
 target=W/'lists'/('after-runtime-'+name+'-list.json.gz');target.parent.mkdir(exist_ok=True);target.write_bytes(gzip.compress(raw,mtime=0))
 assert not (A/('after-runtime-'+name+'-list.stderr')).read_bytes()
 stream.append({'name':name,'packages':pk,'paths':paths,'embeds':en,'raw_sha256':hashlib.sha256(raw).hexdigest(),'runtime_selection_equals_build':True})

R=A/'actual-r3';C=load(R/'attempt6/command.json');I=load(R/'attempt6/live-inspect.json')
assert C['exit']==0 and C['exception'] is None and C['bundle_unchanged'] is True and C['owned_container_remaining'] is False
assert all(x['exit']==0 and not x['stdout'].strip() and not x['stderr'].strip() for x in C['final_container_checks'])
assert I['Id']==C['verified_container_id'] and I['Image']=='sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881'
assert I['User']=='1000:1000' and I['ReadonlyRootfs'] and I['NetworkMode']=='none' and I['State']['Running']
assert {(m['Source'],m['Destination'],m['RW']) for m in I['Mounts']}=={('/home/admin/light-media-plugins-root-asi-native-20261107/bundle','/bundle',False),('/home/admin/light-media-plugins-root-asi-native-20261107/owned-r5','/owned',True)}
net=load(R/'attempt6/live-network.stdout');assert net['uid']==1000 and len(net['ipv4_routes'].strip().splitlines())==1 and not any('eth' in x for x in net['interfaces'].splitlines())
assert '--- PASS: TestAutoSignInActualMainCommandsUpdateTimerShutdown (26.53s)' in (R/'attempt6/actual.stdout').read_text()
assert not (R/'attempt6/actual.stderr').read_bytes()
obs=[json.loads(x)for x in(R/'owned-r5/runtime/evidence/observations.jsonl').read_text().splitlines()];assert len(obs)==100
def event(e):
 rows=[r for r in obs if r['event']==e];assert len(rows)==1,(e,len(rows));return rows[0]
http=[r for r in obs if r['event']=='http']
def data(r):return r['value']['response']['data']
assert all(r['value']['status']==200 for r in http)
logs={n:[json.loads(x)for x in(R/'owned-r5/runtime/evidence'/('host-'+str(n)+'.log')).read_text().splitlines() if x.startswith('{')]for n in range(1,5)}
stopping=[r for r in logs[3]if r.get('event')=='scheduler_stopping'];assert len(stopping)==1
stopping=stopping[0];assert stopping['level']=='INFO' and stopping['message']=='正在停止定时任务...'
checkpoint=event('public_scheduler_stop_observed');cp=ts(checkpoint['at']);stop=ts(stopping['time'])
assert cp>stop and checkpoint['value']['held_callback'] is True
success=[r for r in logs[3]if r.get('operation')=='signin_continue' and r.get('message')=='Owned ASI source peer 签到成功，已确认站点返回的签到状态' and ts(r['time'])>stop]
complete=[r for r in logs[3]if r.get('message')=='站点签到任务完成！' and ts(r['time'])>stop]
assert len(success)==len(complete)==1 and ts(success[0]['time'])>cp+datetime.timedelta(milliseconds=200)
exits=[r for r in obs if r['event']=='main_exit'];assert len(exits)==4 and all(r['value']['error']=='<nil>' for r in exits)
assert cp<ts(success[0]['time'])<ts(complete[0]['time'])<ts(exits[2]['at'])
# Validate pages by the named site's row, not static CSS/header status strings.
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def page_state(page):
 rows=[r for r in walk(page) if r.get('component')=='tr' and any(x.get('text')=='Owned ASI source peer' and x.get('props',{}).get('class')=='autosignin-site-name' for x in walk(r))]
 if not rows:return 'empty'
 states=set()
 # Source has separate signup and login tables containing the same site name.
 for row in rows:
  cells=row['content']
  for state,text,color,icon in [('success','签到成功','success','mdi-check-circle'),('pending','未记录','grey','mdi-minus-circle-outline')]:
   chip=any(x.get('component')=='VChip'and x.get('text')==text and x.get('props',{}).get('color')==color and x.get('props',{}).get('prepend-icon')==icon for x in walk(cells[1]))
   dot=any(x.get('component')=='span' and x.get('props',{}).get('class')=='autosignin-dot autosignin-dot--'+('success'if state=='success'else'none')and x.get('props',{}).get('title','').endswith(' '+text)for x in walk(cells[2]))
   summary=any(x.get('text')==('1/1'if state=='success'else'0/1')and' autosignin-stat__value' in ' '+x.get('props',{}).get('class','')for x in walk(page))
   if chip and dot and summary:states.add(state)
 assert len(states)==1,states;return next(iter(states))
pages=[(i+1,r['at'],r['value']['path'],page_state(data(r)))for i,r in enumerate(obs)if r['event']=='http'and r['value']['path'].endswith('/page')]
assert [(x[0],x[3])for x in pages if x[0]in [21,28,31,41,51,52,67,68,72,73,82,85]]==[(21,'success'),(28,'success'),(31,'empty'),(41,'pending'),(51,'success'),(52,'success'),(67,'success'),(68,'success'),(72,'empty'),(73,'success'),(82,'success'),(85,'success')]
oracle=P/'work/independent-command-main-attempt4-review-20261107/source-oracle.json'
source_pages={r['case']:r['page']for r in load(oracle)['rows']}
assert data(obs[40])['page']==source_pages['disabled-selected-no-history']
assert data(obs[30])['page']==data(obs[71])['page']==source_pages['disabled-unselected-no-history']
copy(oracle,'binding/original-source3-page-oracle.json')
commands=[r for r in http if r['value']['method']=='POST'and r['value']['path']=='/api/message/web'];assert len(commands)==4
web=[]
for idx,c in enumerate(commands):
 end=ts(commands[idx+1]['at'])if idx<3 else datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
 snapshots=[r for r in http if r['value']['path']=='/api/message/web?count=100'and ts(c['at'])<ts(r['at'])<end]
 chosen=next(r for r in snapshots if len(data(r))==[3,8,13,16][idx]);rows=data(chosen)
 counts=(sum(x['action']==0 for x in rows),sum(x.get('title')=='开始站点签到 ...'for x in rows),sum(x.get('title')=='站点签到完成！'for x in rows))
 assert counts==[(1,1,1),(2,3,3),(3,5,5),(4,7,5)][idx]
 for x in rows:
  assert x['userid']=='category-owned'and x['channel']=='Web'
  if x['action']==0:assert x['source']=='category-owned'and x['text']=='/site_signin'
  else:assert x['source']is None and x['action']==1
 callback_end=ts(commands[idx+1]['at'])if idx<3 else ts(event('ordinary_Web_broadcast_complete')['at'])
 deliveries=[r for r in logs[3]if r.get('message')=='收到命令，开始站点签到 ...'and ts(c['at'])<=ts(r['time'])<callback_end]
 assert collections.Counter(r['plugin_instance_id']for r in deliveries)==({'AutoSignIn':1}if idx==0 else {'AutoSignIn':1,'AutoSignIncmd':1})
 web.append({'round':idx+1,'history':len(rows),'incoming_start_complete':counts,'consumer_instances':[r['plugin_instance_id']for r in deliveries],'cumulative_attendance_in_passed_driver':[2,4,6,6][idx]})
timer=event('public_timer_global_shutdown_complete')['value'];assert timer['first_enter_ms']==3637 and timer['cold_additional_attendance']==0 and timer['clone_cold_history_config'] is True
assert event('ordinary_Web_broadcast_complete')['value']['attendance']==6
update=event('same_version_force_update_complete')['value'];assert update['base_pid_before']==121 and update['base_pid_after']==135 and update['clone_pid_unchanged']==113
assert update['before_sha256']==bom['bin/worker']['sha256']and update['after_sha256']==bom['bin/worker-updated']['sha256']
pidmaps=[r['value']for r in obs if r['event']=='pui_worker_pids'];assert pidmaps==[{'AutoSignIn':82},{'AutoSignIn':99},{'AutoSignIn':121,'AutoSignIncmd':113},{'AutoSignIn':135,'AutoSignIncmd':113},{'AutoSignIn':142,'AutoSignIncmd':113},{},{'AutoSignIn':159,'AutoSignIncmd':165},{'AutoSignIn':159},{}]
assert data(obs[83])['enabled'] is False and data(obs[83])['cron']=='0.001'
assert data(obs[85])['enabled'] is False and data(obs[85])['retry_keyword']=='错误|失败'and data(obs[85])['sign_sites']==[501]
assert data(obs[93])['enabled'] is False and data(obs[93])['sign_sites']==[]
cli=[r['value']for r in obs if r['event']=='native_source_CLI'];assert [x['state']for x in cli]==['validated','ready','imported','already_imported']and[x['writes']for x in cli]==[0,0,2,0]and all(x['jobs_queued']==0 and x['external_calls']==0 for x in cli)
peer=event('owned_HTTPS_peer')['value'];assert len(peer['wire'])==7 and all(x=={'method':'GET','path':'/attendance.php','host':'hhanclub.net','cookie':'owned_session=synthetic','ua':'Owned-ASI/1'}for x in peer['wire'])
assert all(x=={'method':'CONNECT','host':'hhanclub.net:443','uri':'hhanclub.net:443'}or(x['method']=='GET'and x['host']=='127.0.0.1:33119'and x['uri']in['http://127.0.0.1:33119/index','http://127.0.0.1:33119/worker'])for x in peer['proxy_requests'])
failures=[r for rows in logs.values()for r in rows if r.get('event')=='notification_failed'];assert len(failures)==12
assert all(not set(r)&{'error','cause','code','error_code','reason'}for r in failures)
assert not any(r.get('event')in ['module_execution_failed','module_declaration_failed']for rows in logs.values()for r in rows)
for rel in ['internal/app/plugin_original_notice.go','internal/app/plugin_original_modules.go','internal/notice/router.go']:
 assert sha(H/rel)==runtime[str(H/rel)]
 copy(H/rel,'source-notification/'+rel)
assert sha(P/'plugins/autosignin/plugin.go')==runtime[str(P/'plugins/autosignin/plugin.go')]
assert '"get_module"'not in (P/'plugins/autosignin/plugin.go').read_text().split('Methods:')[1].split('APIs:')[0]
copy(P/'plugins/autosignin/plugin.go','source-notification/plugins/autosignin/plugin.go')
for rel in ['attempt6','owned-r5/runtime/evidence']:
 for f in(R/rel).rglob('*'):
  if f.is_file():copy(f,'raw/'+str(f.relative_to(R)))
copy(A/'driver.go','binding/driver.go');copy(A/'bundle-bom.json','binding/bundle-bom.json')
save('verification.json',{'classification':'finite actual R3 public-scheduler-stopping-boundary Main accepted; private global stop excluded','launch_seal':sha(L/'seal.json'),'five_ELFs_verified':bom,'before_afterbuild_afterruntime_equal':True,'inputs':7064,'embeds':811,'runtime_streams':stream,'actual_seconds':26.53,'wrapper_seconds':C['seconds'],'observations':100,'stopping_log':stopping,'checkpoint':checkpoint,'first_success_after_boundary_ms':(ts(success[0]['time'])-stop).total_seconds()*1000,'first_success_after_observed_marker_ms':(ts(success[0]['time'])-cp).total_seconds()*1000,'callback_complete_before_Main_exit':True,'pages':pages,'Web':web,'PIDs':pidmaps,'timer':timer,'wire_requests':7,'CLI':cli,'notification_failed_count':12,'notification_error_code_in_original_raw':False,'notification_runtime_exact_cause':'unknown: original records omit code/cause; unavailable provider is source/fixture inference only','Main_reruns':0,'App_runs':0,'source_reruns':0,'NAS_reads':0,'NAS_writes':0,'true_writes':0,'ledger_writes':0,'external_delivery_accepted':False,'private_global_stop_accepted':False,'full_ASI_accepted':False})
print(json.dumps({'status':'PASS','observations':100,'files':7064,'embeds':811,'streams':len(stream),'notification_failed':len(failures),'public_boundary':True,'private_global_stop':False}))
