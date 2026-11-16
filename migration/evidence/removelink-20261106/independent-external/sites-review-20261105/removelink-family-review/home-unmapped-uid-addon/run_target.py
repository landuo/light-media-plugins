from pathlib import Path
import os,json,hashlib,subprocess,uuid,shlex
root=Path('/Users/accidia/projects/light-media-plugins');out=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();manifest=root/'work/migration-20261105/removelink-home-error-20261106/current-files-final.json';assert sha(manifest.read_bytes())=='d9cd3f920c22593599464741b3bd5a43c46c4acf4b227c57ff014b0cb7b6d823'
rows=json.loads(manifest.read_text());assert all(sha((root/r['path']).read_bytes())==r['sha256'] for r in rows)
o=out/'overlay.json';o.write_text(json.dumps({'Replace':{str(root/'plugins/removelink/independent_unmapped_uid_test.go'):str(out/'target_test.go')}},indent=2)+'\n');exe=out/'target-linux.test';env=os.environ.copy();env.update(GOFLAGS='',GOOS='linux',GOARCH='amd64',CGO_ENABLED='0')
cmd=['go','test','-c','-trimpath','-buildvcs=false','-overlay',str(o),'-o',str(exe),'./plugins/removelink']
with (out/'target-build.stdout').open('wb') as f,(out/'target-build.stderr').open('wb') as e:r=subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=e)
assert r.returncode==0;h=sha(exe.read_bytes());nonce=uuid.uuid4().hex[:12];remote='/home/admin/light-media-plugins-review-homeuid-'+nonce;marker='lm-review-homeuid/'+nonce;label='lm-review-homeuid-'+nonce;ssh=['ssh','admin@192.168.8.129']
r=subprocess.run(ssh+['umask 077; mkdir '+shlex.quote(remote)+' && printf %s '+shlex.quote(marker)+' > '+shlex.quote(remote+'/TASK')],capture_output=True);assert r.returncode==0
try:
 r=subprocess.run(['scp','-q',str(exe),'admin@192.168.8.129:'+remote+'/review.test'],capture_output=True);assert r.returncode==0
 command='set -eu; cd '+shlex.quote(remote)+'; test "$(cat TASK)" = '+shlex.quote(marker)+'; chmod 755 review.test; test "$(sha256sum review.test | cut -d " " -f1)" = '+h+'; docker run --rm --label task='+label+' --network none --read-only --user 65533:65533 --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777 --mount type=bind,src='+remote+'/review.test,dst=/usr/local/bin/rlk-review.test,readonly --entrypoint /usr/bin/env sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -u HOME -u USER /usr/local/bin/rlk-review.test -test.v -test.timeout=20s -test.run=^TestIndependentUnmappedCurrentUIDHomeDoesNotBecomeRoot$'
 r=subprocess.run(ssh+[command],capture_output=True);(out/'target-run.stdout').write_bytes(r.stdout);(out/'target-run.stderr').write_bytes(r.stderr)
 record={'classification':'actual target constructor/path helper in read-only network-none fixedLinux image UID65533 with HOME/USER absent; not App/SDK/file mutation','command':ssh+[command],'exit':r.returncode,'binary_sha256':h,'producer_manifest_sha256':sha(manifest.read_bytes()),'target_test_sha256':sha((out/'target_test.go').read_bytes())}
finally:
 clean='set -eu; cd '+shlex.quote(remote)+'; test "$(cat TASK)" = '+shlex.quote(marker)+'; test "$(sha256sum review.test | cut -d " " -f1)" = '+h+'; test -z "$(docker ps -aq --filter label=task='+label+')"; rm review.test TASK; cd /home/admin; rmdir '+shlex.quote(remote)
 c=subprocess.run(ssh+[clean],capture_output=True);(out/'target-cleanup.stdout').write_bytes(c.stdout+c.stderr);record.update(cleanup_command=ssh+[clean],cleanup_exit=c.returncode)
 (out/'target-command.json').write_text(json.dumps(record,indent=2)+'\n');exe.unlink()
print(json.dumps(record));print((out/'target-run.stdout').read_text())
