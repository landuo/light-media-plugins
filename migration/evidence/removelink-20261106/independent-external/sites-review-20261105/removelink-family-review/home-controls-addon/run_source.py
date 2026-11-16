from pathlib import Path
import json,hashlib,subprocess,uuid
out=Path(__file__).resolve().parent;prefix=(out.parent/'log-source-payload.py').read_text().split('\ncases=[]\n',1)[0]
s=prefix+'''
import pwd
missing='__lm_review_no_such_user_20261106__'
try:pwd.getpwnam(missing);raise AssertionError('absent name required')
except KeyError:pass
cases=[('~',''),('~/m/file',''),('~','owned-relative'),('~/m/file','owned-relative')]
rows=[]
for path,home in cases:
 if home is None:os.environ.pop('HOME',None)
 else:os.environ['HOME']=home
 value=None;error=None
 try:value=NS['RemoveLink']._normalize_config_path(path)
 except BaseException as e:error={'class':type(e).__name__,'message':str(e)}
 rows.append({'path':path,'HOME':home,'value':value,'error':error})
print(json.dumps({'runtime':sys.version,'source_sha256':hashlib.sha256(SOURCE_TEXT.encode()).hexdigest(),'classification':'actual installed normalization AST+realPath/pwd; process-only synthetic HOME; no app/config/DB/files/network','cases':rows}))
'''
(out/'source-payload.py').write_text(s);label='lm-review-rlk-home-path-'+uuid.uuid4().hex
cmd=['ssh','admin@192.168.8.129','docker run --rm -i --label task='+label+' --network none --read-only --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777 --entrypoint python sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -B -S -'];r=subprocess.run(cmd,input=s.encode(),capture_output=True);(out/'source-oracle.json').write_bytes(r.stdout);(out/'source.stderr').write_bytes(r.stderr)
check=['ssh','admin@192.168.8.129','docker ps -aq --filter label=task='+label];c=subprocess.run(check,capture_output=True)
(out/'source-command.json').write_text(json.dumps({'command':cmd,'exit':r.returncode,'payload_sha256':hashlib.sha256(s.encode()).hexdigest(),'cleanup_command':check,'cleanup_exit':c.returncode,'containers_remaining':c.stdout.decode()},indent=2)+'\n');assert r.returncode==0,r.stderr.decode();print(r.stdout.decode())
