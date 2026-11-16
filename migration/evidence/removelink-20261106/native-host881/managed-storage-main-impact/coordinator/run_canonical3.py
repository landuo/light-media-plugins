from pathlib import Path
import os,json,hashlib,subprocess,time,datetime
r=Path('/home/admin/light-media-plugins-migration-removelink-20261105');shared=Path('/home/admin/light-media-plugins-migration-sdk98-20261105')
assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/RemoveLink/20261105/owned-only'
assert (shared/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'
inputs=json.loads((r/'canonical-package-storage-inputs.json').read_text())
for name,expected in inputs.items():
 p=Path(name);assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
 if '/bin/' in name:p.chmod(0o755)
run=r/'canonical-package-main-3';assert not run.exists()
env=dict(os.environ,REMOVELINK_HOST_BINARY=str(shared/'bin/light-media-host-managed-storage-linux'),REMOVELINK_EXPECT_HOST_SHA256='6ce69c24f883dba3ab45b9e51bc0262934f3372c454533e119667c5791ea6db1',REMOVELINK_RUNTIME_DIR=str(run),REMOVELINK_LISTEN='127.0.0.1:36259',REMOVELINK_PACKAGE_ZIP=str(r/'canonical-package-auth-input/RemoveLink-2.18-linux-amd64.zip'),REMOVELINK_PACKAGE_INDEX=str(r/'canonical-package-auth-input/go-plugins.v1.json'))
cmd=[str(r/'bin/removelink-main6-linux.test'),'-test.run=^TestRemoveLinkCanonicalPackageOrdinaryMain$','-test.timeout=10m','-test.v']
meta={'classification':'actual canonical10member ZIP installed through ordinary Main651dd+2managed-storage; ELF6ce69c; unchanged canonical ZIP f907/currentworker6d75; current23 new6d75 native worker + platform clone + actual Linux owned hardlink cleanup + native source cache-query imports; no browser claim from this run','command':cmd,'environment':{k:v for k,v in env.items()if k.startswith('REMOVELINK_')},'input_sha256':inputs,'driver_unexecuted_old_PUI_source':'f24 reproducible via frozen-test-inputs single-file overlay; newPUI driver01ba is a separate test input','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};p=r/'canonical-package-main-3-command.json';p.write_text(json.dumps(meta,indent=2)+'\n');start=time.monotonic()
with (r/'canonical-package-main-3.log').open('wb') as log:result=subprocess.run(cmd,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT)
meta.update(exit_code=result.returncode,seconds=time.monotonic()-start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());p.write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({'exit_code':result.returncode,'seconds':meta['seconds']}));print((r/'canonical-package-main-3.log').read_text()[-2500:]);raise SystemExit(result.returncode)
