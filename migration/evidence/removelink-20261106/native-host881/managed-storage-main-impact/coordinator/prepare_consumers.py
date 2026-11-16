from pathlib import Path
import json,subprocess
root=Path.cwd();out=Path(__file__).resolve().parent;shared=Path('/home/admin/light-media-plugins-migration-sdk98-20261105');h='6ce69c24f883dba3ab45b9e51bc0262934f3372c454533e119667c5791ea6db1'
for old,new,inputsname,newinputs,script in [('source-auth-main-four-2','managed-storage-main-four-1','four-auth-inputs.json','managed-storage-four-inputs.json','run_four_auth.py'),('source-declarations-pui-main-3','managed-storage-pui-main-1','pui3-inputs.json','managed-storage-pui-inputs.json','run_pui3.py')]:
 x=json.loads((root/'work/migration-20261106/current-consumer-main'/inputsname).read_text());x.pop(str(shared/'bin/light-media-host-getter-gates-linux'));x[str(shared/'bin/light-media-host-managed-storage-linux')]=h
 p=out/newinputs;p.write_text(json.dumps(x,indent=2)+'\n');subprocess.run(['scp',str(p),'admin@192.168.8.129:'+str(shared/newinputs)],check=True)
 s=(root/'work/migration-20261106/current-consumer-main'/script).read_text().replace(old,new).replace('light-media-host-getter-gates-linux','light-media-host-managed-storage-linux').replace('3c0513c3c92e4ab15128f1d0c0756cdd4c763403d0dc2b6111f8812a36d1c6cb',h)
 s=s.replace('source-auth-four-inputs.json',newinputs).replace('source-declarations-pui3-inputs.json',newinputs)
 s=s.replace("'classification':", "'managed_storage_host_binding':'host651dd+2ordinary-source-storage-files/1838stableinputs; candidateELF6ce69c; no worker orSDK98 changes','classification':",1)
 s=s.replace('current3c05 host','current6ce69c host').replace('ordinary Main3c05','ordinary Main651dd+2managed-storage').replace('ordinary Main3c05','ordinary Main651dd+2managed-storage')
 (out/('run_'+new+'.py')).write_text(s)
print('prepared fresh two-consumer-run wrappers and exact inputs; not executed')
