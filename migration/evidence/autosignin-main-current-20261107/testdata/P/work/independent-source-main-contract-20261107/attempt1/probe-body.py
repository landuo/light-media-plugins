import ast, asyncio, copy, hashlib, inspect, json, logging, multiprocessing, platform, re, threading, time, traceback, typing
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from multiprocessing.pool import ThreadPool
from typing import *
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import BasePoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError
logging.getLogger('apscheduler').setLevel(logging.CRITICAL)
logger=logging.getLogger('source-probe'); logger.addHandler(logging.NullHandler())
START=time.monotonic(); rows=[]; timeline=[]
def stamp(kind, **kw):
 timeline.append(dict(at=round(time.monotonic()-START,6),kind=kind,thread=threading.current_thread().name,**kw))
def selected(path, cls, names):
 tree=ast.parse(SOURCES[path]); orig=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
 body=[]
 for n in orig.body:
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names:
   n=copy.deepcopy(n);n.decorator_list=[d for d in n.decorator_list if isinstance(d,ast.Name) and d.id in ('staticmethod','classmethod')];body.append(n)
  elif isinstance(n,(ast.Assign,ast.AnnAssign)) and cls=='AutoSignIn':body.append(copy.deepcopy(n))
 node=ast.ClassDef(name=cls,bases=[],keywords=[],body=body,decorator_list=[])
 exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),path,'exec',flags=__import__('__future__').annotations.compiler_flag),globals())
 return globals()[cls]
def top(path,name):
 n=copy.deepcopy(next(n for n in ast.parse(SOURCES[path]).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name));n.decorator_list=[]
 # Defaults are route wiring only; every case supplies parameters explicitly.
 n.args.defaults=[];n.args.kw_defaults=[None]*len(n.args.kwonlyargs)
 exec(compile(ast.fix_missing_locations(ast.Module(body=[n],type_ignores=[])),path,'exec',flags=__import__('__future__').annotations.compiler_flag),globals());return globals()[name]
settings=SimpleNamespace(TZ='UTC',MP_DOMAIN=lambda x:'https://owned.invalid/'+x)
class Event:
 def __init__(self,data):self.event_data=data
class EventType:
 PluginAction='PluginAction';CommandExcute='CommandExcute'
class NotificationType:SiteMessage='SiteMessage'
class MessageChannel:Web='Web'
class SiteOper:
 def list_order_by_pri(self):return [SimpleNamespace(id=701)]
class SitesHelper:
 def get_indexers(self):return [dict(id=701,name='Owned synthetic',domain='https://owned.invalid/',public=False)]
class ModuleHelper:
 @staticmethod
 def load(*a,**kw):return []
class Bus:
 def __init__(self):self.events=[]
 def send_event(self,t,data):self.events.append((t,copy.deepcopy(data)))
eventmanager=Bus()
class ObjectUtils:
 @staticmethod
 def arguments(f):return len(inspect.signature(f).parameters)
