package integration

// Opt-in ordinary cmd/server acceptance driver. It is compiled here and run by
// the coordinator only after the final host/SDK freeze. Native HTML parsing,
// SQLite, ordinary events and business worker are real; owned HTML is synthetic.
import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

type ssRelease struct {
	manifest      map[string]any
	binary        []byte
	version, hash string
}

func ssLoadRelease(t *testing.T, path, plugin string) ssRelease {
	t.Helper()
	raw, e := exec.Command(path, "--manifest").Output()
	if e != nil {
		t.Fatal("worker manifest execution", e)
	}
	var m map[string]any
	if json.Unmarshal(raw, &m) != nil || m["plugin_id"] != plugin {
		t.Fatal("wrong worker manifest", plugin)
	}
	b, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	return ssRelease{m, b, m["version"].(string), fileHash(t, path)}
}

type ssRepository struct {
	mu      sync.Mutex
	current ssRelease
	server  *httptest.Server
}

func ssRepo(t *testing.T, release ssRelease) *ssRepository {
	t.Helper()
	repo := &ssRepository{current: release}
	repo.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		repo.mu.Lock()
		defer repo.mu.Unlock()
		x := repo.current
		switch r.URL.Path {
		case "/index":
			artifact := map[string]any{"platform": runtime.GOOS + "-" + runtime.GOARCH, "format": "executable", "sha256": x.hash, "executable_sha256": x.hash, "size": len(x.binary), "host_contract": "light-media.sdk-resources/v1", "url": repo.server.URL + "/worker"}
			_ = json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": x.manifest["plugin_id"], "current_version": x.version, "releases": []any{map[string]any{"version": x.version, "manifest": x.manifest, "artifacts": []any{artifact}}}})
		case "/worker":
			_, _ = w.Write(x.binary)
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(repo.server.Close)
	return repo
}
func (r *ssRepository) change(x ssRelease) { r.mu.Lock(); defer r.mu.Unlock(); r.current = x }
func (s *ssMain) installSS(plugin string, repo *ssRepository, force bool) {
	s.okSS("POST", "/api/plugins/install", map[string]any{"plugin_id": plugin, "force": force, "repo_url": repo.server.URL + "/index"})
}
func ssConfig(enabled, once bool, mode, notify string) map[string]any {
	return map[string]any{"enabled": enabled, "onlyonce": once, "dashboard_type": mode, "notify_type": notify, "owned_unknown": "preserved source extra"}
}
func ssAssertAPI(t *testing.T, status int, raw []byte, success bool, message string) map[string]json.RawMessage {
	t.Helper()
	var response struct {
		Success     bool                       `json:"success"`
		Message     string                     `json:"message"`
		MessageI18n string                     `json:"message_i18n"`
		Data        map[string]json.RawMessage `json:"data"`
	}
	if status != 200 || json.Unmarshal(raw, &response) != nil || response.Success != success || response.Message != message {
		t.Fatalf("source API outcome: status%d %s", status, raw)
	}
	return response.Data
}
func ssAssertKV(t *testing.T, got, want map[string]json.RawMessage) {
	t.Helper()
	a, _ := json.Marshal(got)
	b, _ := json.Marshal(want)
	if !ssJSONEqual(a, b) {
		t.Fatal("instance KV changed unexpectedly", string(a), string(b))
	}
}
func ssHistory(t *testing.T, s *ssMain, site string) json.RawMessage {
	t.Helper()
	return s.okSS("GET", "/api/sites/manage/"+site+"/history", nil)
}
func ssAssertTrafficDTO(t *testing.T, data map[string]json.RawMessage, upload string) {
	t.Helper()
	if len(data) != 19 || string(data["upload"]) != upload || string(data["download"]) != "1073741824" || string(data["username"]) != `" self "` || string(data["userid"]) != `"7"` || string(data["seeding"]) != "2" || string(data["seeding_size"]) != "3072" || string(data["updated_time"]) != "null" || string(data["err_msg"]) != "null" {
		t.Fatal("actual native DTO differs from source fixture", data)
	}
}
func ssTrigger(t *testing.T, s *ssMain, instance, mode, notify string, enabled bool) {
	t.Helper()
	before := s.dbSS().Events["*"]
	started := time.Now()
	s.okSS("PUT", "/api/plugins/"+instance, ssConfig(enabled, true, mode, notify))
	ssWait(t, "source common all-refresh global fact", 45*time.Second, func() bool { return s.dbSS().Events["*"] == before+1 })
	if time.Since(started) < 2900*time.Millisecond {
		t.Fatal("source three-second date ran early")
	}
	s.configSS(instance, ssConfig(enabled, false, mode, notify))
	s.record("ss_source_once", map[string]any{"instance": instance, "real_elapsed_ms": time.Since(started).Milliseconds(), "global_before": before, "global_after": s.dbSS().Events["*"], "enabled": enabled})
}

func TestSiteStatisticActualMainOwnedHTTPS(t *testing.T) {
	worker := os.Getenv("SITESTATISTIC_WORKER_BINARY")
	if worker == "" {
		t.Skip("opt-in SiteStatistic ordinary main; driver compilation is not acceptance")
	}
	for _, key := range []string{"SITESTATISTIC_HOST_BINARY", "SITESTATISTIC_UPDATE_WORKER_BINARY", "SITESTATISTIC_MODULE_WORKER_BINARY"} {
		if os.Getenv(key) == "" {
			t.Fatal("complete owned main driver requires " + key)
		}
	}
	if deadline, ok := t.Deadline(); !ok || time.Until(deadline) < 69*time.Minute || time.Until(deadline) > 71*time.Minute {
		t.Fatal("use go test -timeout 70m; the staged UI alone permits 50 minutes")
	}
	// Keep one minute inside the external70-minute test alarm for owned child
	// termination/cleanup instead of letting the test alarm orphan the server.
	ctx, cancel := context.WithTimeout(context.Background(), 69*time.Minute)
	defer cancel()
	dir := ssOwnedDirectory(t)
	peer := ssNewPeer(t, dir)
	s := ssNewMain(ctx, t, dir, peer.caFile, peer.proxy.URL)
	defer func() {
		s.record("ss_owned_network_on_return", map[string]any{"test_failed": t.Failed(), "peer": peer.report()})
	}()
	s.secrets = append(s.secrets, peer.cookie[ssTargets[0]], peer.cookie[ssTargets[1]])
	first := ssLoadRelease(t, worker, ssSource)
	second := ssLoadRelease(t, os.Getenv("SITESTATISTIC_UPDATE_WORKER_BINARY"), ssSource)
	if first.version != "1.9.7" || second.version == first.version {
		t.Fatal("actual1.9.7 and a distinct manifest-only update fixture required")
	}
	repo := ssRepo(t, first)
	s.installSS(ssSource, repo, false)
	const aID, bID = "ss-owned-native-a", "ss-owned-native-b"
	emptyPage := s.okSS("GET", "/api/plugins/"+ssSource+"/page", nil)
	if !bytes.Contains(emptyPage, []byte("暂无数据")) {
		t.Fatal("source empty page absent")
	}
	form := s.okSS("GET", "/api/plugins/"+ssSource+"/form", nil)
	for _, field := range []string{"enabled", "onlyonce", "dashboard_type", "notify_type"} {
		if !bytes.Contains(form, []byte(field)) {
			t.Fatal("source form missing", field)
		}
	}
	initialPID := s.workersSS()[ssSource]
	if initialPID == 0 {
		t.Fatal("actual standard business process missing")
	}
	disabled := ssConfig(false, false, "all", "total")
	s.okSS("PUT", "/api/plugins/"+ssSource, disabled)
	s.configSS(ssSource, disabled)
	// Normal site management emits its actual SiteUpdated/core cache side effects.
	// All of those requests still traverse the strict owned proxy, never real PT.
	for i, host := range ssTargets {
		id, name := aID, "Owned Nexus A"
		if i == 1 {
			id, name = bID, "Owned Nexus B"
		}
		config := map[string]any{"id": id, "name": name, "kind": "nexusphp", "base_url": "https://" + host + "/", "domain": []string{"btschool.club", "hdsky.me"}[i], "cookie": peer.cookie[host], "ua": "Owned-Source-Nexus-UA", "proxy": true, "enabled": true, "pri": i}
		s.okSS("POST", "/api/sites/manage", config)
	}
	ssWait(t, "ordinary source site-created cache reaches SQLite", 30*time.Second, func() bool {
		return bytes.Contains(ssHistory(t, s, aID), []byte("self")) && bytes.Contains(ssHistory(t, s, bID), []byte("self"))
	})
	lastCount := peer.count()
	quietSince := time.Now()
	ssWait(t, "site-created/icon requests settle", 10*time.Second, func() bool {
		n := peer.count()
		if n != lastCount {
			lastCount = n
			quietSince = time.Now()
		}
		return time.Since(quietSince) > 1200*time.Millisecond
	})
	peer.assert(t)
	s.record("ss_owned_network", peer.report())
	if len(s.kvSS(ssSource)) != 0 || len(s.noticesSS()) != 0 {
		t.Fatal("disabled instance received a summary from single-site events")
	}

	// The source API is still registered while disabled. Test outer auth separately
	// from source's independent query-key branch; no raw key/headers enter evidence.
	before := peer.count()
	status, raw := s.apiSS(ssSource, "btschool.club", "", "wrong-owned-key", false)
	if status != 401 {
		t.Fatal("outer API auth did not reject", status)
	}
	status, raw = s.apiSS(ssSource, "btschool.club", "", "wrong-owned-key", true)
	ssAssertAPI(t, status, raw, false, "API密钥错误")
	if peer.count() != before {
		t.Fatal("wrong source key reached site network")
	}
	status, _ = s.httpSS("GET", "/api/v2/plugin/"+ssSource+"/refresh_by_domain?domain=btschool.club", nil, map[string]string{"X-API-KEY": s.token})
	if status != 422 || peer.count() != before {
		t.Fatal("required source query key lost its HTTP boundary", status)
	}
	for _, locale := range []string{"", "zh-CN", "zh-TW", "en-US"} {
		status, raw = s.apiSS(ssSource, "not-configured.invalid", locale, s.token, false)
		ssAssertAPI(t, status, raw, false, "站点 not-configured.invalid 不存在")
		var response struct {
			MessageI18n string `json:"message_i18n"`
		}
		_ = json.Unmarshal(raw, &response)
		want := "站点 not-configured.invalid 不存在"
		if locale == "zh-TW" {
			want = "站點 not-configured.invalid 不存在"
		}
		if locale == "en-US" {
			want = "Site not-configured.invalid does not exist"
		}
		if response.MessageI18n != want {
			t.Fatal("actual HTTP locale response differs", locale, response.MessageI18n)
		}
	}
	if peer.count() != before {
		t.Fatal("unknown source indexer reached site network")
	}
	for _, locale := range []string{"", "zh-CN", "zh-TW", "en-US"} {
		status, raw = s.apiSS(ssSource, "btschool.club", locale, s.token, false)
		data := ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功")
		ssAssertTrafficDTO(t, data, "2147483648")
	}
	for _, prefix := range []string{"/api/v2/plugin/" + ssSource, "/api/plugins/" + ssSource + "/api"} {
		status, raw = s.httpSS("GET", prefix+"/refresh_by_domain?domain=btschool.club&apikey="+s.token, nil, nil)
		ssAssertTrafficDTO(t, ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功"), "2147483648")
	}
	if len(s.kvSS(ssSource)) != 0 || len(s.noticesSS()) != 0 {
		t.Fatal("single-site refresh became a global summary")
	}
	oldHistory := ssHistory(t, s, aID)
	oldEvents := s.dbSS().Events[aID]
	peer.set(ssTargets[0], "null", 2)
	status, raw = s.apiSS(ssSource, "btschool.club", "en", s.token, false)
	ssAssertAPI(t, status, raw, false, "站点 btschool.club 刷新数据失败，未获取到数据")
	if !ssJSONEqual(oldHistory, ssHistory(t, s, aID)) || s.dbSS().Events[aID] != oldEvents {
		t.Fatal("native None replaced old daily data or emitted SiteRefreshed")
	}
	peer.set(ssTargets[0], "error", 2)
	status, raw = s.apiSS(ssSource, "btschool.club", "zh-TW", s.token, false)
	data := ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功")
	if string(data["err_msg"]) != `"未检测到已登陆，请检查cookies是否过期"` || !ssJSONEqual(oldHistory, ssHistory(t, s, aID)) {
		t.Fatal("current error DTO truth/daily row preservation changed", data)
	}
	peer.set(ssTargets[0], "normal", 8)

	// Actual common SourceRefreshAll -> native HTTPS -> SQLite -> both site facts
	// and one '*' -> ordinary enabled event -> real business notice + instance KV.
	beforeDB := s.dbSS()
	beforeNotices := len(s.noticesSS())
	ssTrigger(t, s, ssSource, "all", "total", true)
	ssWait(t, "actual ordinary summary and persisted receipt", 15*time.Second, func() bool { return len(s.noticesSS()) == beforeNotices+1 && s.kvSS(ssSource)["last_notify"] != nil })
	afterDB := s.dbSS()
	if afterDB.Events[aID] != beforeDB.Events[aID]+1 || afterDB.Events[bID] != beforeDB.Events[bID]+1 {
		t.Fatal("ordinary all refresh missing/duplicated single site facts", beforeDB, afterDB)
	}
	notice := s.noticesSS()[0]
	text, _ := notice["message"].(string)
	for _, part := range []string{"【汇总】", "Owned Nexus A", "Owned Nexus B", "8.0G", "2.0G"} {
		if !strings.Contains(text, part) {
			t.Fatal("native summary incomplete", part, text)
		}
	}
	var receipt struct{ Fingerprint string }
	_ = json.Unmarshal(s.kvSS(ssSource)["last_notify"], &receipt)
	if receipt.Fingerprint != fmt.Sprintf("%x", sha256.Sum256([]byte(text))) {
		t.Fatal("source notice receipt does not fingerprint its exact message")
	}
	originalKV := s.kvSS(ssSource)
	beforeNotices = len(s.noticesSS())
	ssTrigger(t, s, ssSource, "all", "total", true)
	time.Sleep(300 * time.Millisecond)
	if len(s.noticesSS()) != beforeNotices {
		t.Fatal("same source body repeated")
	}
	ssAssertKV(t, s.kvSS(ssSource), originalKV)

	page := s.okSS("GET", "/api/plugins/"+ssSource+"/page", nil)
	if !bytes.Contains(page, []byte("VApexChart")) || !bytes.Contains(page, []byte("Owned Nexus A")) {
		t.Fatal("actual page tree missing source components/data")
	}
	dashboard := s.okSS("GET", "/api/plugins/"+ssSource+"/dashboard?key=", nil)
	if !bytes.Contains(dashboard, []byte("VApexChart")) {
		t.Fatal("actual dashboard missing renderer components")
	}
	metadata := s.okSS("GET", "/api/plugins/dashboard/meta", nil)
	var cards []struct{ ID, Name, Key string }
	if json.Unmarshal(metadata, &cards) != nil || len(cards) != 1 || cards[0].ID != ssSource || cards[0].Key != "" || cards[0].Name != "站点数据统计" {
		t.Fatal("default source dashboard metadata missing")
	}
	nav := s.okSS("GET", "/api/plugins/navigation", nil)
	var sidebar []json.RawMessage
	if json.Unmarshal(nav, &sidebar) != nil || bytes.Contains(nav, []byte(ssSource)) {
		t.Fatal("Vuetify source without get_sidebar_nav must not gain a sidebar entry")
	}
	jobs := s.okSS("GET", "/api/v1/dashboard/schedule", nil)
	if bytes.Contains(jobs, []byte(ssSource)) {
		t.Fatal("source with get_service=None gained public jobs")
	}

	s.okSS("POST", "/api/plugins/"+ssSource+"/clone", map[string]any{"suffix": "Owned", "name": "Owned Site twin"})
	clonePID := s.workersSS()[ssClone]
	if clonePID == 0 || clonePID == initialPID || s.workersSS()[ssSource] != initialPID || len(s.kvSS(ssClone)) != 0 {
		t.Fatal("clone identity/KV not isolated")
	}
	beforeNotices = len(s.noticesSS())
	ssTrigger(t, s, ssClone, "today", "total", true)
	ssWait(t, "clone receipt in own namespace", 15*time.Second, func() bool { return s.kvSS(ssClone)["last_notify"] != nil && len(s.noticesSS()) == beforeNotices+1 })
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	// A changed body would update the source receipt if disabled broadcasts were
	// wrongly delivered. Its API remains usable regardless of this event gate.
	s.okSS("PUT", "/api/plugins/"+ssSource, disabled)
	peer.set(ssTargets[0], "normal", 9)
	beforeNotices = len(s.noticesSS())
	ssTrigger(t, s, ssClone, "today", "total", true)
	ssWait(t, "changed clone-only ordinary notice", 15*time.Second, func() bool { return len(s.noticesSS()) == beforeNotices+1 })
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	metadata = s.okSS("GET", "/api/plugins/dashboard/meta", nil)
	if json.Unmarshal(metadata, &cards) != nil || len(cards) != 1 || cards[0].ID != ssClone || cards[0].Key != "" || cards[0].Name != "Owned Site twin" {
		t.Fatal("disabled/default-key clone dashboard metadata mismatch", string(metadata))
	}
	status, raw = s.apiSS(ssSource, "btschool.club", "", s.token, false)
	ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功")
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	cloneConfig := ssConfig(false, false, "today", "total")
	s.okSS("PUT", "/api/plugins/"+ssClone, cloneConfig)
	cloneKV := s.kvSS(ssClone)
	status, raw = s.apiSS(ssClone, "btschool.club", "", s.token, false)
	ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功")
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	ssAssertKV(t, s.kvSS(ssClone), cloneKV)

	// Explicitly synthetic module-result supplement, not native-site evidence.
	// The ordinary module registry and host chain/SQLite/API are still real.
	module := ssLoadRelease(t, os.Getenv("SITESTATISTIC_MODULE_WORKER_BINARY"), "OwnedModuleOverride")
	moduleRepo := ssRepo(t, module)
	s.installSS("OwnedModuleOverride", moduleRepo, false)
	wide := json.RawMessage(`{"domain":null,"username":"Owned module DTO","userid":"7","user_level":null,"join_at":null,"bonus":null,"upload":9007199254740993,"download":2,"ratio":null,"seeding":0,"leeching":0,"seeding_size":0,"leeching_size":0,"seeding_info":[[3,1024]],"message_unread":0,"message_unread_contents":[["title",null,"body",{"z":1267650600228229401496703205376,"a":2}]],"err_msg":null,"updated_day":null,"updated_time":null}`)
	moduleConfig := func(result any) map[string]any {
		return map[string]any{"enabled": true, "modules": map[string]string{"refresh_userdata": "module_execute"}, "result": result}
	}
	s.okSS("PUT", "/api/plugins/OwnedModuleOverride", moduleConfig(wide))
	before = peer.count()
	status, raw = s.apiSS(ssSource, "btschool.club", "", s.token, false)
	data = ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功")
	got, _ := json.Marshal(data)
	if !ssJSONEqual(got, wide) || !bytes.Contains(raw, []byte(`{"z":1267650600228229401496703205376,"a":2}`)) || peer.count() != before {
		t.Fatal("current synthetic DTO normalized/fell through native", string(got))
	}
	s.record("ss_module_supplement", map[string]any{"classification": "ordinary real module override with synthetic current DTO; not native parser evidence", "case": "wide/null/raw-list current DTO", "data": json.RawMessage(got), "native_requests": 0})
	// SQLite Integer-to-TEXT binding still rejects a >int64 integer userid.
	// An error DTO with an already successful day skips that write in source.
	wideUserID := json.RawMessage(strings.Replace(string(wide), `"userid":"7"`, `"userid":1267650600228229401496703205376`, 1))
	priorHistory := ssHistory(t, s, aID)
	priorFacts := s.dbSS().Events[aID]
	s.okSS("PUT", "/api/plugins/OwnedModuleOverride", moduleConfig(wideUserID))
	before = peer.count()
	status, raw = s.apiSS(ssSource, "btschool.club", "", s.token, false)
	if status < 400 || status >= 600 || peer.count() != before || s.dbSS().Events[aID] != priorFacts || !ssJSONEqual(priorHistory, ssHistory(t, s, aID)) {
		t.Fatal("oversize Integer userid did not fail atomically", status)
	}
	errorWide := json.RawMessage(strings.Replace(string(wideUserID), `"err_msg":null`, `"err_msg":"owned ordinary module error"`, 1))
	s.okSS("PUT", "/api/plugins/OwnedModuleOverride", moduleConfig(errorWide))
	before = peer.count()
	status, raw = s.apiSS(ssSource, "btschool.club", "", s.token, false)
	data = ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功")
	got, _ = json.Marshal(data)
	if !ssJSONEqual(got, errorWide) || peer.count() != before || s.dbSS().Events[aID] != priorFacts+1 || !ssJSONEqual(priorHistory, ssHistory(t, s, aID)) {
		t.Fatal("source old-good-day/error-DTO write skip changed", status, string(got))
	}
	s.record("ss_module_supplement", map[string]any{"classification": "ordinary real module override with synthetic current DTO; source ORM binding distinction", "cases": []string{"integer userid overflow: non2xx/no row or refreshed fact", "error DTO with old-good-day: current wide DTO returned; DB write skipped and single refreshed fact"}})
	s.okSS("PUT", "/api/plugins/OwnedModuleOverride", moduleConfig(false))
	before = peer.count()
	status, raw = s.apiSS(ssSource, "btschool.club", "", s.token, false)
	ssAssertAPI(t, status, raw, false, "站点 btschool.club 刷新数据失败，未获取到数据")
	if peer.count() != before {
		t.Fatal("false module result fell through to native")
	}
	s.okSS("PUT", "/api/plugins/OwnedModuleOverride", map[string]any{"enabled": false})
	s.okSS("DELETE", "/api/plugins/OwnedModuleOverride", nil)
	// Restore page data through the real native chain, with business events gated.
	ssTrigger(t, s, ssSource, "all", "total", false)
	s.okSS("PUT", "/api/plugins/"+ssSource, disabled)
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	ssAssertKV(t, s.kvSS(ssClone), cloneKV)

	beforePIDs := s.workersSS()
	s.okSS("POST", "/api/plugins/"+ssSource+"/reload", map[string]any{})
	afterPIDs := s.workersSS()
	if afterPIDs[ssSource] == beforePIDs[ssSource] || afterPIDs[ssSource] == 0 || afterPIDs[ssClone] != beforePIDs[ssClone] {
		t.Fatal("reload identity/lifecycle mismatch", beforePIDs, afterPIDs)
	}
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	ssAssertKV(t, s.kvSS(ssClone), cloneKV)
	repo.change(second)
	s.installSS(ssSource, repo, true)
	s.record("ss_manifest_only_update", map[string]any{"from": first.version, "to": second.version, "worker_sha256": second.hash, "not_upstream_release": true})
	s.configSS(ssSource, disabled)
	s.configSS(ssClone, cloneConfig)
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	ssAssertKV(t, s.kvSS(ssClone), cloneKV)

	// UI holds only after both instances are disabled, once=false and data ready.
	if os.Getenv("SITESTATISTIC_UI_WAIT") != "" {
		public := os.Getenv("SITESTATISTIC_PUBLIC_URL")
		if public == "" {
			public = s.base
		}
		ready := map[string]any{"url": public, "username": ownedUser, "login": "owned test account constants from testhost_main_test.go; no token or cookie in this file", "source": ssSource, "clone": ssClone, "pid": s.cmd.Process.Pid, "continue_file": filepath.Join(dir, "ui-complete"), "page_data": "two native owned HTTPS sites; both enabled=false and persisted onlyonce=false", "UI_wait_minutes": 50, "global_test_timeout_minutes": 70}
		readyRaw, _ := json.MarshalIndent(ready, "", "  ")
		if e := os.WriteFile(filepath.Join(dir, "ui-ready.json"), append(readyRaw, '\n'), 0600); e != nil {
			t.Fatal(e)
		}
		s.record("ss_ui_ready", map[string]any{"url": public, "pid": s.cmd.Process.Pid, "continue_file": filepath.Join(dir, "ui-complete"), "wait_minutes": 50})
		t.Log("SiteStatistic UI_STAGE_READY", filepath.Join(dir, "ui-ready.json"))
		until := time.Now().Add(50 * time.Minute)
		for {
			if _, e := os.Stat(filepath.Join(dir, "ui-complete")); e == nil {
				break
			}
			if time.Now().After(until) {
				t.Fatal("50-minute actual browser stage expired")
			}
			select {
			case <-ctx.Done():
				t.Fatal("global70-minute driver expired")
			case <-time.After(time.Second):
			}
		}
	}
	// UI can exercise normal enable controls, then this driver disables both with
	// once=false before its subsequent cold/recovery assertions.
	s.okSS("PUT", "/api/plugins/"+ssSource, disabled)
	s.okSS("PUT", "/api/plugins/"+ssClone, cloneConfig)
	originalKV, cloneKV = s.kvSS(ssSource), s.kvSS(ssClone)
	coldFacts := s.dbSS()
	coldNotices := len(s.noticesSS())
	beforePIDs = s.workersSS()
	s.stop()
	s.startSS()
	afterPIDs = s.workersSS()
	for _, id := range []string{ssSource, ssClone} {
		if beforePIDs[id] == afterPIDs[id] || afterPIDs[id] == 0 {
			t.Fatal("cold restart worker identity", beforePIDs, afterPIDs)
		}
	}
	time.Sleep(3500 * time.Millisecond)
	if s.dbSS().Events["*"] != coldFacts.Events["*"] || len(s.noticesSS()) != coldNotices {
		t.Fatal("cold restart replayed source one-shot")
	}
	s.configSS(ssSource, disabled)
	s.configSS(ssClone, cloneConfig)
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	ssAssertKV(t, s.kvSS(ssClone), cloneKV)

	// Reset clears the selected namespace, with the other instance unchanged.
	s.okSS("POST", "/api/plugins/"+ssSource+"/reset", map[string]any{})
	s.configSS(ssSource, map[string]any{})
	if len(s.kvSS(ssSource)) != 0 {
		t.Fatal("base reset retained KV")
	}
	ssAssertKV(t, s.kvSS(ssClone), cloneKV)
	ssTrigger(t, s, ssSource, "all", "total", true)
	ssWait(t, "base receipt reseeded", 15*time.Second, func() bool { return s.kvSS(ssSource)["last_notify"] != nil })
	s.okSS("PUT", "/api/plugins/"+ssSource, disabled)
	originalKV = s.kvSS(ssSource)
	s.okSS("POST", "/api/plugins/"+ssClone+"/reset", map[string]any{})
	s.configSS(ssClone, map[string]any{})
	if len(s.kvSS(ssClone)) != 0 {
		t.Fatal("clone reset retained KV")
	}
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	ssTrigger(t, s, ssClone, "today", "total", true)
	ssWait(t, "clone receipt reseeded before purge", 15*time.Second, func() bool { return s.kvSS(ssClone)["last_notify"] != nil })
	s.okSS("PUT", "/api/plugins/"+ssClone, cloneConfig)
	raw = s.okSS("DELETE", "/api/plugins/"+ssClone, nil)
	if !bytes.Contains(raw, []byte(`"data_retained":false`)) {
		t.Fatal("clone uninstall did not declare purge", string(raw))
	}
	if len(s.kvSS(ssClone)) != 0 || s.dbSS().ConfigRows[ssClone] != 0 {
		t.Fatal("clone uninstall retained namespace")
	}
	if _, e := os.Stat(filepath.Join(dir, "plugin-packages", ssClone)); !os.IsNotExist(e) {
		t.Fatal("clone code retained", e)
	}
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	status, _ = s.apiSS(ssClone, "btschool.club", "", s.token, false)
	if status != 404 {
		t.Fatal("clone API remains after uninstall", status)
	}
	raw = s.okSS("DELETE", "/api/plugins/"+ssSource, nil)
	if !bytes.Contains(raw, []byte(`"data_retained":true`)) {
		t.Fatal("base uninstall did not retain", string(raw))
	}
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	// The source public getter only exposes registered/running plugins.
	// Base uninstall retains storage, but its public configuration is now {}.
	s.configSS(ssSource, map[string]any{})
	if s.dbSS().ConfigRows[ssSource] != 1 {
		t.Fatal("base uninstall lost retained configuration storage row")
	}
	if _, e := os.Stat(filepath.Join(dir, "plugin-packages", ssSource)); e != nil {
		t.Fatal("base source code unexpectedly purged", e)
	}
	status, _ = s.apiSS(ssSource, "btschool.club", "", s.token, false)
	if status != 404 {
		t.Fatal("base API remains registered after uninstall", status)
	}
	s.installSS(ssSource, repo, false)
	s.configSS(ssSource, disabled)
	ssAssertKV(t, s.kvSS(ssSource), originalKV)
	status, raw = s.apiSS(ssSource, "btschool.club", "", s.token, false)
	ssAssertAPI(t, status, raw, true, "站点 btschool.club 刷新成功")
	peer.assert(t)
	s.record("ss_owned_network_final", peer.report())
	s.record("ss_acceptance_complete", map[string]any{"kind": "actual ordinary cmd/server+SQLite+Nexus TLS/parser+proxy+standard SDK business worker", "synthetic_inputs": "owned HTML, site/account settings, artifact index and supplemental module DTOs", "source_worker_sha256": first.hash, "update_worker_sha256": second.hash, "final_db": s.dbSS(), "not_production_or_private_migration": true})
	// Evidence must not acquire the in-memory test API token or site cookies.
	s.stop()
	entries, e := os.ReadDir(s.evidence)
	if e != nil {
		t.Fatal(e)
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		b, e := os.ReadFile(filepath.Join(s.evidence, entry.Name()))
		if e != nil {
			t.Fatal(e)
		}
		for _, secret := range []string{s.token, peer.cookie[ssTargets[0]], peer.cookie[ssTargets[1]], "PRIVATE KEY-----"} {
			if bytes.Contains(b, []byte(secret)) {
				t.Fatal("sensitive owned test material leaked into evidence", entry.Name())
			}
		}
	}
	t.Log("ordinary main native site/API/event/notification/page/dashboard/clone/cold/update/reset/uninstall driver completed; browser proof is separate coordinator evidence")
}
