from pathlib import Path
import json,hashlib,subprocess,os,time
r=Path.cwd();w=Path(__file__).resolve().parent;(w/'tmp-consumers').mkdir(mode=0o700,exist_ok=True);env=dict(os.environ,GOPROXY='off',GOFLAGS='',TMPDIR=str(w/'tmp-consumers'));families=['categoryeditor','torrenttransfer','sitestatistic','mpserverstatus','pluginuninstall','removelink'];cmds=[x['package']for x in json.load(open('build-plugins.json'))['plugins']];packages=cmds+['./plugins/'+x+'/...'for x in families];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():
 paths=[r/'go.mod',r/'go.sum',r/'SDK_ORIGIN.json',r/'build-plugins.json']+list((r/'internal/sdk').rglob('*.go'))
 for family in families:paths+=list((r/'plugins'/family).rglob('*'))
 for cmd in cmds:paths+=list((r/cmd).rglob('*.go'))
 return {str(p.relative_to(r)):sha(p)for p in sorted(paths)if p.is_file()}
before=snapshot();(w/'consumer-inputs-before.json').write_text(json.dumps(before,indent=2)+'\n');rows=[]
for name,flags in [('consumers-normal',[]),('consumers-race',['-race'])]:
 cmd=['go','test',*flags,'-json','-count=1',*packages,'-timeout=8m'];start=time.monotonic();p=subprocess.run(cmd,env=env,cwd=r,capture_output=True);(w/(name+'.stdout')).write_bytes(p.stdout);(w/(name+'.stderr')).write_bytes(p.stderr);xs=[json.loads(x)for x in p.stdout.splitlines()if x.startswith(b'{')];row={'name':name,'command':cmd,'environment':{k:env[k]for k in ['GOPROXY','GOFLAGS','TMPDIR']},'exit':p.returncode,'seconds':time.monotonic()-start,'pass':sum(x.get('Action')=='pass'and'Test'in x for x in xs),'fail':sum(x.get('Action')=='fail'and'Test'in x for x in xs),'skip':sum(x.get('Action')=='skip'and'Test'in x for x in xs)};rows.append(row);(w/'consumer-checks.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
 if p.returncode:raise SystemExit(p.returncode)
after=snapshot();(w/'consumer-inputs-after.json').write_text(json.dumps(after,indent=2)+'\n');assert before==after;print(json.dumps({'stable_consumer_inputs':len(before)}))
