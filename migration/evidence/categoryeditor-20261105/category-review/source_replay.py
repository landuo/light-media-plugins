#!/usr/bin/env python3
"""Execute the exact installed CategoryEditor with standard-library synthetic dependencies.
No production imports, services, settings, configuration or credentials are used.
The helper is deliberately a recorder: YAML/cache acceptance belongs to real host tests.
"""
from pathlib import Path
import ast, hashlib, json, sys, tempfile, types

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'work/migration-20261105/source-snapshot/categoryeditor/__init__.py'
EXPECTED='24a8109b5c15bb73b845e42653933d09eb83b608a53303fbab9ebff39b801c27'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED

def init(config, **kw): return dict(op='init', config=config, **kw)
cases=[]
def case(name, steps): cases.append(dict(id=name,steps=steps))
case('fresh-and-noop', [dict(op=x) for x in ['get_state','get_command','get_api','get_page','stop_service','get_state']])
case('form-fresh-read', [dict(op='get_form'), init(dict(enabled=False,content='saved-user-content')),dict(op='get_form',default_text='default-two\n'),dict(op='get_state')])
case('form-read-fails', [dict(op='get_form',fault='default'),dict(op='get_state')])
case('form-invalid-utf8', [dict(op='get_form',default_bytes='ff'),dict(op='get_state')])
case('form-empty-default', [dict(op='get_form',default_text='')])
case('one-shot-success', [init(dict(enabled=True,content='movie:\n  中文电影: {}\ntv:\n  全部剧集: {}\n',discard='field')),dict(op='get_state'),dict(op='stop_service'),dict(op='get_form')])
case('explicit-repeat', [init(dict(enabled=True,content='same\n')),init(dict(enabled=True,content='same\n'))])
case('disabled-draft', [init(dict(enabled=False,content='not-applied')),dict(op='get_form'),dict(op='get_state')])
case('missing-enabled', [init(dict(content='x')),dict(op='get_state')])
case('missing-content', [init(dict(enabled=True)),dict(op='get_state')])
for i,v in enumerate([None,{},False,0,-0.0,1e-320,'',[]]):
    case(f'falsey-config-{i}',[init(dict(enabled='retained',content='before'),fault='apply'),init(v),dict(op='get_state')])
for i,v in enumerate([True,1,'text',[1]]): case(f'non-object-config-{i}',[init(v),dict(op='get_state')])
for i,v in enumerate([None,False,0,-0.0,'',[],{},'false','0',[0],{'a':0},9007199254740993]):
    case(f'enabled-truth-{i}',[init(dict(enabled=v,content='value')),dict(op='get_state')])
for i,v in enumerate([None,False,0,-0.0,'',[],{},True,123456789012345678901234567890,[0],{'a':1},'中文\r\n# keep\n','movie: [invalid','']):
    case(f'content-type-{i}',[init(dict(enabled=True,content=v)),dict(op='get_state')])
for stage in ['apply','helper','message','update']:
    case(f'fault-{stage}',[init(dict(enabled='yes',content='new\n'),fault=stage),dict(op='get_state'),dict(op='stop_service'),dict(op='get_state')])
for value in [False,None]: case(f'update-return-{value}',[init(dict(enabled=True,content='new\n'),update_return=value),dict(op='get_state')])
for i,text in enumerate(['before\ud800after','before\udc00after','emoji\U0001f60a']): case(f'unicode-{i}',[init(dict(enabled='yes',content=text)),dict(op='get_state')])

with tempfile.TemporaryDirectory(prefix='source-owned-category-') as tmp:
    directory=Path(tmp)
    modules={name:types.ModuleType(name) for name in ['app','app.core','app.core.config','app.modules','app.modules.themoviedb','app.plugins']}
    modules['app.core.config'].settings=types.SimpleNamespace(CONFIG_PATH=directory,INNER_CONFIG_PATH=directory)
    class Base: pass
    modules['app.plugins']._PluginBase=Base
    active={}
    class Helper:
        def init(self):
            active['helper_calls']+=1
            if active['step'].get('fault')=='helper': raise OSError('synthetic helper failure')
    modules['app.modules.themoviedb'].CategoryHelper=Helper
    sys.modules.update(modules)
    namespace={}
    exec(compile(ast.parse(SOURCE.read_text()),str(SOURCE),'exec'),namespace)
    Plugin=namespace['CategoryEditor']
    outputs=[]
    for item in cases:
        user=directory/'user.yaml'; default=directory/'default.yaml'
        user.write_bytes(b'prior\n'); default.write_text('default-one\n',encoding='utf-8')
        events=[]; messages=[]; updates=[]; store=None
        class UserPath:
            def write_text(self,value,encoding):
                events.append(dict(method='apply',payload=dict(content=value)))
                if active['step'].get('fault')=='apply': raise OSError('synthetic write failure')
                return user.write_text(value,encoding=encoding)
        class DefaultPath:
            def read_text(self,encoding):
                events.append(dict(method='default',payload={}))
                if active['step'].get('fault')=='default': raise OSError('synthetic read failure')
                return default.read_text(encoding=encoding)
        class Message:
            def put(self,message,title):
                events.append(dict(method='message',payload=dict(message=message,title=title)))
                if active['step'].get('fault')=='message': raise OSError('synthetic message failure')
                messages.append(dict(message=message,title=title))
        plugin=Plugin(); plugin.user_yaml=UserPath(); plugin.default_yaml=DefaultPath(); plugin.systemmessage=Message()
        def update(config):
            nonlocal_dummy=None
            events.append(dict(method='update',payload=dict(config=config)))
            if active['step'].get('fault')=='update': raise OSError('synthetic update failure')
            updates.append(config)
            return active['step'].get('update_return',True)
        plugin.update_config=update
        observations=[]
        for step in item['steps']:
            active.update(step=step,helper_calls=0)
            if 'default_text' in step: default.write_text(step['default_text'],encoding='utf-8')
            if 'default_bytes' in step: default.write_bytes(bytes.fromhex(step['default_bytes']))
            events.clear(); error=False; error_type=None; result=None
            try:
                result=getattr(plugin,'init_plugin' if step['op']=='init' else step['op'])(step['config']) if step['op']=='init' else getattr(plugin,step['op'])()
            except Exception as exc:
                error=True; error_type=type(exc).__name__
            observations.append(dict(op=step['op'],error=error,result=result,state=plugin.get_state(),events=events.copy(),file_hex=user.read_bytes().hex(),messages=messages.copy(),updates=updates.copy(),helper_calls=active['helper_calls'],source_error_type=error_type))
        outputs.append(dict(id=item['id'],observations=observations))
(HERE/'inputs.json').write_text(json.dumps(cases,ensure_ascii=True,indent=2)+'\n')
(HERE/'source-observations.json').write_text(json.dumps(dict(source_sha256=EXPECTED,helper='synthetic recorder; not YAML parser',cases=outputs),ensure_ascii=True,indent=2)+'\n')
print(json.dumps(dict(cases=len(cases),steps=sum(len(x['steps']) for x in cases),source_sha256=EXPECTED)))
