from pathlib import Path
import subprocess,os,json,hashlib,time
P=Path('/Users/accidia/projects/light-media-plugins');H=Path('/Users/accidia/projects/light-media');W=P/'work/sites-review-20261106/current-consumer-main-review/managed-history-guard-review';R=H/'work/shared-host-managed-storage-20261106';binding=json.loads((R/'build-source-binding.json').read_text());assert binding['base_revision']=='651dd2c3f75f4be74951d0a552f93a9079046e1d';tree={}
for b in subprocess.check_output(['git','ls-tree','-rz','--full-tree',binding['base_revision']],cwd=H).split(b'\0'):
 if b:
  head,name=b.split(b'\t',1);tree[name.decode()]=head.split()[2].decode()
sha=lambda b:hashlib.sha256(b).hexdigest();env=os.environ.copy();env.update(GOFLAGS='',GOPROXY='off',GOOS='linux',GOARCH='amd64',CGO_ENABLED='0')
def objects(b):
 s=b.decode();d=json.JSONDecoder()
 while s.strip():s=s.lstrip();v,n=d.raw_decode(s);yield v;s=s[n:]
def snapshot():
 rows={}
 for package in objects(subprocess.check_output(['go','list','-deps','-json','./cmd/server'],cwd=H,env=env)):
  dr=Path(package['Dir'])
  if not dr.is_relative_to(H):continue
  for key in ['GoFiles','CgoFiles','SFiles','EmbedFiles']:
   for name in package.get(key,[]):
    p=dr/name;rel=str(p.relative_to(H));data=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert sha(data)==binding['before'][rel]['sha256'],rel
    if rel not in binding['finite_increments']:assert blob==tree[rel],rel
    rows[rel]=sha(data)
 for rel in ['go.mod','go.sum']:
  data=(H/rel).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==tree[rel];rows[rel]=sha(data)
 assert set(rows)==set(binding['before']);return rows
before=snapshot();assert len(before)==1838;argv=['go','build','-trimpath','-buildvcs=false','-o',str(W/'independent-host-linux'),'./cmd/server'];t=time.time();r=subprocess.run(argv,cwd=H,env=env,capture_output=True);(W/'host-cold-build.stdout').write_bytes(r.stdout);(W/'host-cold-build.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr;after=snapshot();assert before==after;actual=sha((W/'independent-host-linux').read_bytes());assert actual==binding['binary_sha256'];info=subprocess.check_output(['go','version','-m',str(W/'independent-host-linux')]);(W/'host-buildinfo.txt').write_bytes(info);(W/'host-independent-reproduction.json').write_text(json.dumps({'classification':'compile-only independent current 1838 production inputs exact Git651+two explicit reviewed increments; no gooverlay/SDK/product changes; actual ELF equals Rootnative candidate','root_binding_sha256':sha((R/'build-source-binding.json').read_bytes()),'base_revision':binding['base_revision'],'repository_inputs':1838,'all_non_delta_actual_Gitblob_match':True,'finite_increments':binding['finite_increments'],'argv':argv,'seconds':time.time()-t,'exit':0,'environment':{k:env[k]for k in ['GOOS','GOARCH','CGO_ENABLED','GOFLAGS']},'pre_post_same':True,'binary_sha256':actual},indent=2)+'\n');print(actual)
