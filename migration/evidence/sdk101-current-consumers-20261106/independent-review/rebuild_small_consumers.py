from pathlib import Path
import subprocess,os,json,time,hashlib
r=Path('/Users/accidia/projects/light-media-plugins');w=Path(__file__).resolve().parent;p=r/'work/parallel-sdk-sync-20261106';env=dict(os.environ,GOOS='linux',GOARCH='amd64',CGO_ENABLED='0',GOFLAGS='',GOPROXY='off');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=json.loads((p/'consumer-inputs-after.json').read_text());assert all(sha(r/n)==h for n,h in source.items());rows=[]
for row in json.loads((p/'linux-consumer-builds.json').read_text()):
 if row['id']not in ['CategoryEditor','MPServerStatus']:continue
 out=w/(row['id']+'-independent-temporary-linux');cmd=list(row['command']);cmd[cmd.index('-o')+1]=str(out);start=time.monotonic();q=subprocess.run(cmd,cwd=r,env=env,capture_output=True);(w/(row['id']+'-independent-build.stdout')).write_bytes(q.stdout);(w/(row['id']+'-independent-build.stderr')).write_bytes(q.stderr);proof={'id':row['id'],'command':cmd,'cwd':str(r),'environment':{k:env[k]for k in ['GOOS','GOARCH','CGO_ENABLED','GOFLAGS','GOPROXY']},'exit':q.returncode,'seconds':time.monotonic()-start,'source_snapshot_sha256':sha(p/'consumer-inputs-after.json')}
 if q.returncode==0:
  proof.update(sha256=sha(out),Root_sha256=row['sha256'],byte_identical=sha(out)==row['sha256'],bytes=out.stat().st_size);(w/(row['id']+'-independent-buildinfo.txt')).write_bytes(subprocess.check_output(['go','version','-m',str(out)],cwd=r));out.unlink();proof['temporary_removed']=not out.exists()
 rows.append(proof);print(row['id'],proof,flush=True)
assert all(sha(r/n)==h for n,h in source.items());(w/'independent-rebuilds.json').write_text(json.dumps({'input_count':len(source),'inputs_stable':True,'rows':rows},indent=2)+'\n');assert all(x['exit']==0 and x['byte_identical']for x in rows)
