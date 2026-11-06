import ast,asyncio,copy,hashlib,inspect,json,logging,shutil,tempfile,threading,time,traceback
from pathlib import Path
from types import SimpleNamespace
from typing import *
from apscheduler.schedulers.background import BackgroundScheduler
logger=logging.getLogger('owned');logger.addHandler(logging.NullHandler())
def select(path,cls,names):
 c=next(n for n in ast.parse(SOURCES[path]).body if isinstance(n,ast.ClassDef) and n.name==cls);body=[]
 for n in c.body:
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names:
   n=copy.deepcopy(n);n.decorator_list=[d for d in n.decorator_list if isinstance(d,ast.Name) and d.id in ('classmethod','staticmethod')];body.append(n)
 node=ast.ClassDef(name=cls,bases=[],keywords=[],body=body,decorator_list=[])
 exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),path,'exec',flags=__import__('__future__').annotations.compiler_flag),globals());return globals()[cls]
rows=[]
# Original whole-owner stop has default synchronous wait; no callbacks canceled.
S=select('app/scheduler.py','Scheduler',{'stop'})
o=S();o._scheduler=BackgroundScheduler(timezone='UTC');o._lock=threading.RLock();o._event=threading.Event();o._event.set();entered=threading.Event();release=threading.Event();done=threading.Event();events=[]
def cb():events.append('callback_enter');entered.set();assert release.wait(2);events.append('callback_finished')
o._scheduler.add_job(cb,'interval',seconds=.02,id='owned');o._scheduler.start();assert entered.wait(1)
def stop():events.append('stop_enter');o.stop();events.append('stop_return');done.set()
t=threading.Thread(target=stop);t.start();time.sleep(.06);before=done.is_set();release.set();t.join(1);assert not before and done.is_set() and o._scheduler is None
rows.append(dict(case='whole-owner-scheduler-stop-active-default-wait',events=events,returned_before_release=before,joined=done.is_set(),scheduler_none=o._scheduler is None,event_cleared=not o._event.is_set()))
# Exact original async_install+install_flow; controlled dependency/meta/download helpers and owned tmpfs artifacts.
PH=select('app/helper/plugin.py','PluginHelper',{'async_install','__install_flow_async'})
settings=SimpleNamespace(VERSION_FLAG='v2')
SystemUtils=SimpleNamespace(is_frozen=lambda:False)
for force,prepare_ok,dep_ok in [(False,True,True),(True,True,True),(False,False,True),(True,False,True),(False,True,False),(True,True,False)]:
 with tempfile.TemporaryDirectory(prefix='source-force-owned-') as tmp:
  root=Path(tmp);live=root/'autosignin';live.mkdir();(live/'__init__.py').write_text("plugin_version='2.9.15'\nmarker='old'\n");backup=root/'backup';calls=[]
  h=PH();h.is_local_repo_url=lambda _:False;h.get_repo_info=lambda _:('owned','synthetic');h.check_plugin_system_version=lambda _: (True,'')
  async def package(*args):calls.append(['resolve_package']);return ''
  async def meta(*args):calls.append(['metadata',dict(version='2.9.15',release=False)]);return dict(version='2.9.15',release=False)
  async def backup_fn(pid):calls.append(['backup']);shutil.copytree(live,backup);return backup
  async def remove(pid):calls.append(['remove']);shutil.rmtree(live,ignore_errors=True)
  async def restore(pid,bak):calls.append(['restore']);shutil.rmtree(live,ignore_errors=True);shutil.copytree(bak,live)
  async def prepare(*args):
   calls.append(['prepare_same_version']);live.mkdir(exist_ok=True);(live/'__init__.py').write_text("plugin_version='2.9.15'\nmarker='new'\n");return prepare_ok,'' if prepare_ok else 'owned preparation failure'
  async def deps(pid):calls.append(['dependencies']);return True,dep_ok,'' if dep_ok else 'owned dependency failure'
  def refresh(pid):calls.append(['refresh_persistent_backup'])
  h.async_get_plugin_package_version=package;h._PluginHelper__async_get_plugin_meta=meta;h._PluginHelper__async_backup_plugin=backup_fn;h._PluginHelper__async_remove_old_plugin=remove;h._PluginHelper__async_restore_plugin=restore;h._PluginHelper__prepare_content_via_filelist_async=prepare;h._PluginHelper__async_install_dependencies_if_required=deps;h.refresh_persistent_plugin_backup=refresh
  before=(live/'__init__.py').read_bytes();result=asyncio.run(h.async_install('AutoSignIn','https://github.com/owned/synthetic',force_install=force));after=(live/'__init__.py').read_bytes() if (live/'__init__.py').exists() else None
  expected='new' if prepare_ok and dep_ok else (None if force else 'old')
  assert (after is None if expected is None else ("marker='"+expected+"'").encode() in after)
  rows.append(dict(case='same-version-original-install-helper-flow',force=force,prepare_ok=prepare_ok,dep_ok=dep_ok,result=result,calls=calls,before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest() if after else None,after_text=after.decode() if after else None))
print(json.dumps(dict(classification='immutable333 netnone original selected whole scheduler stop and async_install/flow with real owned tmpfs file mutation; metadata/dependency/content callbacks controlled, no remote downloader or full source App',rows=rows),ensure_ascii=False,indent=2))
