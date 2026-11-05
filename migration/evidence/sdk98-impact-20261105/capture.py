from pathlib import Path
import json,hashlib,sys,subprocess
r=Path.cwd();p=r/'work/migration-20261105/sdk98-impact-20261105';paths=[]
for b in ['plugins/categoryeditor','plugins/torrenttransfer','plugins/sitestatistic','cmd/category-editor','cmd/torrent-transfer','cmd/site-statistic','internal/sdk']:paths.extend(x for x in (r/b).rglob('*')if x.is_file())
paths.extend(r/x for x in ['go.mod','go.sum','SDK_ORIGIN.json','tests/integration/testhost_main_test.go','tests/integration/sitestatistic_helpers_test.go','tests/integration/sitestatistic_main_test.go','tests/integration/sdk98_impact_test.go','tests/integration/sdk98_impact_helpers_test.go'])
x={'classification':'conservative current accepted consumer+SDK+exactdriver compilation inputs; excludes unrelated WIP integration drivers','files':{str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(paths)}}
(p/sys.argv[1]).write_text(json.dumps(x,indent=2)+'\n');print(len(x['files']))
