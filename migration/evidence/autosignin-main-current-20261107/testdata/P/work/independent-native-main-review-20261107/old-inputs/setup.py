from pathlib import Path
import os,subprocess
r=Path('/home/admin/light-media-plugins-root-asi-native-20261107')
assert os.getuid()==1000 and not r.exists()
assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+__LM_TEST_'lm-root-asi-native-20261107'__+'$']).strip()
r.mkdir(mode=0o700)
(r/'.task-owned').write_text('light-media-plugins/root-asi-native/20261107/owned-only')
for name in ['bundle','owned']:(r/name).mkdir(mode=0o700)
(r/'owned/.task-owned').write_text('light-media-plugins/root-asi-native/20261107/owned-only')
(r/'owned/runtime').mkdir(mode=0o700)
