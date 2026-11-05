import hashlib,json,pathlib,subprocess,time
root=pathlib.Path('/Users/accidia/projects/light-media-plugins')
work=root/'work/migration-20261105/removelink-concurrency-20261105'
base=root/'plugins/removelink/watch.go'
s=base.read_text()
cases=[
 ('no-round-robin','w.nextLane = (index + 1) % len(w.lanes)','w.nextLane = 0','TestActualWorkerTenObserverRootsFairWhileSixCallbacksBlocked'),
 ('observer-source-error-aborts-all','if errors.As(err, &source) {','if false && errors.As(err, &source) {','TestActualWorkerTypedSourceAttributeStopsOnlyItsObserver'),
 ('observer-not-started-before-bulk','if first {\n\t\tif err := p.submitWatch','if false && first {\n\t\tif err := p.submitWatch','TestActualWorkerObserverStartsBeforeInitialBulkScanCompletes'),
 ('stop-does-not-join','select {\n\tcase <-w.done:\n\tcase <-ctx.Done():\n\t\treturn ctx.Err()\n\t}', 'if false { <-w.done }', 'TestActualWorkerStopWaitsForIndependentObserverAndTimerWork'),
]
results=[]
for name,old,new,test in cases:
 assert s.count(old)==1,(name,s.count(old))
 d=work/'mutations'/name;d.mkdir(parents=True,exist_ok=True)
 src=d/'watch.go';src.write_text(s.replace(old,new))
 overlay=d/'overlay.json';overlay.write_text(json.dumps({'Replace':{str(base):str(src)}},indent=2)+'\n')
 binary=d/'removelink.test'
 command=['go','test','-race','-c','-overlay',str(overlay),'-o',str(binary),'./plugins/removelink']
 build=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (d/'build.stdout').write_bytes(build.stdout)
 result={'name':name,'build_command':command,'build_exit':build.returncode,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
 if build.returncode==0:
  result['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
  cmd=[str(binary),'-test.v','-test.timeout=18s','-test.run=^'+test+'$'];started=time.monotonic()
  run=subprocess.run(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (d/'run.stdout').write_bytes(run.stdout)
  result.update(run_command=cmd,run_exit=run.returncode,elapsed=time.monotonic()-started,killed=run.returncode!=0)
  binary.unlink();result['binary_removed']=not binary.exists()
 results.append(result)
 (work/'mutations'/'observations.json').write_text(json.dumps(results,indent=2)+'\n')
 print(name,build.returncode,result.get('run_exit'),flush=True)
