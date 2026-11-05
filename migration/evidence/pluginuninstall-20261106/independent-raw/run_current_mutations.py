from pathlib import Path
import json,hashlib,subprocess,os,time
h=Path('/Users/accidia/projects/light-media');p=Path('/Users/accidia/projects/light-media-plugins');w=p/'work/sites-review-20261105/pluginuninstall-review';base=json.loads((w/'current-host-overlay.json').read_bytes())['Replace'];d=w/'current-mutations';d.mkdir(exist_ok=True)
cases=[
 ('membership-order-startup','plugin_original_startup.go','entries, err := directory.ReadDir(-1)','''entries, err := directory.ReadDir(-1)
 sort.SliceStable(entries,func(i,j int)bool{rank:=func(name string)int{for n,id:=range ids{if strings.EqualFold(name,id){return n}};return len(ids)};return rank(entries[i].Name())<rank(entries[j].Name())})''','^TestIndependentSameOrderCloneStartupIgnoresInstalledArrayOrder$'),
 ('stale-installed-local','plugin_original_local_cards.go','slices.Contains(installed, id)','len(installed)>=0 && class.installation.Installed','^TestIndependentFailedInstalledWriteLocalMetadataUsesSourceCache$'),
 ('ignore-installed-version-cache','plugin_original_class_registry.go','!slices.Contains(installed, id)','len(installed)<0','^TestIndependentFailedInstalledWriteLocalMetadataUsesSourceCache$'),
 ('stub-page-presence','plugin_original_local_cards.go','card.HasPage = manifest.HasPage','card.HasPage = slices.Contains(manifest.Methods,"get_page")','^TestSourceUninstallPagePresenceUsesSourceDeclaration$'),
 ('skip-stat-empty','plugin_original_startup.go','func (a *App) originalInstalledPackages(ctx context.Context, ids []string) ([]PluginInstallation, error) {','''func (a *App) originalInstalledPackages(ctx context.Context, ids []string) ([]PluginInstallation, error) {
 if len(ids)==0{return []PluginInstallation{},nil}''','^TestIndependentEmptyInstalledStillChecksPackageRootExists$'),
 ('drop-physical-retirement','plugin_original_host_manager_source.go','call.retire.Store(true)','call.retire.Store(false)','^TestIndependentLoadedSelfInitializerReapsOnlyAfterItsSourceTail$'),
]
env=dict(os.environ,TMPDIR=str(w/'tmp'),SOURCE_UNINSTALL_BINARY=str(p/'work/migration-20261105/pluginuninstall-20261105/plugin-uninstall'),SOURCE_UNINSTALL_FUTURE_BINARY=str(p/'work/migration-20261105/pluginuninstall-20261105/mp-server-status'),OWNED_HOST_SERVICES_FIXTURE_BINARY=str(h/'work/plugin-uninstall-host-services-fixture'),SOURCE_UNINSTALL_COUNTER_BINARY=str(h/'work/plugin-uninstall-standard-fixture'))
rows=[]
for name,file,old,new,test in cases:
 out=d/name;out.mkdir(exist_ok=True);key=str(h/'internal/app'/file);original=Path(base[key]).read_text();assert original.count(old)==1,(name,original.count(old));candidate=out/file;candidate.write_text(original.replace(old,new,1));overlay=out/'overlay.json';overlay.write_text(json.dumps({'Replace':dict(base,**{key:str(candidate)})},indent=2)+'\n');cmd=['go','test','-count=1','-json','-overlay='+str(overlay),'-run',test,'./internal/app'];start=time.time()
 with (out/'stdout.jsonl').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:r=subprocess.run(cmd,cwd=h,env=env,stdout=stdout,stderr=stderr)
 events=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines() if x.startswith('{')];failed=[x.get('Test') for x in events if x.get('Action')=='fail' and x.get('Test')];compiled=not any(x.get('Action')=='build-fail' for x in events) and not 'build failed' in (out/'stderr.txt').read_text().lower();result={'name':name,'command':cmd,'exit':r.returncode,'seconds':time.time()-start,'compiled':compiled,'failed_tests':failed,'killed':r.returncode!=0 and compiled and bool(failed),'original_sha256':hashlib.sha256(original.encode()).hexdigest(),'mutated_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest()};rows.append(result);print(json.dumps(result),flush=True)
(d/'observations.json').write_text(json.dumps({'host_manifest_sha256':'f9e4f90ef62309f4b064dbeb8f9a3b319841dd2c4c6e9bd33aa16201fb022988','results':rows},indent=2)+'\n');assert all(x['killed'] for x in rows)
