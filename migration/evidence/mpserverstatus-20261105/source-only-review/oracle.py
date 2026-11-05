"""Run only fixed original AST with synthetic dependency shells. No app/plugin imports."""
import ast, pathlib, json, re, socket, ssl, time, sys, hashlib, math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Tuple, Dict, Any, Optional
from urllib.parse import urlparse
from types import SimpleNamespace
ROOT=pathlib.Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]/'migration-20261105/source-snapshot/mpserverstatus/__init__.py'
source=SOURCE.read_bytes(); tree=ast.parse(source)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
class Logger:
 def __init__(self): self.calls=[]
 def info(self,x): self.calls.append(['info',x])
 def warn(self,x): self.calls.append(['warn',x])
logger=Logger()
ns=dict(re=re,socket=socket,ssl=ssl,time=time,datetime=datetime,timezone=timezone,parsedate_to_datetime=parsedate_to_datetime,List=List,Tuple=Tuple,Dict=Dict,Any=Any,Optional=Optional,urlparse=urlparse,logger=logger,_PluginBase=object)
exec(compile(ast.Module(body=[cls],type_ignores=[]),str(SOURCE),'exec'),ns)
C=ns['MPServerStatus']; results=[]; coverage=set()
def trace(frame,event,arg):
 if event=='line' and frame.f_code.co_filename==str(SOURCE): coverage.add(frame.f_lineno)
 return trace
sys.settrace(trace)
def clean(x):
 if isinstance(x,float) and not math.isfinite(x): return {'python_float':repr(x)}
 if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(tuple,list)): return [clean(v) for v in x]
 return x

def case(name,fn):
 try: out={'return':clean(fn())}
 except Exception as e: out={'raises':type(e).__name__,'message':str(e)}
 results.append({'name':name,**out})

class Clock:
 def __init__(self,values): self.values=iter(values);self.calls=[]
 def time(self):
  v=next(self.values);self.calls.append(v);return v

def new(config=None):
 p=C();p.init_plugin(config);return p
class Response:
 def __init__(self,status=200,text='Active connections: 7\nserver accepts handled requests\n 10 9 20\nReading: 1 Writing: 2 Waiting: 4',content=None,headers=None,version=11):
  self.status_code=status;self.text=text;self.content=text.encode() if content is None else content;self.headers=headers or {};self.raw=SimpleNamespace(version=version)
 def __bool__(self): return self.status_code<400

for v in [None,{},False,0,1,'false','',[],[0],{'x':0}]:
 case('config-enable-'+repr(v),lambda v=v: (lambda p:[p.get_state(),p.get_form(),p.get_command(),p.get_api()])(new({'enable':v})))
def reset_stop():
 p=new({'enable':True});p._last_sample={'requests':1};p._dns_cache=(1,{'a':2});p._tls_cache=(1,{'b':3});p.stop_service();a=[p._last_sample,p._dns_cache,p._tls_cache];p.init_plugin(None);return {'after_stop':a,'after_init':[p.get_state(),p._last_sample,p._dns_cache,p._tls_cache]}
case('stop-is-noop-init-clears',reset_stop)

def request_case(kind):
 p=new(); logger.calls=[]; calls=[]; clock=Clock([10,10.125]); ns['time']=clock
 class R:
  def __init__(self,**kwargs):
   self.kwargs=kwargs;calls.append(['ctor',kwargs])
   if kind=='ctor-typeerror' and kwargs: raise TypeError('timeout unsupported')
  def get_res(self,url):
   calls.append(['GET',url,self.kwargs])
   if kind=='get-typeerror' and self.kwargs: raise TypeError('inside GET')
   if kind=='get-typeerror-both': raise TypeError('again')
   if kind=='get-error': raise RuntimeError('synthetic-error')
   if kind=='none':return None
   return Response(status=404 if kind=='404' else 200)
 ns['RequestUtils']=R
 out=p._request_server_status();return {'response':None if out[0] is None else {'status':out[0].status_code,'truth':bool(out[0])},'seconds':out[1],'error':out[2],'calls':calls,'clock':clock.calls,'log':logger.calls}
