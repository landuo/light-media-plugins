from pathlib import Path
import json,subprocess,hashlib
r=Path('/Users/accidia/projects/light-media-plugins');host=Path('/Users/accidia/projects/light-media');w=Path(__file__).resolve().parent;build=host/'work/shared-host-source-metadata-20261106';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();a=json.loads((build/'linux-build-inputs-before.json').read_text());b=json.loads((build/'linux-build-inputs-after.json').read_text());meta=json.loads((build/'linux-build.json').read_text());currentbad=[p for p,m in b.items()if not Path(p).is_file()or sha(Path(p))!=m['sha256']];commit=meta['git_base'];tracked=set(subprocess.check_output(['git','ls-tree','-r','--name-only',commit],cwd=host).decode().splitlines());inside={str(Path(p).relative_to(host)):m for p,m in b.items()if Path(p).is_relative_to(host)};names=[n for n in inside if n in tracked];specs=''.join(commit+':'+n+'\n'for n in names);data=subprocess.check_output(['git','cat-file','--batch'],input=specs.encode(),cwd=host);at=0;bad=[]
for name in names:
 end=data.index(b'\n',at);header=data[at:end].decode();size=int(header.split()[-1]);blob=data[end+1:end+1+size];at=end+1+size+1
 if hashlib.sha256(blob).hexdigest()!=inside[name]['sha256']:bad.append(name)
artifact=Path(meta['command'][meta['command'].index('-o')+1]);result={'host':{'commit':commit,'artifact':str(artifact),'artifact_sha256':sha(artifact),'recorded_sha256_equal':sha(artifact)==meta['artifact_sha256'],'input_count':len(a),'before_after_equal':a==b,'current_mismatches':currentbad,'project_input_count':len(inside),'git_blob_bound_inputs':len(names),'git_blob_mismatches':bad,'project_inputs_without_git_blob':[n for n in inside if n not in tracked],'buildinfo_equal':subprocess.check_output(['go','version','-m',str(artifact)],cwd=host)==(build/'linux-buildinfo.txt').read_bytes()},'drivers':{}}
# f24 input snapshot includes the intentionally preserved old PUI test, while
# current01ba is the later single-file expected-hash patch. Do not relabel it101.
f24=r/'work/migration-20261105/removelink-main6-20261106';bound=json.loads((f24/'driver-build-binding.json').read_text());currentdif=[];preserved=[]
for n,h in bound['inputs_before'].items():
 actual=r/n
 if actual.is_file()and sha(actual)==h:continue
 saved=f24/'frozen-test-inputs'/n
 if saved.is_file()and sha(saved)==h:preserved.append(n)
 else:currentdif.append(n)
result['drivers']['f24']={'binary_sha256':bound['binary_sha256'],'old_inputs':len(bound['inputs_before']),'before_after_equal':bound['inputs_before']==bound['inputs_after'],'current_or_preserved_missing':currentdif,'preserved_old_paths':preserved,'module_origin_sha256':bound['module_inputs']['SDK_ORIGIN.json']}
pui=r/'work/migration-20261106/pui-current-driver';f=json.loads((pui/'freeze.json').read_text());result['drivers']['PUI_current_01ba']={'freeze_sha256':sha(pui/'freeze.json'),'artifacts':json.loads((pui/'artifacts.json').read_text()),'diff_proof':json.loads((pui/'source-diff-proof.json').read_text()),'new_required_env_preserved':all(s in(r/'tests/integration/pluginuninstall_main_test.go').read_text()for s in ['PLUGINUNINSTALL_EXPECT_WORKER_SHA256','PLUGINUNINSTALL_EXPECT_MPS_SHA256']),'historical_SDK':'98; this is HTTPMain harness, not newhost Runner source'}
(w/'host-driver-binding.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['host'],indent=2));print('driver',result['drivers']['f24'])
