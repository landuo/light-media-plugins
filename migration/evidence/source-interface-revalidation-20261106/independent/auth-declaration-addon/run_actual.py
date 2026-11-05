from pathlib import Path
import os,json,hashlib,subprocess,time
P=Path('/Users/accidia/projects/light-media-plugins');H=Path('/Users/accidia/projects/light-media');W=P/'work/sites-review-20261106/auth-declaration-addon'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(argv,cwd,env,tag):
 start=time.time(); out=W/(tag+'.stdout');err=W/(tag+'.stderr')
 with out.open('wb') as o,err.open('wb') as e:r=subprocess.run(argv,cwd=cwd,env=env,stdout=o,stderr=e)
 row={'argv':argv,'cwd':str(cwd),'exit_code':r.returncode,'seconds':time.time()-start,'stdout_sha256':sha(out),'stderr_sha256':sha(err)};(W/(tag+'.command.json')).write_text(json.dumps(row,indent=2));print(tag,r.returncode,flush=True);return r.returncode
E=os.environ.copy();E.update(GOFLAGS='',GOPROXY='off');(W/'tmp').mkdir(exist_ok=True);E['TMPDIR']=str((W/'tmp').resolve());(W/'bins').mkdir(exist_ok=True)
old={str(P/r['path']):str(W/'before20'/r['path']) for r in json.loads((W/'before20-inputs.json').read_text())};(W/'old20-overlay.json').write_text(json.dumps({'Replace':old},indent=2))
source=H/'internal/app/plugin_original_session.go';s=source.read_text();needle='return client.CallWithOptions(ctx, method, payload, callback, options)';assert s.count(needle)==1
s=s.replace(needle,'result, callErr := client.CallWithOptions(ctx, method, payload, callback, options)\n observeSourceAuthSDK(ctx, p.installation.InstanceID, method, callErr)\n return result, callErr')
(W/'session-recorder.private.go').write_text(s)
replace={str(source):str(W/'session-recorder.private.go'),str(H/'internal/app/zz_independent_source_auth_test.go'):str(W/'auth_actual_test.go')};(W/'host-overlay.json').write_text(json.dumps({'Replace':replace},indent=2))
(W/'host-session-input.json').write_text(json.dumps({'path':str(source),'sha256':sha(source),'instrumentation':'post-success/error call recorder keyed only by own context; method/payload/host/calloptions unchanged'},indent=2))
for phase in ['old20','current23']:
 binaries={}
 for name,cmd in [('category','category-editor'),('tt','torrent-transfer'),('rlk','remove-link')]:
  binary=W/'bins'/(phase+'-'+name);args=['go','build','-trimpath','-buildvcs=false'];
  if phase=='old20':args+=['-overlay',str(W/'old20-overlay.json')]
  args+=['-o',str(binary),'./cmd/'+cmd]
  if run(args,P,E,phase+'-build-'+name):raise SystemExit('build failed')
  binaries[name]=str(binary)
 env=E.copy();env.update(AUTH_CATEGORY_BINARY=binaries['category'],AUTH_TT_BINARY=binaries['tt'],AUTH_RLK_BINARY=binaries['rlk'],AUTH_REAL_FRONTEND=str(P/'plugins/removelink/frontend'),AUTH_TRACE_OUTPUT=str(W/(phase+'-actual-trace.json')))
 code=run(['go','test','-race','-count=1','-overlay',str(W/'host-overlay.json'),'-run','^TestIndependentActualProductionAuthDiscovery$','-v','./internal/app'],H,env,phase+'-actual-race')
 (W/(phase+'-binaries.json')).write_text(json.dumps({k:{'path':v,'sha256':sha(Path(v))} for k,v in binaries.items()},indent=2))
 if phase=='current23' and code:raise SystemExit('current actual failed')
