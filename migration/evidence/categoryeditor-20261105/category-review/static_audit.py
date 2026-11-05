from pathlib import Path
import ast, hashlib, json, subprocess
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
host=Path('/Users/accidia/projects/light-media')
source=root/'work/migration-20261105/source-snapshot/categoryeditor/__init__.py'
tree=ast.parse(source.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
attrs={n.targets[0].id:ast.literal_eval(n.value) for n in cls.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
methods={n.name:dict(lineno=n.lineno,no_op=all(isinstance(x,(ast.Pass,ast.Expr)) for x in n.body)) for n in cls.body if isinstance(n,ast.FunctionDef)}
form_method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_form')
source_form=ast.literal_eval(next(n for n in form_method.body if isinstance(n,ast.Return)).value.elts[0])
form=json.loads((root/'plugins/categoryeditor/form.json').read_text());assert source_form==form
manifest=json.loads(subprocess.check_output(['go','run','./cmd/category-editor','--manifest'],cwd=root))
for src,key in {'plugin_name':'name','plugin_desc':'description','plugin_icon':'icon','plugin_version':'version','plugin_author':'author','author_url':'author_url','plugin_order':'plugin_order'}.items(): assert manifest[key]==attrs[src],(src,key)
for key in ['events','api','dashboards','frontend']:
    assert not manifest.get(key),key
assert manifest['entry']=='category-editor'
assert manifest['runtime']=='go-executable'
registry=json.loads((root/'build-plugins.json').read_text())['plugins'];build=next(p for p in registry if p['id']=='CategoryEditor')
assert build['package']=='./cmd/category-editor' and build['host_contract']=='light-media.sdk-resources/v1' and 'frontend' not in build
normalized=[]
for target,prior in [('plugins/categoryeditor/categoryeditor.go','internal/plugins/categoryeditor/categoryeditor.go'),('plugins/categoryeditor/form.json','internal/plugins/categoryeditor/form.json'),('cmd/category-editor/main.go','cmd/category-editor/main.go')]:
    a=(root/target).read_text();b=(host/prior).read_text().replace('"light-media/internal/plugins/categoryeditor"','"github.com/landuo/light-media-plugins/plugins/categoryeditor"').replace('"light-media/internal/plugins"','"github.com/landuo/light-media-plugins/internal/sdk"')
    normalized.append(dict(target=target,pinned_host_path=prior,equal_except_module_relocation=a==b))
    assert a==b,target
files=['plugins/categoryeditor/categoryeditor.go','plugins/categoryeditor/form.json','plugins/categoryeditor/categoryeditor_test.go','cmd/category-editor/main.go','cmd/category-editor/main_test.go','build-plugins.json','scripts/build_plugins.py','.github/workflows/linux-amd64.yml','go.mod','go.sum']
hostfiles=['internal/app/plugin_categoryeditor_resources.go','internal/app/plugin_categoryeditor_wire.go','internal/app/media_category.go','internal/app/media_category_runtime.go','internal/app/category_conditions.go','internal/app/category_yaml.go','internal/app/defaults/category.yaml','internal/plugins/category_policy.go','testdata/plugins/category-editor-1.3/installed-category-helper.py','migration/evidence/categoryeditor/resume-20261029/categoryeditor-final-independent-review-20261029.json']
result=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_methods=methods,source_static_metadata=attrs,manifest=manifest,source_form_equals_target=True,current_host_semantic_identity=normalized,target_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),host_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=host,text=True).strip(),files={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},host_files={f:hashlib.sha256((host/f).read_bytes()).hexdigest() for f in hostfiles},notes=['Build helper uses Python only on build machines; release ZIP payload contains Go executable, embedded JSON form and legal notices.','Linux/amd64 actual ZIP build and install require coordinator evidence; not executed by this static audit.','CategoryHelper source is archived 2026-10-20; no new claim about live helper identity.'])
(here/'static-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(form_equal=True,metadata_equal=True,normalized_host_identity=all(x['equal_except_module_relocation'] for x in normalized),host=result['host_head'])))
