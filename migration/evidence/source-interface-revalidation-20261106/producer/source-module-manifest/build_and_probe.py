import pathlib,json,subprocess,os,hashlib,time
r=pathlib.Path('/Users/accidia/projects/light-media-plugins');p=r/'work/migration-20261106/source-module-manifest';bins=p/'bins'
families={'category-editor':'categoryeditor','torrent-transfer':'torrenttransfer','remove-link':'removelink','site-statistic':'sitestatistic','mp-server-status':'mpserverstatus','plugin-uninstall':'pluginuninstall'}
commands=[];artifacts=[];probe=[]
def run(argv,env=None,stdout=None):
 start=time.monotonic()
 with open(stdout or p/'build-last.stdout','w') as out:result=subprocess.run(argv,cwd=r,env=env,stdout=out,stderr=subprocess.STDOUT)
 commands.append({'argv':argv,'cwd':str(r),'explicit_env':{k:env[k] for k in ['GOOS','GOARCH','CGO_ENABLED'] if env and k in env},'stdout':str(stdout),'exit':result.returncode,'elapsed_seconds':time.monotonic()-start});assert result.returncode==0,argv
for target in ['native','linux']:
 env=os.environ.copy()
 if target=='linux':env.update(GOOS='linux',GOARCH='amd64',CGO_ENABLED='0')
 for cmd,family in families.items():
  binary=bins/(cmd+'-'+target)
  argv=['go','build','-trimpath','-buildvcs=false','-o',str(binary),'./cmd/'+cmd]
  run(argv,env,p/('build-'+cmd+'-'+target+'.stdout'));data=binary.read_bytes();artifacts.append({'family':family,'cmd':cmd,'target':target,'path':str(binary),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
  if target=='native':probe.append({'Family':family,'Instance':{'categoryeditor':'CategoryEditor','torrenttransfer':'TorrentTransfer','removelink':'RemoveLink','sitestatistic':'SiteStatistic','mpserverstatus':'MPServerStatus','pluginuninstall':'PluginUnInstall'}[family],'Binary':str(binary)})
  if target=='native' and family=='torrenttransfer':probe.append({'Family':'torrenttransfermusic','Instance':'TorrentTransfermusic','Binary':str(binary)})
# The version-only fixture derives from the entire current product file.
f=r/'plugins/removelink/plugin.go';source=f.read_text();assert source.count('Version: "2.18"')==1
update=p/'version-plugin.go';update.write_text(source.replace('Version: "2.18"','Version: "2.18.1"',1));overlay=p/'version-overlay.json';overlay.write_text(json.dumps({'Replace':{str(f):str(update)}},indent=2)+'\n')
env=os.environ.copy();env.update(GOOS='linux',GOARCH='amd64',CGO_ENABLED='0');binary=bins/'remove-link-2.18.1-linux';run(['go','build','-trimpath','-buildvcs=false','-overlay',str(overlay),'-o',str(binary),'./cmd/remove-link'],env,p/'build-remove-link-update.stdout');data=binary.read_bytes();artifacts.append({'family':'removelink','target':'linux-update-only-version','path':str(binary),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
config={'Oracle':str(r/'tests/sourceinterfaces/testdata/source-oracle.json'),'Artifacts':probe};(p/'native-probe-input.json').write_text(json.dumps(config,indent=2)+'\n')
run(['go','run','./work/migration-20261106/source-module-manifest/sdkprobe',str(p/'native-probe-input.json')],os.environ.copy(),p/'native-sdk-results.json')
# Linux probe executable and identical owned source fixture, with no Python
# runtime. Root owns ordinary-main acceptance; a network-none isolated process
# replay is separately classified when run.
binary=bins/'source-interface-sdk-probe-linux';run(['go','build','-trimpath','-buildvcs=false','-o',str(binary),'./work/migration-20261106/source-module-manifest/sdkprobe'],env,p/'build-linux-probe.stdout');data=binary.read_bytes();artifacts.append({'family':'test-driver','target':'linux','path':str(binary),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(p/'build-commands.json').write_text(json.dumps(commands,indent=2)+'\n');(p/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
