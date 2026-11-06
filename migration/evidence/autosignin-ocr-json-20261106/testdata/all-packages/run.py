from pathlib import Path
import subprocess,json,hashlib,os,time
P=Path.cwd();W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def inputs():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=P).split(b'\0');paths=[P/os.fsdecode(n)for n in names if n]
 paths += [P/'migration/evidence/go.mod',P/'plugins/autosignin/source_ocr_value_domain_test.go',*sorted((P/'plugins/autosignin/testdata/source-ocr-json-values').glob('*.json')),P/'work/go.mod']
 return {str(p):sha(p)for p in paths if p.is_file()}
for mode,extra in [('normal',[]),('race',['-race'])]:
 before=inputs();(W/(mode+'-before.json')).write_text(json.dumps(before,indent=2)+'\n');args=['go','test','-json','-p=1',*extra,'-count=1','./...'];t=time.monotonic();r=subprocess.run(args,cwd=P,env={**os.environ,'GOPROXY':'off','GOFLAGS':''},capture_output=True);after=inputs();(W/(mode+'-after.json')).write_text(json.dumps(after,indent=2)+'\n');(W/(mode+'.stdout')).write_bytes(r.stdout);(W/(mode+'.stderr')).write_bytes(r.stderr)
 events=[]
 for line in r.stdout.decode().splitlines():
  try:events.append(json.loads(line))
  except ValueError:pass
 rec={'argv':args,'cwd':str(P),'exit':r.returncode,'seconds':time.monotonic()-t,'inputs':len(before),'stable':before==after,'test_pass':sum(x.get('Action')=='pass'and bool(x.get('Test'))for x in events),'package_pass':[x['Package']for x in events if x.get('Action')=='pass'and not x.get('Test')],'skipped_tests':[x for x in events if x.get('Action')=='skip'and x.get('Test')],'no_test_packages':[x.get('Package')for x in events if x.get('Action')=='skip'and not x.get('Test')],'failures':[x for x in events if x.get('Action')=='fail'],'environment':{'GOPROXY':'off','GOFLAGS':'','go':subprocess.check_output(['go','version']).decode().strip()},'production_overlay':False,'modfile':False};(W/(mode+'.json')).write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:v for k,v in rec.items()if k not in ['skipped_tests','no_test_packages','failures']}),flush=True);assert r.returncode==0 and before==after
