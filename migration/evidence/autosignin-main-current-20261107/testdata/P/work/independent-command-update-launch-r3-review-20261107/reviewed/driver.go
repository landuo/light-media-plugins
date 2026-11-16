package integration

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"
)

// Original source expectations: fixed8a native Site identity/lifecycle and
// installed270 ASI __do/get_page/init_plugin/stop_service. The independent
// original Main contract96506846 proves private scheduler shutdown waits for
// an already-running callback before applying the next in-memory config.
// No original site/service/data or real network destination is used here.
func TestAutoSignInActualMainCommandsUpdateTimerShutdown(t *testing.T) {
	worker, cli := os.Getenv("AUTOSIGNIN_WORKER_BINARY"), os.Getenv("NATIVE_SOURCE_CLI_BINARY")
	if worker == "" || cli == "" {
		t.Skip("owned actual Linux Main/worker/CLI opt-in required")
	}
	if runtime.GOOS != "linux" || os.Geteuid() != 1000 {
		t.Fatal("Linux UID1000 required")
	}
	dir := os.Getenv("CATEGORYEDITOR_RUNTIME_DIR")
	root := os.Getenv("OWNED_ASI_ROOT")
	if root != "/owned" || filepath.Clean(dir) != filepath.Join(root, "runtime") {
		t.Fatal("named exclusive container runtime required")
	}
	st, err := os.Lstat(root)
	if err != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
		t.Fatal("owned root type", err)
	}
	if owner, ok := st.Sys().(*syscall.Stat_t); !ok || owner.Uid != 1000 {
		t.Fatal("owned root UID")
	}
	marker, err := os.ReadFile(filepath.Join(root, ".task-owned"))
	if err != nil || strings.TrimSpace(string(marker)) != "light-media-plugins/root-asi-native/20261107/owned-only" {
		t.Fatal("owned marker mismatch")
	}
	if entries, err := os.ReadDir(dir); err == nil {
		if len(entries) != 0 {
			t.Fatal("runtime must be fresh before writing test CA/bootstrap")
		}
	} else if !os.IsNotExist(err) {
		t.Fatal(err)
	}
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}
	peer := newOwnedASIHTTPS(t, dir)
	t.Setenv("OWNED_ASI_CA_FILE", peer.caFile)
	raw, err := exec.Command(worker, "--manifest").Output()
	if err != nil {
		t.Fatal(err)
	}
	var manifest map[string]any
	if json.Unmarshal(raw, &manifest) != nil || manifest["plugin_id"] != "AutoSignIn" {
		t.Fatal("actual ASI manifest")
	}
	bin, err := os.ReadFile(worker)
	if err != nil {
		t.Fatal(err)
	}
	digest := fileHash(t, worker)
	var repoMu sync.RWMutex
	activeBin, activeDigest, activeManifest := bin, digest, manifest
	var repo *httptest.Server
	repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		repoMu.RLock()
		defer repoMu.RUnlock()
		switch r.URL.Path {
		case "/index":
			json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": "AutoSignIn", "current_version": activeManifest["version"], "releases": []any{map[string]any{"version": activeManifest["version"], "manifest": activeManifest, "artifacts": []any{map[string]any{"platform": "linux-amd64", "format": "executable", "url": repo.URL + "/worker", "sha256": activeDigest, "executable_sha256": activeDigest, "size": len(activeBin), "host_contract": "light-media.sdk-resources/v1"}}}}})
		case "/worker":
			w.Write(activeBin)
		default:
			http.NotFound(w, r)
		}
	}))
	defer repo.Close()
	h := newMainHost(t)
	observer := &puiMain{mainHost: h, allPIDs: map[int]bool{}}
	defer func() {
		wire, connects := peer.snapshot()
		h.record("owned_HTTPS_peer", map[string]any{"wire": wire, "proxy_hosts": connects, "proxy_requests": peer.proxySnapshot(), "scope": "loopback TLS/proxy only, certificate verification enabled; hosts include denied executable-repository HTTP attempts"})
	}()
	var settings map[string]any
	if json.Unmarshal(h.ok("GET", "/api/settings", nil), &settings) != nil {
		t.Fatal("settings")
	}
	settings["proxy_host"] = peer.proxy
	h.ok("PUT", "/api/settings", settings)
	fields := map[string]any{"id": 501, "name": "Owned ASI source peer", "domain": "hhanclub.net", "url": peer.origin + "/", "pri": nil, "cookie": "owned_session=synthetic", "ua": "Owned-ASI/1", "apikey": nil, "token": nil, "proxy": 1, "render": 0, "public": 0, "is_active": true, "timeout": 2}
	var report struct {
		Imported, Failed int
		Results          []struct {
			SiteID string `json:"site_id"`
		}
	}
	if json.Unmarshal(h.ok("POST", "/api/sites/import", []any{fields}), &report) != nil || report.Imported != 1 || report.Failed != 0 || len(report.Results) != 1 {
		t.Fatal("public import precondition", report)
	}
	opaque := report.Results[0].SiteID
	h.stop()
	// Metadata-only read of the owned stopped SQLite database. Python is a
	// verification helper here; server, worker and importer run only Go.
	metaCode := `import sqlite3,json,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
print(json.dumps(c.execute('SELECT ref_id,site_id,native_source_id FROM native_site_import_refs').fetchall()))`
	meta, err := exec.Command("python3", "-c", metaCode, filepath.Join(h.dir, "light-media.db")).Output()
	if err != nil {
		t.Fatal(err)
	}
	var refs [][]any
	if json.Unmarshal(meta, &refs) != nil || len(refs) != 1 || len(refs[0]) != 3 || refs[0][1] != opaque || refs[0][2] != float64(1) {
		t.Fatal("source original501/native1 metadata", string(meta))
	}
	hashes := map[string]string{
		"/app/app/db/models/site.py":     "5cda6b9eb37de3cc25c66abfd41832341ea5270bc73971a24425bd00ef63c8e4",
		"/app/app/schemas/site.py":       "aa759e3f1348863b109acdecb765c87a14822a14fbf63bab3fc93584d51bfaa6",
		"/app/app/api/endpoints/site.py": "c352a148fd418f7eb6c91f490d8db4319c91c6ac2d68b920b35b525d1d8372a8",
		"/app/app/db/site_oper.py":       "08e202eb3fc97c7fe5d67d7253867334ada9bdd1747eb23b2d3cbe26da7f0cf0",
		"/app/app/db/__init__.py":        "6da490f32d0de67839249b4e318fecbf4c877ec5acde4eef08634738c4cfafc9",
		"/app/app/utils/string.py":       "b21856bf4b309d20fe9d5a68538fbb0ddc7a2c23bbde424e5700caf57587297a",
	}
	fieldBytes, _ := json.Marshal(fields)
	input, _ := json.Marshal(map[string]any{"version": 1, "mode": "fixed8a_native_site_consumed_subset", "source_fingerprint": fmt.Sprintf("%x", sha256.Sum256(fieldBytes)), "source_hashes": hashes, "sites": []any{map[string]any{"import_ref_id": refs[0][0], "fields": fields}}})
	runCLI := func(want string, args ...string) {
		t.Helper()
		cmd := exec.Command(cli, args...)
		cmd.Stdin = bytes.NewReader(input)
		out, err := cmd.CombinedOutput()
		var result map[string]any
		if err != nil || json.Unmarshal(out, &result) != nil || result["state"] != want {
			t.Fatal("actual Go offline stdin importer", err, string(out))
		}
		writes := float64(0)
		if want == "imported" {
			writes = 2
		}
		if result["sites"] != float64(1) || result["writes"] != writes || result["jobs_queued"] != float64(0) || result["external_calls"] != float64(0) {
			t.Fatal("offline importer contract counters", result)
		}
		h.record("native_source_CLI", result)
	}
	runCLI("validated", "-validate-input")
	runCLI("ready", "-target-data-dir", h.dir)
	runCLI("imported", "-target-data-dir", h.dir, "-apply")
	runCLI("already_imported", "-target-data-dir", h.dir, "-apply")
	h.start()
	const id = "AutoSignIn"
	h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": id, "repo_url": repo.URL + "/index"})
	form := h.ok("GET", "/api/plugins/"+id+"/form", nil)
	var formValue any
	if json.Unmarshal(form, &formValue) != nil {
		t.Fatal("actual form JSON")
	}
	var selectedSource bool
	var visit func(any)
	visit = func(v any) {
		switch x := v.(type) {
		case map[string]any:
			if x["model"] == "sign_sites" {
				if items, ok := x["items"].([]any); ok {
					for _, v := range items {
						if item, ok := v.(map[string]any); ok && item["title"] == "Owned ASI source peer" && item["value"] == float64(501) {
							selectedSource = true
						}
					}
				}
			}
			for _, v := range x {
				visit(v)
			}
		case []any:
			for _, v := range x {
				visit(v)
			}
		}
	}
	visit(formValue)
	if !selectedSource {
		t.Fatal("source numeric501 missing from real form")
	}
	config := map[string]any{"enabled": false, "notify": false, "cron": "59 23 31 12 *", "onlyonce": true, "auto_cf": 0, "clean": false, "queue_cnt": 1, "sign_sites": []any{501}, "login_sites": []any{}, "retry_keyword": "错误|失败"}
	gate := peer.blockAttendance(t)
	started := time.Now()
	h.ok("PUT", "/api/plugins/"+id, config)
	config["onlyonce"] = false
	h.config(id, config)
	select {
	case <-gate.entered:
	case <-time.After(8 * time.Second):
		t.Fatal("source three-second private job never reached physical TLS peer")
	}
	if time.Since(started) < 2900*time.Millisecond {
		t.Fatal("private source once ran before3 seconds")
	}
	newConfig := map[string]any{}
	for key, value := range config {
		newConfig[key] = value
	}
	newConfig["cron"] = "58 23 31 12 *"
	type result struct {
		status int
		raw    json.RawMessage
	}
	saved := make(chan result, 1)
	go func() { status, body := h.request("PUT", "/api/plugins/"+id, newConfig); saved <- result{status, body} }()
	select {
	case r := <-saved:
		t.Fatal("source init must await running private scheduler callback", r.status, string(r.raw))
	case <-time.After(200 * time.Millisecond):
	}
	h.record("private_init_waited", map[string]any{"source_stop_wait": true, "observed_block_ms": 200})
	gate.unblock()
	select {
	case r := <-saved:
		if r.status != 200 {
			t.Fatal("private init save", r.status, string(r.raw))
		}
		var business struct {
			Success *bool `json:"success"`
		}
		if json.Unmarshal(r.raw, &business) != nil || business.Success != nil && !*business.Success {
			t.Fatal("private init business failure", string(r.raw))
		}
	case <-time.After(10 * time.Second):
		t.Fatal("private callback did not drain")
	}
	h.config(id, newConfig)
	deadline := time.Now().Add(4 * time.Second)
	for !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+id+"/page", nil)) {
		if time.Now().After(deadline) {
			t.Fatal("private callback source history missing after config init")
		}
		time.Sleep(50 * time.Millisecond)
	}
	pids := observer.pids()
	if len(pids) != 1 || pids[id] == 0 {
		t.Fatal("actual worker absent", pids)
	}
	h.stop()
	for _, pid := range pids {
		observer.waitDead(pid)
	}
	h.start()
	cold := observer.pids()
	if len(cold) != 1 || cold[id] == 0 || cold[id] == pids[id] {
		t.Fatal("cold worker not replaced", cold, pids)
	}
	h.config(id, newConfig)
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+id+"/page", nil)) {
		t.Fatal("cold source history missing")
	}
	time.Sleep(3500 * time.Millisecond)
	wire, _ := peer.snapshot()
	attendance := 0
	for _, row := range wire {
		if row["path"] == "/attendance.php" {
			attendance++
			if row["method"] != "GET" || row["cookie"] != "owned_session=synthetic" || row["ua"] != "Owned-ASI/1" {
				t.Fatal("actual source private credentials/wire", row)
			}
		}
	}
	if attendance != 1 {
		t.Fatal("cold source once replayed", attendance)
	}
	// Original965 contracts: command is broadcast to every enabled ASI class;
	// nonempty nonmatching retry_keyword causes same-day dedup; an empty keyword
	// deliberately repeats a successful selected site. HTTP success is insufficient.
	clone := id + "cmd"
	var cloned map[string]any
	if json.Unmarshal(h.ok("POST", "/api/plugins/"+id+"/clone", map[string]any{"suffix": "cmd", "name": "Owned ASI command clone", "version": "2.9.15"}), &cloned) != nil || cloned["created"] != true || cloned["instance_id"] != clone {
		t.Fatal("clone identity", cloned)
	}
	baseConfig := map[string]any{}
	for key, value := range newConfig {
		baseConfig[key] = value
	}
	baseConfig["enabled"], baseConfig["retry_keyword"] = true, ""
	cloneConfig := map[string]any{}
	for key, value := range baseConfig {
		cloneConfig[key] = value
	}
	cloneConfig["enabled"] = false
	h.ok("POST", "/api/plugins/"+id+"/reset", map[string]any{})
	if !asiOwnedEmptyPage(t, h.ok("GET", "/api/plugins/"+id+"/page", nil)) {
		t.Fatal("first Web precondition: private success history was not cleared")
	}
	h.ok("PUT", "/api/plugins/"+id, baseConfig)
	h.ok("PUT", "/api/plugins/"+clone, cloneConfig)
	attendanceCount := func() int {
		wire, _ := peer.snapshot()
		count := 0
		for _, row := range wire {
			if row["path"] == "/attendance.php" {
				count++
			}
		}
		return count
	}
	waitAttendance := func(want int) {
		t.Helper()
		until := time.Now().Add(5 * time.Second)
		for attendanceCount() != want {
			if attendanceCount() > want || time.Now().After(until) {
				t.Fatal("physical attendance count", attendanceCount(), want)
			}
			time.Sleep(20 * time.Millisecond)
		}
	}
	readMessages := func() []map[string]any {
		t.Helper()
		var rows []map[string]any
		if json.Unmarshal(h.ok("GET", "/api/message/web?count=100", nil), &rows) != nil {
			t.Fatal("message history")
		}
		return rows
	}
	waitMessages := func(want int) []map[string]any {
		t.Helper()
		until := time.Now().Add(5 * time.Second)
		for {
			rows := readMessages()
			if len(rows) == want {
				return rows
			}
			if len(rows) > want || time.Now().After(until) {
				t.Fatal("source message count", len(rows), want)
			}
			time.Sleep(20 * time.Millisecond)
		}
	}
	assertCommandMessages := func(rows []map[string]any, incoming, starts, completed int) {
		t.Helper()
		in, start, complete := 0, 0, 0
		for _, row := range rows {
			if row["channel"] != "Web" || row["userid"] != ownedUser {
				t.Fatal("source Web user/channel", row)
			}
			if row["action"] == float64(0) {
				in++
				if row["source"] != ownedUser || row["text"] != "/site_signin" {
					t.Fatal("source incoming", row)
				}
				continue
			}
			if row["action"] != float64(1) || row["source"] != nil {
				t.Fatal("source outgoing", row)
			}
			title, _ := row["title"].(string)
			text, _ := row["text"].(string)
			switch title + text {
			case "开始站点签到 ...":
				start++
			case "站点签到完成！":
				complete++
			default:
				t.Fatal("unexpected Web output", row)
			}
		}
		if in != incoming || start != starts || complete != completed {
			t.Fatal("command message effects", in, start, complete, incoming, starts, completed)
		}
	}
	if len(readMessages()) != 0 {
		t.Fatal("private notify=false should not generate Web replies")
	}
	h.ok("POST", "/api/message/web", map[string]any{"text": "/site_signin"})
	waitAttendance(2)
	assertCommandMessages(waitMessages(3), 1, 1, 1)
	if !asiOwnedPendingRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {
		t.Fatal("disabled selected clone acquired history or lost its pending row")
	}
	h.config(clone, cloneConfig)
	cloneConfig["enabled"] = true
	h.ok("PUT", "/api/plugins/"+clone, cloneConfig)
	h.ok("POST", "/api/message/web", map[string]any{"text": "/site_signin"})
	waitAttendance(4)
	assertCommandMessages(waitMessages(8), 2, 3, 3)
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+id+"/page", nil)) || !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {
		t.Fatal("broadcast history isolation")
	}
	baseConfig["retry_keyword"], cloneConfig["retry_keyword"] = "错误|失败", "错误|失败"
	h.ok("PUT", "/api/plugins/"+id, baseConfig)
	h.ok("PUT", "/api/plugins/"+clone, cloneConfig)
	h.ok("POST", "/api/message/web", map[string]any{"text": "/site_signin"})
	// Source first consumes the previous pass's retry IDs. The last empty-keyword
	// pass saved [501]; this nonempty-keyword pass executes them and writes [].
	waitAttendance(6)
	assertCommandMessages(waitMessages(13), 3, 5, 5)
	h.ok("POST", "/api/message/web", map[string]any{"text": "/site_signin"})
	assertCommandMessages(waitMessages(16), 4, 7, 5)
	time.Sleep(150 * time.Millisecond)
	if attendanceCount() != 6 {
		t.Fatal("source same-day dedup failed")
	}
	h.record("ordinary_Web_broadcast_complete", map[string]any{"commands": 4, "attendance": 6, "incoming": 4, "start_replies": 7, "complete_replies": 5, "disabled_clone_ignored": true, "both_enabled_broadcast": true, "source_retry_transition": true, "source_dedup": true})

	// A second owned executable changes only its real --manifest description.
	// Business source and version are unchanged. This proves actual artifact and
	// process replacement, not a new upstream release or version semantics.
	updatedWorker := os.Getenv("AUTOSIGNIN_UPDATED_WORKER_BINARY")
	updatedBytes, err := os.ReadFile(updatedWorker)
	if err != nil {
		t.Fatal(err)
	}
	updatedRaw, err := exec.Command(updatedWorker, "--manifest").Output()
	if err != nil {
		t.Fatal(err)
	}
	var updatedManifest map[string]any
	if json.Unmarshal(updatedRaw, &updatedManifest) != nil || updatedManifest["version"] != manifest["version"] || updatedManifest["description"] == manifest["description"] {
		t.Fatal("owned same-version executable variant")
	}
	oldPIDs := observer.pids()
	if len(oldPIDs) != 2 || oldPIDs[id] == 0 || oldPIDs[clone] == 0 {
		t.Fatal("base/clone PIDs", oldPIDs)
	}
	baseEntry := filepath.Join(h.dir, "plugin-packages", id, "auto-sign-in")
	cloneEntry := filepath.Join(h.dir, "plugin-packages", clone, "auto-sign-in")
	if fileHash(t, baseEntry) != digest || fileHash(t, cloneEntry) != digest {
		t.Fatal("pre-update actual code hash")
	}
	repoMu.Lock()
	activeBin = updatedBytes
	activeDigest = fileHash(t, updatedWorker)
	activeManifest = updatedManifest
	repoMu.Unlock()
	h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": id, "repo_url": repo.URL + "/index", "force": true})
	newPIDs := observer.pids()
	if len(newPIDs) != 2 || newPIDs[id] == 0 || newPIDs[id] == oldPIDs[id] || newPIDs[clone] != oldPIDs[clone] {
		t.Fatal("same-version update process isolation", oldPIDs, newPIDs)
	}
	observer.waitDead(oldPIDs[id])
	if fileHash(t, baseEntry) != activeDigest || fileHash(t, cloneEntry) != digest {
		t.Fatal("same-version update executable isolation")
	}
	if fileHash(t, fmt.Sprintf("/proc/%d/exe", newPIDs[id])) != activeDigest || fileHash(t, fmt.Sprintf("/proc/%d/exe", newPIDs[clone])) != digest {
		t.Fatal("actual running executable differs from installed update bytes")
	}
	h.config(id, baseConfig)
	h.config(clone, cloneConfig)
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+id+"/page", nil)) || !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {
		t.Fatal("update lost history")
	}
	h.record("same_version_force_update_complete", map[string]any{"version": manifest["version"], "before_sha256": digest, "after_sha256": activeDigest, "base_pid_before": oldPIDs[id], "base_pid_after": newPIDs[id], "clone_pid_unchanged": newPIDs[clone], "clone_code_unchanged": true, "config_history_preserved": true, "variant": "test-only --manifest description marker; no true product source modification"})

	// Whole scheduler shutdown waits for an already-running public timer callback.
	// Unlike single-plugin remove_job, source lifespan stops the global scheduler
	// before stopping plugins. A real attendance barrier distinguishes waiting from
	// cancellation and tests that history persists after actual callback completion.
	cloneConfig["enabled"] = false
	h.ok("PUT", "/api/plugins/"+clone, cloneConfig)
	h.ok("POST", "/api/plugins/"+id+"/reset", map[string]any{})
	if !asiOwnedEmptyPage(t, h.ok("GET", "/api/plugins/"+id+"/page", nil)) {
		t.Fatal("timer precondition: old base history survived reset")
	}
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {
		t.Fatal("base reset changed clone history")
	}
	timerGate := peer.blockAttendance(t)
	baseConfig["cron"], baseConfig["retry_keyword"] = "0.001", ""
	beforeTimer := attendanceCount()
	registered := time.Now()
	h.ok("PUT", "/api/plugins/"+id, baseConfig)
	timerPIDs := observer.pids()
	if len(timerPIDs) != 2 || timerPIDs[id] == 0 || timerPIDs[clone] != newPIDs[clone] {
		t.Fatal("timer worker identity", timerPIDs)
	}
	select {
	case <-timerGate.entered:
	case <-time.After(10 * time.Second):
		t.Fatal("actual public interval never reached TLS peer")
	}
	enteredAfter := time.Since(registered)
	if enteredAfter < 3400*time.Millisecond {
		t.Fatal("0.001-hour interval fired early", enteredAfter)
	}
	shutdownLog := h.log.Name()
	stopped := make(chan struct{})
	go func() { h.stop(); close(stopped) }()
	// Wait for the original ordinary Scheduler.stop stage, which precedes its
	// callback join. Merely waiting after SIGTERM can measure HTTP/code backup
	// work and let the callback finish before old code revokes it.
	stageDeadline := time.Now().Add(5 * time.Second)
	for {
		raw, err := os.ReadFile(shutdownLog)
		if err != nil {
			t.Fatal(err)
		}
		found := false
		for _, line := range bytes.Split(raw, []byte{'\n'}) {
			var entry struct {
				Event   string `json:"event"`
				Message string `json:"message"`
			}
			if json.Unmarshal(line, &entry) == nil && entry.Event == "scheduler_stopping" && entry.Message == "正在停止定时任务..." {
				found = true
				break
			}
		}
		if found {
			break
		}
		select {
		case <-stopped:
			t.Fatal("global stop returned before source scheduler stage")
		default:
		}
		if time.Now().After(stageDeadline) {
			t.Fatal("source Scheduler.stop stage was not observed while callback held")
		}
		time.Sleep(10 * time.Millisecond)
	}
	h.record("public_scheduler_stop_observed", map[string]any{"event": "scheduler_stopping", "held_callback": true, "checkpoint": "actual runtime INFO before public lifetime wait, before code backup"})
	select {
	case <-stopped:
		t.Fatal("global stop returned before in-flight public callback")
	case <-time.After(200 * time.Millisecond):
	}
	timerGate.unblock()
	select {
	case <-stopped:
	case <-time.After(10 * time.Second):
		t.Fatal("global stop did not drain public callback")
	}
	for _, pid := range timerPIDs {
		observer.waitDead(pid)
	}
	if attendanceCount() != beforeTimer+1 {
		t.Fatal("public callback count before stop", attendanceCount(), beforeTimer)
	}
	if len(observer.pids()) != 0 {
		t.Fatal("worker survived global stop")
	}
	h.start()
	baseConfig["enabled"] = false
	h.ok("PUT", "/api/plugins/"+id, baseConfig)
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+id+"/page", nil)) {
		t.Fatal("public callback history missing after cold restart")
	}
	if attendanceCount() != beforeTimer+1 {
		t.Fatal("cold timer started before history verification; cannot attribute history to shutdown callback")
	}
	if fileHash(t, baseEntry) != activeDigest || fileHash(t, cloneEntry) != digest {
		t.Fatal("cold update executable persistence")
	}
	afterColdPIDs := observer.pids()
	if len(afterColdPIDs) != 2 || afterColdPIDs[id] == 0 || afterColdPIDs[clone] == 0 || fileHash(t, fmt.Sprintf("/proc/%d/exe", afterColdPIDs[id])) != activeDigest || fileHash(t, fmt.Sprintf("/proc/%d/exe", afterColdPIDs[clone])) != digest {
		t.Fatal("cold running executable update persistence", afterColdPIDs)
	}
	h.config(id, baseConfig)
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {
		t.Fatal("clone cold history changed across base timer/reset/update")
	}
	h.config(clone, cloneConfig)
	if len(readMessages()) != 16 {
		t.Fatal("timer invented Web command replies")
	}
	h.record("public_timer_global_shutdown_complete", map[string]any{"source_hours": "0.001", "first_enter_ms": enteredAfter.Milliseconds(), "source_scheduler_stage_observed": true, "observed_stop_wait_after_stage_ms": 200, "callback_completed_before_exit": true, "cold_history": true, "clone_cold_history_config": true, "cold_additional_attendance": 0, "cold_update_hashes": true, "Web_replies_unchanged": true})
	baseConfig["cron"] = "58 23 31 12 *"
	h.ok("PUT", "/api/plugins/"+id, baseConfig)
	newConfig = baseConfig
	h.ok("DELETE", "/api/plugins/"+clone, nil)
	observer.code(clone, false)

	repoOrigin, err := url.Parse(repo.URL)
	if err != nil {
		t.Fatal(err)
	}
	for _, request := range peer.proxySnapshot() {
		if request["method"] == "CONNECT" && request["host"] == "hhanclub.net:443" {
			continue
		}
		if request["method"] == "GET" && request["host"] == repoOrigin.Host && strings.HasPrefix(request["uri"], repo.URL+"/") {
			continue
		}
		t.Fatal("foreign proxy request", request)
	}

	// The fixed manager disables all ordinary handlers when get_state is false.
	// Enable this one class with a distant cron before testing SiteDeleted.
	newConfig["enabled"] = true
	h.ok("PUT", "/api/plugins/"+id, newConfig)
	h.config(id, newConfig)
	h.ok("DELETE", "/api/sites/manage/"+opaque, nil)
	deadline = time.Now().Add(4 * time.Second)
	for {
		var got map[string]any
		if json.Unmarshal(h.ok("GET", "/api/plugins/"+id, nil), &got) != nil {
			t.Fatal("config")
		}
		sites, valid := got["sign_sites"].([]any)
		if got["enabled"] == false && valid && len(sites) == 0 {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("Main site.deleted501 did not clear original selection", got)
		}
		time.Sleep(50 * time.Millisecond)
	}
	final := observer.pids()
	if len(final) != 1 || final[id] == 0 {
		t.Fatal("deleted-site worker unexpectedly absent", final)
	}
	h.ok("DELETE", "/api/plugins/"+id, nil)
	for _, pid := range final {
		observer.waitDead(pid)
	}
	observer.code(id, true)
	if remaining := observer.pids(); len(remaining) != 0 {
		t.Fatal("uninstalled worker survived", remaining)
	}
	h.stop()
	h.record("actual_Main_commands_update_timer_complete", map[string]any{"original_id": 501, "native_local_id": 1, "source_form": true, "initial_private_attendance": attendance, "private_init_waited": true, "cold_no_replay_ms": 3500, "site_deleted_selection_cleared": true, "scope": "actual Go Main+worker+offlineCLI+owned TLS peer; bounded Web broadcast/retry, same-version force update, public timer/global drain; not full ASI/UI/live PT/private import"})
}

