from pathlib import Path
import builtins,hashlib,json,symtable
W=Path(__file__).resolve().parent
body=(W/'remote-body.py').read_bytes()
assert hashlib.sha256(body).hexdigest()=='43c699c0d70fa8bf04bf78fd911412eba68600685d84e224d79cf11f370a1d61'
config={'root':'/home/admin/light-media-plugins-root-asi-native-20261107','marker':'light-media-plugins/root-asi-native/20261107/owned-only','name':'lm-root-asi-native-20261107','owned_dir':'owned-r5','out_dir':'attempt6','image':'sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','bom':json.loads((W/'bundle-bom.json').read_text())}
assert set(config['bom'])=={'bin/host','bin/worker','bin/worker-updated','bin/cli','bin/driver'}
source='CONFIG = '+repr(config)+'\n'+body.decode()
compile(source,'runner.py','exec');table=symtable.symtable(source,'runner.py','exec')
defined={s.get_name()for s in table.get_symbols()if s.is_assigned()or s.is_imported()or s.is_parameter()}
allowed=defined|set(dir(builtins));unbound=[]
def visit(scope):
    for symbol in scope.get_symbols():
        if symbol.is_referenced()and symbol.is_global()and symbol.get_name()not in allowed:unbound.append({'scope':scope.get_name(),'name':symbol.get_name()})
    for child in scope.get_children():visit(child)
visit(table);assert not unbound,unbound
(W/'runner.py').write_text(source)
(W/'runner-preflight.json').write_text(json.dumps({'compile':True,'unbound_global':unbound,'body_sha256':hashlib.sha256(body).hexdigest(),'runner_sha256':hashlib.sha256(source.encode()).hexdigest(),'config':config,'status':'static_only; not_Main_runtime'},indent=2)+'\n')
print(json.dumps({'runner_sha256':hashlib.sha256(source.encode()).hexdigest(),'body_sha256':hashlib.sha256(body).hexdigest(),'unbound_global':unbound}))
