"""Execute actual installed uninstall/stop AST against owned recorders only."""
from pathlib import Path
import ast,copy,hashlib,json,sys,typing,__future__
from types import SimpleNamespace
R=Path(__file__).resolve().parent;W=R.parent.parent
API=R.parent/'tt-install-source/app/api/endpoints/plugin.py'
CORE=W/'migration-20261105/host-reference/app/core/plugin.py'
trace=[]
def emit(op,**kw):trace.append({'op':op,**kw})
class Logger:
 def __getattr__(self,level):return lambda message:emit('log',level=level,message=message)
class Config:
 values={}
 def get(self,key):emit('config.get',key=key);return self.values.get(key)
 def set(self,key,value):emit('config.set',key=key,value=copy.deepcopy(value));self.values[key]=value;return True
 def delete(self,key):emit('config.delete',key=key);return self.values.pop(key,None) is not None
class Data:
 values={}
 def del_data(self,pid):emit('data.delete',pid=pid);self.values.pop(pid,None)
class OwnedPath:
 def __init__(self,text):self.text=text
 def __truediv__(self,child):return OwnedPath(self.text+'/'+child)
 def __str__(self):return self.text
 def exists(self):emit('path.exists',path=self.text,result=path_exists);assert self.text==expected_path;return path_exists
class Response:
 def __init__(self,**kw):self.fields=kw
class Running:
 def close(self):emit('plugin.close',pid=pid)
 def stop_service(self):emit('plugin.stop_service',pid=pid)
 def get_name(self):return pid
class Popping(dict):
 def pop(self,key,*args):emit('map.pop',map=self.label,key=key);return super().pop(key,*args)
class Routes(list):
 def remove(self,route):emit('route.remove',path=route.path);super().remove(route)
