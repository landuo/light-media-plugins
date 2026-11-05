import pathlib,uuid,subprocess,json,hashlib
w=pathlib.Path(__file__).resolve().parent
label='lm-plugin-removelink-repr-20261106-'+uuid.uuid4().hex
command=['ssh','admin@192.168.8.129','docker run --rm -i --label task='+label+' --network none --read-only --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=8m,mode=1777 --entrypoint python sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -I -B -S -']
payload=(w/'repr_oracle.py').read_bytes()
r=subprocess.run(command,input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(w/'source.stdout.json').write_bytes(r.stdout);(w/'source.stderr').write_bytes(r.stderr)
cleanup=['ssh','admin@192.168.8.129','docker ps -aq --filter label=task='+label]
c=subprocess.run(cleanup,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(w/'source-command.json').write_text(json.dumps({'command':command,'exit':r.returncode,'payload_sha256':hashlib.sha256(payload).hexdigest(),'cleanup_command':cleanup,'cleanup_exit':c.returncode,'remaining_containers':c.stdout.decode(),'cleanup_stderr':c.stderr.decode(),'staging_files':'none; source stdin only; disposable tmpfs removed with container'},indent=2)+'\n')
assert r.returncode==0,r.stderr.decode()
assert c.returncode==0 and not c.stdout.strip(),c.stdout.decode()
x=json.loads(r.stdout);print(x['runtime'],x['unicode_version'],x['repr_count'],x['repr_sha256'])
