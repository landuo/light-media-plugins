from pathlib import Path
import ast,json,hashlib,subprocess,time
w=Path(__file__).resolve().parent;raw=(w/'source-payload.py').read_text();tree=ast.parse(raw);constants={n.targets[0].id:ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in['HTTP','OCR']}
cases=[]
for n in [9992,9993,9994]:
 cases.append(('list_dict_child_'+str(n),'[[ '+'{"a":'*n+'0'+'}'*n+' ]]'))
 for initial in ['array','dict']:
  prefix=[];suffix=[]
  for i in range(n):
   kind=initial if i%2==0 else('dict'if initial=='array'else'array');prefix.append('['if kind=='array'else'{"a":');suffix.append(']'if kind=='array'else'}')
  cases.append(('mixed_'+initial+'_child_'+str(n),'[['+''.join(prefix)+'0'+''.join(reversed(suffix))+']]'))
payload='from __future__ import annotations\n'+''.join(k+'='+repr(v)+'\n'for k,v in constants.items())+'CASES='+repr(cases)+'\n'+raw[raw.index('import ast,sys,os,json'):];(w/'depth-cases.json').write_text(json.dumps(cases,indent=2)+'\n');(w/'depth-source-payload.py').write_text(payload);cmd=['ssh','-o','BatchMode=yes','admin@192.168.8.129','docker','run','--rm','-i','--network','none','--read-only','--no-healthcheck','--tmpfs','/tmp','--tmpfs','/config','--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534','--label','task=lm-source-ocr-value-depth-20261106','--entrypoint','python3','sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','-B','-'];start=time.monotonic();p=subprocess.run(cmd,input=payload.encode(),capture_output=True,timeout=100);(w/'depth-source.stdout').write_bytes(p.stdout);(w/'depth-source.stderr').write_bytes(p.stderr);(w/'depth-source-command.json').write_text(json.dumps({'argv':cmd,'exit':p.returncode,'seconds':time.monotonic()-start,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest()},indent=2)+'\n');print({'exit':p.returncode,'bytes':len(p.stdout),'stderr':p.stderr.decode()[-1000:]});raise SystemExit(p.returncode)
