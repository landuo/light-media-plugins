from pathlib import Path
import json,hashlib,subprocess,uuid
out=Path(__file__).resolve().parent;prefix=(out.parent/'log-source-payload.py').read_text().split('\ncases=[]\n',1)[0];rows=[];commands=[]
for mode,uid,present,home in [('present-empty',65533,True,''),('present-value',65533,True,'/owned/home'),('absent-found',65534,False,None),('absent-unmapped',65533,False,None)]:
 suffix='''
import pwd
MODE=MODE_VALUE
PRESENT=PRESENT_VALUE
HOME_VALUE=HOME_REPR
if PRESENT:os.environ['HOME']=HOME_VALUE
else:os.environ.pop('HOME',None)
try:u=pwd.getpwuid(os.getuid());resolved={'name':u.pw_name,'home':u.pw_dir}
except KeyError:resolved=None
values=[]
for path in ['~','~/child','/absolute/no-home']:
 result=None;error=None
 try:result=NS['RemoveLink']._normalize_config_path(path)
 except Exception as e:error={'class':type(e).__name__,'message':str(e)}
 values.append({'path':path,'value':result,'error':error})
obj=NS['RemoveLink']();obj.exclude_dirs=''
empty_exclude=obj._RemoveLink__is_excluded(pathlib.Path('~__absent_name__'))
print(json.dumps({'mode':MODE,'uid':os.getuid(),'HOME_present':PRESENT,'HOME':HOME_VALUE,'passwd':resolved,'values':values,'empty_exclude':empty_exclude,'runtime':sys.version}))
'''.replace('MODE_VALUE',repr(mode)).replace('PRESENT_VALUE',repr(present)).replace('HOME_REPR',repr(home))
 s=prefix+suffix;(out/(mode+'-source-payload.py')).write_text(s);label='lm-review-home-ctor-'+uuid.uuid4().hex;cmd=['ssh','admin@192.168.8.129',f'docker run --rm -i --label task={label} --network none --read-only --user {uid}:{uid} --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777 --entrypoint python sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -B -S -'];r=subprocess.run(cmd,input=s.encode(),capture_output=True);(out/(mode+'-source.stdout')).write_bytes(r.stdout);(out/(mode+'-source.stderr')).write_bytes(r.stderr)
 check=['ssh','admin@192.168.8.129','docker ps -aq --filter label=task='+label];c=subprocess.run(check,capture_output=True);commands.append({'command':cmd,'exit':r.returncode,'payload_sha256':hashlib.sha256(s.encode()).hexdigest(),'cleanup_command':check,'cleanup_exit':c.returncode,'remaining':c.stdout.decode()});assert r.returncode==0,r.stderr.decode();rows.append(json.loads(r.stdout))
(out/'source-oracle.json').write_text(json.dumps({'classification':'independent actual333/Python3.12 Path constructor dependency chain; each UID/env branch is a new read-only network-none disposable process; no app/config/DB imports','source_sha256':'22fb375e531378b3454607c7bca305b637abd60ee8ed69e14e32fbc2ddfc5485','cases':rows},ensure_ascii=False,indent=2)+'\n');(out/'source-commands.json').write_text(json.dumps(commands,indent=2)+'\n');print('source4 branches complete')
