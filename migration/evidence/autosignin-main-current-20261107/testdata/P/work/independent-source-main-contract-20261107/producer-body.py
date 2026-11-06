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
logger=logging.getLogger('source-probe'); logger.addHandler(logging.StreamHandler())
START=time.monotonic(); rows=[]; timeline=[]
import atexit,sys
atexit.register(lambda: print('PARTIAL='+json.dumps(dict(rows=rows,timeline=timeline),ensure_ascii=False),file=sys.stderr) if sys.exc_info()[0] else None)
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
import struct
class Recorder:
 def __init__(self):self.logs=[]
 def __getattr__(self,level):return lambda message,*a,**kw:self.logs.append([level,str(message)])
logger=Recorder()
inputs=['0',0,0.0,False,True,None,'',' 0.0000001 ','-1','NaN','+Inf','-Infinity','1e16','bad','1_0','１２.５','1,5','0/9-23','0/0-23','0/23-9']
for raw in inputs:
 logger.logs=[];a=plugin('producer');init(a,cfg());a._cron=raw;random_calls=[];a._get_random_schedule=lambda:(random_calls.append(True) or [])
 services=a.get_service();out=[];ctor=[]
 s=BackgroundScheduler(timezone='Asia/Shanghai')
 for d in services:
  out.append(dict(id=d['id'],trigger=str(d['trigger']),hours_repr=repr(d['kwargs'].get('hours')),float64_big_endian=struct.pack('>d',d['kwargs']['hours']).hex() if 'hours' in d['kwargs'] else None,kwargs_keys=list(d['kwargs'])))
  try:
   j=s.add_job(lambda:None,d['trigger'],**d['kwargs']);tr=j.trigger;ctor.append(dict(ok=True,interval_us=str((tr.interval.days*86400+tr.interval.seconds)*1000000+tr.interval.microseconds),start=tr.start_date.isoformat(),timezone=str(tr.timezone),timezone_class=type(tr.timezone).__name__,same_timezone_object=tr.timezone is s.timezone,start_same_timezone_object=tr.start_date.tzinfo is tr.timezone))
  except Exception as e:ctor.append(dict(ok=False,type=type(e).__name__,message=str(e)))
 rows.append(dict(input_type=type(raw).__name__,input_repr=repr(raw),services=out,random_schedule_calls=len(random_calls),start_hour=a._start_time,end_hour=a._end_time,logs=logger.logs,real_APS_pending_constructor=ctor))
print(json.dumps(dict(classification='immutable333 source producer get_service actual method and actual APS pending interval constructor; controlled random branch marker (not random schedule oracle), no scheduler start/App/config/DB/network',rows=rows),ensure_ascii=False,indent=2))
