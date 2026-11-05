from pathlib import Path
import json,hashlib,subprocess,os
root=Path.cwd();work=root/'work/site-source-capabilities-20261105';out=work/'negative-final';out.mkdir(exist_ok=True)
mutations=[
 ('drop-current','internal/app/site_manage.go','*hooks.SourceResult = current','*hooks.SourceResult = append(json.RawMessage(nil), current...); *hooks.SourceResult = json.RawMessage(`null`)'),
 ('stateless-list','internal/app/plugin_original_host_sites_source.go','for _, fields := range registry.List(active) {','for _, fields := range func() []map[string]any { out:=[]map[string]any{};for _,db:=range active {key,_:=db["domain"].(string);if row:=registry.Get(key,db);row!=nil {out=append(out,row)}};return out }() {'),
 ('reject-before-err-skip','internal/app/site_account_views.go','data, err := statisticData(snapshot, site)','if snapshot.SourceData!=nil {if err:=snapshot.SourceData.ValidateSourceAccountBinding();err!=nil{return err}}\n data, err := statisticData(snapshot, site)'),
 ('current-history-name','internal/app/plugin_original_host_sites.go','row["name"] = mustCleanSeedJSON(s.Name)','row["name"] = mustCleanSeedJSON(site.Name)'),
 ('swallow-native-guard','internal/sites/source_userdata_result.go','return errors.As(err, &rejected)','_ = errors.As(err,&rejected); return false'),
 ('catalog-id-authority','internal/app/plugin_original_host_sites_source.go','fields["id"] == row.sourceID && fields["url"] == row.site.BaseURL','fields["id"] == row.sourceID'),
]
env=os.environ.copy();env.update(TMPDIR=str(work/'tmp'),PLUGIN_SOURCE_SITES_FIXTURE_BINARY=str(work/'source-sites-worker'),OWNED_MODULE_OVERRIDE_BINARY=str(work/'module-worker'))
rows=[]
pattern='^(TestSourceSitesCurrentAndHistoricalProjectionTable|TestSourceSitesIndexerActualSDKOrderAliasAndCanonicalIdentity|TestSourceSitesBindingErrorSkipRetainsWideCurrentAndUnreadMessage|TestSourceSitesAccountsRenameCloneAndCold|TestSourceSitesIntrinsicNativeGuardStaysRejectedAfterRestore)$'
for name,path,before,after in mutations:
 text=(root/path).read_text();assert before in text,name
 target=out/(name+'.go');target.write_text(text.replace(before,after,1))
 overlay=out/(name+'.json');overlay.write_text(json.dumps({'Replace':{str(root/path):str(target)}})+'\n')
 log=out/(name+'.jsonl');cmd=['go','test','-overlay',str(overlay),'./internal/app','-run',pattern,'-json']
 with log.open('wb') as stream:p=subprocess.run(cmd,env=env,stdout=stream,stderr=subprocess.STDOUT)
 events=[]
 for line in log.read_text().splitlines():
  try:events.append(json.loads(line))
  except:pass
 runs=[e for e in events if e.get('Action')=='run'];failed=[e.get('Test') for e in events if e.get('Action')=='fail' and e.get('Test')]
 row={'name':name,'path':path,'overlay_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'command':cmd,'exit_code':p.returncode,'compiled':bool(runs),'failed_tests':failed,'log':str(log.relative_to(work)),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()};rows.append(row)
 print(json.dumps(row),flush=True)
 assert p.returncode!=0 and runs and failed, 'negative must compile and fail a real assertion'
(out/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
