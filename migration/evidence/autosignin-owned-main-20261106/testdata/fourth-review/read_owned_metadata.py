from pathlib import Path
import os,json,sqlite3,datetime
r=Path('/home/admin/light-media-plugins-root-asi-owned-20261106-r4');assert os.getuid()==1000 and not r.is_symlink()and(r/'.task-owned').read_text().strip()=='light-media-plugins/root-asi-owned/20261106/owned-only'
base=r/'runtime';assert base.is_dir()and not base.is_symlink();db=base/'light-media.db';assert db.is_file()and not db.is_symlink()
c=sqlite3.connect(db.as_uri()+'?mode=ro');c.execute('PRAGMA query_only=ON')
rows=c.execute("SELECT instance_id,plugin_id,version,installed FROM plugin_installations WHERE instance_id IN ('AutoSignIn','AutoSignIncopy') ORDER BY instance_id").fetchall()
counts=c.execute("SELECT instance_id,kind,COUNT(*) FROM plugin_values WHERE instance_id IN ('AutoSignIn','AutoSignIncopy') GROUP BY instance_id,kind ORDER BY instance_id,kind").fetchall();c.close()
code={}
for name in ['AutoSignIn','AutoSignIncopy']:
 p=base/'plugin-packages'/name
 try:s=p.lstat();code[name]={'exists':True,'is_dir':p.is_dir(),'is_symlink':p.is_symlink(),'mode':oct(s.st_mode&0o777),'top_entries':sorted(x.name for x in p.iterdir())if p.is_dir()and not p.is_symlink()else []}
 except FileNotFoundError:code[name]={'exists':False}
processes=[]
for d in Path('/proc').iterdir():
 if not d.name.isdigit():continue
 try:
  target=os.readlink(d/'exe')
  if not target.startswith(str(r)+'/'):continue
  stat=(d/'stat').read_text();right=stat[stat.rfind(') ')+2:].split();processes.append({'pid':int(d.name),'exe':target,'state':right[0],'ppid':int(right[1])})
 except(OSError,ValueError,IndexError):continue
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'read-only post-r4 own-root metadata; no file or DB payloads exported; after Main stop, not per-uninstall process evidence','root':str(r),'sqlite_uri_mode':'ro','sqlite_query_only':True,'installations':rows,'plugin_value_counts':counts,'code':code,'owned_executable_processes':processes,'recorded_main_pid_exists':{str(pid):(Path('/proc')/str(pid)).exists()for pid in [2677045,2677101]}},ensure_ascii=False))