for kind in ['normal','ctor-typeerror','get-typeerror','get-typeerror-both','get-error','none','404']: case('request-'+kind,lambda kind=kind:request_case(kind))

raw_good=Response().text
for name,s in [
 ('normal',raw_good),('Unicode-Nd','Active connections: ٧\nserver accepts handled requests\n١٠ ٩ ٢٠\nReading: ١ Writing: ٢ Waiting: ٤'),
 ('mixed-case','ACTIVE CONNECTIONS: 7\nSERVER ACCEPTS HANDLED REQUESTS\n10 9 20 99\nreading: 1 writing: 2 waiting: 4'),
 ('fallback','x 1 x 2 x 3\nActive connections: 7\nReading:1 Writing:2 Waiting:4'),
 ('fallback-lowercase-rww-first','reading: 1 writing: 2 waiting: 4\nActive connections: 7'),
 ('uppercase-rww-only','READING: 1 WRITING: 2 WAITING: 4\nActive connections: 7'),
 ('uppercase-Reading-excluded','Reading: 1 Writing: 2 Waiting: 4\nActive connections: 7'),
 ('first-header-invalid-next-later-good','server accepts\nnope\nserver accepts\n4 5 6 7\nActive connections:1\nReading:1 Writing:0 Waiting:0'),
 ('zero','Active connections:0\n0 0 0\nReading:0 Writing:0 Waiting:0'),('missing-all',''),
 ('missing-counters','Active connections:1'),('missing-rww','Active connections:1\n1 2 3'),
 ('vertical-separators','\u001cActive connections: 7\u001dserver accepts\u001e10 9 20\u001fReading:1 Writing:2 Waiting:4'),
 ('superscript','Active connections: ²\n1 2 3\nReading:1 Writing:2 Waiting:4'),
 ('huge','Active connections: '+str(10**100)+'\n1 2 3\nReading:1 Writing:2 Waiting:4'),
 ]: case('parse-'+name,lambda s=s:C._parse_status_text(s))

base=C._parse_status_text(raw_good)
def sample(seq):
 p=new();ns['time']=Clock([x[0] for x in seq]); out=[]
 for _,status in seq:out.append(p._build_metrics(status,0.2))
 return {'metrics':out,'last':p._last_sample}
case('sample-increase-decrease-equal-backwards',lambda:sample([(100,base),(102,{**base,'accepts':14,'handled':10,'requests':30}),(104,{**base,'accepts':13,'handled':10,'requests':25}),(104,base),(103,base),(105,base)]))
case('sample-over100percent',lambda:sample([(1,{**base,'active_connections':1,'accepts':1,'handled':4})]))
case('sample-allzero',lambda:sample([(1,{k:0 for k in base})]))
case('sample-huge-division',lambda:sample([(1,{**base,'reading':10**400})]))

def snapshot(kind,detail=True,enabled=True):
 p=new({'enable':enabled});p._last_sample={'timestamp':0,'accepts':1,'handled':1,'requests':1}; calls=[];ns['time']=Clock([10])
 resp=Response(status=100 if kind=='100' else 399 if kind=='399' else 400 if kind in ['400','page-unavailable','dashboard-unavailable'] else 200,text='broken' if kind=='parse-error' else raw_good)
 p._request_server_status=lambda:(calls.append('HTTP') or (None if kind in ['none','request-error'] else resp,0.25,'error' if kind=='request-error' else None))
 original=p._build_http_probe
 p._build_http_probe=lambda **kw:(calls.append('probe') or original(**kw))
 p._get_dns_info=lambda:(calls.append('DNS') or {'host':'owned','port':443,'ips':['127.0.0.1'],'seconds':0.1,'error':''})
 p._get_tls_info=lambda:(calls.append('TLS') or {'enabled':True,'days_left':40,'error':'','expires_at':'owned'})
 logger.calls=[]
 if kind=='disabled-page':out=p.get_page()
 elif kind=='disabled-dashboard':out=p.get_dashboard()
 elif kind in ['page','page-unavailable']:out=p.get_page()
 elif kind in ['dashboard','dashboard-unavailable']:out=p.get_dashboard()
 else:out=p._load_status_snapshot(detail)
 return {'out':out,'calls':calls,'last':p._last_sample,'log':logger.calls}
