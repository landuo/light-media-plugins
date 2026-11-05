"""Actual installed guard AST only, synthetic index/receivers; no imports/IO."""
from pathlib import Path
import ast,asyncio,copy,json,sys,typing,hashlib
from types import SimpleNamespace
R=Path(__file__).resolve().parent;helper=R/'app/helper/plugin.py';api=R/'app/api/endpoints/plugin.py';trace=[]
raw=ast.parse(helper.read_text());src=next(n for n in raw.body if isinstance(n,ast.ClassDef) and n.name=='PluginHelper')
names={'is_local_repo_url','get_repo_info','get_plugin_package_version','async_get_plugin_package_version','async_install','async_get_plugin_system_version_check_message'};selected=[copy.deepcopy(n) for n in src.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
node=ast.ClassDef(name='PluginHelper',bases=[],keywords=[],decorator_list=[],body=selected);ast.fix_missing_locations(node)
index={'TorrentTransfer':{'version':'1.10.3','v2':True}}
class Logger:
 def __getattr__(self,name):return lambda message:trace.append({'op':'log','level':name,'message':message})
ns={**vars(typing),'__name__':'owned_install_ast','settings':SimpleNamespace(VERSION_FLAG='v2'),'SystemUtils':SimpleNamespace(is_frozen=lambda:False),'logger':Logger(),'LOCAL_REPO_PREFIX':'local://','asyncio':asyncio}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(helper),'exec',flags=__import__('__future__').annotations.compiler_flag),ns);Helper=ns['PluginHelper']
def get_plugins(self,repo,version=None):trace.append({'op':'index','repo':repo,'package_version':version});return copy.deepcopy(index)
async def aget(self,repo,version=None):return get_plugins(self,repo,version)
Helper.get_plugins=get_plugins;Helper.async_get_plugins=aget
class Response:
 def __init__(self,**kw):self.fields=kw
class Manager:
 def get_plugin_ids(self):return ['TorrentTransfer','TorrentTransfermusic']
class Config:
 def get(self,key):return ['TorrentTransfer','TorrentTransfermusic']
 async def async_set(self,*args):trace.append({'op':'unexpected_config_write'});raise AssertionError('no install/config write allowed')
async def install_statistics(**kw):trace.append({'op':'statistics','plugin_id':kw['plugin_id']})
def reload(pid):trace.append({'op':'reload','plugin_id':pid})
async def run_thread(fn,*args):return fn(*args)
ns.update(PluginManager=Manager,SystemConfigOper=Config,SystemConfigKey=SimpleNamespace(UserInstalledPlugins='installed'),MoviePilotServerHelper=SimpleNamespace(async_install_plugin_reg=install_statistics),schemas=SimpleNamespace(Response=Response),run_in_threadpool=run_thread,reload_plugin=reload,Depends=lambda f:None,get_current_active_superuser_async=lambda:None)
api_node=copy.deepcopy(next(n for n in ast.parse(api.read_text()).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='install'));api_node.decorator_list=[];exec(compile(ast.Module(body=[api_node],type_ignores=[]),str(api),'exec',flags=__import__('__future__').annotations.compiler_flag),ns)
repo='https://github.com/owned/repo/'
async def main():
 rows=[]
 for pid in ['TorrentTransfer','TorrentTransfermusic']:
  trace.clear();result=await Helper().async_get_plugin_package_version(pid,repo);rows.append({'case':'package-version-'+pid,'result':result,'trace':copy.deepcopy(trace)})
 trace.clear();result=await Helper().async_install('TorrentTransfermusic',repo,force_install=True);rows.append({'case':'force-helper-clone-against-parent-only-index','result':result,'trace':copy.deepcopy(trace)})
 for force in [True,False]:
  trace.clear();response=await ns['install']('TorrentTransfermusic',repo_url=repo,force=force);rows.append({'case':'API-existing-clone-force-'+str(force),'response':response.fields,'trace':copy.deepcopy(trace)})
 assert rows[0]['result']=='v2' and rows[1]['result'] is None
 assert rows[2]['result']==(False,'TorrentTransfermusic 没有找到适用于当前版本的插件')
 assert rows[3]['response']['success'] is False and rows[4]['response']['success'] is True
 assert not any(x['op'] in ['statistics','reload'] for x in rows[3]['trace'])
 result={'classification':'actual installed async helper/version/API guard AST with owned parent-only index and inert stats/reload/DB; no real install/network/application imports','python':sys.version,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [helper,api]},'exact_index':index,'cases':rows,'limitations':['Source guard semantics only, Linux nonfrozen branch fixed','Not a real source install, no filesystem/pip/github calls','LocalPython3.14 versus installed3.12.13; ordinary exact dictionary membership and API branching executed']}
 (R/'install-identity-source-oracle.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':len(rows),'forced_missing_clone_rejected':True,'nonforce_existing_clone_skips_install':True}))
asyncio.run(main())
