from pathlib import Path
import ast,builtins,difflib,hashlib,json,subprocess,symtable
p=Path('/Users/accidia/projects/light-media-plugins');h=Path('/Users/accidia/projects/light-media');a=p/'work/autosignin-command-update-main-20261107';w=Path(__file__).resolve().parent;out=w/'reviewed';out.mkdir(exist_ok=True)
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
expected={'runner.py':'3e4035220bdf55d484c2a17bd2bbcdd86239733c41fc580798391e89127f749d','remote-body.py':'43c699c0d70fa8bf04bf78fd911412eba68600685d84e224d79cf11f370a1d61','execute-runner.py':'72ded19f24b224208608b2b7464179f9338cad05faa200bfc6aa15c187c408e8','prepare-runner.py':'117f0ffd03cfa558527cd778094970148dfd7acb2284ad6baa2d1b548b84f082','driver.go':'f48d30b3511741ab1c7cf6ceb03db6f1a4ae29e678f08c4da00f3d02e3ad956e','bundle-bom.json':'6ee1f21664cb3f4d8cda0485e7323445f04990f9f5f7f9d157991caf42a59cd2'}
for name,digest in expected.items():assert sha(a/name)==digest;(out/name).write_bytes((a/name).read_bytes())
# No runtime execution; only reading existing Go build information from ELF files.
bom=json.loads((a/'bundle-bom.json').read_text());builds=json.loads((a/'builds-current.json').read_text());assert set(bom)=={'bin/'+n for n in ['host','worker','worker-updated','cli','driver']};bins=[]
for row in builds['builds']:
 f=a/row['name'];assert f.is_file()and not f.is_symlink();assert sha(f)==row['sha256']==bom['bin/'+row['name']]['sha256'];assert f.stat().st_size==row['bytes']==bom['bin/'+row['name']]['bytes'];assert row['exit']==0
 with f.open('rb')as s:assert s.read(20)[:6]==b'\x7fELF\x02\x01'
 info=subprocess.check_output(['go','version','-m',str(f)]);(out/(row['name']+'.buildinfo.txt')).write_bytes(info);assert info==(a/(row['name']+'.buildinfo.txt')).read_bytes();assert b'GOOS=linux'in info and b'GOARCH=amd64'in info and b'CGO_ENABLED=0'in info
 bins.append({'name':row['name'],'sha256':row['sha256'],'bytes':row['bytes'],'read_only_buildinfo_matches':True})
assert bom['bin/worker']['sha256']!=bom['bin/worker-updated']['sha256']
# Current producer changes only one owned manifest description, not plugin logic/version.
main=(p/'cmd/auto-sign-in/main.go').read_text();needle='manifest := autosignin.Manifest()';assert main.count(needle)==1
made=main.replace(needle,needle+'\nmanifest.Description = "Owned same-version update verification build2"');fmt=subprocess.run(['gofmt'],input=made.encode(),capture_output=True,check=True).stdout;assert fmt==(a/'updated-main.go').read_bytes()
# Original reviewed body must be exact, and runner is only a literal CONFIG prefix.
runner=(a/'runner.py').read_text();body=(a/'remote-body.py').read_text();first,rest=runner.split('\n',1);assert rest==body
node=ast.parse(first).body[0];assert isinstance(node,ast.Assign)and node.targets[0].id=='CONFIG';config=ast.literal_eval(node.value)
assert config=={'root':'/home/admin/light-media-plugins-root-asi-native-20261107','marker':'light-media-plugins/root-asi-native/20261107/owned-only','name':'lm-root-asi-native-20261107','owned_dir':'owned-r5','out_dir':'attempt6','image':'sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','bom':bom}
assert(a/'remote-body.py').read_bytes()==(p/'work/independent-command-update-runner-review-20261107/remote-body.py').read_bytes()
preflight=json.loads((a/'runner-preflight.json').read_text());assert preflight['config']==config and preflight['runner_sha256']==expected['runner.py']and preflight['body_sha256']==expected['remote-body.py']and preflight['unbound_global']==[]
# Compile and recursively check global lookup for setup, outer and every generated literal program.
checks=[]
def check(name,source):
 compile(source,name,'exec');table=symtable.symtable(source,name,'exec');allowed=set(dir(builtins))|{'__file__'}|{s.get_name()for s in table.get_symbols()if s.is_assigned()or s.is_imported()or s.is_parameter()};missing=[]
 def walk(t):
  for x in t.get_symbols():
   if x.is_referenced()and x.is_global()and x.get_name()not in allowed:missing.append({'scope':t.get_name(),'name':x.get_name()})
  for child in t.get_children():walk(child)
 walk(table);assert not missing,(name,missing);checks.append({'name':name,'compile':True,'unbound_global':missing})