for kind in ['normal','100','399','400','none','request-error','parse-error','page','dashboard','page-unavailable','dashboard-unavailable','disabled-page','disabled-dashboard']:
 case('snapshot-'+kind,lambda kind=kind:snapshot(kind,enabled=not kind.startswith('disabled')))
case('snapshot-normal-no-detail',lambda:snapshot('normal',detail=False))

for name,response,error in [('normal',Response(headers={'Server':'owned','Date':'Fri, 01 Nov 2024 12:34:56 +0200','Content-Type':'text/plain'}),None),('utf8fallback',Response(text='猫',content=b''),None),('none',None,'failure'),('ok-and-error',Response(), 'failure')]:
 case('probe-'+name,lambda response=response,error=error:new()._build_http_probe(response,.1,error))

class SocketFake:
 SOCK_STREAM=socket.SOCK_STREAM
 def __init__(self,fail=False):self.calls=[];self.fail=fail
 def getaddrinfo(self,*a,**kw):
  self.calls.append([list(a),kw])
  if self.fail:raise OSError('synthetic DNS failed')
  return [(0,0,0,'',('2a00::1',0)),(0,0,0,'',('127.0.0.1',0)),(0,0,0,'',('2a00::1',0)),(0,0,0,'',('127.0.0.2',0))]
def dns_case(fail=False):
 p=new();s=SocketFake(fail);ns['socket']=s;ns['time']=Clock([100,100,101,159,160,160,162]); a=p._get_dns_info();b=p._get_dns_info();c=p._get_dns_info();return {'results':[a,b,c],'same':[a is b,b is c],'calls':s.calls,'cache':p._dns_cache}
case('dns-success-cache-expiry',lambda:dns_case(False));case('dns-failure-cache-expiry',lambda:dns_case(True))

def tls_case(notafter='Nov 15 00:00:00 2026 GMT',fail=None,scheme='https'):
 p=new();p._server_base=scheme+'://owned.invalid/status';calls=[];ns['time']=Clock([100,100,101,3699,3700,3700,3701])
 class D(datetime):
  @classmethod
  def now(cls,tz=None):return cls(2026,11,5,12,tzinfo=timezone.utc)
 ns['datetime']=D
 class Sock:
  def __enter__(self):calls.append('enter-socket');return self
  def __exit__(self,*a):calls.append(['exit-socket',None if a[0] is None else a[0].__name__])
 class TLS(Sock):
  def getpeercert(self):
   if fail=='cert':raise ValueError('synthetic cert')
   return {'notAfter':notafter,'issuer':((('organizationName','Org'),),(('commonName','Issuer'),)),'subject':((('commonName','Subject'),),)}
  def version(self):return 'TLSv1.3'
 class Context:
  def wrap_socket(self,sock,server_hostname):calls.append(['wrap',server_hostname]);return TLS()
 def connect(address,timeout):
  calls.append(['connect',list(address),timeout])
  if fail=='connect':raise OSError('synthetic connect')
  return Sock()
 ns['socket']=SimpleNamespace(create_connection=connect);ns['ssl']=SimpleNamespace(create_default_context=lambda:(calls.append('default-context') or Context()))
 a=p._get_tls_info()
 if scheme!='https':return {'result':a,'calls':calls,'cache':p._tls_cache}
 b=p._get_tls_info();c=p._get_tls_info();return {'results':[a,b,c],'same':[a is b,b is c],'calls':calls,'cache':p._tls_cache}
for name,kw in [('normal',{}),('expiredfraction',{'notafter':'Nov 05 11:59:59 2026 GMT'}),('bad-date',{'notafter':'invalid'}),('connect-error',{'fail':'connect'}),('cert-error',{'fail':'cert'}),('http',{'scheme':'http'})]:case('tls-'+name,lambda kw=kw:tls_case(**kw))
for v in [None,(),((('organizationName','Org'),),),((('commonName',''),('commonName','late')),),((('x',''),('y','fallback')),),((('CN','x'),),)]:case('certificate-name-'+repr(v),lambda v=v:C._extract_certificate_name(v))

