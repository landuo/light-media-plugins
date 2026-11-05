from pathlib import Path
import json,hashlib,subprocess,os,time
r=Path('/Users/accidia/projects/light-media-plugins');w=Path(__file__).resolve().parent;prod=r/'work/migration-20261106/source-module-manifest';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();freeze=prod/'freeze.json';assert sha(freeze)=='4693f0b87c3e78efb7d814b4d2db0e19c9302b8c822ee76c236339f8696a54b0';j=json.loads(freeze.read_text())
for row in j['products']:assert sha(r/row['path'])==row['sha256']
for row in j['files']:assert sha(Path(row['path']))==row['sha256'],row['path']
inputs=json.loads((prod/'all-current-inputs.json').read_text());assert len(inputs)==613 and sha(prod/'all-current-inputs.json')==j['current_inputs_sha256']
for row in inputs:assert sha(r/row['path'])==row['sha256'],row['path']
assert (prod/'all-current-inputs.json').read_bytes()==(prod/'all-current-inputs-after.json').read_bytes();assert sha(r/'SDK_ORIGIN.json')=='40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875'
old=json.loads((r/'work/migration-20261105/removelink-home-ctor-20261106/current-files.json').read_text());new={x['path']:x['sha256']for x in json.loads((prod/'removelink-current59.json').read_text())};assert set(new)==set(x['path']for x in old)
delta=[x['path']for x in old if new[x['path']]!=x['sha256']];assert set(delta)=={'plugins/removelink/plugin.go','plugins/removelink/ORIGIN.md'}
cmd=['go','run',str(w/'compare.go'),str(r),str(prod/'before'),str(r/'work/sites-review-20261105/module-method-declarations-20261106/interface-inventory.json')];p=subprocess.run(cmd,cwd=r,capture_output=True);(w/'AST.stdout').write_bytes(p.stdout);(w/'AST.stderr').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode();ast=json.loads(p.stdout);assert sum(ast['families'].values())==20
(w/'bin').mkdir(exist_ok=True);env=dict(os.environ,GOOS='linux',GOARCH='amd64',CGO_ENABLED='0',GOFLAGS='',GOPROXY='off',GOTOOLCHAIN='local');rows=[]
for artifact in j['retained_linux_inputs']:
 if artifact['target']=='linux':
  output=w/'bin'/artifact['cmd'];args=['go','build','-trimpath','-buildvcs=false','-o',str(output),'./cmd/'+artifact['cmd']]
 else:
  output=w/'bin/remove-link-version-only';code=(r/'plugins/removelink/plugin.go').read_text();assert code.count('Version: "2.18"')==1;alternate=w/'version-plugin.go';alternate.write_text(code.replace('Version: "2.18"','Version: "2.18.1"'));overlay=w/'version-overlay.json';overlay.write_text(json.dumps({'Replace':{str(r/'plugins/removelink/plugin.go'):str(alternate)}},indent=2)+'\n');args=['go','build','-trimpath','-buildvcs=false','-overlay='+str(overlay),'-o',str(output),'./cmd/remove-link']
  original=Path(artifact['path']);assert sha(original)==artifact['sha256']
 start=time.monotonic();p=subprocess.run(args,cwd=r,env=env,capture_output=True);assert p.returncode==0,p.stderr.decode();actual=sha(output);assert actual==artifact['sha256'],(artifact['path'],actual,artifact['sha256']);assert sha(Path(artifact['path']))==actual
 bom=subprocess.check_output(['go','version','-m',str(output)],cwd=r);(w/(output.name+'.buildinfo')).write_bytes(bom);assert b'GOOS=linux'in bom and b'CGO_ENABLED=0'in bom
 rows.append({'family':artifact['family'],'target':artifact['target'],'command':args,'exit_code':p.returncode,'seconds':time.monotonic()-start,'sha256':actual,'bytes':output.stat().st_size,'retained_original':artifact['path']});output.unlink();print(json.dumps({'family':artifact['family'],'target':artifact['target'],'exact_ELF':actual}),flush=True)
for row in inputs:assert sha(r/row['path'])==row['sha256']
(w/'ELF-verification.json').write_text(json.dumps({'classification':'independent source-derived 20-method-only AST proof, complete613 frozen input verification and exact independent7Linux ELF rebuild; no ordinary main/UI execution','passed':True,'freeze_sha256':sha(freeze),'inputs':len(inputs),'all613_actual_hashes_before_after_equal':True,'production_AST':ast,'Rlk59_changed_only':delta,'Rlk_unchanged_count':57,'ELFs':rows,'own_ELFs_removed':True,'SDK98_Origin':sha(r/'SDK_ORIGIN.json')},indent=2)+'\n');print(json.dumps({'passed':True,'families':6,'ELFs':len(rows),'certificate_sha256':sha(w/'ELF-verification.json')}))
