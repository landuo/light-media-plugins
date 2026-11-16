CONFIG={'root': '/home/admin/light-media-plugins-root-asi-native-20261107', 'marker': 'light-media-plugins/root-asi-native/20261107/owned-only'}
from pathlib import Path
import tarfile,sys,os
r=Path(CONFIG['root']);assert os.getuid()==1000 and r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text()==CONFIG['marker']
names=['attempt6/actual.stdout','attempt6/actual.stderr','attempt6/command.json','attempt6/live-inspect.json','attempt6/inspect-attempts.json','attempt6/live-network.stdout','attempt6/live-network.stderr','owned-r5/runtime/evidence']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as archive:
 for name in names:
  path=r/name
  if not path.exists():continue
  assert not path.is_symlink()and path.resolve().is_relative_to(r.resolve())
  if path.is_dir():
   for f in path.rglob('*'):
    if f.is_file():assert not f.is_symlink()and f.resolve().is_relative_to(path.resolve());archive.add(f,arcname=str(f.relative_to(r)),recursive=False)
  else:archive.add(path,arcname=name,recursive=False)
