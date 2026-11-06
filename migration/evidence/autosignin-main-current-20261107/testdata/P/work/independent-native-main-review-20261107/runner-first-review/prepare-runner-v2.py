from pathlib import Path
import json,symtable,builtins,hashlib
W=Path(__file__).resolve().parent
config={'root':'/home/admin/light-media-plugins-root-asi-native-20261107','marker':'light-media-plugins/root-asi-native/20261107/owned-only','name':'lm-root-asi-native-20261107','owned_dir':'owned-r2','out_dir':'attempt3','image':'sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','bom':json.loads((W/'bundle-bom.json').read_text())}
source='CONFIG = '+repr(config)+'\n'+(W/'remote-body-v2.py').read_text()
compile(source,'runner-v2.py','exec')
table=symtable.symtable(source,'runner-v2.py','exec')
defined={x.get_name()for x in table.get_symbols()if x.is_assigned()or x.is_imported()or x.is_parameter()}
allowed=defined|set(dir(builtins));unbound=[]
def walk(scope):
    for symbol in scope.get_symbols():
        if symbol.is_referenced()and symbol.is_global()and symbol.get_name()not in allowed:
            unbound.append({'scope':scope.get_name(),'name':symbol.get_name()})
    for child in scope.get_children():walk(child)
walk(table);assert not unbound,unbound
(W/'runner-v2.py').write_text(source)
(W/'runner-v2-preflight.json').write_text(json.dumps({'compile_pass':True,'unbound_global':unbound,'config_keys':sorted(config),'runner_sha256':hashlib.sha256(source.encode()).hexdigest(),'classification':'static setup preflight only; no Main execution'},indent=2)+'\n')
print(json.dumps({'compile_pass':True,'unbound_global':unbound,'runner_sha256':hashlib.sha256(source.encode()).hexdigest()}))
