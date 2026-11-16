from pathlib import Path
import hashlib,json,os,struct,subprocess,tempfile
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
origin_path=root/'SDK_ORIGIN.json';origin_before=sha(origin_path);origin=read(origin_path)
old=read(root/'work/migration-20261105/sdk/source-target-proof.json');old_paths={x['path'] for x in old['files']};assert len(old_paths)==84
for item in old['files']:assert sha(root/item['path'])==item['target_sha256'],item['path']
assert len(origin['files'])==87
for item in origin['files']:assert sha(root/item['path'])==item['sha256'],item['path']
new_files=[x for x in origin['files'] if x['path'] not in old_paths]
assert {x['path'] for x in new_files}=={'internal/sdk/downloader_source.go','internal/sdk/downloader_source_test.go','internal/sdk/downloader_source_wire_test.go'}
new_snapshot={x['path']:sha(root/x['path']) for x in new_files}
initial_hashes={x['path']:sha(root/x['path']) for x in origin['files']}
prior=read(root/'work/migration-20261105/category-review/FINAL-REVIEW-20261105.json')
category_paths=['plugins/categoryeditor/categoryeditor.go','plugins/categoryeditor/form.json','plugins/categoryeditor/categoryeditor_test.go','cmd/category-editor/main.go','cmd/category-editor/main_test.go','go.mod','go.sum']
for path in category_paths:assert sha(root/path)==prior['current_source_files'][path],path
inspection=json.loads(subprocess.check_output(['go','run','./work/migration-20261105/category-review-wire-final/_tools/inspect.go','--',*[str(root/x['path']) for x in new_files]],cwd=root,text=True))
for item in inspection:
 assert item['package']=='plugins'
 assert not item['package_variables'] and not item['init_functions'] and not item['registration_calls'],item
(here/'new-file-ast.json').write_text(json.dumps(inspection,indent=2)+'\n')

def elf_sections(path):
 raw=path.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01'
 offset=struct.unpack_from('<Q',raw,40)[0];size,count,index=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+n*size) for n in range(count)]
 names=sections[index];table=raw[names[4]:names[4]+names[5]];out={}
 for section in sections:
  start=section[0];name=table[start:table.find(b'\0',start)].decode()
  if section[1]!=8:out[name]=dict(bytes=section[5],sha256=hashlib.sha256(raw[section[4]:section[4]+section[5]]).hexdigest())
 return out

def go_packages(flags):
 raw=subprocess.check_output(['go','list',*flags,'-deps','-json','./cmd/category-editor'],cwd=root,text=True)
 decoder=json.JSONDecoder();out=[]
 while raw.strip():
  obj,n=decoder.raw_decode(raw.lstrip());raw=raw.lstrip()[n:];out.append(obj)
 return out