ns={**vars(typing),'__name__':'owned_uninstall_ast','logger':Logger(),'SystemConfigOper':Config,'PluginDataOper':Data,'SystemConfigKey':SimpleNamespace(UserInstalledPlugins='installed',PluginFolders='folders'),'settings':SimpleNamespace(ROOT_PATH=OwnedPath('/owned-root')),'Depends':lambda f:None,'get_current_active_superuser':lambda:None,'schemas':SimpleNamespace(Response=Response),'sys':SimpleNamespace(modules={}), 'importlib':SimpleNamespace(invalidate_caches=lambda:emit('module.invalidate_caches')),'eventmanager':SimpleNamespace(disable_event_handler=lambda typ:emit('event.disable',class_name=typ.__name__)),'PLUGIN_PREFIX':'/api/v1/plugin','PLUGIN_V2_PREFIX':'/api/v2/plugin','PROTECTED_ROUTES':[]}
core=next(n for n in ast.parse(CORE.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='PluginManager')
names={'plugins','stop','__stop_plugin','remove_plugin','delete_plugin_config','delete_plugin_data','_clear_plugin_modules'}
cls=ast.ClassDef(name='PluginManager',bases=[],keywords=[],decorator_list=[],body=[copy.deepcopy(n) for n in core.body if isinstance(n,ast.FunctionDef) and n.name in names]);ast.fix_missing_locations(cls)
exec(compile(ast.Module(body=[cls],type_ignores=[]),str(CORE),'exec',flags=__future__.annotations.compiler_flag),ns);Manager=ns['PluginManager']
api=ast.parse(API.read_text());names={'uninstall_plugin','_remove_plugin_from_folders','remove_plugin_api','_update_plugin_api_routes','_remove_routes','_clean_protected_routes'}
for node in [copy.deepcopy(n) for n in api.body if isinstance(n,ast.FunctionDef) and n.name in names]:
 node.decorator_list=[];exec(compile(ast.Module(body=[node],type_ignores=[]),str(API),'exec',flags=__future__.annotations.compiler_flag),ns)
rows=[]
for label,is_clone,path_exists,fail_remove in [('base',False,True,False),('clone',True,True,False),('clone-directory-absent',True,False,False),('clone-rmtree-error',True,True,True)]:
 trace.clear();pid='TorrentTransfermusic' if is_clone else 'TorrentTransfer';other='TorrentTransfer' if is_clone else 'TorrentTransfermusic';expected_path='/owned-root/app/plugins/'+pid.lower()
 Config.values={'installed':['Other',pid,other], 'plugin.'+pid:{'enabled':True,'owned':'keep-or-delete'},'plugin.'+other:{'owned':'unrelated'},'folders':{'new':{'plugins':[pid,other],'order':7,'icon':'owned'},'old':[other,pid],'unrelated':['Other']}}
 Data.values={pid:{'history':list(range(106))},other:{'history':['unrelated']}}
 manager=Manager();manager._config_key='plugin.%s';manager._plugins=Popping({pid:type('OwnedClass',(),{'is_clone':is_clone}),other:type('OtherClass',(),{})});manager._plugins.label='classes';manager._running_plugins=Popping({pid:Running()});manager._running_plugins.label='running';manager.clear_plugin_agent_tools_cache=lambda:emit('agent_tool_cache.clear')
 ns['PluginManager']=lambda:manager
 ns['Scheduler']=lambda:SimpleNamespace(remove_plugin_job=lambda ident:emit('scheduler.remove',pid=ident))
 def rmtree(path):
  emit('rmtree',path=str(path));assert str(path)==expected_path
  if fail_remove:raise OSError('owned rmtree failure')
 ns['shutil']=SimpleNamespace(rmtree=rmtree)
 module_prefix='app.plugins.'+pid.lower();ns['sys'].modules={module_prefix:object(),module_prefix+'.child':object(),module_prefix+'other':object(),'unrelated':object()}
 routes=Routes(SimpleNamespace(path=p) for p in [f'/api/v1/plugin/{pid}/refresh',f'/api/v2/plugin/{pid}/refresh',f'/api/v1/plugin/{other}/refresh','/api/v1/system/health'])
 ns['app']=SimpleNamespace(routes=routes,openapi_schema={'owned':'cached'},setup=lambda:emit('app.setup'))
 before={'config':copy.deepcopy(Config.values),'data':copy.deepcopy(Data.values),'modules':list(ns['sys'].modules),'routes':[r.path for r in routes]}
 result=ns['uninstall_plugin'](pid)
 after={'config':copy.deepcopy(Config.values),'data':copy.deepcopy(Data.values),'class_ids':list(manager.plugins),'running_ids':list(manager._running_plugins),'modules':list(ns['sys'].modules),'routes':[r.path for r in routes]}
 row={'case':label,'plugin_id':pid,'is_clone':is_clone,'path_exists':path_exists,'rmtree_error':fail_remove,'response':result.fields,'before':before,'trace':copy.deepcopy(trace),'after':after};rows.append(row)
 assert result.fields=={'success':True}
 assert ('plugin.'+pid in after['config']) is not is_clone
 assert (pid in after['data']) is not is_clone
 assert after['data'].get(pid,{}).get('history',[])==([] if is_clone else list(range(106)))
 assert not any(x['op'] in ('config.delete','data.delete','path.exists','rmtree') for x in trace) if not is_clone else True
 assert all(not x.startswith(module_prefix+'.') and x!=module_prefix for x in after['modules'])
 assert module_prefix+'other' in after['modules']
 assert len([x for x in trace if x['op']=='rmtree'])==(1 if is_clone and path_exists else 0)
 assert other in after['data'] and 'plugin.'+other in after['config']
 ops=[x['op'] for x in trace];assert ops.index('config.set')<ops.index('route.remove')<ops.index('scheduler.remove')<ops.index('plugin.close')<ops.index('plugin.stop_service')
 if is_clone:assert ops.index('scheduler.remove')<ops.index('config.delete')<ops.index('data.delete')<ops.index('path.exists')<ops.index('plugin.close')
result={'classification':'actual installed API uninstall/folders/routes and PluginManager delete/stop/remove/module-cache AST with inert owned DB/filesystem/API/scheduler/event recorders; no source app imports or real deletions','python':sys.version,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (API,CORE)},'cases':rows,'limitations':['Local Python3.14 versus installed3.12.13; ordinary list/dict/getattr/branch semantics only','Scheduler job removal, event handler disable, plugin close/stop and cache reset represented by bounded recorders','No real application uninstall/reinstall or persistent DB/filesystem execution; independent oracle for main driver expectations']}
(R/'uninstall-source-oracle.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':len(rows),'base_history_retained':106,'base_config_and_code_retained':True,'clone_data_config_deleted':True,'clone_file_scope': '/owned-root/app/plugins/torrenttransfermusic','failure_still_success':True}))
