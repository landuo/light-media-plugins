from pathlib import Path
import os,json,signal,time
r=Path('/home/admin/light-media-plugins-migration-removelink-20261105');run=r/'main-run-8'
assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/RemoveLink/20261105/owned-only'
ready=json.loads((run/'ui-ready.json').read_text());pid=ready['pid'];cmd=Path('/proc')/str(pid)/'cmdline';argv=cmd.read_bytes().split(b'\0');assert argv[0]==b'/home/admin/light-media-plugins-migration-sdk98-20261105/bin/light-media-host-managed-storage-linux' and any(str(run).encode()in x for x in argv)
assert (Path('/proc')/str(pid)).stat().st_uid==1000
os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+30
while cmd.exists() and time.monotonic()<deadline:time.sleep(.05)
assert not cmd.exists(),'owned host did not finish graceful stop'
drivers=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes().split(b'\0');env=(p/'environ').read_bytes().split(b'\0')
  if args[0]==str(r/'bin/removelink-main6-linux.test').encode() and ('REMOVELINK_RUNTIME_DIR='+str(run)).encode()in env:
   assert p.stat().st_uid==1000;drivers.append(int(p.name))
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
assert len(drivers)==1,drivers
os.kill(drivers[0],signal.SIGTERM)
meta={'classification':'owned Main8 harness error: REMOVELINK_UI_WAIT=0 is nonempty and source driver waits UI for any nonempty value; loopback-only run had no browser execution. Host gracefully stopped before terminating driver; no ui-complete fabricated; no cold/reset/uninstall tail claim','host_pid':pid,'driver_pid':drivers[0],'host_gracefully_joined':True,'no_ui_complete':not(run/'ui-complete').exists(),'fix':'fresh Main9 with REMOVELINK_UI_WAIT empty, not a product change'}
(r/'main-run-8-harness-stop.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
