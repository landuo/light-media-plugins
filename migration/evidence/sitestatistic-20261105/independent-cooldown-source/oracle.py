"""Actual collector/request AST, owned parser extraction/HTTP responses only."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
from urllib.parse import urlsplit,urljoin
from abc import ABCMeta
import ast,copy,typing,json,hashlib,sys,__future__
R=Path(__file__).resolve().parent;trace=[];mode='logged-out'
class Logger:
 def __getattr__(self,name):return lambda text:trace.append({'op':'log','level':name,'text':text})
class DTO:
 def __init__(self,**values):self.values=copy.deepcopy(values)
 def model_dump(self):return copy.deepcopy(self.values)
class Parent:pass
class RequestError(Exception):pass
def request(method,url,**kw):
 trace.append({'op':'http','method':method,'url':url,'mode':mode})
 return SimpleNamespace(status_code=200,text='logout.php owned' if mode=='normal' else 'owned login page')
ns={**vars(typing),'__name__':'owned_cooldown_source','datetime':datetime,'logger':Logger(),'urlsplit':urlsplit,'urljoin':urljoin,'ABCMeta':ABCMeta,'_ModuleBase':Parent,'SiteUserData':DTO,'SiteParserBase':Parent,'settings':SimpleNamespace(SITE_MESSAGE=False,PROXY=None,ENCODING_DETECTION_PERFORMANCE_MODE=False,ENCODING_DETECTION_MIN_CONFIDENCE=0.8),'requests':SimpleNamespace(request=request,exceptions=SimpleNamespace(RequestException=RequestError,ConnectionError=RequestError,ChunkedEncodingError=RequestError,ReadTimeout=RequestError)),'cookie_parse':lambda _: {'owned':'synthetic'},'under_challenge':lambda _:False,'SiteUtils':SimpleNamespace(is_logged_in=lambda text:'logout.php' in text),'StringUtils':SimpleNamespace(get_url_domain=lambda url:urlsplit(url).netloc)}
def source_class(file,name,methods,bases=None):
 node=copy.deepcopy(next(x for x in ast.parse((R/file).read_text()).body if isinstance(x,ast.ClassDef) and x.name==name));node.decorator_list=[];node.body=[x for x in node.body if isinstance(x,ast.FunctionDef) and x.name in methods or name=='SiteParserBase' and isinstance(x,(ast.Assign,ast.AnnAssign))]
 if bases is not None:node.bases=[ast.Name(id=x,ctx=ast.Load()) for x in bases];node.keywords=[]
 exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(R/file),'exec',flags=__future__.annotations.compiler_flag),ns);return ns[name]
Req=source_class('app/utils/http.py','RequestUtils',{'__init__','request','get_res'},[]);Req.get_decoded_html_content=staticmethod(lambda response,*_:response.text)
Base=source_class('app/modules/indexer/parser/__init__.py','SiteParserBase',{'__init__','parse','_get_page_content','_parse_logged_in','close','clear'},[])
class OwnedParser(Base):
 schema=SimpleNamespace(value='NexusPhp')
 def __init__(self,**kw):
  super().__init__(**kw);self._user_basic_page='';self._user_detail_page='';self._user_traffic_page=''
 def _parse_site_page(self,_):self.upload=8589934592;self.download=2147483648;self.ratio=4.0;self.userid='7';self.username='Owned'
 def _parse_user_base_info(self,_):pass
 def _parse_seeding_pages(self):pass
Module=source_class('app/modules/indexer/__init__.py','IndexerModule',{'refresh_userdata'},['_ModuleBase']);m=Module();m._site_schemas=[OwnedParser];site={'name':'Owned','schema':'NexusPhp','domain':'https://owned.invalid/','url':'https://owned.invalid/','cookie':'owned-synthetic-cookie','ua':'owned-UA','proxy':False};cases=[]
for mode in ['logged-out','normal','normal']:
 before=len([x for x in trace if x['op']=='http']);data=m.refresh_userdata(site);after=len([x for x in trace if x['op']=='http']);cases.append({'mode':mode,'http_delta':after-before,'dto':data.model_dump()})
assert [x['http_delta'] for x in cases]==[1,1,1];assert cases[0]['dto']['err_msg']=='未检测到已登陆，请检查cookies是否过期' and cases[1]['dto']['err_msg'] is None and cases[1]['dto']['upload']==8589934592
result={'classification':'actual installed IndexerModule.refresh_userdata + SiteParserBase constructor/parse/request/login/close/clear + RequestUtils constructor/get_res/request AST; owned response/parser extraction and DTO boundaries, no app imports/network','python':sys.version,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((R/'app').rglob('*.py'))},'cases':cases,'trace':trace,'limits':['Local3.14 AST observation; source files are exact installed3.12-image static captures','Synthetic parser extraction and login/decode/DTO boundaries; not actual NexusHTML or live tracker','Proves repeated collector/request calls do not invent persistent authentication cooldown; generic runtime request budgets remain target adaptation']};(R/'oracle.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'http_deltas':[x['http_delta'] for x in cases],'logged_out_then_normal_succeeds':True}))
