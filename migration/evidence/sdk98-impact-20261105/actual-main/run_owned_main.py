from pathlib import Path
import subprocess,os,json,hashlib,datetime
r=Path('/home/admin/light-media-plugins-migration-sdk98-20261105');assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'
inputs={'bin/category-editor-sdk98-linux-amd64': '6f816f075373597647bbb91e29619394d2e468986da70a0e9110f07bbb7da868', 'bin/torrent-transfer-sdk98-linux-amd64': 'b2ba2090f1380be18445fe00c5e5031abb40cdb196204884df90e46f137cb1b5', 'bin/site-statistic-sdk98-linux-amd64': 'e2d81f53ac72aa75c06541418204e8469fbf6bd66a26dfafb4968fd50b027c75', 'bin/sdk98-impact-main-tests-linux-amd64': '95c1f38f6351be5b898ac065d6247497aebfebd84849c363bde56085d55fb36f', 'bin/light-media-hostf7-linux': '7521f81d24cddd658368b4b4ebd724c2dfc23494f460acc48e63370d6950fb17'}
for name,h in inputs.items():
 p=r/name;assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h,name;p.chmod(0o755)
run=r/'main-run-4';assert not run.exists()
env=dict(os.environ,SDK98_IMPACT_HOST_BINARY=str(r/'bin/light-media-hostf7-linux'),SDK98_IMPACT_CATEGORY_BINARY=str(r/'bin/category-editor-sdk98-linux-amd64'),SDK98_IMPACT_TORRENT_BINARY=str(r/'bin/torrent-transfer-sdk98-linux-amd64'),SDK98_IMPACT_SITE_BINARY=str(r/'bin/site-statistic-sdk98-linux-amd64'),SDK98_IMPACT_RUNTIME_DIR=str(run),SDK98_IMPACT_LISTEN='127.0.0.1:36257')
cmd=[str(r/'bin/sdk98-impact-main-tests-linux-amd64'),'-test.run=^TestSDK98ImpactOrdinaryMainFourInstances$','-test.timeout=10m','-test.v']
meta={'classification':'actual UID1000 native Linux ordinary f7 main plus current98 Cat/TT/music/Site workers; owned qB queryprotocol and real TLS/NexusHTML peers; not real daemon fulltransfer replay','command':cmd,'input_sha256':inputs,'environment':{k:v for k,v in env.items() if k.startswith('SDK98_IMPACT_')},'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_role':'wrapper/read-only owned SQLite instrumentation only; product and workers are Go'}
p=r/'main-run-4-command.json';p.write_text(json.dumps(meta,indent=2)+'\n')
with (r/'main-run-4.log').open('wb') as log:out=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
meta.update(exit_code=out.returncode,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());p.write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({'exit_code':out.returncode}),flush=True);print((r/'main-run-4.log').read_text()[-6000:]);raise SystemExit(out.returncode)
