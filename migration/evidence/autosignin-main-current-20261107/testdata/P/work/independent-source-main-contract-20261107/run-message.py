from pathlib import Path
import hashlib,json,subprocess,time
w=Path(__file__).resolve().parent
sources={str(p.relative_to(w/'fixed-source')):p.read_text() for p in (w/'fixed-source').rglob('*.py')}
sources.update({'installed-asi/'+p.name:p.read_text() for p in (w/'installed-asi').glob('*.py')})
payload='SOURCES='+repr(sources)+'\n'+(w/'message-body.py').read_text()
(w/'message-payload.py').write_text(payload)
remote='docker run --rm -i --no-healthcheck --name lm-independent-source-main-message-20261107 --label migration.review=independent-source-main-contract-20261107 --network none --read-only --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --memory 256m --pids-limit 96 --tmpfs /tmp:rw,noexec,nosuid,size=16m --tmpfs /config:rw,noexec,nosuid,size=16m --entrypoint python3 sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -B -'
argv=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','admin@192.168.8.129',remote]
begin=time.monotonic()
p=subprocess.run(argv,input=payload.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
(w/'message-actual.stdout').write_bytes(p.stdout);(w/'message-actual.stderr').write_bytes(p.stderr)
(w/'message-command.json').write_text(json.dumps(dict(argv=argv,payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),exit=p.returncode,seconds=time.monotonic()-begin,mounts=[]),indent=2)+'\n')
print(json.dumps(dict(exit=p.returncode,seconds=time.monotonic()-begin,stdout_bytes=len(p.stdout),stderr=p.stderr.decode()[-3500:])))
raise SystemExit(p.returncode)
