from pathlib import Path
import subprocess,json,hashlib,tarfile,io,time,os
P=Path('/Users/accidia/projects/light-media-plugins');W=Path(__file__).resolve().parent
ROOT='/home/admin/light-media-plugins-root-asi-native-20261107'
MARKER='light-media-plugins/root-asi-native/20261107/owned-only'
NAME='lm-root-asi-native-20261107'
IMAGE='sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={f'bin/{name}':W/name for name in ('host','worker','cli','driver')}
bom={name:{'sha256':sha(path),'bytes':path.stat().st_size}for name,path in files.items()}
(W/'bundle-bom.json').write_text(json.dumps(bom,indent=2)+'\n')
setup='''from pathlib import Path
import os,subprocess
r=Path(ROOT)
assert os.getuid()==1000 and not r.exists()
assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+__LM_TEST_NAME__+'$']).strip()
r.mkdir(mode=0o700)
(r/'.task-owned').write_text(MARKER)
for name in ['bundle','owned']:(r/name).mkdir(mode=0o700)
(r/'owned/.task-owned').write_text(MARKER)
(r/'owned/runtime').mkdir(mode=0o700)
'''.replace('ROOT',repr(ROOT)).replace('MARKER',repr(MARKER)).replace('NAME',repr(NAME))
(W/'setup.py').write_text(setup)
if os.environ.get('LM_REUSE_UNSTARTED_NATIVE_MAIN')=='1':
    setup="from pathlib import Path\nimport os,subprocess,json,hashlib\nr=Path("+repr(ROOT)+")\nassert os.getuid()==1000 and r.is_dir() and not r.is_symlink() and (r/'.task-owned').read_text()=="+repr(MARKER)+"\nassert not list((r/'owned/runtime').iterdir())\nassert not any((r/n).exists() for n in ['actual.stdout','actual.stderr','command.json'])\nassert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+"+repr(NAME)+"+'$']).strip()\nbom="+repr(bom)+"\nfor n,row in bom.items():\n p=r/'bundle'/n; assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']\n"
    (W/'reuse-preflight.py').write_text(setup)
