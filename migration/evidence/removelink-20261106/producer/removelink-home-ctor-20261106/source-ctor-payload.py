import os,sys,json,hashlib,pwd
from pathlib import Path
def _normalize_config_path(config_path: str) -> str:
    """规范化配置中的目录路径，保留不存在路径的可比较形式。"""
    return os.path.normcase(os.path.normpath(str(Path(config_path).expanduser())))
mode=sys.argv[1]
os.environ.pop('HOME',None);os.environ.pop('USER',None)
if mode=='present-empty':os.environ['HOME']=''
if mode=='present-value':os.environ['HOME']='/owned/home'
try:pw=pwd.getpwuid(os.getuid());mapped=True
except KeyError:mapped=False
rows=[]
for path in ['~','~/child','/absolute/owned']:
 try:value=_normalize_config_path(path);error=None
 except Exception as e:value=None;error={'class':type(e).__name__,'message':str(e)}
 rows.append({'path':path,'value':value,'error':error})
print(json.dumps({'mode':mode,'uid':os.getuid(),'pwd_mapped':mapped,'HOME_present':'HOME'in os.environ,'runtime':sys.version,'source_sha256':'22fb375e531378b3454607c7bca305b637abd60ee8ed69e14e32fbc2ddfc5485','cases':rows,'classification':'actual installed normalize AST and real Path/pwd in fixed333; HOME controlled only in disposable process; no app/config/db/network'}))