for name in ['runner.py','execute-runner.py','prepare-runner.py']:check(name,(a/name).read_text())
outer=(a/'execute-runner.py').read_text();tree=ast.parse(outer)
for name in ['probe','fetch']:
 node=next(n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id==name for x in n.targets));part=ast.literal_eval(node.value);source='CONFIG='+repr({'root':config['root'],'marker':config['marker'],'name':config['name'],'bom':bom})+'\n'+part;check(name+'.py',source);(out/(name+'-checked.py')).write_text(source)
assert "['ssh','-o','BatchMode=yes','admin@192.168.8.129','tar','-xf','-','-C',ROOT+'/bundle']"in outer
assert "n in ['bin/host','bin/worker','bin/worker-updated','bin/cli','bin/driver']"in outer
assert "assert not (r/'owned-r5').exists()and not(r/'attempt6').exists()"in outer
assert "timeout=360"in outer and 'except (subprocess.TimeoutExpired,OSError)as error:'in outer
assert "(W/'remote-v2.stdout').write_bytes(remote_stdout)"in outer and "(W/'remote-v2.stderr').write_bytes(remote_stderr)"in outer
assert "'attempt6/inspect-attempts.json'"in outer and "'owned-r5/runtime/evidence'"in outer
assert "if not path.exists():continue"in outer and"archive.extractall(dest,filter='data')"in outer
# Exact R3 delta from the executed R2: real stop-entry observation and clone cold reads only.
old=p/'work/independent-command-update-launch-r2-review-20261107/reviewed/driver.go';assert sha(old)=='d87067940fc58353a3e86984bc6430502bafafd3a95df14208c3ae01c1f9c694';oldtext=old.read_text();newtext=(a/'driver.go').read_text();normalized=newtext.replace('\tshutdownLog := h.log.Name()\n','')
i=normalized.index('\t// Wait for the original ordinary Scheduler.stop stage,');j=normalized.index('\n\tselect {',normalized.index('\th.record("public_scheduler_stop_observed"',i));normalized=normalized[:i]+normalized[j+1:]
newreads='\th.config(id, baseConfig)\n\tif !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {\n\t\tt.Fatal("clone cold history changed across base timer/reset/update")\n\t}\n\th.config(clone, cloneConfig)';assert normalized.count(newreads)==1;normalized=normalized.replace(newreads,'\th.config(id, baseConfig)')
oldline=next(l for l in oldtext.splitlines(True)if 'h.record("public_timer_global_shutdown_complete"'in l);newline=next(l for l in normalized.splitlines(True)if 'h.record("public_timer_global_shutdown_complete"'in l);normalized=normalized.replace(newline,oldline);assert normalized==oldtext
(out/'driver-from-d870.patch').write_text(''.join(difflib.unified_diff(oldtext.splitlines(True),newtext.splitlines(True),fromfile='executed-r2-d870',tofile='new-r3-f48d')))
prior=p/'work/independent-command-update-launch-r2-review-20261107/reviewed'
for name in ['prepare-runner.py','execute-runner.py']:
 prior_text=(prior/name).read_text().replace('owned-r4','owned-r5').replace('attempt5','attempt6')
 if name=='execute-runner.py':prior_text=prior_text.replace("dest=W/'actual-r2';", "dest=W/'actual-r3';")
 assert prior_text==(a/name).read_text(),name
