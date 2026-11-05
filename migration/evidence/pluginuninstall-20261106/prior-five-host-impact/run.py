import pathlib,subprocess,json,hashlib,os,time,sys
root=pathlib.Path('/Users/accidia/projects/light-media-plugins');host=pathlib.Path('/Users/accidia/projects/light-media');r=root/'work/migration-20261105/pui-host19-accepted-impact-20261106'
manifest=host/'work/pluginuninstall-source-startup-20261105/host-files-current.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(manifest)=='f9e4f90ef62309f4b064dbeb8f9a3b319841dd2c4c6e9bd33aa16201fb022988'
expected=json.load(open(manifest));assert len(expected['files'])==19
for f in expected['files']:assert sha(pathlib.Path(f['path']))==f['sha256'],f['path']
sdk=json.load(open(root/'work/migration-20261105/sdk98-current-freeze/current-freeze.json'))
for f,s in sdk['files'].items():assert sha(root/f)==s,f
assert sha(root/'SDK_ORIGIN.json')=='40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875'
def binding():
 files=subprocess.check_output(['git','ls-files','-z'],cwd=host).split(b'\0');hp={str(host/x.decode()) for x in files if x};hp.update(f['path'] for f in expected['files'])
 tp={str(root/x) for x in sdk['files']};tp.update(str(root/x) for x in ['go.mod','go.sum','SDK_ORIGIN.json'])
 for folder in ['categoryeditor','torrenttransfer','sitestatistic','mpserverstatus']:
  tp.update(str(p) for p in (root/'plugins'/folder).rglob('*') if p.is_file())
 for cmd in ['category-editor','torrent-transfer','site-statistic','mp-server-status']:
  tp.update(str(p) for p in (root/'cmd'/cmd).rglob('*') if p.is_file())
 return {'host':{p:sha(pathlib.Path(p)) for p in sorted(hp) if pathlib.Path(p).is_file()},'workers':{p:sha(pathlib.Path(p)) for p in sorted(tp) if pathlib.Path(p).is_file()},'overlay_source':sha(r/'accepted_impact_test.go'),'overlay':sha(r/'app-overlay.json')}
before=binding();(r/'before-inputs.json').write_text(json.dumps(before,indent=2)+'\n')
env=os.environ.copy();env.pop('GOFLAGS',None);(r/'tmp').mkdir(exist_ok=True)
env.update({'TMPDIR':str(r/'tmp'),'TZ':'Asia/Shanghai','PLUGIN_MARKET':'','DEV':'false','LIGHT_MEDIA_SAFE_MODE':'false'})
commands=[];owned=[]
def run(name,cmd,cwd,extra=None):
 start=time.time();e=env.copy();e.update(extra or {})
 with open(r/(name+'.stdout'),'wb') as out,open(r/(name+'.stderr'),'wb') as err:
  p=subprocess.run(cmd,cwd=cwd,env=e,stdout=out,stderr=err)
 commands.append({'name':name,'command':cmd,'cwd':str(cwd),'exit_code':p.returncode,'elapsed_seconds':round(time.time()-start,3)});(r/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');print(name,p.returncode,flush=True)
 if p.returncode:sys.exit(p.returncode)
for name,cmd,var in [('category-editor','category-editor','IMPACT_CATEGORY_BINARY'),('torrent-transfer','torrent-transfer','IMPACT_TT_BINARY'),('site-statistic','site-statistic','IMPACT_SITE_BINARY')]:
 path=r/(name+'-native');run('build-'+name,['go','build','-trimpath','-buildvcs=false','-o',str(path),'./cmd/'+cmd],root,{'CGO_ENABLED':'0'});owned.append(path);env[var]=str(path)
env['IMPACT_MPS_BINARY']=str(root/'work/migration-20261105/pluginuninstall-20261105/mp-server-status')
artifacts={p.name:{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'new_owned_temporary':p in owned} for p in owned+[pathlib.Path(env['IMPACT_MPS_BINARY'])]}
(r/'native-artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
for key in ['IMPACT_CATEGORY_BINARY','IMPACT_TT_BINARY','IMPACT_SITE_BINARY','IMPACT_MPS_BINARY']:
 p=env[key];run('manifest-'+key.lower(),[p,'--manifest'],root)
overlay=str(r/'app-overlay.json');run('app-normal',['go','test','-json','-count=1','-overlay='+overlay,'./internal/app','-run','^TestIndependentPUIHost19AcceptedConsumers$','-timeout','3m'],host)
run('app-race',['go','test','-race','-json','-count=1','-overlay='+overlay,'./internal/app','-run','^TestIndependentPUIHost19AcceptedConsumers$','-timeout','3m'],host)
after=binding();assert before==after,'input drift'
(r/'after-inputs.json').write_text(json.dumps(after,indent=2)+'\n')
cleanup=[]
for p in owned:
 assert sha(p)==artifacts[p.name]['sha256'];p.unlink();cleanup.append({'path':str(p),'sha256_before_delete':artifacts[p.name]['sha256'],'absent_after':not p.exists()})
(r/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
print('all input stable; three owned temporary native binaries removed',flush=True)
