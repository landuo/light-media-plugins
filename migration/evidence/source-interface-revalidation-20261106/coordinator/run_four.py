from pathlib import Path
import os,hashlib,json,subprocess,time,datetime
r=Path('/home/admin/light-media-plugins-migration-sdk98-20261105');rlk=Path('/home/admin/light-media-plugins-migration-removelink-20261105')
assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'
assert (rlk/'.task-owned').read_text().strip()=='light-media-plugins/RemoveLink/20261105/owned-only'
inputs=json.loads((r/'source-declarations-four-inputs.json').read_text())
for name,expected in inputs.items():
 p=Path(name);assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,name;p.chmod(0o755)
run=r/'source-declarations-main-four-1';assert not run.exists()
env=dict(os.environ,SDK98_IMPACT_HOST_BINARY=str(r/'bin/light-media-host-getter-gates-linux'),SDK98_IMPACT_CATEGORY_BINARY=str(r/'bin/category-editor-source-declarations-linux'),SDK98_IMPACT_TORRENT_BINARY=str(r/'bin/torrent-transfer-source-declarations-linux'),SDK98_IMPACT_SITE_BINARY=str(r/'bin/site-statistic-source-declarations-linux'),SDK98_IMPACT_RUNTIME_DIR=str(run),SDK98_IMPACT_LISTEN='127.0.0.1:36257')
cmd=[str(rlk/'bin/removelink-main6-linux.test'),'-test.run=^TestSDK98ImpactOrdinaryMainFourInstances$','-test.timeout=10m','-test.v']
meta={'classification':'actual native UID1000 ordinary Main3c05 plus corrected current Cat/TT/music/Site manifests; owned source-qB query-protocol peer and TLS/Nexus HTML, not real daemon full-transfer repeat','raw_driver_historical_label':'sdk98 impact driver retains earlier ordinary f7 wording; actual current host and source inputs are identified by this exact command/input binding, not that old label','command':cmd,'environment':{k:v for k,v in env.items()if k.startswith('SDK98_IMPACT_')},'input_sha256':inputs,'producer_freeze':'4693f0b87c3e78efb7d814b4d2db0e19c9302b8c822ee76c236339f8696a54b0','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};p=r/'source-declarations-main-four-1-command.json';p.write_text(json.dumps(meta,indent=2)+'\n');start=time.monotonic()
with (r/'source-declarations-main-four-1.log').open('wb') as log:result=subprocess.run(cmd,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT)
meta.update(exit_code=result.returncode,seconds=time.monotonic()-start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());p.write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({'exit_code':result.returncode,'seconds':meta['seconds']}));print((r/'source-declarations-main-four-1.log').read_text()[-2500:]);raise SystemExit(result.returncode)
