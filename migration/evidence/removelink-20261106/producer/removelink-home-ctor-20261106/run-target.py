from pathlib import Path
import subprocess,json,hashlib,shlex,uuid,sys
w=Path(__file__).resolve().parent;phase=sys.argv[1];exe=Path(sys.argv[2]).resolve();image='sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881';fixture=Path('/Users/accidia/projects/light-media-plugins/plugins/removelink/reference/unknown-home-source312.json');nonce=uuid.uuid4().hex[:12];remote='/home/admin/light-media-plugins-migration-rlk-ctor-'+nonce;marker='lm-plugin-removelink-ctor/'+nonce;ssh=['ssh','admin@192.168.8.129'];records=[]
run=subprocess.run(ssh+['umask 077; mkdir '+remote+' && printf %s '+shlex.quote(marker)+' > '+remote+'/TASK'],capture_output=True);assert run.returncode==0
try:
 for p,n in [(exe,'ctor.test'),(fixture,'source.json')]:
  r=subprocess.run(['scp','-q',str(p),'admin@192.168.8.129:'+remote+'/'+n],capture_output=True);assert r.returncode==0
 r=subprocess.run(ssh+['chmod 755 '+remote+'/ctor.test; chmod 644 '+remote+'/source.json'],capture_output=True);assert r.returncode==0
 for mode,uid in [('present-empty',65533),('present-value',65533),('absent-found',65534),('absent-unmapped',65533)]:
  label='lm-plugin-removelink-ctor-'+nonce+'-'+mode
  env=['/usr/bin/env','-u','HOME','-u','USER','REMOVELINK_HOME_CTOR_CASE='+mode]
  if mode=='present-empty':env.append('HOME=')
  if mode=='present-value':env.append('HOME=/owned/home')
  cmd=['docker','run','--rm','--label','task='+label,'--network','none','--read-only','--user',f'{uid}:{uid}','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777','--mount',f'type=bind,src={remote}/ctor.test,dst=/oracle/ctor.test,readonly','--mount',f'type=bind,src={remote}/source.json,dst=/oracle/reference/unknown-home-source312.json,readonly','--workdir','/oracle','--entrypoint',env[0],image]+env[1:]+['/oracle/ctor.test','-test.v','-test.timeout=20s','-test.run=^TestSource312ConstructorHomeBranches$']
  r=subprocess.run(ssh+[' '.join(map(shlex.quote,cmd))],capture_output=True);(w/(phase+'-'+mode+'.stdout')).write_bytes(r.stdout);(w/(phase+'-'+mode+'.stderr')).write_bytes(r.stderr)
  cleanup=ssh+['docker ps -aq --filter label=task='+label];c=subprocess.run(cleanup,capture_output=True);assert c.returncode==0 and not c.stdout.strip()
  records.append({'mode':mode,'command':ssh+[' '.join(map(shlex.quote,cmd))],'exit':r.returncode,'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'containers_remaining':c.stdout.decode()})
  (w/(phase+'-commands.json')).write_text(json.dumps(records,indent=2)+'\n')
finally:
 clean='set -eu; test "$(cat '+remote+'/TASK)" = '+shlex.quote(marker)+'; rm '+remote+'/ctor.test '+remote+'/source.json '+remote+'/TASK; rmdir '+remote+'; test ! -e '+remote
 c=subprocess.run(ssh+[clean],capture_output=True);(w/(phase+'-cleanup.stdout')).write_bytes(c.stdout+c.stderr)
 (w/(phase+'-cleanup.json')).write_text(json.dumps({'command':ssh+[clean],'exit':c.returncode,'local_test_binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()},indent=2)+'\n');assert c.returncode==0
print(json.dumps([{'mode':r['mode'],'exit':r['exit']} for r in records]))
