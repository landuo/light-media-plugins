from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent;runtime=root/'work/migration-20261105/category-runtime';host=Path('/Users/accidia/projects/light-media');commit='75e13686a0e3df05ac251e359303ef3fd5971cf6'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
binding=read(runtime/'host-build-source-binding.json');assert binding['source_commit']==commit
# Verify saved source inputs against immutable Git blobs, rather than today's
# worktree (which another approved worker is now changing for TorrentTransfer).
process=subprocess.Popen(['git','cat-file','--batch'],cwd=host,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
mismatches=[];count=0
for path,want in binding['compile_inputs'].items():
 process.stdin.write((commit+':'+path+'\n').encode());process.stdin.flush();header=process.stdout.readline().decode().strip();parts=header.split()
 if len(parts)!=3 or parts[1]!='blob': mismatches.append(dict(path=path,error=header));continue
 remaining=int(parts[2]);digest=hashlib.sha256()
 while remaining:
  b=process.stdout.read(min(remaining,1024*1024));assert b;digest.update(b);remaining-=len(b)
 assert process.stdout.read(1)==b'\n';actual=digest.hexdigest();count+=1
 if actual!=want: mismatches.append(dict(path=path,expected=want,git_blob=actual))
process.stdin.close();process.wait();assert process.returncode==0
assert not mismatches,mismatches
assert count==1818,count
inputs=read(runtime/'runtime-inputs-and-status.json');checked=[];removed=[]
allowed_removed=set(inputs['cleanup']['task_generated_binaries_removed'])
for item in inputs['files']:
 path=root/item['path']
 if not path.exists():
  assert item['path'] in allowed_removed,item['path'];removed.append(item);continue
 assert sha(path)==item['sha256'],item['path'];assert path.stat().st_size==item['size'];checked.append(item)
for name,item in binding['artifacts'].items():
 path=root/'work/migration-20261105'/name
 assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],name
# The overlay fixture has exactly one extra version assignment, no behavior edit.
source=(root/'cmd/category-editor/main.go').read_text();fixture=(runtime/'category-editor-version-fixture.go').read_text()
assert source.replace('manifest := categoryeditor.Manifest()','manifest := categoryeditor.Manifest()\n\tmanifest.Version = "1.3.1"')==fixture
summaries={};coverage={}
source_form=read(root/'plugins/categoryeditor/form.json');default=(root/'work/migration-20261105/host-reference/config/category.yaml').read_text()
message='二级分类策略已更新，请注意同步调整目录设置，插件将恢复关闭状态！'
for run,expected_http,summary in [('linux-run',42,'linux-run-summary.json'),('mac-run-2',41,'mac-run-2-summary.json')]:
 events=[json.loads(s) for s in (runtime/run/'evidence/observations.jsonl').read_text().splitlines()];http=[x['value'] for x in events if x['event']=='http'];assert len(http)==expected_http
 values=lambda e:[x['value'] for x in events if x['event']==e]
 assert len(values('main_start'))==len(values('main_exit'))==2
 starts=values('main_start');assert starts[0]['pid']!=starts[1]['pid']
 for x in values('main_exit'):assert x['error']=='<nil>'
 expected_binary=binding['artifacts']['light-media-host-linux' if run=='linux-run' else 'light-media-host-mac']['sha256']
 assert all(x['binary_sha256']==expected_binary for x in starts)
 for x in http:
  if 200<=x['status']<300: assert x['response'].get('data',{}).get('success') is not False
 fail=[x for x in http if x['status']==500];assert len(fail)==1 and fail[0]['request']['enabled'] is True
 assert [(x['method'],x['path'],x['status']) for x in http if x['status']==404]==[('GET','/api/plugins/CategoryEditorowned/form',404),('GET','/api/plugins/CategoryEditor/form',404)]
 form=next(x['response']['data'] for x in http if x['path']=='/api/plugins/CategoryEditor/form' and x['status']==200)
 assert form['conf']==source_form and form['model']==dict(enabled=False,content=default)
 assert form['render_mode']=='vuetify'
 sse=values('system_message');nonempty=[json.loads(x['data']) for x in sse if x['data']];assert len(nonempty)==1 and nonempty[0]['text']==message and nonempty[0]['title']=='二级分类策略'
 assert sse[-1]['data']==''
 writes=[x for x in http if x['method']=='PUT' and x['path']=='/api/plugins/CategoryEditor'];assert writes[0]['request']['enabled'] is False
 configs=[x['response']['data'] for x in http if x['method']=='GET' and x['path']=='/api/plugins/CategoryEditor']
 assert configs[1]['discard_on_success']=='owned synthetic extra' and configs[1]['enabled'] is False
 assert configs[2]==dict(enabled=False,content=writes[1]['request']['content'])
 assert configs[3]==dict(enabled=False,content='movie:\n  [ordinary syntax error\n')
 assert configs[4]==dict(enabled=True,content=fail[0]['request']['content'],retained_on_failure=True)
 cache=[x['response']['data']['categories'] for x in http if x['path']=='/api/settings/rules'];assert cache[0]==cache[1]==cache[2]
 pids=values('worker_pids');assert pids[0]==pids[1]==pids[2]==pids[3]
 assert pids[4]['CategoryEditor']==pids[0]['CategoryEditor'] and pids[4]['CategoryEditorowned']!=pids[4]['CategoryEditor']
 assert pids[5]['CategoryEditor']!=pids[4]['CategoryEditor'] and pids[5]['CategoryEditorowned']==pids[4]['CategoryEditorowned']
 assert all(pids[-1][k]!=pids[-2][k] for k in ['CategoryEditor','CategoryEditorowned'])
 assert values('artifact_acquisition')==[{'/index':4,'/worker':4}]
 assert values('version_update')[0]['from']=='1.3' and values('version_update')[0]['to']=='1.3.1'
 tail=[x for x in http if x['method'] in ['POST','DELETE']][-4:]
 assert [x['path'] for x in tail]==['/api/plugins/CategoryEditorowned/reset','/api/plugins/CategoryEditorowned/uninstall','/api/plugins/CategoryEditor','/api/plugins/install']
 assert tail[1]['response']['data']['data_retained'] is False and tail[2]['response']['data']['data_retained'] is True
 summaries[run]=dict(raw_events=len(events),public_http=len(http),main_pids=[x['pid'] for x in starts],all_main_exits_normal=True,worker_pids=pids,sse_nonempty=len(nonempty),index_and_executable_acquisitions=values('artifact_acquisition')[0],http500='one intentional non-root driver0400 failure',not_loaded_404_count=2)
 coverage[run]=['real executable install through owned HTTP index','source form tree/default bytes','disabled save without apply','write/reload/message/auto-off/full replacement','malformed YAML warm cache','actual0400 failure preserving config/cache/worker','same-worker0600 recovery','clone config/code/PID identity; shared global policy','source-only reload/force reacquire/version fixture','cold new main/worker PIDs; unchanged policy inode/mtime via driver assertions; empty SSE','clone reset/uninstall, source uninstall/reinstall config retention']
 # Read and bind all host log records; expected request_failed events are allowed.
 logs=[]
 for logfile in [runtime/run/'evidence/host-1.log',runtime/run/'evidence/host-2.log']:
  records=[]
  for line in logfile.read_text().splitlines():
   if line.startswith('{'): records.append(json.loads(line))
  failures=[x for x in records if x.get('event')=='request_failed']
  assert all(x.get('http_status')==500 for x in failures)
  assert not any(any(word in str(x.get('event','')) for word in ['stop_failed','stop_method_failed','worker_io_failed','execution_canceled']) for x in records)
  logs.append(dict(path=str(logfile.relative_to(root)),records=len(records),request_failed_ids=[x['request_id'] for x in failures]))
 summaries[run]['host_logs']=logs
