from pathlib import Path
import hashlib,json,os,subprocess,time
P=Path('/Users/accidia/projects/light-media-plugins');W=P/'work/sites-review-20261106/auth-declaration-addon';A=P/'work/migration-20261106/source-auth-declaration-addon'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((A/'source613-auth-epoch.json').read_text());mismatch=[r['path'] for r in rows if sha(P/r['path'])!=r['sha256']];assert not mismatch,mismatch
changes=[]
for r in json.loads((W/'before20-inputs.json').read_text()):
 p=P/r['path'];s=(W/'before20'/r['path']).read_text();assert '"get_auth_providers"' in s
 # Only the advertised Manifest occurrence is removed. Handle's compatibility
 # branch remains byte-identical after gofmt, as does every other method body.
 head,tail=s.split('func ',1);prefix,body=tail.split('func ',1);assert prefix.count('"get_auth_providers"')==1
 candidate=head+'func '+prefix.replace('"get_auth_providers",','')+'func '+body
 formatted=subprocess.run(['gofmt'],input=candidate.encode(),stdout=subprocess.PIPE,check=True).stdout
 assert formatted==p.read_bytes(),p
 changes.append({'path':r['path'],'before_sha256':r['sha256'],'after_sha256':sha(p),'complete_file_equal_to_one_Manifest_deletion_plus_gofmt':True})
(W/'independent-input-review.json').write_text(json.dumps({'source613_count':len(rows),'source613_sha256':sha(A/'source613-auth-epoch.json'),'all_current_hashes_match':True,'production_diffs':changes,'sdk_origin_sha256':sha(P/'SDK_ORIGIN.json') if (P/'SDK_ORIGIN.json').exists() else None},indent=2))
E=os.environ.copy();E.update(GOFLAGS='',GOPROXY='off',GOOS='linux',GOARCH='amd64',CGO_ENABLED='0');bins=W/'independent-linux';bins.mkdir(exist_ok=True)
artifacts=json.loads((A/'artifacts.json').read_text());res=[]
for name,cmd in [('category','category-editor'),('tt','torrent-transfer'),('rlk','remove-link'),('site','site-statistic'),('mps','mp-server-status'),('pui','plugin-uninstall'),('update','remove-link')]:
 args=['go','build','-trimpath','-buildvcs=false'];
 if name=='update':args+=['-overlay',str(A/'version-overlay.json')]
 b=bins/name;args+=['-o',str(b),'./cmd/'+cmd];start=time.time();r=subprocess.run(args,cwd=P,env=E,capture_output=True);(W/(name+'-linux-build.stderr')).write_bytes(r.stderr);assert r.returncode==0,r.stderr
 info=subprocess.run(['go','version','-m',str(b)],capture_output=True,check=True).stdout;(W/(name+'-linux-buildinfo.txt')).write_bytes(info)
 expected=next(x for x in artifacts if x['command']==('remove-link-version-only-update' if name=='update' else cmd));assert sha(b)==expected['sha256'],name
 res.append({'name':name,'argv':args,'seconds':time.time()-start,'sha256':sha(b),'expected':expected['sha256'],'byte_identical':True,'ELF_magic':b.read_bytes()[:4].hex()});print(name,sha(b),flush=True)
(W/'independent-ELF-review.json').write_text(json.dumps(res,indent=2))
