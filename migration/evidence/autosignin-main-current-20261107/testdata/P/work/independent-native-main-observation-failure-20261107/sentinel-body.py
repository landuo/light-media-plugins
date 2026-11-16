import subprocess,json,time,math,os
NAME='lm-independent-startup-sentinel-20261107';LABEL='lm-independent-startup-sentinel-20261107';IMAGE='sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881'
assert os.getuid()==1000
records=[];process=None;seen=None;stdout=b'';stderr=b'';failure=None;started=time.monotonic();wall=time.time()
def call(argv,timeout=5):
 begin=time.monotonic();at=time.time()
 try:
  p=subprocess.run(argv,capture_output=True,timeout=timeout);row=dict(argv=argv,at_epoch=at,relative=begin-started,seconds=time.monotonic()-begin,exit=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace'));records.append(row);return p
 except subprocess.TimeoutExpired as e:
  records.append(dict(argv=argv,at_epoch=at,relative=begin-started,seconds=time.monotonic()-begin,exception='TimeoutExpired',stdout=(e.stdout or b'').decode(errors='replace'),stderr=(e.stderr or b'').decode(errors='replace')));return None

def owned(info):
 assert info['Image']==IMAGE and info['Config']['Labels'].get('task')==LABEL and info['Name']=='/'+NAME
 assert info['Config']['User']=='1000:1000'and info['HostConfig']['NetworkMode']=='none'and info['HostConfig']['ReadonlyRootfs']and not info['HostConfig']['Privileged']
 assert not any(x['Type']=='bind'for x in info['Mounts'])
 return info['Id']
ps=['docker','ps','-aq','--filter','label=task='+LABEL,'--filter','name=^/'+NAME+'$'];pre=call(ps);assert pre and pre.returncode==0 and not pre.stdout.strip()
code="import os,time,json;print(json.dumps({'sentinel':'owned-startup-only','uid':os.getuid(),'wall':time.time(),'monotonic':time.monotonic()}),flush=True);time.sleep(8)"
args=['docker','run','--rm','--name',NAME,'--label','task='+LABEL,'--network','none','--read-only','--no-healthcheck','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--pids-limit','64','--tmpfs','/tmp:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700,size=16777216','--tmpfs','/config:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700,size=16777216','--entrypoint','python3',IMAGE,'-B','-c',code]
launched=time.monotonic();launch_wall=time.time();deadline=launched+30
try:
 process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 while time.monotonic()<deadline:
  p=call(['docker','inspect',NAME],timeout=min(2,max(.1,deadline-time.monotonic())))
  if p and p.returncode==0:
   info=json.loads(p.stdout)[0];ident=owned(info)
   if seen is None:seen=dict(id=ident,first_visible_relative=time.monotonic()-launched,first_state=info['State'],created=info['Created'])
   else:assert seen['id']==ident
   if info['State']['Running']:
    seen['running_visible_relative']=time.monotonic()-launched;seen['running_state']=info['State'];break
  if process.poll()is not None:break
  time.sleep(.1)
 stdout,stderr=process.communicate(timeout=20)
 assert seen is not None and 'running_visible_relative'in seen,'no observed Running within monotonic30s'
 assert process.returncode==0 and b'owned-startup-only'in stdout
except BaseException as e:failure=dict(type=type(e).__name__,message=str(e))
finally:
 # Query the exact task label even if name was not visible at an earlier poll.
 q=call(ps)
 if q and q.returncode==0:
  for ident in q.stdout.decode().split():
   z=call(['docker','inspect',ident]);assert z and z.returncode==0;info=json.loads(z.stdout)[0];assert owned(info)==ident
   call(['docker','rm','-f',ident],timeout=10)
 if process is not None:
  try:
   out,err=process.communicate(timeout=5);stdout=out or stdout;stderr=err or stderr
  except subprocess.TimeoutExpired:
   process.kill();out,err=process.communicate(timeout=5);stdout=out or stdout;stderr=err or stderr
 final=call(ps)
 assert final and final.returncode==0 and not final.stdout.strip(),'owned sentinel container remains'
 events=call(['docker','events','--since',str(int(launch_wall)-1),'--until',str(math.ceil(time.time())),'--filter','type=container','--filter','label=task='+LABEL,'--format','{{json .}}'],timeout=15)
print(json.dumps(dict(classification='single precondition lifecycle probe, no Main/worker/app import, no bind mounts or old DB, fixedimage netnone read-only UID1000 tmpfs print/sleep8 only',argv=args,launch_epoch=launch_wall,seconds=time.monotonic()-launched,seen=seen,stdout=stdout.decode(errors='replace'),stderr=stderr.decode(errors='replace'),exit=process.returncode if process else None,failure=failure,records=records,final_owned_containers=0),indent=2))
assert failure is None
