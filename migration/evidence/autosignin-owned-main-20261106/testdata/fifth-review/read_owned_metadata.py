from pathlib import Path
import os,json,sqlite3,datetime
r=Path('/home/admin/light-media-plugins-root-asi-owned-20261106-r5');assert os.getuid()==1000 and not r.is_symlink()and(r/'.task-owned').read_text().strip()=='light-media-plugins/root-asi-owned/20261106/owned-only'
b=r/'runtime';assert b.is_dir()and not b.is_symlink();db=b/'light-media.db';assert db.is_file()and not db.is_symlink();c=sqlite3.connect(db.as_uri()+'?mode=ro');c.execute('PRAGMA query_only=ON');rows=c.execute("SELECT instance_id,installed FROM plugin_installations WHERE instance_id IN ('AutoSignIn','AutoSignIncopy') ORDER BY instance_id").fetchall();counts=c.execute("SELECT instance_id,kind,COUNT(*) FROM plugin_values WHERE instance_id IN ('AutoSignIn','AutoSignIncopy') GROUP BY instance_id,kind ORDER BY instance_id,kind").fetchall();c.close()
code={}
for name in ['AutoSignIn','AutoSignIncopy']:
 p=b/'plugin-packages'/name
 try:s=p.lstat();code[name]={'exists':True,'is_dir':p.is_dir(),'is_symlink':p.is_symlink(),'top_entries':sorted(x.name for x in p.iterdir())if p.is_dir()and not p.is_symlink()else []}
 except FileNotFoundError:code[name]={'exists':False}
processes=[]
for d in Path('/proc').iterdir():
 if not d.name.isdigit():continue
 try:
  target=os.readlink(d/'exe')
  if target.startswith(str(r)+'/'):processes.append({'pid':int(d.name),'exe':target})
 except OSError:continue
pids=[2680553,2680696,2680611,2680669,2680707,2680715,2680727,2680765]
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'post-r5 owned root read-only metadata; no private value/DB/key payload exported','root':str(r),'sqlite_mode':'ro/query_only','installed':rows,'plugin_value_counts':counts,'code':code,'owned_executable_processes':processes,'recorded_pid_exists':{str(p):(Path('/proc')/str(p)).exists()for p in pids}},ensure_ascii=False))
