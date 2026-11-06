package integration

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

// Original270ae0 __signin_base1856-1931 requires both login and positive
// attendance evidence. init_plugin104-134 resets onlyonce before a real 3s job.
// Every endpoint below is an owned loopback protocol peer, never a PT site.
func TestAutoSignInActualMainBrowserAndPopulatedClone(t *testing.T) {
	worker := os.Getenv("AUTOSIGNIN_WORKER_BINARY")
	if worker == "" {
		t.Skip("owned Linux Main opt-in not configured; no execution acceptance")
	}
	if runtime.GOOS != "linux" || os.Geteuid() == 0 {
		t.Fatal("Linux UID1000 owned execution required")
	}
	raw, e := exec.Command(worker, "--manifest").Output()
	if e != nil {
		t.Fatal(e)
	}
	var manifest map[string]any
	if json.Unmarshal(raw, &manifest) != nil || manifest["plugin_id"] != "AutoSignIn" {
		t.Fatal("ASI manifest")
	}
	bin, e := os.ReadFile(worker)
	if e != nil {
		t.Fatal(e)
	}
	digest := fileHash(t, worker)
	var repo *httptest.Server
	repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/index":
			json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": "AutoSignIn", "current_version": manifest["version"], "releases": []any{map[string]any{"version": manifest["version"], "manifest": manifest, "artifacts": []any{map[string]any{"platform": "linux-" + runtime.GOARCH, "format": "executable", "url": repo.URL + "/worker", "sha256": digest, "executable_sha256": digest, "size": len(bin), "host_contract": "light-media.sdk-resources/v1"}}}}})
		case "/worker":
			w.Write(bin)
		default:
			http.NotFound(w, r)
		}
	}))
	defer repo.Close()
	var mu sync.Mutex
	paths := []string{}
	var attendanceAt time.Time
	seen := []map[string]string{}
	badCredentials := false
	peer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		seen = append(seen, map[string]string{"method": r.Method, "path": r.URL.RequestURI(), "cookie": r.Header.Get("Cookie"), "ua": r.Header.Get("User-Agent"), "arrived_at": time.Now().Format(time.RFC3339Nano)})
		if r.URL.Path == "/attendance.php" {
			paths = append(paths, r.URL.RequestURI())
			if attendanceAt.IsZero() {
				attendanceAt = time.Now()
			}
			if r.Method != "GET" || r.Header.Get("Cookie") != "owned_session=synthetic" || r.Header.Get("User-Agent") != "Owned-ASI/1" {
				badCredentials = true
			}
		}
		mu.Unlock()
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		switch r.URL.Path {
		case "/attendance.php":
			w.Write([]byte(`<html><body><a href="logout.php">退出登录</a><div>签到成功</div></body></html>`))
		case "/":
			w.Write([]byte(`<html><body><a href="logout.php">退出登录</a></body></html>`))
		case "/favicon.ico":
			w.Header().Set("Content-Type", "image/x-icon")
			w.Write([]byte{0, 0, 1, 0})
		default:
			http.NotFound(w, r)
		}
	}))
	defer peer.Close()
	h := newMainHost(t)
	// Reuse the existing generic /proc and package-path observer; no plugin callbacks.
	observer := &puiMain{mainHost: h, allPIDs: map[int]bool{}}
	t.Cleanup(func() { mu.Lock(); defer mu.Unlock(); h.record("owned_peer_observations", seen) })
	const id = "AutoSignIn"
	const clone = "AutoSignIncopy"
	h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": id, "repo_url": repo.URL + "/index"})
	h.ok("POST", "/api/plugins/"+id+"/clone", map[string]any{"suffix": "copy"})
	initialPIDs := observer.pids()
	if len(initialPIDs) != 2 || initialPIDs[id] == 0 || initialPIDs[clone] == 0 || initialPIDs[id] == initialPIDs[clone] {
		t.Fatal("separate base/clone workers absent", initialPIDs)
	}
	observer.code(id, true)
	observer.code(clone, true)
	h.ok("POST", "/api/sites/manage", map[string]any{"kind": "hhanclub", "name": "Owned ASI source peer", "url": peer.URL, "domain": "hhanclub.net", "cookie": "owned_session=synthetic", "ua": "Owned-ASI/1", "is_active": true, "timeout": 2, "daily_budget": 600, "pri": 1, "proxy": false, "render": false})
	form := h.ok("GET", "/api/plugins/"+id+"/form", nil)
	var root any
	if json.Unmarshal(form, &root) != nil {
		t.Fatal(string(form))
	}
	var sourceID any
	var visit func(any)
	visit = func(v any) {
		switch x := v.(type) {
		case map[string]any:
			if x["title"] == "Owned ASI source peer" {
				sourceID = x["value"]
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
	visit(root)
	if sourceID == nil {
		t.Fatal("actual managed source ID absent from original form choices", string(form))
	}
	config := map[string]any{"enabled": true, "notify": false, "cron": "59 23 31 12 *", "onlyonce": true, "auto_cf": 0, "clean": false, "queue_cnt": 1, "sign_sites": []any{sourceID}, "login_sites": []any{}, "retry_keyword": "错误|失败"}
	started := time.Now()
	h.ok("PUT", "/api/plugins/"+id, config)
	config["onlyonce"] = false
	h.config(id, config)
	if !reflect.DeepEqual(observer.pids(), initialPIDs) {
		t.Fatal("config save unexpectedly replaced workers")
	}
	deadline := time.Now().Add(15 * time.Second)
	var page json.RawMessage
	for {
		page = h.ok("GET", "/api/plugins/"+id+"/page", nil)
		mu.Lock()
		count := len(paths)
		bad := badCredentials
		mu.Unlock()
		if bad {
			t.Fatal("bound source Cookie/UA differs at physical peer")
		}
		if count > 0 && asiOwnedSuccessfulRow(t, page) {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("3-second source once job did not produce real request + successful history", string(page))
		}
		time.Sleep(200 * time.Millisecond)
	}
	mu.Lock()
	arrivalDelay := attendanceAt.Sub(started)
	mu.Unlock()
	// 100ms scheduling/measurement tolerance; source schedules now+3 seconds.
	if arrivalDelay < 2900*time.Millisecond {
		t.Fatal("once task bypassed source 3-second delay", arrivalDelay)
	}
	mu.Lock()
	actual := append([]string(nil), paths...)
	mu.Unlock()
	if len(actual) != 1 || actual[0] != "/attendance.php" {
		t.Fatal("source request/replay differs", actual)
	}
	clonePage := h.ok("GET", "/api/plugins/"+clone+"/page", nil)
	h.config(clone, map[string]any{})
	if !asiOwnedEmptyPage(t, clonePage) {
		t.Fatal("clone inherited base execution history", string(clonePage))
	}
	if os.Getenv("AUTOSIGNIN_UI_WAIT") != "1" {
		t.Fatal("this UI gate requires an actual browser and explicit completion marker")
	}
	ready, _ := json.Marshal(map[string]any{"base": h.base, "username": ownedUser, "password": ownedPassword, "base_instance": id, "clone_instance": clone, "source_id": sourceID})
	if err := os.WriteFile(filepath.Join(h.dir, "ui-ready.json"), ready, 0600); err != nil {
		t.Fatal(err)
	}
	h.record("asi_UI_ready", map[string]any{"private_ready_file": filepath.Join(h.dir, "ui-ready.json"), "scope": "actualbrowser required; syntheticlogin, no production"})
	uiDeadline := time.Now().Add(12 * time.Minute)
	for {
		if _, err := os.Stat(filepath.Join(h.dir, "ui-complete.json")); err == nil {
			break
		}
		if time.Now().After(uiDeadline) {
			t.Fatal("actual browser stage not completed")
		}
		time.Sleep(250 * time.Millisecond)
	}
	// The prescribed browser actions come from source get_form's literal model:
	// base cron only; clone notify off, selected owned site, run once while disabled.
	config["cron"] = "58 23 31 12 *"
	cloneConfig := map[string]any{"enabled": false, "notify": false, "cron": "57 23 31 12 *", "onlyonce": false, "auto_cf": 0, "clean": false, "queue_cnt": 5, "sign_sites": []any{sourceID}, "login_sites": []any{}, "retry_keyword": "错误|失败"}
	h.config(id, config)
	h.config(clone, cloneConfig)
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {
		t.Fatal("GUI clone once did not create independent real history")
	}
	mu.Lock()
	guiCalls := len(paths)
	mu.Unlock()
	if guiCalls != 2 {
		t.Fatal("GUI clone once request count", guiCalls)
	}
	if !reflect.DeepEqual(observer.pids(), initialPIDs) {
		t.Fatal("GUI saves replaced retained instance workers")
	}
	h.record("asi_GUI_saved_and_clone_once", map[string]any{"base_cron": "58 23 31 12 *", "clone_cron": "57 23 31 12 *", "clone_enabled": false, "clone_history": "actualsuccess", "attendance_count": guiCalls})
	h.stop()
	for _, pid := range initialPIDs {
		observer.waitDead(pid)
	}
	if len(observer.pids()) != 0 {
		t.Fatal("workers survived stopped Main")
	}
	h.start()
	coldPIDs := observer.pids()
	if len(coldPIDs) != 2 || coldPIDs[id] == 0 || coldPIDs[clone] == 0 || coldPIDs[id] == initialPIDs[id] || coldPIDs[clone] == initialPIDs[clone] {
		t.Fatal("cold workers not replaced", initialPIDs, coldPIDs)
	}
	h.config(id, config)
	restored := h.ok("GET", "/api/plugins/"+id+"/page", nil)
	if !asiOwnedSuccessfulRow(t, restored) {
		t.Fatal("cold persisted history absent", string(restored))
	}
	time.Sleep(3500 * time.Millisecond)
	mu.Lock()
	after := len(paths)
	mu.Unlock()
	if after != 2 {
		t.Fatal("cold restart replayed one-shot", after)
	}
	// Fixed plugin.py992-1030 retains ordinary base code/config/KV.
	// The reinstall uses the same nonempty repository, then real init/registration.
	h.ok("POST", "/api/plugins/"+id+"/uninstall", map[string]any{})
	observer.waitDead(coldPIDs[id])
	observer.code(id, true)
	observer.code(clone, true)
	if got := observer.pids(); len(got) != 1 || got[clone] != coldPIDs[clone] {
		t.Fatal("base uninstall disturbed clone", got)
	}
	h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": id, "repo_url": repo.URL + "/index"})
	reinstalledPIDs := observer.pids()
	if len(reinstalledPIDs) != 2 || reinstalledPIDs[id] == 0 || reinstalledPIDs[id] == coldPIDs[id] || reinstalledPIDs[clone] != coldPIDs[clone] {
		t.Fatal("base reinstall worker identity", reinstalledPIDs)
	}
	h.config(id, config)
	if retained := h.ok("GET", "/api/plugins/"+id+"/page", nil); !asiOwnedSuccessfulRow(t, retained) {
		t.Fatal("ordinary reinstall lost actual signup history", string(retained))
	}
	mu.Lock()
	reinstallCalls := len(paths)
	mu.Unlock()
	if reinstallCalls != 2 {
		t.Fatal("ordinary reinstall replayed signin", reinstallCalls)
	}
	h.ok("POST", "/api/plugins/"+id+"/reset", nil)
	observer.waitDead(reinstalledPIDs[id])
	resetPIDs := observer.pids()
	if len(resetPIDs) != 2 || resetPIDs[id] == 0 || resetPIDs[id] == reinstalledPIDs[id] || resetPIDs[clone] != reinstalledPIDs[clone] {
		t.Fatal("reset worker or clone isolation", resetPIDs)
	}
	empty := h.ok("GET", "/api/plugins/"+id+"/page", nil)
	h.config(id, map[string]any{})
	h.config(clone, cloneConfig)
	if !asiOwnedSuccessfulRow(t, h.ok("GET", "/api/plugins/"+clone+"/page", nil)) {
		t.Fatal("base reset destroyed populated clone history")
	}
	if !asiOwnedEmptyPage(t, empty) {
		t.Fatal("reset did not clear actual history", string(empty))
	}
	h.ok("POST", "/api/plugins/"+clone+"/uninstall", map[string]any{})
	observer.waitDead(resetPIDs[clone])
	observer.code(clone, false)
	observer.code(id, true)
	if got := observer.pids(); len(got) != 1 || got[id] != resetPIDs[id] {
		t.Fatal("clone uninstall disturbed base", got)
	}
	h.ok("POST", "/api/plugins/"+id+"/uninstall", map[string]any{})
	observer.waitDead(resetPIDs[id])
	observer.code(id, true)
	if got := observer.pids(); len(got) != 0 {
		t.Fatal("uninstalled worker survived", got)
	}
	h.stop()
	for pid := range observer.allPIDs {
		observer.waitDead(pid)
	}
	h.record("asi_all_workers_joined", map[string]any{"observed_workers": len(observer.allPIDs), "base_code_retained": true, "clone_code_removed": true, "pui_observer_reuse": "generic existing /proc+Lstat methods only; not PUI business execution"})
	h.record("asi_owned_site_once_complete", map[string]any{"source_id": sourceID, "physical_paths": actual, "elapsed_seconds": time.Since(started).Seconds(), "attendance_delay_seconds": arrivalDelay.Seconds(), "cold_no_replay_observation_ms": 3500, "worker_sha256": digest, "scope": "owned protocol peer, trueMain/once/history/clone/cold/no-replay/reset; not realPT/browser/OCR or completeASI"})
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