builds=[]
with tempfile.TemporaryDirectory(prefix='owned-category-wire-',dir=here) as directory:
 directory=Path(directory);overlay=directory/'exclude-new-sdk.json';overlay.write_text(json.dumps({'Replace':{str(root/p):'' for p in new_snapshot}}))
 lists={}
 for mode,flags in [('current',[]),('exclude-new-sdk',['-overlay='+str(overlay)])]:
  lists[mode]=go_packages(flags)
  binary=directory/(mode+'-linux');env={**os.environ,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'}
  argv=['go','build',*flags,'-trimpath','-buildvcs=false','-o',str(binary),'./cmd/category-editor']
  run=subprocess.run(argv,cwd=root,env=env,text=True,capture_output=True);(here/(mode+'-build.log')).write_text(run.stdout+run.stderr+'BUILD_EXIT='+str(run.returncode)+'\n');assert run.returncode==0,run.stderr
  nm=subprocess.check_output(['go','tool','nm','-size',str(binary)],cwd=root,text=True);(here/(mode+'-nm.txt')).write_text(nm)
  names=[line.split()[-1] for line in nm.splitlines() if line.split()]
  forbidden=[name for name in names if any(x in name for x in ['.SourceTasks','.SourceCompleted','.SourceAdd','.SourceControl','.sourceTasks','.sourceMutation','DownloaderSourceAddRequestV1'])]
  assert not forbidden,forbidden
  builds.append(dict(mode=mode,command=' '.join(argv).replace(str(directory),'<owned-temp>'),environment={k:env[k] for k in ['GOOS','GOARCH','CGO_ENABLED']},binary_sha256=sha(binary),bytes=binary.stat().st_size,nm_sha256=sha(here/(mode+'-nm.txt')),symbol_count=len(names),new_linked_source_symbols=forbidden,elf_sections=elf_sections(binary)))
 assert {x['ImportPath'] for x in lists['current']}=={x['ImportPath'] for x in lists['exclude-new-sdk']}
 package_diff=[]
 for a,b in zip(lists['current'],lists['exclude-new-sdk']):
  assert a['ImportPath']==b['ImportPath']
  assert a.get('Imports',[])==b.get('Imports',[]),a['ImportPath']
  if a.get('GoFiles',[])!=b.get('GoFiles',[]):package_diff.append(dict(package=a['ImportPath'],added=sorted(set(a.get('GoFiles',[]))-set(b.get('GoFiles',[]))),removed=sorted(set(b.get('GoFiles',[]))-set(a.get('GoFiles',[])))))
 assert package_diff==[dict(package='github.com/landuo/light-media-plugins/internal/sdk',added=['downloader_source.go'],removed=[])]

critical=['.text','.rodata','.typelink','.itablink','.go.buildinfo','.go.fipsinfo','.noptrdata','.data']
assert builds[0]['nm_sha256']==builds[1]['nm_sha256']
for name in critical:assert builds[0]['elf_sections'][name]==builds[1]['elf_sections'][name],name
manifest=json.loads(subprocess.check_output(['go','run','./cmd/category-editor','--manifest'],cwd=root,text=True));assert manifest==prior['current_category_tests']['manifest']
(here/'current-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
# Historical command supplement is a metadata read, never a claimed rebuild.
history_path=root/'work/migration-20261105/category-runtime/category-worker-driver-build-binding.json';history=read(history_path)
old_runtime=read(root/'work/migration-20261105/category-runtime/runtime-inputs-and-status.json');old_artifacts={x['path']:x for x in old_runtime['files']}
assert len(history['artifacts'])==5 and len(history['mac_driver_runs'])==2
for item in history['artifacts']:
 expected=old_artifacts[item['artifact']];assert item['sha256']==expected['sha256'] and item['size']==expected['size']
 assert item['cwd']==str(root)
 if item['artifact'].endswith('-mac'):
  assert item['explicit_environment']=={} and all(item[k] is None for k in ['GOOS','GOARCH','CGO_ENABLED'])
 else:assert item['explicit_environment']=={'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'}
 assert '-trimpath' not in item['command'] and '-buildvcs=false' not in item['command']
for item in history['mac_driver_runs']:
 assert all(item[k] is None for k in ['GOOS','GOARCH','CGO_ENABLED'])
 assert 'go test ./tests/integration' in item['command'] and '-count=1 -v' in item['command']
assert sha(origin_path)==origin_before,'metadata changed during review'
assert initial_hashes=={x['path']:sha(root/x['path']) for x in origin['files']},'SDK changed during review'
assert new_snapshot=={p:sha(root/p) for p in new_snapshot}
result=dict(status='passed_no_CategoryEditor_dependency_impact',scope='SourceAdd wire SDK micro-increment only; no main/UI replay',source_base_commit=origin.get('source_base_commit'),sdk_origin_sha256=origin_before,sdk_origin_files=len(origin['files']),sdk_source_commit=origin.get('source_commit'),sdk_source_state=origin.get('source_state'),sdk_source_branch=origin.get('source_branch'),frozen_84_files_unchanged=True,new_files=new_files,ast_no_init_vars_registration=True,category_unchanged={p:sha(root/p) for p in category_paths},manifest_unchanged=True,package_count=len(lists['current']),package_import_graph_unchanged=True,package_file_delta=package_diff,builds=builds,identical_critical_sections=critical,identical_linked_nm=True,new_source_symbols_linked=False,temporary_binaries_removed=True,historical_build_supplement=dict(path=str(history_path.relative_to(root)),sha256=sha(history_path),matches_original_five_artifact_SHA_and_size=True,original_flags_preserved=True,mac_unknown_environment_still_null=True,linux_explicit_env_recorded=True,driver_source_binding_limit='run1 failure has no separate exact source hash snapshot; final run2 source is separately bound',review='consistent supplemental historical command metadata; no reconstruction or new runtime claim'),prior_acceptance_preserved=True,old_runtime_SHA_replaced=False,ledger_changed=False,limits=['New Source API behavior/host acceptance is outside this Category dependency certificate.','This run is current Linux crosscompile/link analysis and native manifest only, not actual Linux/main/browser execution.','Original main/UI evidence remains under its original exact binary/source/hash bindings.','Old Mac per-build environment remains unknown; no value is inferred from another SDK/environment observation.'])
(here/'impact-certificate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],origin_sha256=origin_before,new_source_sha256=new_snapshot['internal/sdk/downloader_source.go'],symbols=builds[0]['symbol_count'],critical_sections_equal=critical,historical_supplement_sha256=sha(history_path))))
