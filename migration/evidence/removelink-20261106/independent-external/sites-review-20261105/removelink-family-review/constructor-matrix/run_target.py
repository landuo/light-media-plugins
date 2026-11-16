from pathlib import Path
import json,hashlib,subprocess,os,uuid,shlex
root=Path('/Users/accidia/projects/light-media-plugins');out=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();manifest=root/'work/migration-20261105/removelink-home-ctor-20261106/current-files.json';assert sha(manifest.read_bytes())=='d52bf7b0f6e06ef524833ccbb079b5a8a43305dc4f950d39e6ccd1767fc5b156';rows=json.loads(manifest.read_text());assert all(sha((root/r['path']).read_bytes())==r['sha256'] for r in rows)
expected=(out/'source-oracle.json').read_text();test='''package removelink
import("encoding/json";"os";"testing")
const independentCtorOracle = ORACLE_LITERAL
func TestIndependentHOMEConstructorAllBranches(t *testing.T){
 var source struct {Cases []struct{Mode string;Uid int;Values []struct{Path string;Value *string;Error *struct{Class,Message string}};EmptyExclude bool `json:"empty_exclude"`}};if err:=json.Unmarshal([]byte(independentCtorOracle),&source);err!=nil{t.Fatal(err)}
 mode:=os.Getenv("LM_REVIEW_CTOR_CASE");var index=-1;for i,c:=range source.Cases{if c.Mode==mode{index=i}};if index<0{t.Skip("explicit isolated UID/env constructor case required")};c:=source.Cases[index];if os.Getuid()!=c.Uid{t.Fatal("wrong uid",os.Getuid(),c.Uid)}
 p:=NewPlugin()
 for _,r:=range c.Values{t.Run(r.Path,func(t *testing.T){var got string;var recovered any;func(){defer func(){recovered=recover()}();got=normalized(r.Path,p.machine.Home)}()
 if r.Error==nil{if recovered!=nil||r.Value==nil||got!=*r.Value{t.Fatalf("source normalization value=%v Go=%q panic=%v",r.Value,got,recovered)}}else{failure,ok:=recovered.(effectFailure);if !ok||failure.err.Error()!=r.Error.Class+":"+r.Error.Message{t.Fatalf("source error=%+v Go=%q panic=%v",r.Error,got,recovered)}}
 })}
 t.Run("empty-exclude-no-premature-normalize",func(t *testing.T){cfg:=NewConfig();if got:=cfg.Excluded("~__lm_review_absent__",p.machine.Home);got!=c.EmptyExclude{t.Fatal("source empty excludes",got,c.EmptyExclude)}})
}
'''.replace('ORACLE_LITERAL',json.dumps(expected));p=out/'constructor_matrix_test.go';p.write_text(test);subprocess.run(['gofmt','-w',str(p)],check=True);o=out/'overlay.json';o.write_text(json.dumps({'Replace':{str(root/'plugins/removelink/independent_constructor_matrix_test.go'):str(p)}},indent=2)+'\n');exe=out/'constructor-linux.test';env=os.environ.copy();env.update(GOFLAGS='',GOOS='linux',GOARCH='amd64',CGO_ENABLED='0')
cmd=['go','test','-c','-trimpath','-buildvcs=false','-overlay',str(o),'-o',str(exe),'./plugins/removelink']
with (out/'target-build.stdout').open('wb') as f,(out/'target-build.stderr').open('wb') as e:r=subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=e)
assert r.returncode==0;h=sha(exe.read_bytes());nonce=uuid.uuid4().hex[:12];remote='/home/admin/light-media-plugins-review-ctor-'+nonce;marker='lm-review-ctor/'+nonce;ssh=['ssh','admin@192.168.8.129'];r=subprocess.run(ssh+['umask 077; mkdir '+shlex.quote(remote)+' && printf %s '+shlex.quote(marker)+' > '+shlex.quote(remote+'/TASK')],capture_output=True);assert r.returncode==0
records=[]
try:
 r=subprocess.run(['scp','-q',str(exe),'admin@192.168.8.129:'+remote+'/review.test'],capture_output=True);assert r.returncode==0
 for case in json.loads(expected)['cases']:
  mode=case['mode'];uid=case['uid'];home=['-u','HOME'] if not case['HOME_present'] else ['HOME='+case['HOME']]
  tail=['-u','USER']+(['-u','HOME'] if not case['HOME_present'] else [])+(['HOME='+case['HOME']] if case['HOME_present'] else [])+['LM_REVIEW_CTOR_CASE='+mode,'/usr/local/bin/rlk-review.test','-test.v','-test.timeout=25s','-test.run=^TestIndependentHOMEConstructorAllBranches$']
  # GNU env options must precede NAME=VALUE operands.
  label='lm-review-ctor-'+uuid.uuid4().hex;docker=['docker','run','--rm','--label','task='+label,'--network','none','--read-only','--user',str(uid)+':'+str(uid),'--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777','--mount','type=bind,src='+remote+'/review.test,dst=/usr/local/bin/rlk-review.test,readonly','--entrypoint','/usr/bin/env','sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881']+tail
  shell='set -eu; cd '+shlex.quote(remote)+'; test "$(cat TASK)" = '+shlex.quote(marker)+'; chmod 755 review.test; test "$(sha256sum review.test | cut -d " " -f1)" = '+h+'; '+shlex.join(docker)
  r=subprocess.run(ssh+[shell],capture_output=True);(out/(mode+'-target.stdout')).write_bytes(r.stdout);(out/(mode+'-target.stderr')).write_bytes(r.stderr)
  c=subprocess.run(ssh+['docker ps -aq --filter label=task='+label],capture_output=True);records.append({'mode':mode,'command':ssh+[shell],'exit':r.returncode,'containers_remaining':c.stdout.decode(),'cleanup_check_exit':c.returncode});assert r.returncode==0,r.stdout.decode()+r.stderr.decode()
finally:
 clean='set -eu; cd '+shlex.quote(remote)+'; test "$(cat TASK)" = '+shlex.quote(marker)+'; test "$(sha256sum review.test | cut -d " " -f1)" = '+h+'; rm review.test TASK; cd /home/admin; rmdir '+shlex.quote(remote)
 c=subprocess.run(ssh+[clean],capture_output=True);(out/'target-cleanup.stdout').write_bytes(c.stdout+c.stderr);(out/'target-commands.json').write_text(json.dumps({'classification':'actual target constructor/path helper in four independent CGO0 Linux subprocesses; fixed333 read-only network-none UID/env; no App/SDK/filesystem writes','producer_manifest_sha256':sha(manifest.read_bytes()),'binary_sha256':h,'test_sha256':sha(p.read_bytes()),'records':records,'cleanup_command':ssh+[clean],'cleanup_exit':c.returncode},indent=2)+'\n');exe.unlink()
print('actual target four constructor branches pass')
