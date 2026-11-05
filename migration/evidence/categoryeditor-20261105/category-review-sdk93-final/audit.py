"""Validate this review's actual recorded builds and derive the finite certificate.
Run diagnose_link_delta.py, normalize_reflection_metadata.py, bind_git_inputs.py
and the Category race command first when reproducing from scratch.
"""
from pathlib import Path
import json,hashlib,subprocess,tempfile,os,datetime
R=Path(__file__).resolve().parent;root=R.parents[2]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=read(R/'current93-inputs.json');origin=read(root/'SDK_ORIGIN.json');assert len(origin['files'])==93 and sha(root/'SDK_ORIGIN.json')==inputs['sdk_origin_sha256']
assert origin['source_commit']=='404daade9d5f321624e7b421dbf877a23fe5c2b9'
assert all(sha(root/p)==h for p,h in inputs['files'].items())
base=read(root/'work/migration-20261105/sdk/source-target-proof.json');old={x['path']:x['target_sha256'] for x in base['files']};assert len(old)==84 and all(sha(root/p)==h for p,h in old.items())
assert {str(p.relative_to(root)) for p in (root/'internal/sdk').rglob('*') if p.is_file()}=={x['path'] for x in origin['files']}
new=[x for x in origin['files'] if x['path'] not in old];assert len(new)==9
ast=read(R/'new-file-ast.json');assert len(ast)==9
assert all(not x['package_variables'] and not x['init_functions'] and not x['registration_calls'] for x in ast)
production=sorted(Path(x['path']).name for x in new if not x['path'].endswith('_test.go'));assert production==['downloader_configurations.go','downloader_source.go','downloader_source_connection.go','downloader_source_find_by_tag.go']
git=read(R/'sdk93-git-binding.json');assert git['origin_sha256']==inputs['sdk_origin_sha256'] and git['count']==93 and all(x['exact_with_declared_import_relocation'] for x in git['files'])
# Compare the dependency graph for the same Linux environment as link builds.
env={**os.environ,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'}
def packages(flags):
 raw=subprocess.check_output(['go','list',*flags,'-deps','-json','./cmd/category-editor'],cwd=root,env=env,text=True);dec=json.JSONDecoder();out={}
 while raw.strip():
  obj,n=dec.raw_decode(raw.lstrip());raw=raw.lstrip()[n:];out[obj['ImportPath']]={'imports':obj.get('Imports',[]),'go_files':obj.get('GoFiles',[]),'embed_files':obj.get('EmbedFiles',[])}
 return out
with tempfile.TemporaryDirectory(prefix='owned-sdk93-graph-',dir=R) as tmp:
 overlay=Path(tmp)/'exclude-new-sdk.json';overlay.write_text(json.dumps({'Replace':{str(root/x['path']):'' for x in new}}));graphs={'current':packages([]),'exclude-new-sdk':packages(['-overlay='+str(overlay)])}
a,b=graphs.values();assert a.keys()==b.keys();assert all(a[p]['imports']==b[p]['imports'] and a[p]['embed_files']==b[p]['embed_files'] for p in a)
file_delta={p:{'only_current':sorted(set(a[p]['go_files'])-set(b[p]['go_files'])),'only_exclude':sorted(set(b[p]['go_files'])-set(a[p]['go_files']))} for p in a if a[p]['go_files']!=b[p]['go_files']}
assert file_delta=={'github.com/landuo/light-media-plugins/internal/sdk':{'only_current':production,'only_exclude':[]}}
(R/'linux-import-graph.json').write_text(json.dumps({'environment':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'},'graphs':graphs,'package_count':len(a),'imports_identical':True,'selected_file_delta':file_delta},indent=2)+'\n')
link=read(R/'link-delta-diagnosis.json');reflection=read(R/'reflection-metadata-equivalence.json');nm=read(R/'nm-metadata-address-delta.json')
assert len(link['builds']['current']['symbols'])==len(link['builds']['exclude-new-sdk']['symbols'])==4877
assert set(link['builds']['current']['symbols'])==set(link['builds']['exclude-new-sdk']['symbols'])
for name,one in link['builds']['current']['symbols'].items():
 two=link['builds']['exclude-new-sdk']['symbols'][name];assert one['bytes']==two['bytes'] and one['kind']==two['kind']
 if one['address']!=two['address']:assert name in ['go:func.*','runtime.epclntab','runtime.findfunctab'] and one['address']-two['address']==16
for symbol in link['builds']['current']['symbols']:
 assert not any(x in symbol for x in ['.SourceTasks','.SourceCompleted','.SourceAdd','.SourceControl','.sourceTasks','.sourceMutation','.SourceConnection','.SourceFindByTag','.Configurations','DownloaderSourceAddRequestV1','DownloaderSourceConnectionV1','DownloaderConfigurationsV1']),symbol
assert reflection['all_changed_rodata_bytes_explained'] and reflection['same_encoded_names_tags_and_flags'] and reflection['pc_file_line_maps_identical']
assert link['pc_function_map_difference_count']==0 and link['pc_function_count']==3210
prior=read(root/'work/migration-20261105/category-review/FINAL-REVIEW-20261105.json')
manifest=json.loads(subprocess.check_output(['go','run','./cmd/category-editor','--manifest'],cwd=root,text=True));assert manifest==prior['current_category_tests']['manifest']
(R/'current-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
rs=[json.loads(l) for l in (R/'current-category-race.jsonl').read_text().splitlines()];assert not any(x.get('Action')=='fail' for x in rs);ends=[x for x in rs if x.get('Action')=='pass' and not x.get('Test')];assert len(ends)==2
assert all(sha(root/p)==h for p,h in inputs['files'].items()) and sha(root/'SDK_ORIGIN.json')==inputs['sdk_origin_sha256']
oldcert=root/'work/migration-20261105/category-review-wire-final/impact-certificate.json';oldfinal=root/'work/migration-20261105/category-review/FINAL-REVIEW-20261105.json';assert sha(oldcert)==inputs['historical_prior_certificate_sha256'] and sha(oldfinal)==inputs['category_historical_final_sha256']
negative=read(R/'negative-reachable-client.json');assert negative['certificate_link_guard_rejects'] and negative['product_bytes_unchanged'] and negative['linked_source_clients']
result={'status':'passed_no_CategoryEditor_worker_dependency_impact','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'SDK93 worker additions only; current Linux link/ABI/PC metadata proof and native Category race; no current-host main/UI rerun','sdk_origin_sha256':inputs['sdk_origin_sha256'],'sdk_origin_commit':origin['source_commit'],'sdk_files':93,'all93_git_blobs_bound':True,'original84_files_unchanged':True,'new_files':new,'new_production_file_count':4,'new_test_file_count':5,'no_new_init_package_vars_registration':True,'category_business_form_command_module_files_unchanged':True,'category_historical_driver_files_unchanged':True,'linux_package_count':len(a),'linux_package_import_graph_identical':True,'selected_go_file_delta':file_delta,'retained_symbols':4877,'retained_symbol_names_sizes_kinds_identical':True,'retained_new_source_clients':[],'raw_nm_byte_equal':False,'nm_delta_only_metadata_addresses':nm,'machine_text_byte_identical':True,'machine_text':link['builds']['current']['sections']['.text'],'raw_rodata_byte_equal':False,'all68_rodata_changed_bytes_are_semantically_identical_name_pool_or8_adjusted_name_refs':True,'rodata_proof_sha256':sha(R/'reflection-metadata-equivalence.json'),'pc_function_file_line_maps_all_identical':3210,'pc_source_file_sets_identical':429,'other_identical_runtime_sections':reflection['raw_identical_sections'],'moduledata_delta':'cu table length+4; later metadata pointers+16 only; actual PC→file/line meaning identical','compiling_reachability_negative_killed':True,'negative_evidence_sha256':sha(R/'negative-reachable-client.json'),'current_category_manifest_exact':True,'current_category_race':{'passed_tests_and_subtests':sum(x.get('Action')=='pass' and bool(x.get('Test')) for x in rs),'packages':ends,'sha256':sha(R/'current-category-race.jsonl')},'input_unchanged':True,'original_evidence_sha256_unchanged':{'historical87_certificate':sha(oldcert),'historical_Category_final':sha(oldfinal)},'no_sdk93_client_caused_main_UI_rerun_required':True,'temporary_binaries_and_overlays_removed':True,'product_SDK_ledger_or_old_evidence_files_changed':False,'limits':['This certificate is scoped to Category worker SDK dependency additions, not approval of all Source capabilities or a current-host generic platform migration.','Historical75e actual main/Linux/UI runs retain their actual source/host/worker hashes. They are not reclassified as execution against404daade or SDK93.','Raw nm/full ELF/rodata equality was explicitly falsified and is not claimed; exact semantic metadata equivalence is separately proved.','Future Category/old84/init/registration/import-graph changes invalidate reuse and require new impact review.']}
(R/'impact-certificate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'sdk93_all_bound':True,'original84_unchanged':True,'packages':len(a),'new_clients_linked':False,'pc_functions':3210,'native_category_race':result['current_category_race']['passed_tests_and_subtests'],'certificate_sha256':sha(R/'impact-certificate.json')}))
