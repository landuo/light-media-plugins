from pathlib import Path
import ast,hashlib,json,subprocess
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
host=Path('/Users/accidia/projects/light-media');ref=root/'work/migration-20261105/host-reference';sha='75e13686a0e3df05ac251e359303ef3fd5971cf6'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((root/'work/migration-20261105/host-reference-manifest.json').read_text())
for item in manifest['files']: assert digest(ref/item['path'])==item['sha256'],item['path']
helper=ref/'app/modules/themoviedb/category.py';archived=host/'testdata/plugins/category-editor-1.3/installed-category-helper.py';default=ref/'config/category.yaml';embedded=host/'internal/app/defaults/category.yaml'
assert helper.read_bytes()==archived.read_bytes()
assert default.read_bytes()==embedded.read_bytes()
config=ref/'app/core/config.py';tree=ast.parse(config.read_text())
settings=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Settings')
methods={m.name:m for m in settings.body if isinstance(m,ast.FunctionDef)}
# Pure AST inspection. Do not import production settings or execute the module.
assert ast.unparse(methods['ROOT_PATH'].body[0].value)=='Path(__file__).parents[2]'
assert ast.unparse(methods['INNER_CONFIG_PATH'].body[0].value)=="self.ROOT_PATH / 'config'"
assert "return Path('/config')" in ast.unparse(methods['CONFIG_PATH'])
origin=root/'SDK_ORIGIN.json';data=json.loads(origin.read_text());assert data['source_commit']==sha
sdk=[]
for item in data['files']:
    raw=subprocess.check_output(['git','show',sha+':'+item['source_path']],cwd=host)
    assert hashlib.sha256(raw).hexdigest()==item['source_sha256']
    expected=raw.replace(b'"light-media/internal/plugins"',b'"github.com/landuo/light-media-plugins/internal/sdk"').replace(b'"light-media/internal/sourcejson"',b'"github.com/landuo/light-media-plugins/internal/sdk/sourcejson"')
    current=(root/item['path']).read_bytes();assert current==expected,item['path'];assert hashlib.sha256(current).hexdigest()==item['sha256']
    sdk.append(dict(path=item['path'],sha256=item['sha256'],source_path=item['source_path'],source_exact_after_import_relocation=True))
verification=root/'work/migration-20261105/sdk/verification.json';verified=json.loads(verification.read_text());assert digest(origin)==verified['sdk_origin_sha256']
for cmd in verified['commands']:
    if 'evidence_sha256' in cmd: assert digest(verification.parent/cmd['evidence'])==cmd['evidence_sha256']
initial={x['path']:digest(root/x['path']) for x in sdk}
run=subprocess.run(['go','test','./plugins/categoryeditor','./cmd/category-editor','-count=1','-v'],cwd=root,text=True,capture_output=True)
(here/'unit-tests-sdk-frozen.log').write_text(run.stdout+run.stderr+'COMMAND_EXIT='+str(run.returncode)+'\n');assert run.returncode==0
assert initial=={x['path']:digest(root/x['path']) for x in sdk},'SDK changed during unit verification'
out=dict(status='live_source_and_default_identity_verified; actual_host_acceptance_pending',live_reference_manifest_sha256=digest(root/'work/migration-20261105/host-reference-manifest.json'),container_image_id=manifest['container_image_id'],started_at=manifest['started_at'],live_helper=dict(path=str(helper.relative_to(root)),sha256=digest(helper),bytes=helper.stat().st_size,equals_archived_source_exactly=True),live_builtin_default=dict(path=str(default.relative_to(root)),sha256=digest(default),bytes=default.stat().st_size,equals_current_host_embedded_resource_exactly=True,source_container_path='/app/config/category.yaml',not_active_user_path='/config/category.yaml'),live_config_path_semantics=dict(source_sha256=digest(config),ROOT_PATH='Path(__file__).parents[2] -> /app for collected /app/app/core/config.py',INNER_CONFIG_PATH='/app/config',CONFIG_PATH='CONFIG_DIR override, else /config when Docker; not interchangeable with INNER_CONFIG_PATH',inspection='AST and source only; no production settings import'),sdk=dict(source_commit=sha,origin_sha256=digest(origin),files_checked=len(sdk),source_target_exact=True,production_tree_sha256_as_independently_file_checked_sdk_evidence=verified['production_tree_sha256'],verification_sha256=digest(verification),evidence_hashes_validated=True,tests_executed_by_sdk_worker=verified['commands'],files=sdk),unit_test=dict(command='go test ./plugins/categoryeditor ./cmd/category-editor -count=1 -v',exit_code=run.returncode,log_sha256=digest(here/'unit-tests-sdk-frozen.log'),sdk_unchanged_during_run=True,linux_worker_transport='skipped on this darwin/arm64 machine, not counted as acceptance'),limits=['No old oracle/test output was edited or presented as a new live execution.','Byte identity upgrades the source provenance of historical helper/default inputs; it does not prove the live ruamel/WeakSingleton/message/config DB runtime matches historical adapters.','No active user category.yaml/configuration content has been used as the builtin default.','No private configuration migration or current target App/browser/Linux runtime acceptance is claimed.'])
(here/'live-dependency-binding.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(live_helper_equals_archive=True,live_default_equals_embedded=True,sdk_complete_files_checked=len(sdk),sdk_origin_sha256=digest(origin),frozen_unit_tests_passed=True)))