ui=read(runtime/'ui-final-http.json');assert ui==read(runtime/'linux-run/evidence/ui-final-http.json')
assert ui['source']['enabled'] is False and ui['clone']['enabled'] is False and ui['source']['content']!=ui['clone']['content']
assert ui['cached_categories']=={'电影':['UI分身电影'],'电视剧':['UI分身剧集']}
policy=(runtime/'linux-run/final-category.yaml').read_bytes();assert policy==ui['clone']['content'].encode() and hashlib.sha256(policy).hexdigest()==ui['global_policy_sha256']
pre=read(runtime/'browser-write-failure-precondition.json');rest=read(runtime/'browser-write-failure-restoration.json');assert pre['blocked_mode']=='0o400' and rest['restored_mode']=='0o600' and rest['inode_unchanged'] and rest['failed_save_policy_bytes_unchanged'] and pre['before_sha256']==rest['sha256']
namespace=read(runtime/'linux-namespace-proof.json');source_pkg=namespace['CategoryEditor'];clone_pkg=namespace['CategoryEditorowned'];assert source_pkg['directory_inode']!=clone_pkg['directory_inode']
assert source_pkg['files'][0]['manifest']['version']=='1.3.1' and clone_pkg['files'][0]['manifest']['version']=='1.3'
assert source_pkg['files'][1]['inode']!=clone_pkg['files'][1]['inode']
clean=read(runtime/'linux-cleanup.json');assert clean['root_marker_validated'] and clean['owned_remote_directory_removed'] and clean['owned_port_closed'] and clean['running_owned_processes']==[]
assert clean['final_policy']['sha256']==ui['global_policy_sha256'] and clean['final_policy']['same_inode_as_UI'] and clean['final_policy']['same_mtime_ns_as_UI']
assert clean['clone_package_removed'] and clean['source_package_reinstalled']
mac_clean=read(runtime/'mac-cleanup.json');assert mac_clean['remaining_owned_processes']==[] and mac_clean['task_worker_and_driver_binaries_removed'] and mac_clean['runtime_databases_and_secret_keys_removed']
allfiles={str(f.relative_to(root)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(runtime.rglob('*')) if f.is_file()}
result=dict(status='runtime evidence independently consistent',source_input_git_blob_checks=count,source_input_mismatches=mismatches,host_source=commit,actual_binary_records_checked=checked,removed_task_binaries_recorded=removed,summaries=summaries,coverage=coverage,browser=dict(independently_read='five AX snapshots, five PNGs and root observation; not personally reexecuted browser',source_config=ui['source'],clone_config=ui['clone'],shared_policy_sha256=ui['global_policy_sha256'],failure_request='req_p6EQ0FEEZq6MVGXbJVfUIt9M',actual0400_to0600_evidence_consistent=True),fixture_version='1.3.1 only manifest overlay, same1.3 business',cleanups_verified=True,artifacts=allfiles,limits=['This reviewer inspected original execution records and code; the actual Linux/main/browser executions were performed by coordinator/runtime worker.','Original Python differential execution remains the independent57case oracle, not rerun during real-main acceptance.','Executable-format artifact acquisition is tested; no claim of newly published remote release or end-user private configuration migration.','Current host checkout has in-progress TorrentTransfer edits; this report binds actual75e host binaries and exact immutable Git inputs, not a new host build from those unaccepted edits.'])
(here/'final-evidence-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(git_inputs=count,raw_events={k:v['raw_events'] for k,v in summaries.items()},public_http={k:v['public_http'] for k,v in summaries.items()},artifact_files=len(allfiles),cleanups_verified=True)))
