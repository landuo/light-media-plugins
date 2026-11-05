from pathlib import Path
import os,subprocess,json,time
r=Path('/Users/accidia/projects/light-media-plugins');p=r/'work/migration-20261106/pui-current-driver';results=[]
for missing in ['PLUGINUNINSTALL_EXPECT_WORKER_SHA256','PLUGINUNINSTALL_EXPECT_MPS_SHA256']:
 env={k:v for k,v in os.environ.items() if not k.startswith('PLUGINUNINSTALL_')};runtime=p/('must-not-create-'+missing.lower());assert not runtime.exists()
 for name in ['HOST_BINARY','WORKER_BINARY','UPDATE_BINARY','MPS_BINARY','FIXTURE_BINARY']:env['PLUGINUNINSTALL_'+name]='/owned/not-loaded-before-required-hash-check'
 for name in ['EXPECT_HOST_SHA256','EXPECT_WORKER_SHA256','EXPECT_MPS_SHA256']:env['PLUGINUNINSTALL_'+name]='0'*64
 env.pop(missing);env['PLUGINUNINSTALL_RUNTIME_DIR']=str(runtime)
 argv=['go','test','./tests/integration','-run','^TestPluginUninstallOrdinaryMain$','-count=1','-json'];start=time.monotonic();s=subprocess.run(argv,cwd=r,env=env,capture_output=True)
 log=p/(missing.lower()+'.negative.jsonl');log.write_bytes(s.stdout);(p/(missing.lower()+'.stderr')).write_bytes(s.stderr)
 events=[json.loads(l) for l in s.stdout.decode().splitlines()];found=any('required owned input '+missing in e.get('Output','') for e in events);failed=any(e['Action']=='fail' and e.get('Test')=='TestPluginUninstallOrdinaryMain' for e in events)
 assert s.returncode!=0 and found and failed and not runtime.exists(),(s.returncode,missing,s.stdout.decode())
 results.append({'argv':argv,'cwd':str(r),'classification':'real preflight negative only, no bootstrap/native load/Main; intentionally missing required expected hash','missing':missing,'exit':s.returncode,'matched_required_input_error':found,'runtime_directory_created':runtime.exists(),'elapsed_seconds':time.monotonic()-start})
(p/'inputguard-negatives.json').write_text(json.dumps(results,indent=2)+'\n')
