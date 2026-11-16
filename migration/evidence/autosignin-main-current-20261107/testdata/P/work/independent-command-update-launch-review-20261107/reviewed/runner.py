CONFIG = {'root': '/home/admin/light-media-plugins-root-asi-native-20261107', 'marker': 'light-media-plugins/root-asi-native/20261107/owned-only', 'name': 'lm-root-asi-native-20261107', 'owned_dir': 'owned-r3', 'out_dir': 'attempt4', 'image': 'sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881', 'bom': {'bin/host': {'sha256': '8ea38cff7e98f6a1eb7089f7ff04cc8c56fdb41baedfdbc843db13824b999f67', 'bytes': 57217186}, 'bin/worker': {'sha256': '2b77bc3db6c80ff67314a68daa0df90b1595e99ab2bc658ca80cfaafd6a251a0', 'bytes': 12796066}, 'bin/worker-updated': {'sha256': 'e38f19188cfbfe4b295893b9707c1ba8ee77117880ffdcfb7952e77bf0108f36', 'bytes': 12796066}, 'bin/cli': {'sha256': '525e34407b50f4bd38e16d29bfe4d775c8052504f40072789cc8a4b43f4cf1b8', 'bytes': 25215138}, 'bin/driver': {'sha256': 'f725924537c0d650802d4626166e02f8249401f782dcb154bdcf51ee8399d1e8', 'bytes': 9748642}}}
# CONFIG is an explicit literal prefix added by prepare-runner-v2.py.
from pathlib import Path
import os,subprocess,json,hashlib,time

root=Path(CONFIG['root'])
assert os.getuid()==1000 and root.is_dir()and not root.is_symlink()
assert(root/'.task-owned').read_text()==CONFIG['marker']
owned=root/CONFIG['owned_dir'];out=root/CONFIG['out_dir']
assert owned.parent==root and out.parent==root and not owned.exists()and not out.exists()
assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+CONFIG['name']+'$']).strip()
for name,row in CONFIG['bom'].items():
    f=root/'bundle'/name
    assert f.is_file()and not f.is_symlink()and f.resolve().is_relative_to((root/'bundle').resolve())
    assert hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256']and f.stat().st_size==row['bytes']
owned.mkdir(mode=0o700);out.mkdir(mode=0o700)
(owned/'.task-owned').write_text(CONFIG['marker']);(owned/'runtime').mkdir(mode=0o700)
env={'CATEGORYEDITOR_HOST_BINARY':'/bundle/bin/host','CATEGORYEDITOR_RUNTIME_DIR':'/owned/runtime','CATEGORYEDITOR_LISTEN':'127.0.0.1:36322','AUTOSIGNIN_WORKER_BINARY':'/bundle/bin/worker','AUTOSIGNIN_UPDATED_WORKER_BINARY':'/bundle/bin/worker-updated','NATIVE_SOURCE_CLI_BINARY':'/bundle/bin/cli','OWNED_ASI_ROOT':'/owned','TMPDIR':'/tmp'}
argv=['docker','run','--rm','--name',CONFIG['name'],'--network','none','--read-only','--no-healthcheck','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--label','task=lm-root-asi-native-20261107','--tmpfs','/tmp:rw,nosuid,nodev,uid=1000,gid=1000,mode=1777,size=134217728','--tmpfs','/config:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700,size=16777216','-v',str(root/'bundle')+':/bundle:ro','-v',str(owned)+':/owned:rw','--workdir','/owned']
for key,value in env.items():argv+=['-e',key+'='+value]
argv+=['--entrypoint','/bundle/bin/driver',CONFIG['image'],'-test.v','-test.timeout=180s','-test.run=^TestAutoSignInActualMainCommandsUpdateTimerShutdown$']