_Finish=[]
def _finish_command_processing_status(status,user_id=None):_Finish.append(dict(status=status,user_id=user_id))
# Exact installed NamedTuple, exact selected plugin method bodies; only external I/O is controlled.
nt=next(n for n in ast.parse(SOURCES['installed-asi/result.py']).body if isinstance(n,ast.ClassDef) and n.name=='SiteResult')
exec(compile(ast.Module(body=[nt],type_ignores=[]),'installed-asi/result.py','exec'),globals())
ASI=selected('installed-asi/__init__.py','AutoSignIn',{'init_plugin','stop_service','sign_in','__do','__update_config','__custom_sites','_clean_history','_date_label','get_state','get_command','get_service'})
BASE=selected('app/plugins/__init__.py','_PluginBase',{'close','post_message'})
PM=selected('app/core/plugin.py','PluginManager',{'__stop_plugin','init_plugin'})
COMMAND=selected('app/command.py','Command',{'command_event','execute','__run_command','send_plugin_event','__build_plugin_commands'})
SCHED=selected('app/scheduler.py','Scheduler',{'remove_plugin_job','update_plugin_job','start','__prepare_job','__finish_job','__supports_progress_callback','__get_result_error','_get_progress_key','_format_time'})
# No original target app is imported. Per-instance memory DB and synthetic site execution are explicit boundaries.
def plugin(case,block=False):
 a=ASI();a.case=case;a.kv={};a.cfg=[];a.posts=[];a.calls=[];a.release=threading.Event();a.enter=threading.Event();a.done=threading.Event()
 a.get_config=lambda *args:None
 a.get_data=lambda key=None:copy.deepcopy(a.kv.get(key)) if key is not None else [SimpleNamespace(key=k) for k in a.kv]
 def save(key,value):a.kv[key]=copy.deepcopy(value);stamp('save_data',case=case,key=key)
 a.save_data=save;a.del_data=lambda key:a.kv.pop(key,None)
 def config(c):a.cfg.append(copy.deepcopy(c));stamp('config',case=case,cron=c['cron'],onlyonce=c['onlyonce'])
 a.update_config=config
 def post(**kw):a.posts.append(copy.deepcopy(kw));stamp('post',case=case,title=kw.get('title'))
 a.post_message=post;a.eventmanager=Bus()
 def visit(s):
  a.calls.append(dict(site=copy.deepcopy(s),at=time.monotonic()-START));stamp('site_enter',case=case);a.enter.set()
  if block:assert a.release.wait(5),'owned release timeout'
  stamp('site_return',case=case);a.done.set();return SiteResult(s['name'],'签到成功',True,True)
 a.signin_site=visit;a.login_site=visit
 return a
def cfg(**kw):return dict(enabled=True,cron='1',onlyonce=False,notify=False,queue_cnt=1,sign_sites=[701],login_sites=[],retry_keyword='^NEVER-MATCH$',auto_cf=0,clean=False,**kw)
def init(a,c):a.init_plugin(c)
# Private once: actual original +3-second date callback; init must wait for active private pool.
a=plugin('private-init',block=True); c=cfg();c['onlyonce']=True;begin=time.monotonic();init(a,c);after=time.monotonic()
assert a.cfg[-1]['onlyonce'] is False
assert a.enter.wait(4.5),'actual original private date did not fire'
entered_delay=a.calls[0]['at']-(begin-START)
c2=cfg();c2['cron']='2';returned=threading.Event()
def reinit():stamp('reinit_enter');init(a,c2);stamp('reinit_return');returned.set()
t=threading.Thread(target=reinit,name='owned-reinit');t.start();time.sleep(.12)
blocked=not returned.is_set();old_config=a._cron;stamp('private_before_release',blocked=blocked,cron=old_config);a.release.set();t.join(2)
assert blocked and old_config=='1' and returned.is_set() and a._cron=='2'
rows.append(dict(case='private-once-default-shutdown-blocks-reinit',delay=entered_delay,onlyonce_false_before_fire=a.cfg[1]['onlyonce'] is False,blocked_before_release=blocked,config_before_release=old_config,final_cron=a._cron,history_keys=sorted(a.kv),calls=len(a.calls),scheduler_none=a._scheduler is None))
# Same actual default shutdown through fixed host close->stop_service; close is an unchanged source pass.
a=plugin('private-manager-stop',block=True);a.close=lambda:(stamp('close_enter'),BASE.close(a),stamp('close_return'))
s=BackgroundScheduler(timezone='UTC');a._scheduler=s;s.add_job(a.sign_in,'date',run_date=datetime.now(pytz.UTC)+timedelta(seconds=.03));init_config=cfg()
for k,v in init_config.items():setattr(a,'_'+k,v)
s.start();assert a.enter.wait(1);finished=threading.Event()
def stop():stamp('manager_stop_enter');PM._PluginManager__stop_plugin(a);stamp('manager_stop_return');finished.set()
t=threading.Thread(target=stop,name='owned-manager-stop');t.start();time.sleep(.1);before=finished.is_set();a.release.set();t.join(2)
assert not before and finished.is_set() and a._scheduler is None
rows.append(dict(case='manager-close-then-private-stop',returned_before_release=before,joined=finished.is_set(),calls=len(a.calls),history_keys=sorted(a.kv)))
# Public interval owner: exact get_service->update_plugin_job->start path, real APS.
class ProgressHelper:
 def __init__(self,*a):pass
 def start(self):pass
 def update(self,**kw):pass
 def get(self):return {}
 def end(self,**kw):stamp('progress_end',status=kw['data']['status'])
