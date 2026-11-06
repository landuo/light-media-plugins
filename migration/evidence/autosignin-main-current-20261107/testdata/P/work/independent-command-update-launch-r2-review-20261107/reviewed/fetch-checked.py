CONFIG={'root': '/home/admin/light-media-plugins-root-asi-native-20261107', 'marker': 'light-media-plugins/root-asi-native/20261107/owned-only', 'name': 'lm-root-asi-native-20261107', 'bom': {'bin/host': {'sha256': '8ea38cff7e98f6a1eb7089f7ff04cc8c56fdb41baedfdbc843db13824b999f67', 'bytes': 57217186}, 'bin/worker': {'sha256': '2b77bc3db6c80ff67314a68daa0df90b1595e99ab2bc658ca80cfaafd6a251a0', 'bytes': 12796066}, 'bin/worker-updated': {'sha256': 'e38f19188cfbfe4b295893b9707c1ba8ee77117880ffdcfb7952e77bf0108f36', 'bytes': 12796066}, 'bin/cli': {'sha256': '525e34407b50f4bd38e16d29bfe4d775c8052504f40072789cc8a4b43f4cf1b8', 'bytes': 25215138}, 'bin/driver': {'sha256': 'a2d0a15dc003fd3823cc1ad48cc66f418c71c6403f9651f2c4ea4e0093171591', 'bytes': 9756834}}}
from pathlib import Path
import tarfile,sys,os
r=Path(CONFIG['root']);assert os.getuid()==1000 and r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text()==CONFIG['marker']
names=['attempt5/actual.stdout','attempt5/actual.stderr','attempt5/command.json','attempt5/live-inspect.json','attempt5/inspect-attempts.json','attempt5/live-network.stdout','attempt5/live-network.stderr','owned-r4/runtime/evidence']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as archive:
 for name in names:
  path=r/name
  if not path.exists():continue
  assert not path.is_symlink()and path.resolve().is_relative_to(r.resolve())
  if path.is_dir():
   for f in path.rglob('*'):
    if f.is_file():assert not f.is_symlink()and f.resolve().is_relative_to(path.resolve());archive.add(f,arcname=str(f.relative_to(r)),recursive=False)
  else:archive.add(path,arcname=name,recursive=False)