// Source get_page1441-1529: inspect the named row, exact status chip and
// first (today) dot. A substring in static CSS/headings cannot pass this gate.
func asiOwnedSuccessfulRow(t *testing.T, raw []byte) bool {
	t.Helper()
	var root any
	if json.Unmarshal(raw, &root) != nil {
		t.Fatal("invalid page JSON")
	}
	var walk func(any, func(map[string]any) bool) bool
	walk = func(v any, pred func(map[string]any) bool) bool {
		switch x := v.(type) {
		case map[string]any:
			if pred(x) {
				return true
			}
			for _, v := range x {
				if walk(v, pred) {
					return true
				}
			}
		case []any:
			for _, v := range x {
				if walk(v, pred) {
					return true
				}
			}
		}
		return false
	}
	named := func(m map[string]any) bool {
		p, _ := m["props"].(map[string]any)
		return m["text"] == "Owned ASI source peer" && p["class"] == "autosignin-site-name" && p["title"] == "Owned ASI source peer"
	}
	return walk(root, func(row map[string]any) bool {
		if row["component"] != "tr" {
			return false
		}
		cells, _ := row["content"].([]any)
		if len(cells) < 3 || !walk(cells[0], named) {
			return false
		}
		chip := walk(cells[1], func(m map[string]any) bool {
			p, _ := m["props"].(map[string]any)
			return m["component"] == "VChip" && m["text"] == "签到成功" && p["color"] == "success" && p["prepend-icon"] == "mdi-check-circle"
		})
		dot := walk(cells[2], func(m map[string]any) bool {
			p, _ := m["props"].(map[string]any)
			title, _ := p["title"].(string)
			return m["component"] == "span" && p["class"] == "autosignin-dot autosignin-dot--success" && strings.HasSuffix(title, " 签到成功")
		})
		return chip && dot && walk(root, func(m map[string]any) bool {
			p, _ := m["props"].(map[string]any)
			c, _ := p["class"].(string)
			return m["text"] == "1/1" && strings.Contains(c, "autosignin-stat__value")
		})
	})
}