class SchedulerChain:
 messagehelper=SimpleNamespace(put=lambda **kw:stamp('system_message',data=kw))
manager=SimpleNamespace(get_plugin_services=lambda pid:public.get_service(),get_plugin_attr=lambda pid,key:'站点自动签到')
# Function global intentionally replaces manager constructor with an owned registry, never an original service.
PluginManager=lambda:manager
public=plugin('public-interval',block=True);init(public,cfg());public._cron=str(.12/3600)
o=SCHED();o._jobs={};o._lock=threading.RLock();o._scheduler=BackgroundScheduler(timezone='UTC');o.update_plugin_job('AutoSignIn');register=time.monotonic();o._scheduler.start();assert public.enter.wait(1)
logical_running=copy.deepcopy({k:{kk:vv for kk,vv in v.items() if kk not in ['func']} for k,v in o._jobs.items()})
# Source plugin.stop_service has no public scheduler; remove public job does not join an active call.
stamp('public_plugin_stop_enter');public.stop_service();stamp('public_plugin_stop_return');remove_before=time.monotonic();o.remove_plugin_job('AutoSignIn');remove_after=time.monotonic();before_release=public.done.is_set();public.release.set();assert public.done.wait(1);o._scheduler.shutdown()
rows.append(dict(case='public-interval-real-owner-active-remove',interval_seconds=.12,first_callback_delay=public.calls[0]['at']-(register-START),running=logical_running,plugin_private_scheduler_none=public._scheduler is None,remove_seconds=remove_after-remove_before,task_done_at_remove=before_release,calls=len(public.calls),history_keys=sorted(public.kv),jobs_after_remove=list(o._jobs)))
# Ordinary Web endpoint and command chain; exact source methods with event delivery boundary controlled.
web=top('app/api/endpoints/message.py','web_message');web_calls=[]
MessageChain=lambda:SimpleNamespace(handle_message=lambda **kw:web_calls.append(copy.deepcopy(kw)))
schemas=SimpleNamespace(Response=lambda **kw:kw)
class Request:
 headers={'content-type':'application/json'}
 async def json(self):return {'text':'/site_signin owned arg'}
asyncio.run(web(request=Request(),text=None,current_user=SimpleNamespace(name='owned-user')))
assert web_calls[0]==dict(channel='Web',source='owned-user',userid='owned-user',username='owned-user',text='/site_signin owned arg',images=None)
# Preserve exact ordinary command if-branch from fixed source (source lines349–362), not AI/default routes.
core=next(n for n in ast.walk(ast.parse(SOURCES['app/chain/message.py'])) if isinstance(n,ast.FunctionDef) and n.name=='_handle_message_core')
branch=copy.deepcopy(next(n for n in core.body if isinstance(n,ast.If) and getattr(n,'lineno',0)==349))
branch_fn=ast.FunctionDef(name='ordinary_branch',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n) for n in ['self','text','userid','channel','source','processing_status']],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[branch],decorator_list=[])
exec(compile(ast.fix_missing_locations(ast.Module(body=[branch_fn],type_ignores=[])),'app/chain/message.py:349-362','exec'),globals())
command_bus=Bus();mc=SimpleNamespace(eventmanager=command_bus,_has_ai_prefix=lambda text:False)
ordinary_branch(mc,web_calls[0]['text'],web_calls[0]['userid'],web_calls[0]['channel'],web_calls[0]['source'],None)
assert len(command_bus.events)==1
web_plugin=plugin('web-first');init(web_plugin,cfg());eventmanager=Bus();manager.get_plugin_commands=lambda:{'AutoSignIn':web_plugin.get_command()}
co=COMMAND();co.messagehelper=SimpleNamespace(put=lambda **kw:stamp('command_error',data=kw));co._plugin_commands=co._Command__build_plugin_commands();co.get=lambda cmd:co._plugin_commands.get(cmd)
co.command_event(Event(command_bus.events[0][1]));assert len(eventmanager.events)==1
kind,data=eventmanager.events.pop();web_plugin.sign_in(Event(data));first=dict(event=copy.deepcopy(data),posts=copy.deepcopy(web_plugin.posts),history=copy.deepcopy(web_plugin.kv),calls=len(web_plugin.calls))
web_plugin.posts=[];web_plugin.sign_in(Event(data));dedup=dict(posts=copy.deepcopy(web_plugin.posts),calls=len(web_plugin.calls))
# Nonempty retry keyword differs from empty-keyword source default.
empty=plugin('empty-retry');c=cfg();c['retry_keyword']='';init(empty,c);empty.sign_in();empty.sign_in()
rows.append(dict(case='web-command-source-method-replay',web=web_calls[0],command_event=command_bus.events[0],plugin_event_kind=kind,first=first,second_same_day=dedup,empty_retry_two_invocations=dict(calls=len(empty.calls),history=empty.kv),processing_finish=_Finish))
assert first['posts'][0]['title']=='开始站点签到 ...' and first['posts'][-1]['title']=='站点签到完成！'
assert first['event']['source']=='owned-user' and first['event']['arg_str']=='owned arg'
assert dedup['calls']==1 and len(dedup['posts'])==1 and len(empty.calls)==2
# Force same-version: source endpoint branch and exact original installer control-flow, bounded fixture IO.
install_endpoint=top('app/api/endpoints/plugin.py','install');INSTALLED=['AutoSignIn'];install_calls=[]
class SystemConfigKey:UserInstalledPlugins='installed'
class SystemConfigOper:
 def get(self,key):return list(INSTALLED)
 async def async_set(self,key,value):install_calls.append(['persist_installed',value])
