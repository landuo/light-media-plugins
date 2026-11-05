from pathlib import Path
import importlib.util,json,hashlib,zipfile,tempfile
r=Path('/Users/accidia/projects/light-media-plugins');w=r/'work/sites-review-20261105/mpserverstatus-packaging-addon';w.mkdir(exist_ok=True)
h=lambda b:hashlib.sha256(b).hexdigest()
pub=r/'migration/evidence/mpserverstatus-20261105/packaging';meta=json.loads((pub/'cross-package-result.json').read_bytes());script=r/'scripts/build_plugins.py'
spec=importlib.util.spec_from_file_location('canonical_packager',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert h(script.read_bytes())==meta['build_script_sha256'];assert h((r/'build-plugins.json').read_bytes())==meta['build_config_sha256']
cfg=m.read_config(r/'build-plugins.json');entry=next(x for x in cfg['plugins'] if x['id']=='MPServerStatus');assert entry==meta['plugin_spec'];assert len(entry['license_files'])==18
raw=(pub/'actual-linux-manifest.json').read_bytes();assert h(raw)==meta['actual_manifest_sha256'];manifest=m.validate_manifest(raw,'MPServerStatus')
art={Path(x['path']).name:x for x in meta['artifacts']};output=r/'work/migration-20261105/mpserverstatus-packaging/cross-output'
for name,x in art.items():assert h((output/name).read_bytes())==x['sha256']
plugin=next(p for p in output.glob('MPServerStatus*.zip'))
with zipfile.ZipFile(plugin) as z:
 assert len(z.namelist())==20 and len(set(z.namelist()))==20
 assert not any(Path(n).is_absolute() or '..' in Path(n).parts or ((z.getinfo(n).external_attr>>16)&0o170000)==0o120000 for n in z.namelist())
 files={n:z.read(n) for n in z.namelist()};assert z.testzip() is None
binary=files[manifest['entry']];assert binary[:4]==b'\x7fELF' and h(binary)=='66300eecf0ce7d785e3a448c338e163cfa83ac43cb13bce3e4efaeebfe852055'
licenses=m.license_inventory(r,[entry]);assert len(licenses)==19
assert files==dict(licenses,**{manifest['entry']:binary})
assert {x['path']:(x['size'],x['sha256']) for x in meta['member_inventory']}=={n:(len(b),h(b)) for n,b in files.items()}
index=json.loads((output/'go-plugins.v1.json').read_bytes());pi=index['plugins'][0];release=pi['releases'][0];artifact=release['artifacts'][0];assert release['manifest']==manifest
assert artifact['sha256']==h(plugin.read_bytes()) and artifact['executable_sha256']==h(binary) and artifact['size']==plugin.stat().st_size
assert artifact['url'].startswith('https://example.invalid/')
with tempfile.TemporaryDirectory(dir=w,prefix='canonical-replay-') as td:
 t=Path(td);a=t/plugin.name;n=t/'THIRD_PARTY_LICENSES.zip';m.archive_plugin(a,files);m.archive_plugin(n,licenses)
 assert a.read_bytes()==plugin.read_bytes();assert n.read_bytes()==(output/n.name).read_bytes()
 dest=t/'published';m.publish_fresh(dest,[a,n],index)
 assert all((dest/p.name).read_bytes()==p.read_bytes() for p in output.iterdir())
cert={'status':'passed','scope':'bounded packaging addon; no new business/main/UI execution, no remote release or deployment','canonical_builder_sha256':meta['build_script_sha256'],'build_config_sha256':meta['build_config_sha256'],'worker_sha256':h(binary),'previous_seals_unchanged':['72f9cde8fd6ffdbd5a1c0d266222787376433780daad9b9009ed84d2ba193e6a','02c22b2c86670c3eba7c8ee9e7982e998ee0a2e4928cf2a6079382c542444f5a','48f6ecbec472c6179f0b4e53d0d95b8f9a93612af476fa954919f47376e835f5'],'checks':['18 explicit notices plus canonical LICENSE produce19 notice members; byteexact current source and source provenance','20 plugin ZIP members: original ELF plus19 notices; no links/path escapes','validate_manifest actual NAS UID1000 output; worker byteexact independently certified66300','canonical archive_plugin and publish_fresh replay reproduced all3 outputs byte-for-byte','Mac CLI Linux-only failure and Docker proxy pull failure retained; task-only crossbuilder uses real Go crosscompile without platform spoofing'],'artifacts':meta['artifacts'],'source_inputs':[{'path':str(p.relative_to(r)),'sha256':h(p.read_bytes())} for p in [script,r/'build-plugins.json',pub/'cross_package.py',pub/'cross-package-result.json',pub/'actual-linux-manifest.json']],'cleanup':'replay TemporaryDirectory removed; no processes or binary extracted'}
(w/'review-evidence.json').write_text(json.dumps(cert,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'passed','certificate_sha256':h((w/'review-evidence.json').read_bytes()),'path':str(w/'review-evidence.json')}))
