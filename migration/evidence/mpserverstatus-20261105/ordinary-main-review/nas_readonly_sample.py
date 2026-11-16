import pathlib,hashlib,json,sqlite3,subprocess,datetime,os
root=pathlib.Path('/home/admin/light-media-plugins-migration-mps-20261105')
run=root/'main-run-4'
out={'classification':'independent readonly exact-owned NAS sample; no secret key or credential decryption; no Main/worker startup','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
marker=run/'.task-owned'
out['marker']={'content':marker.read_text(),'uid':marker.stat().st_uid,'mode':oct(marker.stat().st_mode&0o777)}
assert out['marker']['content']=='light-media-plugins/MPServerStatus/20261105/owned-only'
out['binaries']={}
for name in ['light-media-host75e-linux','mp-server-status-linux-amd64','mp-server-status-update-linux-amd64','mpserverstatus-main-tests-linux-amd64']:
 p=root/'bin'/name;out['binaries'][name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
out['owned_container_status']=subprocess.check_output(['docker','ps','-a','--filter','label=task=light-media-plugins.MPServerStatus.20261105','--format','{{.Names}} {{.Status}}'],text=True).splitlines()
processes=subprocess.check_output(['ps','-eo','pid,args'],text=True)
out['owned_processes']=[{'pid':int(x.split(None,1)[0]),'owned_root_in_arguments':True} for x in processes.splitlines()[1:] if str(root) in x]
con=sqlite3.connect('file:'+str(run/'light-media.db')+'?mode=ro&immutable=1',uri=True)
tables=[x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
out['plugin_tables']={}
for table in tables:
 if 'plugin' not in table:continue
 cols=[x[1] for x in con.execute('PRAGMA table_info("'+table+'")')]
 entry={'columns':cols,'rows':con.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0]}
 allowed=[c for c in ['instance_id','plugin_id','version','installed','enabled','generation','is_clone','base_id','status'] if c in cols]
 if allowed:
  entry['identity_fields']=allowed
  entry['identity_rows']=con.execute('SELECT '+','.join('"'+c+'"' for c in allowed)+' FROM "'+table+'" ORDER BY rowid').fetchall()
 out['plugin_tables'][table]=entry
con.close()
out['package_id_dirs']=sorted(p.name for p in (run/'plugin-packages').iterdir() if p.is_dir())
out['continuation_marker_present']=(run/'ui-complete').is_file()
print(json.dumps(out,indent=2))
