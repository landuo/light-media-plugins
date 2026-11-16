from pathlib import Path
import os,subprocess,json,hashlib,time
r=Path('/home/admin/light-media-plugins-root-asi-native-20261107');bom={'bin/host': {'sha256': '062da6f0e5f5814dc4f60ac8bb30c7240c2d71b940cc4250261cdf97bed136fb', 'bytes': 57200802}, 'bin/worker': {'sha256': '02ece64a7ecb85c64b126279014d026d5684591cd19237b24e12af8108481269', 'bytes': 12779682}, 'bin/cli': {'sha256': '72ee655a8aa706fa487201047bba360902886828d608f4efac31a40e0f8d5865', 'bytes': 25215138}, 'bin/driver': {'sha256': '97e544e53901c666d9654e237cd09079ac5040a2918bfa46f90ca37610e030ef', 'bytes': 9707682}}
assert os.getuid()==1000 and not r.is_symlink() and(r/'.task-owned').read_text()=='light-media-plugins/root-asi-native/20261107/owned-only'
for name,row in bom.items():
    path=r/'bundle'/name
    assert path.is_file()and not path.is_symlink()and path.resolve().is_relative_to((r/'bundle').resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']and path.stat().st_size==row['bytes']
    path.chmod(0o755)
env={'CATEGORYEDITOR_HOST_BINARY':'/bundle/bin/host','CATEGORYEDITOR_RUNTIME_DIR':'/owned/runtime','CATEGORYEDITOR_LISTEN':'127.0.0.1:36322','AUTOSIGNIN_WORKER_BINARY':'/bundle/bin/worker','NATIVE_SOURCE_CLI_BINARY':'/bundle/bin/cli','OWNED_ASI_ROOT':'/owned','TMPDIR':'/tmp'}
args=['docker','run','--rm','--name','lm-root-asi-native-20261107','--network','none','--read-only','--no-healthcheck','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--label','task=lm-root-asi-native-20261107','--tmpfs','/tmp:rw,nosuid,nodev,uid=1000,gid=1000,mode=1777,size=134217728','--tmpfs','/config:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700,size=16777216','-v',str(r/'bundle')+':/bundle:ro','-v',str(r/'owned')+':/owned:rw','--workdir','/owned']
for key,value in env.items():args+=['-e',key+'='+value]
args+=['--entrypoint','/bundle/bin/driver','sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','-test.v','-test.timeout=90s','-test.run=^TestAutoSignInActualMainNativeSourceAndPrivateDrain$']
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
    assert inspected and inspected['Image']=='sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881' and inspected['User']=='1000:1000' and inspected['ReadonlyRootfs']and inspected['NetworkMode']=='none'
    observation="import json,os;print(json.dumps({'uid':os.getuid(),'interfaces':open('/proc/net/dev').read(),'ipv4_routes':open('/proc/net/route').read(),'ipv6_routes':open('/proc/net/ipv6_route').read()}))"
    proof=subprocess.run(['docker','exec','--user','1000:1000',NAME,'python3','-B','-c',observation],capture_output=True,timeout=5)
    (r/'live-network.stdout').write_bytes(proof.stdout);(r/'live-network.stderr').write_bytes(proof.stderr)
    assert proof.returncode==0
    result=process.wait(timeout=110)
remaining=subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+'lm-root-asi-native-20261107'+'$']).decode().strip()
assert not remaining
for name,row in bom.items():assert hashlib.sha256((r/'bundle'/name).read_bytes()).hexdigest()==row['sha256']
record={'argv':args,'exit':result,'seconds':time.monotonic()-started,'env':env,'bundle_unchanged':True,'owned_container_remaining':False,'network':'actual live Docker inspect plus timed in-container interface/route readback; owned loopback TLS/proxy; no production service/database mounts','scope':'actual Go Main+worker+offlineCLI; Python only verification metadata/network readback, no Python product dependency'}
(r/'command.json').write_text(json.dumps(record,indent=2))
print(json.dumps({'exit':result,'seconds':record['seconds']}))
