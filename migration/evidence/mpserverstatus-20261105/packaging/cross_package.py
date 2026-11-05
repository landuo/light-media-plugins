from pathlib import Path
import importlib.util,subprocess,os,json,hashlib,tempfile,zipfile,datetime
root=Path.cwd();work=root/"work/migration-20261105/mpserverstatus-packaging";spec=importlib.util.spec_from_file_location("packager",root/"scripts/build_plugins.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda data:hashlib.sha256(data).hexdigest()
config=m.read_config(root/"build-plugins.json");entry=next(x for x in config["plugins"] if x["id"]=="MPServerStatus");base=m.release_base("https://example.invalid/not-published/mps-20261105");output=m.fresh_output(work/"cross-output")
meta={"classification":"real cross-built Go ELF, actual NAS Linux amd64 --manifest, existing canonical packaging validation/archive/publish functions; no platform spoof, no modified production builder or Python product runtime", "canonical_mac_CLI":"failed as designed; retained original build-command/stdout/stderr", "started_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"build_config_sha256":sha((root/"build-plugins.json").read_bytes()),"build_script_sha256":sha((root/"scripts/build_plugins.py").read_bytes()),"plugin_spec":entry,"release_url":"explicit nonpublished example.invalid fixture; no remote release/upload"}
remote="/home/admin/light-media-plugins-migration-mps-20261105";peer="admin@192.168.8.129"
with tempfile.TemporaryDirectory(prefix=".mps-cross-build-",dir=work) as td:
 build=Path(td);worker=build/"compiled-worker";cmd=["go","build","-trimpath","-buildvcs=false","-o",str(worker),entry["package"]];out=subprocess.run(cmd,cwd=root,env=dict(os.environ,GOOS="linux",GOARCH="amd64",CGO_ENABLED="0"),capture_output=True);(work/"cross-build.stdout").write_bytes(out.stdout);(work/"cross-build.stderr").write_bytes(out.stderr);meta["build"]={"command":cmd,"exit_code":out.returncode};assert out.returncode==0
 binary=worker.read_bytes();h=sha(binary);meta["worker_sha256"]=h;assert h=="66300eecf0ce7d785e3a448c338e163cfa83ac43cb13bce3e4efaeebfe852055",h
 check="from pathlib import Path; import os; r=Path("+repr(remote)+");assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/MPServerStatus/20261105/owned-only'; p=r/'package-manifest-owned';p.mkdir(mode=0o700)"
 subprocess.run(["ssh",peer,"python3","-c",__import__('shlex').quote(check)],check=True)
 try:
  subprocess.run(["scp",str(worker),peer+":"+remote+"/package-manifest-owned/compiled-worker"],check=True)
  run="from pathlib import Path; import hashlib,subprocess,os; r=Path("+repr(remote)+");assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/MPServerStatus/20261105/owned-only'; p=r/'package-manifest-owned/compiled-worker'; assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(h)+"; p.chmod(0o755); out=subprocess.run([str(p),'--manifest'],capture_output=True,timeout=30);assert out.returncode==0;os.write(1,out.stdout)"
  actual=subprocess.run(["ssh",peer,"python3","-c",__import__('shlex').quote(run)],check=True,capture_output=True).stdout;(work/"actual-linux-manifest.json").write_bytes(actual);manifest=m.validate_manifest(actual,"MPServerStatus")
 finally:
  clean="from pathlib import Path;import os;r=Path("+repr(remote)+");assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/MPServerStatus/20261105/owned-only';p=r/'package-manifest-owned/compiled-worker';assert not p.is_symlink();p.unlink(missing_ok=True);(r/'package-manifest-owned').rmdir()"
  subprocess.run(["ssh",peer,"python3","-c",__import__('shlex').quote(clean)],check=True)
 files={};m.add_file(files,manifest["entry"],binary)
 for name,data in m.license_inventory(root,[entry]).items():m.add_file(files,name,data)
 assert len(files)==20 and len(m.license_inventory(root,[entry]))==19
 filename=f"{manifest['plugin_id']}-{manifest['version']}-linux-amd64.zip";archive=build/filename;m.archive_plugin(archive,files);data=archive.read_bytes();artifact={"platform":"linux-amd64","url":base+filename,"sha256":sha(data),"size":len(data),"format":"zip","executable_sha256":h,"host_contract":entry["host_contract"],"files":[{"path":name,"size":len(files[name]),"sha256":sha(files[name])} for name in sorted(files)]};index={"schema_version":1,"plugin_id":manifest["plugin_id"],"current_version":manifest["version"],"releases":[{"version":manifest["version"],"manifest":manifest,"artifacts":[artifact]}]}
 notices=build/"THIRD_PARTY_LICENSES.zip";m.archive_plugin(notices,m.license_inventory(root,[entry]));m.publish_fresh(output,[archive,notices],{"schema_version":1,"plugins":[index]})
 for z in [output/filename,output/notices.name]:
  with zipfile.ZipFile(z) as f:
   assert f.testzip() is None
   expected=files if z.name==filename else m.license_inventory(root,[entry]);assert set(f.namelist())==set(expected)
   assert all(f.read(n)==expected[n] for n in f.namelist())
 meta.update(exit_code=0,artifacts=[{"path":str(q.relative_to(root)),"sha256":sha(q.read_bytes()),"bytes":q.stat().st_size} for q in sorted(output.iterdir())],member_inventory=artifact["files"],actual_manifest_sha256=sha(actual),ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(work/"cross-package-result.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n");print(json.dumps({"exit_code":0,"worker_sha256":h,"notices":19,"package_members":20,"artifacts":len(meta['artifacts'])}))
