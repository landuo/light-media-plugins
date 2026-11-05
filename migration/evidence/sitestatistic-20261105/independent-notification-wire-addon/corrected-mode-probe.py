"""Installed send_msg AST plus owned mode-read stream; no application import."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
import ast,bisect,copy,hashlib,json,math,re,sys,threading,typing,__future__
R=Path(__file__).resolve().parent;P=R.parent.parent/'migration-20261105/source-snapshot/sitestatistic/__init__.py';S=R.parent.parent/'migration-20261105/host-reference/app/utils/string.py'
trace=[];store={};notices=[]
class Base:
 def get_data(self,key):trace.append({'op':'get_data','key':key});return copy.deepcopy(store.get(key))
 def save_data(self,key,value):trace.append({'op':'save_data','key':key,'value':copy.deepcopy(value)});store[key]=copy.deepcopy(value)
 def post_message(self,**value):trace.append({'op':'post','value':copy.deepcopy(value)});notices.append(value)
class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return cls(2026,10,16,12,34,56)
class Logger:
 def __getattr__(self,level):return lambda text:trace.append({'op':'log','level':level,'text':text})
import enum
TYPES=R.parent.parent/'migration-20261105/sitestatistic-runtime/actual-notification-types.py'
type_node=next(n for n in ast.parse(TYPES.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='NotificationType');type_ns={'Enum':enum.Enum};exec(compile(ast.Module(body=[type_node],type_ignores=[]),str(TYPES),'exec'),type_ns)
site_message=type_ns['NotificationType'].SiteMessage.value
assert site_message=='站点'
ns={**vars(typing),'__name__':'owned_mode_source','_PluginBase':Base,'datetime':Clock,'logger':Logger(),'math':math,'hashlib':hashlib,'re':re,'bisect':bisect,'lock':threading.Lock(),'eventmanager':SimpleNamespace(register=lambda _:lambda f:f),'EventType':SimpleNamespace(SiteRefreshed='site.refreshed'),'NotificationType':SimpleNamespace(SiteMessage=site_message)}
node=copy.deepcopy(next(n for n in ast.parse(S.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='StringUtils'));node.body=[n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='str_filesize'];exec(compile(ast.Module(body=[node],type_ignores=[]),str(S),'exec',flags=__future__.annotations.compiler_flag),ns)
node=copy.deepcopy(next(n for n in ast.parse(P.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='SiteStatistic'));exec(compile(ast.Module(body=[node],type_ignores=[]),str(P),'exec',flags=__future__.annotations.compiler_flag),ns);Plugin=ns['SiteStatistic']
def row(name,up,down,day):return {'name':name,'upload':up,'download':down,'updated_day':day,'err_msg':''}
current=[row('A',200.0,100.0,'2026-10-16'),row('B',80.0,40.0,'2026-10-16')];previous=[row('A',100.0,60.0,'2026-10-15'),row('B',10.0,20.0,'2026-10-15')]
Plugin._SiteStatistic__get_data=staticmethod(lambda:('2026-10-16',[SimpleNamespace(**r) for r in current],[SimpleNamespace(**r) for r in previous]))
class Dynamic(Plugin):
 def __getattribute__(self,key):
  if key=='_notify_type':
   reads=object.__getattribute__(self,'reads');stream=object.__getattribute__(self,'stream');value=stream[min(len(reads),len(stream)-1)];reads.append({'line':sys._getframe(1).f_lineno,'value':value});return value
  return super().__getattribute__(key)
rows=[]
for name,stream in [('first-inc-second-total',['inc']*5+['total']),('first-total-second-inc',['total']*5+['inc'])]:
 trace.clear();store.clear();notices.clear();p=Dynamic();p.reads=[];p.stream=stream;p.send_msg(SimpleNamespace(event_data={'site_id':'*'}))
 assert len(p.reads)==11 and len(notices)==1 and len([x for x in trace if x['op']=='save_data'])==1
 rows.append({'case':name,'mode_stream':stream,'mode_reads':p.reads,'day':'2026-10-16','current':current,'previous':previous,'trace':copy.deepcopy(trace),'notices':copy.deepcopy(notices),'last_notify':copy.deepcopy(store['last_notify'])})
assert '总上传：180.0B' in rows[0]['notices'][0]['text'] and '总上传：270.0B' in rows[1]['notices'][0]['text']
result={'classification':'actual installed send_msg/approximation/traffic/fingerprint/format and actual StringUtils.str_filesize AST; get_data returns owned selected rows, config mode attribute returns an explicit ordered stream','python':sys.version,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (P,S,TYPES)},'cases':rows,'limits':['Local Python3.14 versus installed3.12.13; no float-sensitive sum or Unicode cases here','Attribute read stream deterministically models concurrent init between existing source reads, not a production scheduler test','Source data provider, data storage, logger and post are owned recorders; no source application imports, real notifications or DB']}
(R/'oracle.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':len(rows),'mode_read_lines':[[x['line'] for x in r['mode_reads']] for r in rows],'totals':[r['notices'][0]['text'].splitlines()[1] for r in rows]}))
