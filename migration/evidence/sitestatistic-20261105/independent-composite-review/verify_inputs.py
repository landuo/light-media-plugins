import json,pathlib,hashlib,subprocess,tarfile,io
REPO=pathlib.Path('/Users/accidia/projects/light-media-plugins');HOST=pathlib.Path('/Users/accidia/projects/light-media');OUT=REPO/'work/sites-review-20261105/site-final-composite';RUNTIME=REPO/'work/migration-20261105/sitestatistic-runtime'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def check(d,base):
 rows=[]
 for p,h in d.items():
  a=sha(base/p);rows.append({'path':p,'expected':h,'actual':a,'matches':a==h})
 return rows
f=load(RUNTIME/'enum-fixed-freeze.json');h=load(RUNTIME/'host-build-source-binding.json');br=load(RUNTIME/'browser/browser-verification.json');dr=load(REPO/'work/migration-20261105/sitestatistic-preparation/main-driver-freeze.json')
result={'classification':'independent exact current input, original Git object, browser raw and driver freeze checks; no product/host/remote mutation','product40':check(f['target_files_sha256'],REPO),'sdk_build62':check(f['sdk_build_inputs_sha256'],REPO),'binaries':check(f['binaries'],RUNTIME),'driver_build_inputs':check(dr['driver_build_inputs_sha256'],REPO),'driver_binary':check({dr['linux_test_binary']['path']:dr['linux_test_binary']['sha256']},REPO),'browser22':check({p:x['sha256'] for p,x in br['files'].items()},RUNTIME/'browser')}
origin=load(REPO/'SDK_ORIGIN.json');result['sdk_origin_sha256']=sha(REPO/'SDK_ORIGIN.json');result['sdk_origin_keys']=list(origin)
# Original Git blobs, not a filesystem copy of the host checkout.
items=list(h['repository_inputs'].items());requests=''.join(h['source_commit']+':'+p+'\n' for p,_ in items).encode();proc=subprocess.run(['git','-C',str(HOST),'cat-file','--batch'],input=requests,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);data=proc.stdout;off=0;rows=[]
for p,expected in items:
 end=data.index(b'\n',off);header=data[off:end].decode();parts=header.split();assert parts[1]=='blob',header;size=int(parts[2]);start=end+1;b=data[start:start+size];assert data[start+size:start+size+1]==b'\n';off=start+size+1;actual=hashlib.sha256(b).hexdigest();rows.append({'path':p,'expected':expected,'commit_blob_sha256':actual,'matches':actual==expected,'git_blob':parts[0]})
assert off==len(data)
result['host1832_committed_inputs']=rows;result['host_binary']=check({'light-media-site-host-linux':h['binary_sha256']},RUNTIME)
result['input_bindings']={str(p.relative_to(REPO)):sha(p) for p in [RUNTIME/'enum-fixed-freeze.json',RUNTIME/'host-build-source-binding.json',RUNTIME/'browser/browser-verification.json',REPO/'work/migration-20261105/sitestatistic-preparation/main-driver-freeze.json']}
allrows=[x for v in result.values() if isinstance(v,list) and v and isinstance(v[0],dict) for x in v];fail=[x for x in allrows if x.get('matches') is False];result['checked_file_count']=len(allrows);result['mismatches']=fail
(OUT/'input-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'checked_file_count':len(allrows),'mismatches':fail,'product40':len(result['product40']),'sdk62':len(result['sdk_build62']),'host_git_blobs':len(rows),'browser_files':len(result['browser22']),'origin_keys':list(origin)}))
assert not fail