inspect_attempts=[]
def own_container(phase='check',timeout=5):
    global observed_id
    checked_at=time.monotonic()
    entry={'phase':phase,'at_monotonic':checked_at,'timeout':timeout,'target':observed_id or CONFIG['name'],'exit':None,'exception':None}
    try:
        result=subprocess.run(['docker','inspect',entry['target']],capture_output=True,timeout=timeout)
        entry.update(exit=result.returncode,stdout=result.stdout.decode(errors='replace'),stderr=result.stderr.decode(errors='replace'))
    except (subprocess.TimeoutExpired,OSError)as error:
        entry.update(exception={'type':type(error).__name__,'message':str(error)},stdout=(getattr(error,'stdout',None)or b'').decode(errors='replace'),stderr=(getattr(error,'stderr',None)or b'').decode(errors='replace'))
        raise
    finally:
        entry['seconds']=time.monotonic()-checked_at
        inspect_attempts.append(entry)
        (out/'inspect-attempts.json').write_text(json.dumps(inspect_attempts,indent=2))
    if result.returncode!=0:
        entry['stdout']=result.stdout.decode(errors='replace')
        (out/'inspect-attempts.json').write_text(json.dumps(inspect_attempts,indent=2))
        assert result.returncode==1 and any(text in result.stderr.decode(errors='replace')for text in ('No such object:','No such container:')),'owned inspect failed without proving absence'
        return None
    info=json.loads(result.stdout)[0]
    entry.update(id=info['Id'],state=info['State'])
    (out/'inspect-attempts.json').write_text(json.dumps(inspect_attempts,indent=2))
    assert info['Image']==CONFIG['image']and info['Config']['Labels'].get('task')=='lm-root-asi-native-20261107'
    assert info['Config']['User']=='1000:1000'and info['HostConfig']['NetworkMode']=='none'and info['HostConfig']['ReadonlyRootfs']
    mounts={x['Destination']:x for x in info['Mounts']}
    assert mounts['/bundle']['Source']==str(root/'bundle')and not mounts['/bundle']['RW']
    assert mounts['/owned']['Source']==str(owned)and mounts['/owned']['RW']
    if observed_id is None:observed_id=info['Id']
    else:assert observed_id==info['Id']
    return info

process=None;exit_code=None;failure=None;cleanup=[];started=time.monotonic();observed_id=None
record={'argv':argv,'env':env,'exit':None,'exception':None,'cleanup':cleanup,'owned_container_remaining':None,'bundle_unchanged':None,'scope':'actual Go Main/worker/offlineCLI, test-only owned TLS and verified UID1000/netnone mounts. Python is verification only.'}
try:
    with(out/'actual.stdout').open('wb')as stdout,(out/'actual.stderr').open('wb')as stderr:
        process=subprocess.Popen(argv,stdout=stdout,stderr=stderr)
        info=None
        startup_deadline=time.monotonic()+30
        while time.monotonic()<startup_deadline:
            if process.poll()is not None:break
            remaining=startup_deadline-time.monotonic()
            if remaining<=0:break
            info=own_container('startup',min(5,remaining))
            if info and info['State']['Running']:break
            time.sleep(.1)
        assert info and info['State']['Running'],'owned container did not reach observable running state'
        observed_id=info['Id']
        inspection={'Id':info['Id'],'Image':info['Image'],'State':{'Running':True,'StartedAt':info['State']['StartedAt'],'Pid':info['State']['Pid']},'User':info['Config']['User'],'ReadonlyRootfs':info['HostConfig']['ReadonlyRootfs'],'NetworkMode':info['HostConfig']['NetworkMode'],'CapDrop':info['HostConfig']['CapDrop'],'SecurityOpt':info['HostConfig']['SecurityOpt'],'Mounts':info['Mounts'],'Tmpfs':info['HostConfig']['Tmpfs']}
        (out/'live-inspect.json').write_text(json.dumps(inspection,indent=2))
        source="import json,os;print(json.dumps({'uid':os.getuid(),'interfaces':open('/proc/net/dev').read(),'ipv4_routes':open('/proc/net/route').read(),'ipv6_routes':open('/proc/net/ipv6_route').read()}))"
        compile(source,'network-readback.py','exec')
        probe=subprocess.run(['docker','exec','--user','1000:1000',observed_id,'python3','-B','-c',source],capture_output=True,timeout=5)
        (out/'live-network.stdout').write_bytes(probe.stdout);(out/'live-network.stderr').write_bytes(probe.stderr)
        assert probe.returncode==0,'timed network readback failed'
        network=json.loads(probe.stdout)
        assert network['uid']==1000
        assert all(line.split(':',1)[0].strip()=='lo'for line in network['interfaces'].splitlines()if':'in line)
        assert len(network['ipv4_routes'].splitlines())==1
        exit_code=process.wait(timeout=200)