class PH:
 state=True
 async def async_get_plugin_system_version_check_message(self,*args):install_calls.append(['version_check',*args]);return ''
 async def async_install(self,**kw):install_calls.append(['download',kw]);return self.state,'owned prepare failure' if not self.state else ''
PluginHelper=PH
PluginManager=lambda:SimpleNamespace(get_plugin_ids=lambda:['AutoSignIn'])
class MoviePilotServerHelper:
 @staticmethod
 async def async_install_plugin_reg(**kw):install_calls.append(['stats',kw])
def reload_plugin(pid):install_calls.append(['reload',pid])
async def run_in_threadpool(f,*args):return f(*args)
force_rows=[]
for force,repo,state in [(False,'https://github.com/owned/synthetic',True),(True,'https://github.com/owned/synthetic',True),(True,'https://github.com/owned/synthetic',False),(True,'',True)]:
 install_calls=[];PH.state=state;result=asyncio.run(install_endpoint(plugin_id='AutoSignIn',repo_url=repo,release_version='2.9.15',force=force,_=None));force_rows.append(dict(force=force,repo_present=bool(repo),prepare_success=state,result=result,calls=copy.deepcopy(install_calls)))
assert not any(c[0]=='download' for c in force_rows[0]['calls']) and force_rows[1]['calls'][0][0]=='download'
assert force_rows[1]['calls'][0][1]['force_install'] is True and force_rows[1]['calls'][-1][0]=='reload'
assert not any(c[0]=='reload' for c in force_rows[2]['calls'])
rows.append(dict(case='force-same-version-source-endpoint-control-flow',rows=force_rows))
# Library contracts from actual installed library, including default wait=True and real executor join.
refs=[]
for cls,methods in [(BaseScheduler,['shutdown']),(BackgroundScheduler,['shutdown']),(BlockingScheduler,['shutdown']),(BasePoolExecutor,['shutdown'])]:
 path=inspect.getsourcefile(cls);refs.append(dict(class_name=cls.__name__,path=path,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),methods={n:dict(signature=str(inspect.signature(getattr(cls,n))),source=inspect.getsource(getattr(cls,n))) for n in methods}))
print(json.dumps(dict(classification='immutable333 netnone synthetic source-method replay with real APScheduler/private date and public interval execution; memory store, fake registry/site results/event delivery/HTTP request/installer network boundaries; not full MP App, not target Go App',python=platform.python_version(),apscheduler=__import__('apscheduler').__version__,rows=rows,timeline=timeline,library=refs),ensure_ascii=False,indent=2))