// Fixed270 get_page640-832: selected sites with no history have a pending row.
func asiOwnedPendingRow(t *testing.T, raw []byte) bool {
	t.Helper()
	var root any
	if json.Unmarshal(raw, &root) != nil {
		t.Fatal("invalid page JSON")
	}
	var walk func(any, func(map[string]any) bool) bool
	walk = func(v any, pred func(map[string]any) bool) bool {
		switch x := v.(type) {
		case map[string]any:
			if pred(x) {
				return true
			}
			for _, v := range x {
				if walk(v, pred) {
					return true
				}
			}
		case []any:
			for _, v := range x {
				if walk(v, pred) {
					return true
				}
			}
		}
		return false
	}
	named := func(m map[string]any) bool {
		p, _ := m["props"].(map[string]any)
		return m["text"] == "Owned ASI source peer" && p["class"] == "autosignin-site-name" && p["title"] == "Owned ASI source peer"
	}
	return walk(root, func(row map[string]any) bool {
		if row["component"] != "tr" {
			return false
		}
		cells, _ := row["content"].([]any)
		if len(cells) < 3 || !walk(cells[0], named) {
			return false
		}
		chip := walk(cells[1], func(m map[string]any) bool {
			p, _ := m["props"].(map[string]any)
			return m["component"] == "VChip" && m["text"] == "未记录" && p["color"] == "grey" && p["prepend-icon"] == "mdi-minus-circle-outline"
		})
		dot := walk(cells[2], func(m map[string]any) bool {
			p, _ := m["props"].(map[string]any)
			title, _ := p["title"].(string)
			return m["component"] == "span" && p["class"] == "autosignin-dot autosignin-dot--none" && strings.HasSuffix(title, " 未记录")
		})
		return chip && dot && walk(cells[0], func(m map[string]any) bool { return m["text"] == "暂无记录" }) && walk(root, func(m map[string]any) bool {
			p, _ := m["props"].(map[string]any)
			c, _ := p["class"].(string)
			return m["text"] == "0/1" && strings.Contains(c, "autosignin-stat__value")
		})
	})
}
func asiOwnedEmptyPage(t *testing.T, raw []byte) bool {
	t.Helper()
	var got struct {
		Page any `json:"page"`
	}
	if json.Unmarshal(raw, &got) != nil {
		t.Fatal("invalid empty page JSON")
	}
	want := []any{map[string]any{"component": "VAlert", "props": map[string]any{"type": "info", "text": "暂无签到数据", "variant": "tonal", "class": "mt-4", "prepend-icon": "mdi-information"}}}
	return reflect.DeepEqual(got.Page, want)
}
