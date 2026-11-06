from pathlib import Path
import hashlib,json,subprocess
P=Path('/Users/accidia/projects/light-media-plugins');W=Path(__file__).resolve().parent
base=P/'work/autosignin-native-main-20261107'
source=(base/'driver.go').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='d06eabb5724e538e7b8db0bac9f9030c3ed72aa5c89bc6a8316757233e1acf9f'
def once(old,new):
    global source
    assert source.count(old)==1,old
    source=source.replace(old,new,1)
once('TestAutoSignInActualMainNativeSourceAndPrivateDrain','TestAutoSignInActualMainCommandsUpdateTimerShutdown')
once('"strings"','"strings"\n"sync"')
once('var repo *httptest.Server','var repoMu sync.RWMutex\nactiveBin,activeDigest,activeManifest:=bin,digest,manifest\nvar repo *httptest.Server')
once('repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {','repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {\nrepoMu.RLock();defer repoMu.RUnlock()')
once('"current_version": manifest["version"], "releases": []any{map[string]any{"version": manifest["version"], "manifest": manifest,','"current_version": activeManifest["version"], "releases": []any{map[string]any{"version": activeManifest["version"], "manifest": activeManifest,')
once('"sha256": digest, "executable_sha256": digest, "size": len(bin)','"sha256": activeDigest, "executable_sha256": activeDigest, "size": len(activeBin)')
once('w.Write(bin)','w.Write(activeBin)')
start=source.index('\trepoOrigin, err := url.Parse(repo.URL)')
end=source.index('\t// The fixed manager disables all ordinary handlers when get_state is false.',start)
proxy_assertion=source[start:end]
source=source[:start]+source[end:]
extra=(W/'extra-stages.go.txt').read_text()+'\n'+proxy_assertion
once('\t// The fixed manager disables all ordinary handlers when get_state is false.',extra+'\n\t// The fixed manager disables all ordinary handlers when get_state is false.')
once('"native_source_Main_complete"','"actual_Main_commands_update_timer_complete"')
once('"actual_attendance": attendance','"initial_private_attendance": attendance')
once('not all ASI/UI/PT/commands/timer/update/globaldrain','bounded Web broadcast/retry, same-version force update, public timer/global drain; not full ASI/UI/live PT/private import')
begin=source.index('func asiOwnedSuccessfulRow(')
end=source.index('func asiOwnedEmptyPage(',begin)
pending=source[begin:end].replace('asiOwnedSuccessfulRow','asiOwnedPendingRow').replace('签到成功','未记录').replace('"success"','"grey"').replace('mdi-check-circle','mdi-minus-circle-outline').replace('autosignin-dot--success','autosignin-dot--none').replace('"1/1"','"0/1"')
pending=pending.replace('return chip && dot && walk(root,', 'return chip && dot && walk(cells[0], func(m map[string]any) bool { return m[\"text\"] == \"暂无记录\" }) && walk(root,')
source=source[:end]+'// Fixed270 get_page640-832: selected sites with no history have a pending row.\n'+pending+source[end:]
(W/'driver.go').write_text(source)
subprocess.run(['gofmt','-w',str(W/'driver.go')],check=True)
mapping=json.loads((base/'driver-overlay.json').read_text())['Replace']
key=str(P/'tests/integration/autosignin_native_source_main_test.go')
mapping[key]=str(W/'driver.go')
(W/'driver-overlay.json').write_text(json.dumps({'Replace':mapping},indent=2)+'\n')
# An owned new binary content marker; no change to the ASI source or version.
cmd=P/'cmd/auto-sign-in/main.go';text=cmd.read_text();needle='manifest := autosignin.Manifest()'
assert text.count(needle)==1
(W/'updated-main.go').write_text(text.replace(needle,needle+'\nmanifest.Description = "Owned same-version update verification build2"'))
subprocess.run(['gofmt','-w',str(W/'updated-main.go')],check=True)
(W/'updated-worker-overlay.json').write_text(json.dumps({'Replace':{str(cmd):str(W/'updated-main.go')}},indent=2)+'\n')
(W/'provenance.json').write_text(json.dumps({'base_driver_sha256':hashlib.sha256((base/'driver.go').read_bytes()).hexdigest(),'driver_sha256':hashlib.sha256((W/'driver.go').read_bytes()).hexdigest(),'variant':'test-only command main overlay changes real manifest description, preserves plugin business source and version','source_contract':'work/independent-source-main-contract-20261107/contract-index.json','status':'prepared_not_built_or_run'},indent=2)+'\n')
