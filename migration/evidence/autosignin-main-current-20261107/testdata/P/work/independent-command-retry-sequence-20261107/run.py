from pathlib import Path
import hashlib,json,subprocess,time
w=Path(__file__).resolve().parent
sources=json.loads((w/'sources.json').read_text())
payload='SOURCES='+repr(sources)+'\n'+(w/'body-prefix.py').read_text()+(w/'sequence-body.py').read_text()
compile(payload,'sequence-payload.py','exec')
(w/'payload.py').write_text(payload)
remote='docker run --rm -i --no-healthcheck --name lm-independent-command-retry-sequence-20261107 --label migration.review=independent-command-retry-sequence-20261107 --network none --read-only --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --memory 256m --pids-limit 96 --tmpfs /tmp:rw,noexec,nosuid,size=16m --tmpfs /config:rw,noexec,nosuid,size=16m --entrypoint python3 sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -B -'
argv=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','admin@192.168.8.129',remote]
begin=time.monotonic();p=subprocess.run(argv,input=payload.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
(w/'actual.stdout').write_bytes(p.stdout);(w/'actual.stderr').write_bytes(p.stderr)
(w/'command.json').write_text(json.dumps(dict(argv=argv,payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),exit=p.returncode,seconds=time.monotonic()-begin,mounts=[],classification='source-only synthetic replay; no target Main'),indent=2)+'\n')
print(json.dumps(dict(exit=p.returncode,seconds=time.monotonic()-begin,stdout_bytes=len(p.stdout),stderr=p.stderr.decode()[-3000:])))
raise SystemExit(p.returncode)
