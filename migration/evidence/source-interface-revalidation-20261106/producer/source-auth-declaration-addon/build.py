from pathlib import Path
import json,hashlib,subprocess,os,time
r=Path('/Users/accidia/projects/light-media-plugins');p=r/'work/migration-20261106/source-auth-declaration-addon';env=os.environ.copy();env.update(GOOS='linux',GOARCH='amd64',CGO_ENABLED='0');h=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();oldp=r/'work/migration-20261106/source-module-manifest'
expected={x['cmd']:x['sha256'] for x in json.loads((oldp/'artifacts.json').read_text()) if x['target']=='linux' and x['family']!='test-driver'}
commands=[];artifacts=[]
for cmd in ['category-editor','torrent-transfer','remove-link','site-statistic','mp-server-status','plugin-uninstall']:
 binary=p/'bins'/(cmd+'-linux');argv=['go','build','-trimpath','-buildvcs=false','-o',str(binary),'./cmd/'+cmd];start=time.monotonic()
 with (p/(cmd+'.stdout')).open('w') as out,(p/(cmd+'.stderr')).open('w') as err:s=subprocess.run(argv,cwd=r,env=env,stdout=out,stderr=err)
 commands.append({'argv':argv,'cwd':str(r),'explicit_env':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'},'exit':s.returncode,'elapsed_seconds':time.monotonic()-start});assert s.returncode==0
 sha=h(binary);same=sha==expected[cmd]
 if cmd in ['site-statistic','mp-server-status','plugin-uninstall']:assert same,(cmd,sha,expected[cmd])
 artifacts.append({'path':str(binary),'command':cmd,'sha256':sha,'bytes':binary.stat().st_size,'old20_sha256':expected[cmd],'byte_identical_to_old20':same,'retain_for_Root':cmd in ['category-editor','torrent-transfer','remove-link']})
 (p/(cmd+'.buildinfo.txt')).write_text(subprocess.check_output(['go','version','-m',str(binary)],cwd=r,text=True))
f=r/'plugins/removelink/plugin.go';src=f.read_text();assert src.count('Version: "2.18"')==1;v=p/'version-plugin.go';v.write_text(src.replace('Version: "2.18"','Version: "2.18.1"',1));assert v.read_text().replace('Version: "2.18.1"','Version: "2.18"',1)==src
ov=p/'version-overlay.json';ov.write_text(json.dumps({'Replace':{str(f):str(v)}},indent=2)+'\n');binary=p/'bins/remove-link-2.18.1-linux';argv=['go','build','-trimpath','-buildvcs=false','-overlay',str(ov),'-o',str(binary),'./cmd/remove-link'];start=time.monotonic()
with (p/'update.stdout').open('w') as out,(p/'update.stderr').open('w') as err:s=subprocess.run(argv,cwd=r,env=env,stdout=out,stderr=err)
commands.append({'argv':argv,'cwd':str(r),'explicit_env':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'},'exit':s.returncode,'elapsed_seconds':time.monotonic()-start});assert s.returncode==0
artifacts.append({'path':str(binary),'command':'remove-link-version-only-update','sha256':h(binary),'bytes':binary.stat().st_size,'old20_sha256':'d0b2bbda7f6366a91f7fda172922b99598be44cebe790cf14407e33881fd4125','byte_identical_to_old20':False,'retain_for_Root':True});(p/'update.buildinfo.txt').write_text(subprocess.check_output(['go','version','-m',str(binary)],cwd=r,text=True));(p/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(p/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
print(json.dumps(artifacts,indent=2))
