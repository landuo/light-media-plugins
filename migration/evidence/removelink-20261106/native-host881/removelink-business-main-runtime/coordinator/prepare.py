from pathlib import Path
import hashlib,json,subprocess
root=Path.cwd();out=Path(__file__).resolve().parent;prep=root/'work/migration-20261106/removelink-business-main-preparation';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(prep/'freeze.json')=='21a5c6e3d6373a0c0c186e64e6541c33e02581148a2010ece311932e9c9579f0'
r=Path('/home/admin/light-media-plugins-migration-removelink-20261105');s=Path('/home/admin/light-media-plugins-migration-sdk98-20261105')
files=[('removelink-business-main-linux.test','757ce25cdde414437ccdcb43e62ab09b9612c72264a8fdf78174d4ce81db80b4'),('owned-notice-fixture-linux','406d13fa0e7c36ee30968117198e9c1ee84f5105fae10d15632e25cf78292952')]
check=f"from pathlib import Path\nimport os\nr=Path({str(r)!r});assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/RemoveLink/20261105/owned-only'\nfor name in {[n for n,h in files]!r}:\n p=r/'bin'/name;assert not p.exists() and not p.is_symlink() and not p.parent.is_symlink()\n"
subprocess.run(['ssh','admin@192.168.8.129','python3','-'],input=check.encode(),check=True)
inputs={}
for n,h in files:
 assert sha(prep/n)==h;subprocess.run(['scp',str(prep/n),'admin@192.168.8.129:'+str(r/'bin'/n)],check=True);inputs[str(r/'bin'/n)]=h
inputs[str(s/'bin/light-media-host-managed-storage-linux')]='6ce69c24f883dba3ab45b9e51bc0262934f3372c454533e119667c5791ea6db1';inputs[str(r/'bin/remove-link-auth-declarations-linux')]='6d7511431944fd72b8eec8fddd02a8ebdcf7632cf4900a0832d193c20dc60031'
for name in ['remoteEntry.js','view.js','style.css']:inputs[str(r/'frontend-run4'/name)]=sha(root/'plugins/removelink/frontend'/name)
(out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n');subprocess.run(['scp',str(out/'inputs.json'),'admin@192.168.8.129:'+str(r/'business-main-1-inputs.json')],check=True)
print(json.dumps({'driver_freeze':'21a5c6e3d6373a0c0c186e64e6541c33e02581148a2010ece311932e9c9579f0','exact_inputs':len(inputs),'actual_main_executed':False}))
