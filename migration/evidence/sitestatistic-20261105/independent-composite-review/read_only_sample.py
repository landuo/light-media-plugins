import pathlib,hashlib,json,sqlite3,os,subprocess
root=pathlib.Path('/home/admin/light-media-plugins-migration-site-20261105');run=root/'main-run-5'
assert (run/'.task-owned').read_text()=='light-media-plugins/SiteStatistic/20261105/owned-only'
files=['bin/light-media-source-recovery','bin/site-statistic-fixed','bin/site-statistic-update-fixed','bin/main-driver-public-config-fixed']
out={'classification':'independent NAS read-only retained owned sample; no service startup, config, credentials or live PT access','marker':'verified exact run5 marker','binaries':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}}
c=sqlite3.connect('file:'+str(run/'light-media.db')+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
e={}
for raw, in c.execute('SELECT payload FROM domain_events ORDER BY rowid'):
 d=json.loads(raw)
 if d.get('event_type')=='site.refreshed':
  k=str(d.get('site_id'));e[k]=e.get(k,0)+1
out['db']={'events':e,'records':dict(c.execute("SELECT kind,count(*) FROM records WHERE kind LIKE 'site%' GROUP BY kind")),'plugin_value_row_counts':list(c.execute("SELECT instance_id,kind,count(*) FROM plugin_values GROUP BY instance_id,kind ORDER BY instance_id,kind"))};c.close()
ps=subprocess.run(['ps','-eo','pid=,args='],stdout=subprocess.PIPE,text=True,check=True).stdout
out['owned_processes']=[line.strip() for line in ps.splitlines() if str(root) in line and any(s in line for s in ['bin/light-media','/plugin-packages/','bin/main-driver'])]
print(json.dumps(out,ensure_ascii=False,indent=2))
