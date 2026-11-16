from pathlib import Path
import json,os,subprocess,time
r=Path.cwd();out=Path(__file__).resolve().parent;(out/'tmp-optin').mkdir(mode=0o700,exist_ok=True);env=dict(os.environ,GOPROXY='off',GOFLAGS='',TMPDIR=str(out/'tmp-optin'));rows=[]
for race in [False,True]:
 name='optin-race'if race else'optin-normal';binary=out/('owned-concurrent-fixture-race'if race else'owned-concurrent-fixture');env['LIGHT_MEDIA_CONCURRENT_FIXTURE']=str(binary)
 stages=[('build',['go','build',*(['-race']if race else[]),'-trimpath','-buildvcs=false','-o',str(binary),'./internal/sdk/testdata/owned-concurrent-fixture']),('tests',['go','test',*(['-race']if race else[]),'-json','-count=1','./internal/sdk','-run','^TestOwned(Concurrent|PendingCall)','-timeout=8m'])]
 for stage,cmd in stages:
  label=name+'-'+stage;start=time.monotonic();p=subprocess.run(cmd,env=env,cwd=r,capture_output=True);(out/(label+'.stdout')).write_bytes(p.stdout);(out/(label+'.stderr')).write_bytes(p.stderr);xs=[json.loads(x)for x in p.stdout.splitlines()if x.startswith(b'{')];row={'name':label,'command':cmd,'environment':{k:env[k]for k in ['GOPROXY','GOFLAGS','TMPDIR','LIGHT_MEDIA_CONCURRENT_FIXTURE']},'exit':p.returncode,'seconds':time.monotonic()-start,'pass':sum(x.get('Action')=='pass'and'Test'in x for x in xs),'fail':sum(x.get('Action')=='fail'and'Test'in x for x in xs),'skip':sum(x.get('Action')=='skip'and'Test'in x for x in xs)};rows.append(row);(out/'sdk101-optin-commands.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
  if p.returncode:raise SystemExit(p.returncode)
