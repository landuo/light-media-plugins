from pathlib import Path
import subprocess, json, hashlib, os, datetime

root=Path('/Users/accidia/projects/light-media')
out=Path(__file__).resolve().parent
revision='3a3f9e544073bf1c17e6698ad2eac2aef90d7f59'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git',*a],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==revision
allowed={'internal/app/plugin_implementation.go': 'a6057009d55c5e5cc21fe2d74cf3e78a8199ae1f490204df7cf696c9966e95a1', 'internal/app/plugin_original_commands.go': '90a2c079d2955da7f1d08ab9d4cb263010ef133362a513fa64270e6f31573434', 'internal/app/plugin_original_services.go': '2c405c0a944b90d095eb2f04cbb49e27768de48b20f694aa109e98645888b7a4', 'internal/app/plugin_original_view_adapter.go': '05793eecac7a598db9b108479202baeec865426bb1774dd7d9fc44de921fded3'}
for name,expected in allowed.items():
 data=(root/name).read_bytes();assert sha(data)==expected
 dest=out/'finite-increments'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
tree={}
for record in git('ls-tree','-rz','--full-tree',revision).split(b'\0'):
 if record:
  head,name=record.split(b'\t',1);_,kind,blob=head.split();assert kind==b'blob';tree[name.decode()]=blob.decode()
env=dict(os.environ,CGO_ENABLED='0',GOOS='linux',GOARCH='amd64',GOFLAGS='')
def objects(data):
 s=data.decode();dec=json.JSONDecoder()
 while s.strip():
  s=s.lstrip();obj,n=dec.raw_decode(s);yield obj;s=s[n:]
def snapshot():
 raw=subprocess.check_output(['go','list','-deps','-json','./cmd/server'],cwd=root,env=env)
 result={}
 for package in objects(raw):
  directory=Path(package['Dir'])
  if not directory.is_relative_to(root):continue
  for field in ['GoFiles','CgoFiles','SFiles','EmbedFiles']:
   for leaf in package.get(field,[]):
    p=directory/leaf;name=str(p.relative_to(root));data=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if name in allowed:assert sha(data)==allowed[name]
    else:assert blob==tree[name],name
    result[name]={'sha256':sha(data),'actual_blob':blob,'git_blob':tree.get(name),'finite_increment':name in allowed}
 for name in ['go.mod','go.sum']:
  data=(root/name).read_bytes();assert data==git('show',revision+':'+name)
  result[name]={'sha256':sha(data),'git_blob':tree[name],'finite_increment':False}
 return result
before=snapshot();binary=out/'light-media-host-getter-gates-linux'
cmd=['go','build','-trimpath','-buildvcs=false','-o',str(binary),'./cmd/server']
p=subprocess.run(cmd,cwd=root,env=env,capture_output=True);(out/'build.log').write_bytes(p.stdout+p.stderr)
assert p.returncode==0,p.stderr.decode()
after=snapshot();assert before==after
result={'classification':'compile-only exact host3a3f(state/query/PUI19/parent0300) plus4source-derived optional-getter gate/preflight/direct-dashboard increments; current independent review and actual Main still pending; no SDK98 changes','base_revision':revision,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'environment':{k:env[k]for k in ['CGO_ENABLED','GOOS','GOARCH','GOFLAGS']},'go_version':subprocess.check_output(['go','version']).decode().strip(),'finite_increments':allowed,'repository_inputs':len(before),'all_inputs_equal_before_after':before==after,'before':before,'after':after,'exit_code':p.returncode,'binary_sha256':sha(binary.read_bytes()),'binary_bytes':binary.stat().st_size}
(out/'build-source-binding.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'buildinfo.txt').write_bytes(subprocess.check_output(['go','version','-m',str(binary)]))
print(json.dumps({k:result[k]for k in ['base_revision','repository_inputs','binary_sha256','binary_bytes','exit_code']}))