r=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=setup.encode(),capture_output=True,timeout=30)
(W/'setup.stdout').write_bytes(r.stdout);(W/'setup.stderr').write_bytes(r.stderr)
assert r.returncode==0,r.stderr.decode()
upload=subprocess.Popen(['ssh','-o','BatchMode=yes','admin@192.168.8.129','tar','-xf','-','-C',ROOT+'/bundle'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
with tarfile.open(fileobj=upload.stdin,mode='w|')as archive:
    for name,path in files.items():
        assert path.is_file()and not path.is_symlink()
        archive.add(path,arcname=name,recursive=False)
upload.stdin.close();out=upload.stdout.read();err=upload.stderr.read();code=upload.wait()
(W/'upload.stdout').write_bytes(out);(W/'upload.stderr').write_bytes(err)
assert code==0,err.decode()
script='''from pathlib import Path
import os,subprocess,json,hashlib,time
r=Path(__LM_TEST_ROOT__);bom=__LM_TEST_BOM__
assert os.getuid()==1000 and not r.is_symlink() and(r/'.task-owned').read_text()==__LM_TEST_MARKER__
for name,row in bom.items():
    path=r/'bundle'/name
    assert path.is_file()and not path.is_symlink()and path.resolve().is_relative_to((r/'bundle').resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']and path.stat().st_size==row['bytes']
    path.chmod(0o755)
env={'CATEGORYEDITOR_HOST_BINARY':'/bundle/bin/host','CATEGORYEDITOR_RUNTIME_DIR':'/owned/runtime','CATEGORYEDITOR_LISTEN':'127.0.0.1:36322','AUTOSIGNIN_WORKER_BINARY':'/bundle/bin/worker','NATIVE_SOURCE_CLI_BINARY':'/bundle/bin/cli','OWNED_ASI_ROOT':'/owned','TMPDIR':'/tmp'}
args=['docker','run','--rm','--name',__LM_TEST_NAME__,'--network','none','--read-only','--no-healthcheck','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--label','task=lm-root-asi-native-20261107','--tmpfs','/tmp:rw,nosuid,nodev,uid=1000,gid=1000,mode=1777,size=134217728','--tmpfs','/config:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700,size=16777216','-v',str(r/'bundle')+':/bundle:ro','-v',str(r/'owned')+':/owned:rw','--workdir','/owned']
for key,value in env.items():args+=['-e',key+'='+value]
args+=['--entrypoint','/bundle/bin/driver',__LM_TEST_IMAGE__,'-test.v','-test.timeout=90s','-test.run=^TestAutoSignInActualMainNativeSourceAndPrivateDrain$']
started=time.monotonic()
with(r/'actual.stdout').open('wb')as out,(r/'actual.stderr').open('wb')as err:
    process=subprocess.Popen(args,stdout=out,stderr=err)
    inspected=None
    for attempt in range(30):
        if process.poll()is not None:break
        probe=subprocess.run(['docker','inspect',NAME],capture_output=True)
        if probe.returncode==0:
            value=json.loads(probe.stdout)[0]
            if value['State']['Running']:
                inspected={'Id':value['Id'],'Image':value['Image'],'State':{'Running':True,'StartedAt':value['State']['StartedAt'],'Pid':value['State']['Pid']},'User':value['Config']['User'],'ReadonlyRootfs':value['HostConfig']['ReadonlyRootfs'],'NetworkMode':value['HostConfig']['NetworkMode'],'CapDrop':value['HostConfig']['CapDrop'],'SecurityOpt':value['HostConfig']['SecurityOpt'],'Mounts':value['Mounts'],'Tmpfs':value['HostConfig']['Tmpfs']}
                break
        time.sleep(.05)
    (r/'live-inspect.json').write_text(json.dumps(inspected,indent=2))
    assert inspected and inspected['Image']==__LM_TEST_IMAGE__ and inspected['User']=='1000:1000' and inspected['ReadonlyRootfs']and inspected['NetworkMode']=='none'
    observation="import json,os;print(json.dumps({'uid':os.getuid(),'interfaces':open('/proc/net/dev').read(),'ipv4_routes':open('/proc/net/route').read(),'ipv6_routes':open('/proc/net/ipv6_route').read()}))"
    proof=subprocess.run(['docker','exec','--user','1000:1000',NAME,'python3','-B','-c',observation],capture_output=True,timeout=5)
    (r/'live-network.stdout').write_bytes(proof.stdout);(r/'live-network.stderr').write_bytes(proof.stderr)
    assert proof.returncode==0
    result=process.wait(timeout=110)
remaining=subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+__LM_TEST_NAME__+'$']).decode().strip()
assert not remaining
for name,row in bom.items():assert hashlib.sha256((r/'bundle'/name).read_bytes()).hexdigest()==row['sha256']
record={'argv':args,'exit':result,'seconds':time.monotonic()-started,'env':env,'bundle_unchanged':True,'owned_container_remaining':False,'network':'actual live Docker inspect plus timed in-container interface/route readback; owned loopback TLS/proxy; no production service/database mounts','scope':'actual Go Main+worker+offlineCLI; Python only verification metadata/network readback, no Python product dependency'}
(r/'command.json').write_text(json.dumps(record,indent=2))
print(json.dumps({'exit':result,'seconds':record['seconds']}))
'''.replace('__LM_TEST_ROOT__',repr(ROOT)).replace('__LM_TEST_BOM__',repr(bom)).replace('__LM_TEST_MARKER__',repr(MARKER)).replace('__LM_TEST_NAME__',repr(NAME)).replace('__LM_TEST_IMAGE__',repr(IMAGE))
compile(script,'remote-runner.py','exec')
(W/'remote-runner.py').write_text(script)
t=time.monotonic();r=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=script.encode(),capture_output=True,timeout=140)
(W/'remote.stdout').write_bytes(r.stdout);(W/'remote.stderr').write_bytes(r.stderr)
(W/'remote-command.json').write_text(json.dumps({'exit':r.returncode,'seconds':time.monotonic()-t,'stdin_sha256':sha(W/'remote-runner.py')},indent=2)+'\n')
# Fetch only test observations. Never fetch the runtime SQLite/key/config files.
names=['actual.stdout','actual.stderr','command.json','live-inspect.json','live-network.stdout','live-network.stderr','owned/runtime/evidence']
fetch=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','tar','-cf','-','-C',ROOT,*names],capture_output=True,timeout=20)
(W/'fetch.stderr').write_bytes(fetch.stderr)
assert fetch.returncode==0,fetch.stderr.decode()
dest=W/'actual';dest.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(fetch.stdout))as archive:
    for member in archive.getmembers():assert not member.issym()and not member.islnk()and not Path(member.name).is_absolute()and'..'not in Path(member.name).parts
    archive.extractall(dest,filter='data')
print(r.stdout.decode())
assert r.returncode==0,r.stderr.decode()
command=json.loads((dest/'command.json').read_text())
assert command['exit']==0,command