for v in [None,-.0,-.0005,.0005,.9995,1,2.5,3,float('inf'),float('-inf'),float('nan')]:
 for fn in ['_format_integer','_format_float','_format_percent','_format_seconds','_format_sample_caption']:
  case('format-'+fn+'-'+repr(v),lambda fn=fn,v=v:getattr(C,fn)(v))
for v in [None,-1,0,0.125,1]:case('rate-'+repr(v),lambda v=v:C._format_rate(v,'x/s'))
for v in [-1,0,1023,1024,1024**2-1,1024**2,1024**3]:case('size-'+str(v),lambda v=v:C._format_size(v))
for v in [10,11,20,9,None,'11',True]:case('protocol-'+repr(v),lambda v=v:C._format_http_version(v))
for v in [None,'','bad-date','Fri, 01 Nov 2024 12:34:56 GMT','Fri, 01 Nov 2024 12:34:56 -0000','Fri, 01 Nov 2024 12:34:56 +0200']:
 case('date-'+repr(v),lambda v=v:C._format_response_date(v))
for ips,err in [([],None),(['a'],None),(['a','b','c','d'],None),(['a'],'failed')]:case('ips-'+repr((ips,err)),lambda ips=ips,err=err:C._format_ips(ips,err))
for value in [-1,0,1,7,10,30]:
 case('severity-asc-'+str(value),lambda value=value:C._severity_color(value,1,10));case('severity-desc-'+str(value),lambda value=value:C._severity_color(value,1,0))
for value in [None,0,1,2.99,3]:
 for ok in [False,True]:case('latency-'+repr((value,ok)),lambda value=value,ok=ok:C._latency_color(value,ok))
for info in [{},{'enabled':False,'error':'x','days_left':0},{'enabled':True,'error':'x','days_left':40}]+[{'enabled':True,'days_left':v} for v in [None,-1,0,6,7,29,30]]:
 case('tls-display-'+repr(info),lambda info=info:[C._format_tls_days(info),C._tls_color(info)])
case('card-sm-zero-and-empty-subtitle',lambda:C._build_stat_card('label','value','icon','color',sm=0))
case('info-table-empty',lambda:C._build_info_table('title',[],12))

def inflight_reinit():
 p=new({'enable':True});p._last_sample={'timestamp':0,'accepts':1,'handled':1,'requests':1};p._dns_cache=(1,{'old':True});p._tls_cache=(1,{'old':True});calls=[];ns['time']=Clock([20])
 def req():
  calls.append(['old-enable',p.get_state()]);p.init_plugin({'enable':False});calls.append(['after-reinit',p.get_state()]);return Response(),.2,None
 p._request_server_status=req
 p._get_dns_info=lambda:(calls.append('DNS') or {'host':'owned','port':443,'ips':[]})
 p._get_tls_info=lambda:(calls.append('TLS') or {'enabled':False})
 out=p.get_page();return {'out':out,'calls':calls,'enable':p.get_state(),'last':p._last_sample}
case('inflight-page-reinit-no-cancel-and-refill',inflight_reinit)
sys.settrace(None)
methods=[{'name':n.name,'lines':[n.lineno,n.end_lineno],'executed_lines':sorted(coverage.intersection(range(n.lineno,n.end_lineno+1)))} for n in cls.body if isinstance(n,ast.FunctionDef)]
output={'classification':'fixed original plugin AST in synthetic shells; local Python3.14.4 stdlib; no app import/live state/external network; not target output','source_sha256':hashlib.sha256(source).hexdigest(),'runtime':sys.version,'cases':results,'coverage':methods}
(ROOT/'oracle.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'cases':len(results),'raises':len([r for r in results if 'raises'in r]),'methods_executed':len([m for m in methods if m['executed_lines']]),'methods_total':len(methods),'oracle_sha256':hashlib.sha256((ROOT/'oracle.json').read_bytes()).hexdigest()}))
