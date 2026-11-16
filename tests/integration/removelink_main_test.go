package integration

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

// Actual ordinary cmd/server and independent production worker, not App.Handler
// or a synthetic HostCaller. Root runs this on an owned Linux directory only.
func TestRemoveLinkActualMain(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("RemoveLink delivered runtime is Linux; compile/skip is not main acceptance")
	}
	worker, update, frontend := os.Getenv("REMOVELINK_WORKER_BINARY"), os.Getenv("REMOVELINK_UPDATE_WORKER_BINARY"), os.Getenv("REMOVELINK_FRONTEND_DIR")
	if worker == "" || update == "" || frontend == "" {
		t.Skip("opt-in main requires worker/update/frontend paths; no acceptance executed")
	}
	if os.Geteuid() == 0 {
		t.Fatal("ordinary EACCES acceptance requires non-root owned execution")
	}
	first := rmLoadRelease(t, worker, frontend)
	second := rmLoadRelease(t, update, frontend)
	if first.version != "2.18" || second.version == first.version {
		t.Fatal("initial source2.18 and explicit version-only test update required")
	}
	s := rmNewMain(t)
	repo := rmRepo(t, first)
	s.record("rm_artifact_inputs", map[string]any{"initial_version": first.version, "initial_worker_sha256": first.workerHash, "initial_zip_sha256": first.hash, "initial_files": first.inventory, "fixture_update_version": second.version, "fixture_update_worker_sha256": second.workerHash, "not_upstream_release": true})
	s.installRM(repo, false)
	s.config(rmSource, map[string]any{})
	s.frontendRM(rmSource)
	var form struct {
		Model map[string]any `json:"model"`
	}
	raw := s.ok("GET", "/api/plugins/"+rmSource+"/form", nil)
	if json.Unmarshal(raw, &form) != nil || len(form.Model) != 13 || form.Model["enabled"] != false {
		t.Fatal("actual source13defaults", string(raw))
	}
	pid := s.workersRM()[rmSource]
	if pid == 0 {
		t.Fatal("actual installed independent worker absent")
	}
	missing := func(paths []string) bool {
		for _, p := range paths {
			if rmExists(p) {
				return false
			}
		}
		return true
	}
	allPresent := func(paths []string) {
		t.Helper()
		for _, p := range paths {
			if !rmExists(p) {
				t.Fatal("owned source-preserved file missing", p)
			}
		}
	}
	removeSource := func(p string) {
		t.Helper()
		if e := os.Remove(p); e != nil {
			t.Fatal(e)
		}
		s.record("rm_external_owned_delete", map[string]any{"path": p, "at": time.Now().UTC().Format(time.RFC3339Nano)})
	}
	samePID := func() {
		t.Helper()
		if got := s.workersRM()[rmSource]; got != pid {
			t.Fatal("same-object save/failure replaced worker", pid, got)
		}
	}

	// Actual fixed333/Python3.12 getter observations: positive/negative float
	// overflow is truthy, underflow is false, and containers use their length.
	// Keep JSON tokens intact; mainHost.config's ordinary float decoder cannot
	// compare these values. No watch directories or deletion are configured.
	for _, c := range []struct {
		raw  string
		want bool
	}{{"1e400", true}, {"-1e400", true}, {"1e-400", false}, {"0", false}, {`"false"`, true}, {"[]", false}, {"[0]", true}, {"{}", false}} {
		body := map[string]any{"enabled": json.RawMessage(c.raw)}
		ack := s.ok("PUT", "/api/plugins/"+rmSource, body)
		var result struct {
			Success bool `json:"success"`
		}
		if json.Unmarshal(ack, &result) != nil || !result.Success {
			t.Fatal("explicit raw-state init acknowledgement", string(ack))
		}
		var stored map[string]json.RawMessage
		config := s.ok("GET", "/api/plugins/"+rmSource, nil)
		if json.Unmarshal(config, &stored) != nil || string(stored["enabled"]) != c.raw || len(stored) != 1 {
			t.Fatal("raw state config changed", string(config), c.raw)
		}
		var cards []struct {
			InstanceID string `json:"instance_id"`
			State      bool   `json:"state"`
		}
		local := s.ok("GET", "/api/plugins?state=installed", nil)
		if json.Unmarshal(local, &cards) != nil {
			t.Fatal("actual installed cards", string(local))
		}
		found := false
		for _, card := range cards {
			if card.InstanceID == rmSource {
				found = true
				if card.State != c.want {
					t.Fatal("source raw-state truth", c.raw, card.State, c.want)
				}
			}
		}
		if !found {
			t.Fatal("state probe lost actual installed class")
		}
		samePID()
	}
	s.record("rm_raw_state_source8", map[string]any{"cases": 8, "ordinary_HTTP_config_and_local_state": true, "same_real_worker": true, "source": "fixed333 Python3.12 RemoveLink.get_state:554-555; raw-state-source-oracle.json"})

	// Actual100-link event plus an existing keyword-named alias. Source bulk
	// scan:259-302 ignores keyword filters; unlink:1246-1274 checks excluded
	// directories only. Keywords gate created/deleted events, not those aliases.
	immediate := filepath.Join(s.files, "immediate")
	source, links := rmLinks(t, immediate, "immediate", 100)
	protected := filepath.Join(s.home, "protected.mkv")
	if e := os.Link(source, protected); e != nil {
		t.Fatal(e)
	}
	keyword := filepath.Join(immediate, "保留-keyword.mkv")
	if e := os.Link(source, keyword); e != nil {
		t.Fatal(e)
	}
	trick := filepath.Join(immediate, "show.trickplay", "ignored.mkv")
	if e := os.MkdirAll(filepath.Dir(trick), 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.Link(source, trick); e != nil {
		t.Fatal(e)
	}
	cfg := rmConfig(immediate+"\n"+s.home, false)
	cfg["exclude_dirs"] = "~/protected.mkv"
	cfg["exclude_keywords"] = "保留"
	cfg["delete_history"] = true
	cfg["delete_torrents"] = true
	cfg["notify"] = true
	s.configRM(rmSource, cfg)
	samePID()
	s.observeFiles("before100", append(append([]string{source, protected, keyword, trick}, links...), s.home))
	removeSource(source)
	rmWait(t, "actual inotify100links plus preexisting keyword alias cleanup", 15*time.Second, func() bool { return missing(append(append([]string{}, links...), keyword)) })
	allPresent([]string{protected, trick})
	s.observeFiles("after100", append(append([]string{source, protected, keyword, trick}, links...), s.home))
	samePID()
	// A keyword in the deleted event's own path suppresses the cleanup. The
	// later created event is a real FIFO observer barrier, not a fixed sleep.
	keywordDir := filepath.Join(s.files, "keyword-trigger")
	keywordSource, keywordLinks := rmLinks(t, keywordDir, "保留-trigger", 2)
	keywordConfig := rmConfig(keywordDir, false)
	keywordConfig["exclude_keywords"] = "保留"
	s.configRM(rmSource, keywordConfig)
	removeSource(keywordSource)
	witness := filepath.Join(keywordDir, "observer-witness.txt")
	rmWrite(t, witness)
	rmWait(t, "keyword event followed by actual created-event barrier", 10*time.Second, func() bool { return strings.Contains(s.logsRM(rmSource), "监测到新增文件："+witness) })
	allPresent(keywordLinks)
	s.observeFiles("keyword-event-suppressed", append(keywordLinks, witness))
	samePID()

	// Ordinary native write failure is false, not a guard: read/traverse remain
	// allowed while write denied. Other links and later events must still work.
	failure := filepath.Join(s.files, "permission")
	original, ordinary := rmLinks(t, failure, "permission", 1)
	deniedDir := filepath.Join(failure, "no-write")
	if e := os.MkdirAll(deniedDir, 0700); e != nil {
		t.Fatal(e)
	}
	denied := filepath.Join(deniedDir, "denied.mkv")
	if e := os.Link(original, denied); e != nil {
		t.Fatal(e)
	}
	s.configRM(rmSource, rmConfig(failure, false))
	if e := os.Chmod(deniedDir, 0500); e != nil {
		t.Fatal(e)
	}
	defer os.Chmod(deniedDir, 0700)
	removeSource(original)
	rmWait(t, "other link progresses after native EACCES", 10*time.Second, func() bool { return missing(ordinary) })
	allPresent([]string{denied})
	rmWait(t, "ordinary false deletion is visible", 8*time.Second, func() bool { return strings.Contains(s.logsRM(rmSource), "local deletion not confirmed") })
	s.observeFiles("ordinary-EACCES", append(ordinary, denied))
	samePID()
	if e := os.Chmod(deniedDir, 0700); e != nil {
		t.Fatal(e)
	}
	retry := filepath.Join(failure, "retry.mkv")
	if e := os.Link(denied, retry); e != nil {
		t.Fatal(e)
	}
	rmWait(t, "actual created event observed", 8*time.Second, func() bool { return strings.Contains(s.logsRM(rmSource), "监测到新增文件："+retry) })
	removeSource(retry)
	rmWait(t, "same observer recovers after permission restored", 10*time.Second, func() bool { return !rmExists(denied) })
	samePID()

	// Source Path.unlink requires write/search on its parent, without read.
	// This must traverse the real RemoveLink adapter and ordinary host, not
	// merely a direct Storage.Delete fixture that bypasses authorizeDir.
	noReadRoot := filepath.Join(s.files, "parent-search-only")
	noReadSource, _ := rmLinks(t, noReadRoot, "search-only", 0)
	noReadParent := filepath.Join(noReadRoot, "no-read")
	if e := os.MkdirAll(noReadParent, 0700); e != nil {
		t.Fatal(e)
	}
	noReadAlias := filepath.Join(noReadParent, "selected.mkv")
	noReadRetained := filepath.Join(s.files, "retained-outside-search-only-monitor.mkv")
	for _, p := range []string{noReadAlias, noReadRetained} {
		if e := os.Link(noReadSource, p); e != nil {
			t.Fatal(e)
		}
	}
	retainedBefore, e := os.Stat(noReadRetained)
	if e != nil {
		t.Fatal(e)
	}
	s.configRM(rmSource, rmConfig(noReadRoot, false))
	if e = os.Chmod(noReadParent, 0300); e != nil {
		t.Fatal(e)
	}
	defer os.Chmod(noReadParent, 0700)
	removeSource(noReadSource)
	rmWait(t, "actual adapter and host unlink without parent read permission", 10*time.Second, func() bool { return !rmExists(noReadAlias) })
	if e = os.Chmod(noReadParent, 0700); e != nil {
		t.Fatal(e)
	}
	retainedAfter, e := os.Stat(noReadRetained)
	if e != nil || !os.SameFile(retainedBefore, retainedAfter) {
		t.Fatal("unmonitored hardlink inode changed", e)
	}
	s.observeFiles("parent0300-real-plugin-adapter", []string{noReadSource, noReadAlias, noReadRetained})
	samePID()

	// A real10second source Timer, followed by source recreation protection.
	timerDir := filepath.Join(s.files, "timer")
	timer, targets := rmLinks(t, timerDir, "timer", 2)
	timerConfig := rmConfig(timerDir, true)
	s.configRM(rmSource, timerConfig)
	started := time.Now()
	removeSource(timer)
	s.queuedRM(rmSource, "timer")
	time.Sleep(8 * time.Second)
	allPresent(targets)
	rmWait(t, "real minimum10second timer effects", 10*time.Second, func() bool { return missing(targets) })
	elapsed := time.Since(started)
	if elapsed < 9*time.Second {
		t.Fatal("source timer ran early", elapsed)
	}
	s.record("rm_real_timer", map[string]any{"elapsed_ms": elapsed.Milliseconds(), "minimum_source_delay_seconds": 10})
	samePID()
	recreated, recreatedLinks := rmLinks(t, timerDir, "recreated", 2)
	s.configRM(rmSource, timerConfig)
	removeSource(recreated)
	s.queuedRM(rmSource, "recreated")
	rmWrite(t, recreated)
	time.Sleep(11 * time.Second)
	allPresent(recreatedLinks)
	rmWait(t, "source recreation skip actually executed", 5*time.Second, func() bool { return strings.Contains(s.logsRM(rmSource), recreated+" 已被重新创建") })
	s.observeFiles("recreated-before-due", append(recreatedLinks, recreated))
	samePID()

	// One local STRM storage match, real media/scrap removal and unrelated file
	// retained. History-none is source false; src-only event is not torrent proof.
	strmDir := filepath.Join(s.files, "strm")
	media := filepath.Join(s.files, "media")
	strm := filepath.Join(strmDir, "OwnedFilm.strm")
	video := filepath.Join(media, "OwnedFilm.1080p.mkv")
	nfo := filepath.Join(media, "OwnedFilm.1080p.nfo")
	unrelatedNFO := filepath.Join(media, "OwnedFilm.nfo")
	poster := filepath.Join(media, "poster.jpg")
	keep := filepath.Join(media, "keep.txt")
	for _, p := range []string{strm, video, nfo, unrelatedNFO, poster, keep} {
		rmWrite(t, p)
	}
	strmConfig := rmConfig("", false)
	strmConfig["monitor_strm_deletion"] = true
	strmConfig["strm_path_mappings"] = strmDir + ":local:" + media
	strmConfig["delete_scrap_infos"] = true
	strmConfig["delete_history"] = true
	s.configRM(rmSource, strmConfig)
	removeSource(strm)
	rmWait(t, "real local STRM native storage cleanup", 10*time.Second, func() bool { return missing([]string{video, nfo, poster}) })
	allPresent([]string{unrelatedNFO, keep})
	s.observeFiles("STRM", []string{strm, video, nfo, unrelatedNFO, poster, keep})
	samePID()

	// Current roots revocation must be a real failure, never ordinary false. No
	// HTTP source event injection and no old FileItem grant authorizes deletion.
	guardDir := filepath.Join(s.files, "guard")
	guardSource, guardTargets := rmLinks(t, guardDir, "guard", 2)
	guardConfig := rmConfig(guardDir, false)
	s.configRM(rmSource, guardConfig)
	beforeGuard := strings.Count(s.logsRM(rmSource), "存储宿主调用失败")
	quarantine := filepath.Join(s.files, "unrelated-scope")
	if e := os.MkdirAll(quarantine, 0700); e != nil {
		t.Fatal(e)
	}
	s.ok("PUT", "/api/settings", map[string]any{"allowed_roots": []string{quarantine}})
	removeSource(guardSource)
	rmWait(t, "actual current storage guard refusal", 10*time.Second, func() bool { return strings.Count(s.logsRM(rmSource), "存储宿主调用失败") > beforeGuard })
	allPresent(guardTargets)
	samePID()
	s.observeFiles("current-root-guard", guardTargets)
	s.ok("PUT", "/api/settings", map[string]any{"allowed_roots": []string{s.files}})
	s.configRM(rmSource, guardConfig)
	samePID()
	allPresent(guardTargets)

	// Source stop flushes queued90links through the genuine CallCleanup lineage.
	// Public reload returns only after the final file effect and creates new PID.
	queuedDir := filepath.Join(s.files, "queued-stop")
	queued, queuedLinks := rmLinks(t, queuedDir, "queued-stop", 90)
	queuedConfig := rmConfig(queuedDir, true)
	queuedConfig["delay_seconds"] = 86400
	queuedConfig["delete_history"] = true
	queuedConfig["delete_torrents"] = true
	s.configRM(rmSource, queuedConfig)
	removeSource(queued)
	s.queuedRM(rmSource, "queued-stop")
	allPresent(queuedLinks)
	s.ok("POST", "/api/plugins/"+rmSource+"/reload", map[string]any{})
	if !missing(queuedLinks) {
		t.Fatal("reload returned before real90-link cleanup root joined")
	}
	newPID := s.workersRM()[rmSource]
	if newPID == 0 || newPID == pid {
		t.Fatal("reload did not replace actual source worker", pid, newPID)
	}
	pid = newPID
	s.observeFiles("queued-root-after-reload", queuedLinks)

	// Actual clone file/config namespace independent; monitor different files.
	s.ok("POST", "/api/plugins/"+rmSource+"/clone", map[string]any{"suffix": "Owned"})
	clonePID := s.workersRM()[rmClone]
	if clonePID == 0 || clonePID == pid {
		t.Fatal("clone missing/shared worker")
	}
	cloneDir := filepath.Join(s.files, "clone")
	cloneOriginal, cloneLinks := rmLinks(t, cloneDir, "clone", 3)
	cloneConfig := rmConfig(cloneDir, false)
	cloneConfig["owned_unknown"] = "clone separate"
	s.configRM(rmClone, cloneConfig)
	s.config(rmSource, queuedConfig)
	removeSource(cloneOriginal)
	rmWait(t, "clone owned effects", 10*time.Second, func() bool { return missing(cloneLinks) })
	s.config(rmSource, queuedConfig)
	if s.workersRM()[rmSource] != pid {
		t.Fatal("clone changed source process")
	}

	// Version-only test artifact: same business input, explicit fixture version.
	repo.change(second)
	s.installRM(repo, true)
	s.config(rmSource, queuedConfig)
	s.frontendRM(rmSource)
	updated := s.workersRM()[rmSource]
	if updated == 0 || updated == pid {
		t.Fatal("update did not use current executable")
	}
	if s.workersRM()[rmClone] != clonePID || fileHash(t, filepath.Join("/proc", fmt.Sprint(clonePID), "exe")) != first.workerHash || fileHash(t, filepath.Join("/proc", fmt.Sprint(updated), "exe")) != second.workerHash {
		t.Fatal("source update changed clone process/code or failed to activate new source executable")
	}
	for id, version := range map[string]string{rmSource: second.version, rmClone: first.version} {
		var desc struct {
			Version string `json:"version"`
		}
		if data := s.ok("GET", "/api/plugins/"+id+"/frontend", nil); json.Unmarshal(data, &desc) != nil || desc.Version != version {
			t.Fatal("source/clone loaded package version", id, desc.Version, version)
		}
	}
	pid = updated
	s.record("rm_version_fixture_update", map[string]any{"version": second.version, "worker_sha256": second.workerHash, "not_upstream_release": true})
	s.noInheritedModuleDiscovery("all-pre-UI-flows-including-queued-stop")

	// UI operates only empty owned directories; preserves source/clone config
	// independence. Root marks ui-complete after actual frontend screenshots.
	uiDir := filepath.Join(s.files, "ui")
	uiClone := filepath.Join(s.files, "ui-clone")
	for _, p := range []string{uiDir, uiClone} {
		if e := os.MkdirAll(p, 0700); e != nil {
			t.Fatal(e)
		}
	}
	uiConfig := rmConfig(uiDir, false)
	uiConfig["enabled"] = false
	uiCloneConfig := rmConfig(uiClone, false)
	uiCloneConfig["enabled"] = false
	uiCloneConfig["owned_unknown"] = "clone UI namespace"
	s.configRM(rmSource, uiConfig)
	s.configRM(rmClone, uiCloneConfig)
	if os.Getenv("REMOVELINK_UI_WAIT") != "" {
		public := os.Getenv("REMOVELINK_PUBLIC_URL")
		if public == "" {
			public = s.base
		}
		ready, _ := json.Marshal(map[string]any{"url": public, "username": rmUser, "password": rmPassword, "pid": s.cmd.Process.Pid, "source": rmSource, "clone": rmClone, "source_owned_dir": uiDir, "clone_owned_dir": uiClone, "continue_file": filepath.Join(s.root, "ui-complete")})
		if e := os.WriteFile(filepath.Join(s.root, "ui-ready.json"), ready, 0600); e != nil {
			t.Fatal(e)
		}
		s.record("rm_ui_ready", map[string]any{"url": public, "pid": s.cmd.Process.Pid})
		rmWait(t, "Root actual browser complete", 20*time.Minute, func() bool { return rmExists(filepath.Join(s.root, "ui-complete")) })
	}
	uiSource := s.ok("GET", "/api/plugins/"+rmSource, nil)
	uiCloneRaw := s.ok("GET", "/api/plugins/"+rmClone, nil)
	s.record("rm_after_browser_configs", map[string]any{"source": json.RawMessage(uiSource), "clone": json.RawMessage(uiCloneRaw)})

	// Crash, not graceful stop: source volatile pending queue must not replay.
	coldDir := filepath.Join(s.files, "cold")
	cold, coldLinks := rmLinks(t, coldDir, "cold", 70)
	coldConfig := rmConfig(coldDir, true)
	coldConfig["delay_seconds"] = 86400
	s.configRM(rmSource, coldConfig)
	removeSource(cold)
	s.queuedRM(rmSource, "cold")
	allPresent(coldLinks)
	oldPIDs := s.workersRM()
	s.crashRM()
	s.startRM()
	pids := s.workersRM()
	for _, id := range []string{rmSource, rmClone} {
		if pids[id] == 0 || pids[id] == oldPIDs[id] {
			t.Fatal("cold main retained/missed worker", oldPIDs, pids)
		}
	}
	time.Sleep(time.Second)
	allPresent(coldLinks)
	s.config(rmSource, coldConfig)
	if got := s.ok("GET", "/api/plugins/"+rmClone, nil); !bytes.Equal(got, uiCloneRaw) {
		t.Fatal("cold clone config changed", string(got), string(uiCloneRaw))
	}
	s.observeFiles("cold-no-replay", coldLinks)
	pid = pids[rmSource]

	// Ordinary reset/uninstall/reinstall. Base retains configuration storage;
	// clone removal purges namespace. No backup API or private DB writer used.
	finalConfig := rmConfig(uiDir, false)
	finalConfig["enabled"] = false
	s.configRM(rmSource, finalConfig)
	s.ok("POST", "/api/plugins/"+rmClone+"/reset", map[string]any{})
	s.config(rmClone, map[string]any{})
	s.config(rmSource, finalConfig)
	raw = s.ok("DELETE", "/api/plugins/"+rmClone, nil)
	if !bytes.Contains(raw, []byte(`"data_retained":false`)) {
		t.Fatal("clone purge response", string(raw))
	}
	if rmExists(filepath.Join(s.dir, "plugin-packages", rmClone)) {
		t.Fatal("clone code namespace retained")
	}
	s.config(rmSource, finalConfig)
	raw = s.ok("DELETE", "/api/plugins/"+rmSource, nil)
	if !bytes.Contains(raw, []byte(`"data_retained":true`)) {
		t.Fatal("source retain response", string(raw))
	}
	s.config(rmSource, map[string]any{})
	if !rmExists(filepath.Join(s.dir, "plugin-packages", rmSource)) {
		t.Fatal("source retained code absent")
	}
	allPresent(coldLinks)
	s.installRM(repo, false)
	s.config(rmSource, finalConfig)
	s.frontendRM(rmSource)
	s.ok("POST", "/api/plugins/"+rmSource+"/reset", map[string]any{})
	s.config(rmSource, map[string]any{})
	allPresent(coldLinks)
	repo.mu.Lock()
	hits := map[string]int{}
	for k, v := range repo.hits {
		hits[k] = v
	}
	repo.mu.Unlock()
	s.record("rm_main_complete", map[string]any{"repository_hits": hits, "Linux": runtime.GOOS, "worker_count_before_cleanup": s.workersRM(), "history_none_not_faked_as_deleted_row": true, "src_only_event_not_claimed_as_torrent_delete": true, "no_external_message_channel_configured": true})
	s.mainHost.stop()
	for pid := range s.allPIDs {
		s.waitWorkerGone(pid)
	}
	s.record("rm_all_workers_joined", map[string]any{"observed_workers": len(s.allPIDs), "main_exited": true, "all_observed_PIDs_gone": true})
	s.noInheritedModuleDiscovery("full-tail-after-all-worker-joins")
	t.Log("actual ordinary cmd/server+ZIP+production independent worker+owned Linux filesystem completed; browser evidence separate; no synthetic HostCaller/private callback or in-process App")
}
