from pathlib import Path
import subprocess,json,os,hashlib,uuid,time,shlex
out=Path(__file__).resolve().parent;repo=Path('/Users/accidia/projects/light-media-plugins');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();env=os.environ.copy();env.update(GOFLAGS='',GOOS='linux',GOARCH='amd64',CGO_ENABLED='0',TMPDIR=str(out/'tmp'))
exe=out/'independent-linux.test'; cmd=['go','test','-c','-trimpath','-buildvcs=false','-overlay',str(out/'overlay.json'),'-o',str(exe),'./plugins/removelink']
with (out/'linux-build.stdout').open('wb') as f,(out/'linux-build.stderr').open('wb') as e:r=subprocess.run(cmd,cwd=repo,env=env,stdout=f,stderr=e)
assert r.returncode==0
record={'build_command':cmd,'build_exit':r.returncode,'test_binary_sha256':sha(exe),'explicit_build_env':{k:env[k] for k in ['GOOS','GOARCH','CGO_ENABLED','GOFLAGS']},'classification':'independent Linux UID1000 actual kernel+SDK subprocess+owned filesystem; synthetic host capability peer; no App/Main/real downloader'}
subprocess.run(['go','version','-m',str(exe)],stdout=(out/'linux-test-buildinfo.txt').open('wb'),check=True)
nonce=uuid.uuid4().hex[:12];remote='/home/admin/light-media-plugins-review-removelink59-20261106-'+nonce;marker='lm-independent-removelink59/'+nonce;record.update(remote_owned_directory=remote,marker=marker)
ssh=['ssh','admin@192.168.8.129']; setup='umask 077; mkdir '+shlex.quote(remote)+' && printf %s '+shlex.quote(marker)+' > '+shlex.quote(remote+'/TASK')+' && mkdir '+shlex.quote(remote+'/tmp')
r=subprocess.run(ssh+[setup],capture_output=True);(out/'linux-setup.stdout').write_bytes(r.stdout+r.stderr);assert r.returncode==0
try:
 r=subprocess.run(['scp','-q',str(exe),'admin@192.168.8.129:'+remote+'/review.test'],capture_output=True);(out/'linux-copy.stdout').write_bytes(r.stdout+r.stderr);assert r.returncode==0
 pattern='^(TestActualWorker(UnknownHomeKeepsSourceCatchAndObserverBoundary|IndependentTimerAndObserverCallers|ObserverLanesSerialPerRootAndIndependentAcrossRoots|ObserverStartsBeforeInitialBulkScanCompletes|StopWaitsForIndependentObserverAndTimerWork|TypedSourceAttributeStopsOnlyItsObserver|StopJoinsTimerBeforeQueueFlush|TenObserverRootsFairWhileSixCallbacksBlocked|ObserverToOwnedFilesystemCleanup|ObserverRenameAndStopBeforeDue|ObserverRealTimerDoesNotRunEarly|MoreThan64LinksOwnerWaitsThroughLastEffect|LargeScrapeDirectoryAndFilteredCandidates|QueuedStopAndReloadFlushWithNewFlags|TransientAuthorityFailureStopsLaterEffects|UnknownWriteCancellationRetainsFactNoReplay|FreshStopFlushesUnenteredTaskWithoutReplayingUnknownNotice)|TestActualCleanupRootFlushesOver64LinksBeforeOwnerReturns|TestLinuxSourceObserver(StartFailure|ActualNativeDelete)|TestIndependent(CreatedDuringDelayedExistsKeepsOldLinks|OneObserverErrorDoesNotStopSiblingDirectoryEvents|SourceNamedHomeProtection|DelayOverflowBeforeStop|WorkerUnlinkNoParentReadPrecondition|HomeRuntimeKillsOnlyFailedObserver))$'
 script='set -eu; cd '+shlex.quote(remote)+'; test "$(cat TASK)" = '+shlex.quote(marker)+'; test "$(id -u)" = 1000; chmod 700 review.test; export TMPDIR="$PWD/tmp"; id; sha256sum review.test; ./review.test -test.v -test.timeout=150s -test.count=1 -test.run='+shlex.quote(pattern)
 cmd=ssh+[script];start=time.time()
 with (out/'linux-run.stdout').open('wb') as f,(out/'linux-run.stderr').open('wb') as e:r=subprocess.run(cmd,stdout=f,stderr=e)
 record.update(run_command=cmd,run_exit=r.returncode,elapsed=time.time()-start)
finally:
 script='set -eu; cd '+shlex.quote(remote)+'; test "$(cat TASK)" = '+shlex.quote(marker)+'; test "$(sha256sum review.test | cut -d " " -f1)" = '+shlex.quote(record['test_binary_sha256'])+'; rm review.test; test -z "$(find tmp -mindepth 1 -print -quit)"; rmdir tmp; rm TASK; cd /home/admin; rmdir '+shlex.quote(remote)+'; test ! -e '+shlex.quote(remote)
 r=subprocess.run(ssh+[script],capture_output=True);(out/'linux-cleanup.stdout').write_bytes(r.stdout+r.stderr);record.update(cleanup_command=ssh+[script],remote_cleanup_exit=r.returncode)
 (out/'linux-replay.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