except BaseException as error:
    failure={'type':type(error).__name__,'message':str(error)}
finally:
    try:
        info=own_container('cleanup')
        if info is None and process is not None and process.poll()is None:
            late_deadline=time.monotonic()+10
            while info is None and process.poll()is None and time.monotonic()<late_deadline:
                time.sleep(.1)
                info=own_container('cleanup_late_create')
        if info:
            if observed_id is not None:assert info['Id']==observed_id
            try:
                result=subprocess.run(['docker','stop','--time','10',info['Id']],capture_output=True,timeout=20)
                cleanup.append({'action':'stop_verified_owned_container','id':info['Id'],'exit':result.returncode})
            except subprocess.TimeoutExpired:
                cleanup.append({'action':'stop_verified_owned_container','id':info['Id'],'error':'timeout'})
            remaining=own_container()
            if remaining:
                assert remaining['Id']==info['Id']
                # Re-verified exact image/label/mounts/immutable ID above. Only
                # this owned failed test container may be force-removed.
                result=subprocess.run(['docker','rm','-f',remaining['Id']],capture_output=True,timeout=10)
                cleanup.append({'action':'remove_reverified_owned_container','id':remaining['Id'],'exit':result.returncode})
                assert result.returncode==0
    except BaseException as error:
        cleanup.append({'error':type(error).__name__,'message':str(error)})
        if failure is None:failure={'type':'cleanup_failed','message':str(error)}
    if process is not None:
        try:
            try:exit_code=process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:process.terminate()
                except ProcessLookupError:pass
                try:exit_code=process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:process.kill()
                    except ProcessLookupError:pass
                    exit_code=process.wait(timeout=5)
                cleanup.append({'action':'terminated_owned_docker_client','exit':exit_code})
        except BaseException as error:
            cleanup.append({'action':'final_docker_client_join','error':type(error).__name__,'message':str(error)})
            if failure is None:failure={'type':'final_docker_client_join_failed','message':str(error)}
    try:
        record['owned_container_remaining']=None
        final_checks=[]
        for selector in ('name=^/'+CONFIG['name']+'$','label=task=lm-root-asi-native-20261107'):
            result=subprocess.run(['docker','ps','-aq','--filter',selector],capture_output=True,timeout=5)
            final_checks.append({'selector':selector,'exit':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode()})
            record['final_container_checks']=final_checks
            assert result.returncode==0,'final owned-container query failed'
        record['final_container_checks']=final_checks
        present=any(check['stdout'].strip()for check in final_checks)
        # Without a verified created ID, killing a pending docker client cannot
        # prove the daemon will never create it later. Preserve unknown.
        record['verified_container_id']=observed_id
        final_info=None
        if observed_id is not None:
            final_info=own_container('final_verified_id')
        record['owned_container_remaining']=True if present or final_info is not None else(False if observed_id is not None or process is None else None)
    except BaseException as error:
        cleanup.append({'action':'final_container_query','error':type(error).__name__,'message':str(error)})
        if failure is None:failure={'type':'final_container_query_failed','message':str(error)}
    try:
        record['bundle_unchanged']=all(hashlib.sha256((root/'bundle'/name).read_bytes()).hexdigest()==row['sha256']for name,row in CONFIG['bom'].items())
    except BaseException as error:
        cleanup.append({'action':'final_bundle_check','error':type(error).__name__,'message':str(error)})
        record['bundle_unchanged']=False
        if failure is None:failure={'type':'final_bundle_check_failed','message':str(error)}
    record.update(exit=exit_code,exception=failure,seconds=time.monotonic()-started)
    (out/'command.json').write_text(json.dumps(record,indent=2))
print(json.dumps({'exit':exit_code,'exception':failure,'seconds':record['seconds'],'owned_container_remaining':record['owned_container_remaining']}))
assert failure is None and exit_code==0 and record['owned_container_remaining']is False and record['bundle_unchanged']is True
