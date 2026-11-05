from pathlib import Path,PurePosixPath
import json,hashlib,zipfile,importlib.util,tempfile,subprocess,struct
root=Path('/Users/accidia/projects/light-media-plugins');out=Path(__file__).resolve().parent;work=root/'work/migration-20261105/pluginuninstall-packaging-20261106';sha=lambda b:hashlib.sha256(b).hexdigest()
record=json.loads((work/'cross-package-result.json').read_text());assert record['exit_code']==0
assert sha((root/'build-plugins.json').read_bytes())==record['build_config_sha256'];assert sha((root/'scripts/build_plugins.py').read_bytes())==record['build_script_sha256']
for a in record['artifacts']:assert sha((root/a['path']).read_bytes())==a['sha256']
spec=importlib.util.spec_from_file_location('independent_pui_packager',root/'scripts/build_plugins.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
entry=next(x for x in m.read_config(root/'build-plugins.json')['plugins'] if x['id']=='PluginUnInstall');assert entry==record['plugin_spec']
actual=(work/'actual-linux-manifest.json').read_bytes();assert sha(actual)==record['actual_manifest_sha256'];manifest=m.validate_manifest(actual,'PluginUnInstall')
name='PluginUnInstall-2.2-linux-amd64.zip';archive=work/'cross-output'/name
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==7
 for i in z.infolist():
  p=PurePosixPath(i.filename);assert not p.is_absolute() and '..' not in p.parts and ((i.external_attr>>16)&0o170000)!=0o120000
 binary=z.read(manifest['entry']);assert sha(binary)=='86cf644722a7bace3b8f860426c86d044e5c9d9659586160f737c76e58fb2df1'
 assert binary[:4]==b'\x7fELF' and binary[4]==2 and binary[5]==1 and struct.unpack_from('<H',binary,18)[0]==62
 files={};m.add_file(files,manifest['entry'],binary)
 for n,b in m.license_inventory(root,[entry]).items():m.add_file(files,n,b)
 assert len(files)==7 and set(files)==set(z.namelist());assert all(z.read(n)==b for n,b in files.items())
 notices=m.license_inventory(root,[entry]);assert len(notices)==6
 with zipfile.ZipFile(work/'cross-output/THIRD_PARTY_LICENSES.zip') as n:
  assert set(n.namelist())==set(notices) and all(n.read(k)==b for k,b in notices.items())
with tempfile.TemporaryDirectory(prefix='canonical-replay-',dir=out) as d:
 p=Path(d);(p/'worker-elf-for-buildinfo').write_bytes(binary)
 with (out/'PUI-ELF-buildinfo.txt').open('wb') as f:subprocess.run(['go','version','-m',str(p/'worker-elf-for-buildinfo')],stdout=f,check=True)
 z=p/name;m.archive_plugin(z,files);assert z.read_bytes()==archive.read_bytes()
 n=p/'THIRD_PARTY_LICENSES.zip';m.archive_plugin(n,notices)
 art={'platform':'linux-amd64','url':m.release_base('https://example.invalid/not-published/pluginuninstall-20261105')+name,'sha256':sha(z.read_bytes()),'size':z.stat().st_size,'format':'zip','executable_sha256':sha(binary),'host_contract':entry['host_contract'],'files':[{'path':k,'size':len(files[k]),'sha256':sha(files[k])} for k in sorted(files)]}
 index={'schema_version':1,'plugin_id':manifest['plugin_id'],'current_version':manifest['version'],'releases':[{'version':manifest['version'],'manifest':manifest,'artifacts':[art]}]}
 published=m.fresh_output(p/'published');m.publish_fresh(published,[z,n],{'schema_version':1,'plugins':[index]})
 for x in published.iterdir():assert x.read_bytes()==(work/'cross-output'/x.name).read_bytes(),x.name
report={'classification':'independent canonical package API replay, archive ELF/notices/BOM inspection; reused original actual NAS --manifest, no new Linux execution and no remote release','worker_sha256':sha(binary),'zip_members':7,'declared_notices':6,'canonical_outputs_byteexact':3,'actual_manifest_sha256':sha(actual),'config_sha256':record['build_config_sha256'],'builder_sha256':record['build_script_sha256'],'module_closure':'actual worker buildinfo x/text0.43.0; brotli/x/net not linked','notice_map':{k:sha(b) for k,b in notices.items()},'own_temp_worker_archives_removed':True}
(out/'packaging-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
