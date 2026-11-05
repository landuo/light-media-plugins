from pathlib import Path
import subprocess,json,hashlib,time,os,sys
h=Path('/Users/accidia/projects/light-media');p=Path('/Users/accidia/projects/light-media-plugins');w=p/'work/sites-review-20261105/pluginuninstall-review';source=h/'work/pluginuninstall-source-startup-20261105/host-files-current.json';expected='f9e4f90ef62309f4b064dbeb8f9a3b319841dd2c4c6e9bd33aa16201fb022988';assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
manifest=json.loads(source.read_bytes());(w/'host-files-current-final.json').write_bytes(source.read_bytes());replace=json.loads((w/'stage2-host-overlay.json').read_bytes())['Replace']
for row in manifest['files']:
 src=Path(row['path']);b=src.read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'];q=w/'current-frozen19'/src.relative_to(h);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);replace[str(src)]=str(q)
overlay=w/'current-host-overlay.json';overlay.write_text(json.dumps({'Replace':replace},indent=2)+'\n')
def inputs():
 raw=subprocess.check_output(['go','list','-deps','-test','-json','-overlay='+str(overlay),'./internal/app'],cwd=h,text=True);decoder=json.JSONDecoder();i=0;paths={h/'go.mod',h/'go.sum'}
 while i<len(raw):
  while i<len(raw) and raw[i].isspace():i+=1
  if i==len(raw):break
  entry,i=decoder.raw_decode(raw,i);d=Path(entry.get('Dir','/missing'))
  if not str(d).startswith(str(h)+'/'):continue
  for field in ['GoFiles','CgoFiles','TestGoFiles','XTestGoFiles','CFiles','HFiles','SFiles','SysoFiles','EmbedFiles']:
   for v in entry.get(field,[]):
    f=d/v;actual=replace.get(str(f),str(f))
    if actual and Path(actual).is_file():paths.add(Path(actual))
 paths.update((h/'testdata/plugin-source-uninstall-20261105').rglob('*'))
 for f in ['private-files-final.json','host-files-current-final.json','current-host-overlay.json','stage2-tests/independent_host_test.go']:paths.add(w/f)
 for e in json.loads((w/'private-files-final.json').read_bytes())['files']:paths.add(Path(e['path']))
 for e in json.loads((p/'SDK_ORIGIN.json').read_bytes())['files']:paths.add(p/e['path'])
 return {str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(paths) if f.is_file()}
env=dict(os.environ,TMPDIR=str(w/'tmp'),SOURCE_UNINSTALL_BINARY=str(p/'work/migration-20261105/pluginuninstall-20261105/plugin-uninstall'),SOURCE_UNINSTALL_FUTURE_BINARY=str(p/'work/migration-20261105/pluginuninstall-20261105/mp-server-status'),OWNED_HOST_SERVICES_FIXTURE_BINARY=str(h/'work/plugin-uninstall-host-services-fixture'),SOURCE_UNINSTALL_COUNTER_BINARY=str(h/'work/plugin-uninstall-standard-fixture'))
selection='^TestSourceUninstall|^TestIndependentSameOrderCloneStartupIgnoresInstalledArrayOrder$|^TestIndependentLoadedSelfInitializerReapsOnlyAfterItsSourceTail$|^TestIndependentFailedInstalledWriteLocalMetadataUsesSourceCache$|^TestIndependentEmptyInstalledStillChecksPackageRootExists$'
label=sys.argv[1];extra=sys.argv[2:];before=inputs();(w/(label+'-inputs-before.json')).write_text(json.dumps(before,indent=2)+'\n');cmd=['go','test',*extra,'-count=1','-json','-overlay='+str(overlay),'-run',selection,'./internal/app'];start=time.time()
with (w/(label+'.jsonl')).open('w') as out,(w/(label+'.stderr')).open('w') as err:r=subprocess.run(cmd,cwd=h,env=env,stdout=out,stderr=err)
after=inputs();(w/(label+'-inputs-after.json')).write_text(json.dumps(after,indent=2)+'\n');result={'command':cmd,'cwd':str(h),'explicit_env':{k:env[k] for k in ['TMPDIR','SOURCE_UNINSTALL_BINARY','SOURCE_UNINSTALL_FUTURE_BINARY','OWNED_HOST_SERVICES_FIXTURE_BINARY','SOURCE_UNINSTALL_COUNTER_BINARY']},'host_manifest_sha256':expected,'exit':r.returncode,'seconds':time.time()-start,'inputs':len(before),'changed':[f for f in sorted(set(before)|set(after)) if before.get(f)!=after.get(f)]};(w/(label+'-binding.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(0 if r.returncode==0 and before==after else 1)