assert(a/'build.py').read_bytes()==(a/'attempt2-four-Web-update-cooperative-stop-pass/build.py').read_bytes()
# The checkpoint is an actual once-per-App public drain entry, not an API or timer sleep.
application=h/'work/root-public-drain-integration-20261107/application.json';app=json.loads(application.read_text())
for r in app['targets']:assert sha(r['target'])==r['after_sha256']
for r in app['reviews']:assert sha(r['path'])==r['sha256']
logcode=(h/'internal/app/plugin_original_direct_dispatch.go').read_text();i=logcode.index('func (a *App) drainOriginalPluginScheduler()');drain=logcode[i:];assert drain.index('state.serviceAdmissionClosed = true')<drain.index('"scheduler_stopping"')<drain.index('state.serviceLifetimes.Wait()')
runtime=(h/'internal/app/runtime.go').read_text();i=runtime.index('func (a *App) Close()');close=runtime[i:];assert close.index('a.drainOriginalPluginScheduler()')<close.index('a.closeOriginalBackgroundAdmission()')<close.index('a.cancel()')<close.index('a.backupOriginalPluginCode(')
assert'shutdownLog := h.log.Name()'in newtext and 'observed_stop_wait_after_stage_ms'in newtext;assert newtext.index('"public_scheduler_stop_observed"')<newtext.index('case <-time.After(200 * time.Millisecond):',newtext.index('"public_scheduler_stop_observed"'))<newtext.index('timerGate.unblock()',newtext.index('"public_scheduler_stop_observed"'))
helpers=(p/'work/autosignin-native-main-20261107/testhost_main_helpers_test.go').read_text();assert 'fmt.Sprintf("host-%d.log", h.generation)'in helpers and'file, err := os.Create('in helpers
(out/'public-integration-application.json').write_bytes(application.read_bytes())
# File/input bindings. Saved lists were parsed by the builder rather than retained;
# do not call them independently reconstructed package-stream records.
before=json.loads((a/'before-build-inputs.json').read_text());after=json.loads((a/'after-build-inputs.json').read_text());assert before==after and len(before)==7064
changed=[]
for f,digest in before.items():
 if not Path(f).is_file()or sha(f)!=digest:changed.append(f)
assert not changed,changed
embeds=json.loads((a/'before-build-embeds.json').read_text());assert len(embeds)==811 and embeds==json.loads((a/'after-build-embeds.json').read_text())
for f,digest in embeds.items():assert before[f]==digest
assert before[str(a/'driver.go')]==expected['driver.go']and before[str(a/'updated-main.go')]==sha(a/'updated-main.go')
commands=json.loads((a/'before-build-list-commands.json').read_text());assert len(commands)==5 and all('-compiled'in x['argv']for x in commands)
for name in ['before-build-inputs.json','after-build-inputs.json','before-build-embeds.json','after-build-embeds.json','builds-current.json','driver-overlay.json','updated-worker-overlay.json','updated-main.go','before-build-list-commands.json','runner-preflight.json']:(out/name).write_bytes((a/name).read_bytes())
result={'classification':'final local static launch/BOM review only; no Main/SSH upload/runtime/true write','config':config,'files':expected,'bins':bins,'compile_symtable':checks,'driver_only_real_scheduler_boundary_and_clone_cold_reads_from_d870':True,'four_Web_source_oracle':'4f8badd440416add1575e44238ac580e98cba64c8e3d5cf92f50ce282feaf5e3','current_input_files':len(before),'embeds':len(embeds),'saved_before_after_equal':True,'current_files_match_saved_inputs':True,'closure_limit':'five before/after raw go-list streams now retained and checked in supplemental file','runtime_runs':0,'Main_runs':0,'true_writes':0,'NAS_writes':0,'ready_for_parent_internal_launch_gate':True}
(w/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'fixed':expected,'inputs':len(before),'embeds':len(embeds),'bins':bins,'syntax_checks':len(checks),'runtime':False},indent=2))
