from pathlib import Path
import os,subprocess,json,hashlib,time,datetime
host=Path('/Users/accidia/projects/light-media')
out=Path(__file__).resolve().parent
binary=out/'light-media-site-host-linux'
env=dict(os.environ,GOOS='linux',GOARCH='amd64',CGO_ENABLED='0')
def call(args):return subprocess.check_output(args,cwd=host,env=env)
def documents(raw):
 s=raw.decode(); dec=json.JSONDecoder();result=[];pos=0
 while pos<len(s):
  while pos<len(s) and s[pos].isspace():pos+=1
  if pos==len(s):break
  v,pos=dec.raw_decode(s,pos);result.append(v)
 return result
packages=documents(call(['go','list','-deps','-json','./cmd/server']))
paths={'go.mod','go.sum'}
for p in packages:
 d=Path(p.get('Dir','/'))
 if not d.is_relative_to(host):continue
 for field in ['GoFiles','CgoFiles','CFiles','CXXFiles','MFiles','HFiles','FFiles','SFiles','SwigFiles','SwigCXXFiles','SysoFiles','EmbedFiles']:
  for name in p.get(field,[]):paths.add((d/name).relative_to(host).as_posix())
def snapshot():return {p:hashlib.sha256((host/p).read_bytes()).hexdigest() for p in sorted(paths)}
before=snapshot(); revision=call(['git','rev-parse','HEAD']).decode().strip()
# Prove every actual repository input is the named committed blob before building.
for p,h in before.items():
 assert hashlib.sha256(call(['git','show',revision+':'+p])).hexdigest()==h,p
cmd=['go','build','-trimpath','-buildvcs=false','-o',str(binary),'./cmd/server']
start=time.monotonic();p=subprocess.run(cmd,cwd=host,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);elapsed=time.monotonic()-start
(out/'host-build.log').write_bytes(p.stdout);after=snapshot()
record={'classification':'ordinary cmd/server Linux cross-build; actual main execution is recorded separately','built_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_repository':'https://github.com/landuo/light-media','source_commit':revision,'source_state':'local reviewed increment, not pushed/merged/deployed','branch':call(['git','branch','--show-current']).decode().strip(),'command':cmd,'explicit_environment':{x:env[x] for x in ['GOOS','GOARCH','CGO_ENABLED']},'go_environment':json.loads(call(['go','env','-json','GOOS','GOARCH','CGO_ENABLED','GOTOOLCHAIN','GOFLAGS','GOWORK'])),'go_version':call(['go','version']).decode().strip(),'repository_inputs':before,'input_count':len(before),'inputs_unchanged_during_build':before==after,'every_input_matches_committed_blob':True,'exit_code':p.returncode,'build_elapsed_seconds':elapsed,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest() if p.returncode==0 else None,'binary_bytes':binary.stat().st_size if p.returncode==0 else None,'module_dependencies':documents(call(['go','list','-m','-json','all']))}
(out/'host-build-source-binding.json').write_text(json.dumps(record,indent=2)+'\n')
if p.returncode:raise SystemExit(p.returncode)
assert before==after
(out/'host-buildinfo.txt').write_bytes(call(['go','version','-m',str(binary)]))
print(json.dumps({'source_commit':revision,'inputs':len(before),'sha256':record['binary_sha256'],'elapsed_seconds':elapsed}))
