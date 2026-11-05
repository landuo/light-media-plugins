from pathlib import Path
import json,subprocess,os,time,hashlib
out=Path(__file__).resolve().parent;root=Path('/Users/accidia/projects/light-media-plugins');base=json.loads((out/'overlay.json').read_text())['Replace'];env=os.environ.copy();env.update(GOFLAGS='',TMPDIR=str(out/'tmp')); results=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
def source(rel):return Path(base[str(root/rel)]).read_text()
cases=[]
m=source('plugins/removelink/machine.go');needle='if m.Ops.Exists(t.Path) {';assert m.count(needle)==1
cases.append(('lock-delayed-exists',{'plugins/removelink/machine.go':m.replace(needle,'m.mu.Lock()\n sourceExists := m.Ops.Exists(t.Path)\n m.mu.Unlock()\n if sourceExists {')},'^TestIndependentCreatedDuringDelayedExistsKeepsOldLinks$'))
w=source('plugins/removelink/watch.go');needle='if errors.As(err, &source) || errors.As(err, &home) {';assert w.count(needle)==1
cases.append(('source-error-closes-all-roots',{'plugins/removelink/watch.go':w.replace(needle,'if false && (errors.As(err, &source) || errors.As(err, &home)) {')},'^TestIndependentOneObserverErrorDoesNotStopSiblingDirectoryEvents$'))
o=source('plugins/removelink/sdk_ops.go');needle='func (o *sdkOps) delete(path, kind string) error {';assert o.count(needle)==1
cases.append(('unlink-requires-parent-read',{'plugins/removelink/sdk_ops.go':o.replace(needle,needle+'\n if err := o.authorizeDir(filepath.Dir(path)); err != nil { return err }')},'^TestIndependentWorkerUnlinkNoParentReadPrecondition$'))
p=source('plugins/removelink/pass.go');p=p.replace('pass.result = body(&operation{Machine: p.machine, Ops: pass.ops})','p.machine.Ops = pass.ops\n pass.result = body(&operation{Machine: p.machine})')
op=source('plugins/removelink/operation.go');op=op.replace('\n\tOps         Ops','');assert '\n\tOps         Ops' not in op
m2=m.replace('&operation{Machine: m, Ops: ops}','&operation{Machine: m}')
cases.append(('shared-machine-effect-caller',{'plugins/removelink/pass.go':p,'plugins/removelink/operation.go':op,'plugins/removelink/machine.go':m2},'^TestActualWorkerIndependentTimerAndObserverCallers$'))
needle='case r <= 0xff:\n\t\t\t\tfmt.Fprintf(&b, `\\x%02x`, r)';assert m.count(needle)==1
cases.append(('wrong-python-repr-width',{'plugins/removelink/machine.go':m.replace(needle,'case r <= 0xff:\n\t\t\t\tfmt.Fprintf(&b, `\\u%04x`, r)')},'^TestIndependentDirectoryListLogUsesPythonRepr$'))
t=source('plugins/removelink/types.go');needle='\tc.Extensions = ParseExtensions(c.Custom)\n';assert t.count(needle)==1
t=t.replace(needle,'').replace('\tc.Delay = max(10, min(86400, nextDelay))',needle+'\tc.Delay = max(10, min(86400, nextDelay))')
cases.append(('custom-extensions-after-overflow',{'plugins/removelink/types.go':t},'^TestIndependentOverflowKeepsEarlierCustomExtensionAssignment$'))
t=source('plugins/removelink/types.go');assert t.count('checked(sourceHomeError{})')==2
t=t.replace('checked(sourceHomeError{})','return normPath(p)')
cases.append(('unknown-home-continues-unlink',{'plugins/removelink/types.go':t},'^TestIndependentUnknownNamedHomeStopsUnlinkLikePathlib$'))
w2=source('plugins/removelink/watch.go').replace('|| errors.As(err, &home)','|| false && errors.As(err, &home)')
cases.append(('home-runtime-kills-sibling',{'plugins/removelink/watch.go':w2},'^TestIndependentHomeRuntimeKillsOnlyFailedObserver$'))
for name,files,test in cases:
 d=out/'mutations'/name;d.mkdir(parents=True,exist_ok=True);maps=base.copy();inputs={}
 for rel,s in files.items():
  dest=d/Path(rel).name;dest.write_text(s);subprocess.run(['gofmt','-w',str(dest)],check=True);maps[str(root/rel)]=str(dest);inputs[rel]=sha(dest.read_bytes())
 overlay=d/'overlay.json';overlay.write_text(json.dumps({'Replace':maps},indent=2)+'\n');exe=d/'mutant.test'
 cmd=['go','test','-race','-c','-overlay',str(overlay),'-o',str(exe),'./plugins/removelink'];start=time.time()
 with (d/'build.stdout').open('wb') as f,(d/'build.stderr').open('wb') as e:r=subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=e)
 rec={'name':name,'changed_source_sha256':inputs,'build_command':cmd,'build_exit':r.returncode}
 if r.returncode==0:
  rec['binary_sha256']=sha(exe.read_bytes());cmd=[str(exe),'-test.v','-test.timeout=18s','-test.run='+test]
  with (d/'run.stdout').open('wb') as f,(d/'run.stderr').open('wb') as e:r=subprocess.run(cmd,cwd=root/'plugins/removelink',env=env,stdout=f,stderr=e)
  rec.update(run_command=cmd,run_exit=r.returncode,killed=r.returncode!=0)
  exe.unlink();rec['binary_removed']=True
 rec['elapsed']=time.time()-start;results.append(rec);(out/'mutations/observations.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(rec),flush=True)
