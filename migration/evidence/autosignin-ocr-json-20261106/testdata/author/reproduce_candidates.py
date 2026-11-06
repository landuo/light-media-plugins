from pathlib import Path
import json,hashlib,subprocess,tempfile
w=Path(__file__).resolve().parent
for r in json.loads((w/'production-files.json').read_text()):
 p=Path(r['candidate']);b=Path(r['before']);assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']and hashlib.sha256(b.read_bytes()).hexdigest()==r['before_sha256']
 with tempfile.TemporaryDirectory()as td:
  out=Path(td)/'reproduced.go';v=subprocess.run(['patch','--silent','--output',str(out),str(b),str(w/(p.name+'.diff'))],capture_output=True);assert v.returncode==0,(v.stdout,v.stderr);assert out.read_bytes()==p.read_bytes(),r['target']
print('five candidate hunks reproduce exactly')
