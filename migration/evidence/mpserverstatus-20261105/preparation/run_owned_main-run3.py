#!/usr/bin/env python3
"""NAS test orchestration only. Product and driver processes are Go executables."""
from pathlib import Path
import datetime
import hashlib
import json
import socket
import socketserver
import subprocess
import threading
import time

R = Path('/home/admin/light-media-plugins-migration-mps-20261105')
MARKER = 'light-media-plugins/MPServerStatus/20261105/owned-only'
LABEL = 'light-media-plugins.MPServerStatus.20261105'
NETWORK = 'lm-plugins-mps-internal-20261105'
IMAGE = 'sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881'
NAME = 'lm-plugins-mps-main-20261105-run3'
RUN = R / 'main-run-3'
assert (R / '.task-owned').read_text().strip() == MARKER
assert not RUN.exists()
RUN.mkdir(mode=0o700)
ca = RUN / 'owned-ca.pem'
assert not ca.exists()
ca.write_bytes(b'')
ca.chmod(0o644)
net = json.loads(subprocess.check_output(['docker', 'network', 'inspect', NETWORK]))[0]
assert net['Internal'] and net['Labels']['task'] == LABEL
expected = {
    'light-media-host75e-linux': '0162d7edd2c22af31b2adf6348c224304d020c5800551605d9e172b9c525cce5',
    'mp-server-status-linux-amd64': '66300eecf0ce7d785e3a448c338e163cfa83ac43cb13bce3e4efaeebfe852055',
    'mp-server-status-update-linux-amd64': '748fd4d48d919d69ae64af021f8ce8ede962a5035c7d3c0ae4c85633302624f4',
    'mpserverstatus-main-tests-linux-amd64': '8a35d384334d80f7c91c12a5aa79fa081fb0d46d2041486514afb8435de2c180',
}
for name, checksum in expected.items():
    p = R / 'bin' / name
    assert p.is_file() and not p.is_symlink()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == checksum, name
    p.chmod(0o755)
environment = {
    'MPS_HOST_BINARY': '/owned/bin/light-media-host75e-linux',
    'MPS_WORKER_BINARY': '/owned/bin/mp-server-status-linux-amd64',
    'MPS_UPDATE_WORKER_BINARY': '/owned/bin/mp-server-status-update-linux-amd64',
    'MPS_RUNTIME_DIR': '/owned/main-run-3',
    'MPS_NAMESPACE_OWNED': '1',
    'MPS_OWNED_CA_FILE': '/owned/main-run-3/owned-ca.pem',
    'MPS_LISTEN': '0.0.0.0:36255',
    'MPS_PUBLIC_URL': 'http://192.168.8.129:36255',
    'MPS_UI_WAIT': '1',
}
args = ['docker', 'run', '--rm', '--name', NAME, '--label', 'task=' + LABEL,
        '--no-healthcheck', '--network', NETWORK,
        '--add-host', 'movie-pilot.org:127.0.0.1', '--user', '1000:1000',
        '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--sysctl', 'net.ipv4.ip_unprivileged_port_start=0',
        '--tmpfs', '/tmp:rw,nosuid,size=128m',
        '--mount', f'type=bind,src={R},dst=/owned',
        '--mount', f'type=bind,src={ca},dst=/etc/ssl/certs/ca-certificates.crt,readonly']
for key, value in environment.items():
    args.extend(['-e', key + '=' + value])
args.extend(['--entrypoint', '/owned/bin/mpserverstatus-main-tests-linux-amd64', IMAGE,
             '-test.run', '^TestMPServerStatusActualMainOwnedNamespace$', '-test.v', '-test.timeout', '70m'])
meta = {'classification': 'actual ordinary published75e Go main + current98 MPS worker in strictly owned isolated namespace; synthetic HTTPS/Nginx-shaped fixture, real OS hosts lookup and native verified TLS; no public upstream availability claim',
        'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': args, 'binary_sha256': expected, 'environment': environment,
        'network': {'name': NETWORK, 'id': net['Id'], 'internal': True},
        'stable_public_CA_inode_before': ca.stat().st_ino,
        'relay': {'bind': '192.168.8.129:36255', 'mode': 'fixed transparent TCP, no parsing or payload logging'},
        'python_role': 'temporary test orchestration/transport only, not product/worker runtime'}
record = R / 'main-run-3-command.json'
record.write_text(json.dumps(meta, indent=2) + '\n')
log = (R / 'main-run-3.log').open('wb')
ip = None
class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        if not ip:
            return
        try:
            upstream = socket.create_connection((ip, 36255), timeout=5)
        except OSError:
            return
        with upstream:
            upstream.settimeout(None)
            def copy(source, target):
                try:
                    while True:
                        body = source.recv(65536)
                        if not body:
                            break
                        target.sendall(body)
                except OSError:
                    pass
                try:
                    target.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
            out = threading.Thread(target=copy, args=(self.request, upstream), daemon=True)
            out.start()
            copy(upstream, self.request)
            out.join(timeout=5)

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

server = Server(('192.168.8.129', 36255), Relay)
threading.Thread(target=server.serve_forever, daemon=True).start()
process = None
try:
    process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(100):
        status = subprocess.run(['docker', 'inspect', NAME], capture_output=True, text=True)
        if status.returncode == 0:
            c = json.loads(status.stdout)[0]
            assert c['Config']['Labels']['task'] == LABEL
            assert c['HostConfig']['NetworkMode'] == NETWORK
            ip = c['NetworkSettings']['Networks'][NETWORK]['IPAddress']
            if ip:
                break
        if process.poll() is not None:
            break
        time.sleep(.1)
    assert ip, 'owned container did not acquire namespace address'
    
    meta['relay']['fixed_target'] = ip + ':36255'
    record.write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps({'started_owned_container': NAME, 'fixed_target': ip, 'public_url': environment['MPS_PUBLIC_URL']}), flush=True)
    code = process.wait()
except BaseException as failure:
    meta['wrapper_error'] = {'type': type(failure).__name__, 'message': str(failure)}
    if process is not None and process.poll() is None:
        check = subprocess.run(['docker','inspect',NAME], capture_output=True, text=True)
        if check.returncode == 0:
            actual = json.loads(check.stdout)[0]
            assert actual['Config']['Labels']['task'] == LABEL
            subprocess.run(['docker','stop','--time','10',NAME], capture_output=True)
        code = process.wait(timeout=20)
    else:
        code = process.returncode if process is not None else 1
    if code == 0: code = 1
finally:
    server.shutdown()
    server.server_close()
    log.close()
meta.update(exit_code=code, ended_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            stable_public_CA_inode_after=ca.stat().st_ino,
            container_auto_removed=not bool(subprocess.check_output(['docker', 'ps', '-aq', '--filter', 'name=^/' + NAME + '$']).strip()))
record.write_text(json.dumps(meta, indent=2) + '\n')
print(json.dumps({'exit_code': code, 'container_auto_removed': meta['container_auto_removed']}), flush=True)
print((R / 'main-run-3.log').read_text()[-6000:])
raise SystemExit(code)
