from pathlib import Path
import json,hashlib,subprocess
root=Path.cwd();out=Path(__file__).resolve().parent;rows=json.loads((out/'local-plugin-generated-inventory.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
keep={'ab341eaf':'category-editor-linux','c9685309':'torrent-transfer-linux','6d751143':'remove-link-linux','145f7439':'site-statistic-linux','32780c52':'mp-server-status-linux','d001e679':'plugin-uninstall-linux','8864147b':'remove-link-update-linux','e0b5f2f6':'plugin-uninstall-update-linux','b4d23deb':'owned-pui-fixture-linux','757ce25c':'removelink-business-main-linux.test','406d13fa':'owned-notice-fixture-linux','f24e9b1f':'current-legacy-main-linux.test','01ba473c':'pluginuninstall-current-main-linux.test'}
ps=subprocess.check_output(['ps','-eo','pid=,args=']);assert not any(r['path'].encode()in line for line in ps.splitlines()for r in rows),'owned generated binary still running'
dest=root/'work/migration-20261106/current-acceptance-inputs';assert not dest.exists();dest.mkdir(mode=0o700);kept=set();result=[]
for row in rows:
 p=Path(row['path']);assert p.is_relative_to(root/'work')and not p.is_symlink()and sha(p)==row['sha256']
 prefix=row['sha256'][:8]
 if prefix in keep and prefix not in kept:
  q=dest/keep[prefix];p.rename(q);assert sha(q)==row['sha256'];row.update(action='moved_single_current_compatibility_input',retained_path=str(q));kept.add(prefix)
 else:p.unlink();row['action']='deleted_superseded_or_duplicate_generated_Go_binary'
 result.append(row)
assert kept==set(keep)
private=[]
for name in ['work/migration-20261105/removelink-main6-20261106/private/ui-ready.json','work/migration-20261105/removelink-main7-20261106/private/ui-ready.json','work/migration-20261105/pluginuninstall-main-runtime-20261106/private/ui-ready.json']:
 p=root/name
 if p.exists():
  assert not p.is_symlink()and p.stat().st_mode&0o777==0o600;p.unlink();private.append(name)
record={'classification':'only generated taskGo binaries and no-longer-needed private synthetic UI-ready fixtures; source/raw/proofs remain. One current set moved to a single ignored directory for upcoming shared-SDK impact; prior actual commands keep original paths/hashes, not relabelled.','records':result,'retained_current_inputs':13,'removed_generated_binaries':sum(r['action'].startswith('deleted')for r in result),'private_synthetic_UI_ready_removed':private,'browser':'owned IAB tab closed and in-memory rlkReady cleared; no live handoff remains'}
(out/'local-plugin-cleanup.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'retained':13,'removed_generated':record['removed_generated_binaries'],'private_UI_ready_removed':len(private),'sha256':sha(out/'local-plugin-cleanup.json')}))
