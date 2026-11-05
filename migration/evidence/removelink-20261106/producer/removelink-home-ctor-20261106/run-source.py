import pathlib,subprocess,json,uuid,hashlib
w=pathlib.Path(__file__).resolve().parent;image='sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881';payload=(w/'source-ctor-payload.py').read_bytes();results=[];commands=[]
for mode,uid in [('present-empty',65533),('present-value',65533),('absent-found',65534),('absent-unmapped',65533)]:
 label='lm-plugin-removelink-ctor-'+uuid.uuid4().hex
 cmd=['ssh','admin@192.168.8.129',f'docker run --rm -i --label task={label} --network none --read-only --user {uid}:{uid} --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=8m,mode=1777 --entrypoint python {image} -I -B -S - {mode}']
 r=subprocess.run(cmd,input=payload,capture_output=True);(w/(mode+'-source.stdout')).write_bytes(r.stdout);(w/(mode+'-source.stderr')).write_bytes(r.stderr)
 cleanup=['ssh','admin@192.168.8.129','docker ps -aq --filter label=task='+label];c=subprocess.run(cleanup,capture_output=True)
 commands.append({'mode':mode,'command':cmd,'exit':r.returncode,'cleanup_command':cleanup,'cleanup_exit':c.returncode,'remaining':c.stdout.decode(),'payload_sha256':hashlib.sha256(payload).hexdigest()});(w/'source-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 assert r.returncode==0 and c.returncode==0 and not c.stdout.strip(),(r.stderr,c.stdout)
 results.append(json.loads(r.stdout))
(w/'source-ctor-oracle.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
