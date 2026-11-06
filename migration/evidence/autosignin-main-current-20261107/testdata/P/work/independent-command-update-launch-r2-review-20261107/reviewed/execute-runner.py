from pathlib import Path
import subprocess,json,hashlib,tarfile,io,time
W=Path(__file__).resolve().parent
ROOT='/home/admin/light-media-plugins-root-asi-native-20261107'
MARKER='light-media-plugins/root-asi-native/20261107/owned-only'
NAME='lm-root-asi-native-20261107'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bom={f'bin/{name}':{'sha256':sha(W/name),'bytes':(W/name).stat().st_size}for name in('host','worker','worker-updated','cli','driver')}
(W/'bundle-bom-v2.json').write_text(json.dumps(bom,indent=2)+'\n')
probe='''from pathlib import Path
import json,subprocess,os,hashlib
r=Path(CONFIG['root'])
assert os.getuid()==1000 and r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text()==CONFIG['marker']
assert not (r/'owned-r4').exists()and not(r/'attempt5').exists()
assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+CONFIG['name']+'$']).strip()
changed=[]
for n,row in CONFIG['bom'].items():
 f=r/'bundle'/n
 assert n in ['bin/host','bin/worker','bin/worker-updated','bin/cli','bin/driver']and not f.is_symlink()
 if not f.exists():
  assert n=='bin/worker-updated'and f.parent.is_dir()and not f.parent.is_symlink();changed.append(n);continue
 assert f.is_file()
 if hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']:changed.append(n)
print(json.dumps({'changed':changed}))
'''
config={'root':ROOT,'marker':MARKER,'name':NAME,'bom':bom}
source='CONFIG='+repr(config)+'\n'+probe
compile(source,'upload-preflight.py','exec')
(W/'upload-preflight-v2.py').write_text(source)
r=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=source.encode(),capture_output=True,timeout=20)
(W/'upload-preflight-v2.stdout').write_bytes(r.stdout);(W/'upload-preflight-v2.stderr').write_bytes(r.stderr)
assert r.returncode==0,r.stderr.decode()
changed=json.loads(r.stdout)['changed']
assert all(name in bom for name in changed)
if changed:
    process=subprocess.Popen(['ssh','-o','BatchMode=yes','admin@192.168.8.129','tar','-xf','-','-C',ROOT+'/bundle'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    with tarfile.open(fileobj=process.stdin,mode='w|')as archive:
        for name in changed:archive.add(W/name.removeprefix('bin/'),arcname=name,recursive=False)
    process.stdin.close();stdout=process.stdout.read();stderr=process.stderr.read();code=process.wait()
    (W/'upload-v2.stdout').write_bytes(stdout);(W/'upload-v2.stderr').write_bytes(stderr)
    assert code==0,stderr.decode()
# The generator uses only this explicit current BOM; no string interpolation
# is applied to environment variable names or the remote program body.
(W/'bundle-bom.json').write_text(json.dumps(bom,indent=2)+'\n')
r=subprocess.run(['python3',str(W/'prepare-runner.py')],capture_output=True)
(W/'prepare-v2.stdout').write_bytes(r.stdout);(W/'prepare-v2.stderr').write_bytes(r.stderr)
assert r.returncode==0,r.stderr.decode()
script=(W/'runner.py').read_bytes();t=time.monotonic()
assert (W/'launch-approved.json').is_file(),'final independent BOM/prefix review is required before Main launch'
approval=json.loads((W/'launch-approved.json').read_text())
assert hashlib.sha256(script).hexdigest()==approval['runner_sha256']and bom==approval['bom']
remote_exit=None;remote_error=None;remote_stdout=b'';remote_stderr=b''
try:
    r=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=script,capture_output=True,timeout=360)
    remote_exit=r.returncode;remote_stdout=r.stdout;remote_stderr=r.stderr
except (subprocess.TimeoutExpired,OSError)as error:
    remote_error={'type':type(error).__name__,'message':str(error)}
    remote_stdout=getattr(error,'stdout',None)or b''
    remote_stderr=getattr(error,'stderr',None)or b''
finally:
    (W/'remote-v2.stdout').write_bytes(remote_stdout);(W/'remote-v2.stderr').write_bytes(remote_stderr)
    (W/'remote-v2-command.json').write_text(json.dumps({'exit':remote_exit,'exception':remote_error,'seconds':time.monotonic()-t,'stdin_sha256':hashlib.sha256(script).hexdigest(),'uploaded_only_changed':changed},indent=2)+'\n')
fetch='''from pathlib import Path
import tarfile,sys,os
r=Path(CONFIG['root']);assert os.getuid()==1000 and r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text()==CONFIG['marker']
names=['attempt5/actual.stdout','attempt5/actual.stderr','attempt5/command.json','attempt5/live-inspect.json','attempt5/inspect-attempts.json','attempt5/live-network.stdout','attempt5/live-network.stderr','owned-r4/runtime/evidence']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as archive:
 for name in names:
  path=r/name
  if not path.exists():continue
  assert not path.is_symlink()and path.resolve().is_relative_to(r.resolve())
  if path.is_dir():
   for f in path.rglob('*'):
    if f.is_file():assert not f.is_symlink()and f.resolve().is_relative_to(path.resolve());archive.add(f,arcname=str(f.relative_to(r)),recursive=False)
  else:archive.add(path,arcname=name,recursive=False)
'''
source='CONFIG='+repr({'root':ROOT,'marker':MARKER})+'\n'+fetch
(W/'harvest-v2.py').write_text(source)
dest=W/'actual-r2';dest.mkdir(exist_ok=True);harvest_error=None
try:
    harvest=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=source.encode(),capture_output=True,timeout=30)
    (W/'harvest-v2.stderr').write_bytes(harvest.stderr)
    assert harvest.returncode==0,harvest.stderr.decode()
    with tarfile.open(fileobj=io.BytesIO(harvest.stdout))as archive:
        for member in archive.getmembers():assert not member.issym()and not member.islnk()and not Path(member.name).is_absolute()and'..'not in Path(member.name).parts
        archive.extractall(dest,filter='data')
except (subprocess.TimeoutExpired,OSError,AssertionError,tarfile.TarError)as error:
    harvest_error={'type':type(error).__name__,'message':str(error)}
    (W/'harvest-v2-error.json').write_text(json.dumps(harvest_error,indent=2)+'\n')
    if isinstance(error,subprocess.TimeoutExpired):
        (W/'harvest-v2-partial.stderr').write_bytes(error.stderr or b'')
        # Partial tar bytes are diagnostic only and never extracted as evidence.
        (W/'harvest-v2-partial.tar').write_bytes(error.stdout or b'')
print(remote_stdout.decode(errors='replace'))
assert remote_error is None and remote_exit==0,{'remote_error':remote_error,'exit':remote_exit,'stderr':remote_stderr.decode(errors='replace'),'harvest_error':harvest_error}
assert harvest_error is None,harvest_error
assert(dest/'attempt5/command.json').is_file(),'no runtime record; inspect preserved setup/SSH stderr'
record=json.loads((dest/'attempt5/command.json').read_text())
assert record['exception']is None and record['exit']==0 and record['owned_container_remaining']is False,record
