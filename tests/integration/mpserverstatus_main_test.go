package integration

// Ordinary unmodified Linux cmd/server + frozen Go business worker. Root runs
// this only in a new --no-healthcheck owned internal-network container, then
// independently operates the real frontend. Compilation alone is not acceptance.
import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

type mpsRelease struct {
	manifest      map[string]any
	binary        []byte
	version, hash string
}

func mpsLoad(t *testing.T, path string) mpsRelease {
	t.Helper()
	raw, e := exec.Command(path, "--manifest").Output()
	if e != nil {
		t.Fatal("actual worker manifest", e)
	}
	var m map[string]any
	if json.Unmarshal(raw, &m) != nil || m["plugin_id"] != mpsSource {
		t.Fatal("source manifest identity")
	}
	b, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	return mpsRelease{m, b, m["version"].(string), fileHash(t, path)}
}

type mpsRepository struct {
	mu      sync.Mutex
	current mpsRelease
	server  *httptest.Server
}

func mpsRepo(t *testing.T, x mpsRelease) *mpsRepository {
	t.Helper()
	p := &mpsRepository{current: x}
	p.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		defer p.mu.Unlock()
		x := p.current
		switch r.URL.Path {
		case "/index":
			artifact := map[string]any{"platform": runtime.GOOS + "-" + runtime.GOARCH, "format": "executable", "url": p.server.URL + "/worker", "sha256": x.hash, "executable_sha256": x.hash, "size": len(x.binary), "host_contract": "light-media.sdk-resources/v1"}
			_ = json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": mpsSource, "current_version": x.version, "releases": []any{map[string]any{"version": x.version, "manifest": x.manifest, "artifacts": []any{artifact}}}})
		case "/worker":
			_, _ = w.Write(x.binary)
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(p.server.Close)
	return p
}
func (p *mpsRepository) change(x mpsRelease) { p.mu.Lock(); p.current = x; p.mu.Unlock() }
func (s *mpsMain) installMPS(repo *mpsRepository, force bool) {
	s.okMPS("POST", "/api/plugins/install", map[string]any{"plugin_id": mpsSource, "force": force, "repo_url": repo.server.URL + "/index"})
}
func mpsConfig(enable any) map[string]any {
	return map[string]any{"enable": enable, "onlyonce": true, "owned_unknown": "source preserves unknown value; one-shot is not a source feature"}
}
func mpsTexts(raw []byte) []string {
	var root any
	_ = json.Unmarshal(raw, &root)
	out := []string{}
	var walk func(any)
	walk = func(v any) {
		switch x := v.(type) {
		case map[string]any:
			if text, ok := x["text"].(string); ok {
				out = append(out, text)
			}
			for _, v := range x {
				walk(v)
			}
		case []any:
			for _, v := range x {
				walk(v)
			}
		}
	}
	walk(root)
	return out
}
func mpsCard(t *testing.T, raw []byte, label string) string {
	t.Helper()
	var root any
	_ = json.Unmarshal(raw, &root)
	found := ""
	var walk func(any)
	walk = func(v any) {
		switch x := v.(type) {
		case map[string]any:
			if x["component"] == "div" {
				if children, ok := x["content"].([]any); ok && len(children) > 1 {
					first, _ := children[0].(map[string]any)
					second, _ := children[1].(map[string]any)
					if first["text"] == label {
						found, _ = second["text"].(string)
					}
				}
			}
			for _, v := range x {
				walk(v)
			}
		case []any:
			for _, v := range x {
				walk(v)
			}
		}
	}
	walk(root)
	if found == "" {
		t.Fatal("source card missing", label, string(raw))
	}
	return found
}
func mpsHas(t *testing.T, raw []byte, values ...string) {
	t.Helper()
	text := strings.Join(mpsTexts(raw), "\n")
	for _, value := range values {
		if !strings.Contains(text, value) {
			t.Fatal("source tree text missing", value, string(raw))
		}
	}
}
func mpsFormEnable(t *testing.T, raw []byte, want any) {
	t.Helper()
	var root any
	_ = json.Unmarshal(raw, &root)
	var model map[string]any
	if x, ok := root.(map[string]any); ok {
		model, _ = x["model"].(map[string]any)
	} else if x, ok := root.([]any); ok && len(x) == 2 {
		model, _ = x[1].(map[string]any)
	}
	if model == nil || model["enable"] != want {
		t.Fatal("source merged form model value missing", want, string(raw))
	}
}

func TestMPServerStatusActualMainOwnedNamespace(t *testing.T) {
	if os.Getenv("MPS_WORKER_BINARY") == "" {
		t.Skip("opt-in ordinary Main; compile-only is not acceptance")
	}
	for _, key := range []string{"MPS_HOST_BINARY", "MPS_UPDATE_WORKER_BINARY"} {
		if os.Getenv(key) == "" {
			t.Fatal(key, "required")
		}
	}
	if runtime.GOOS != "linux" || os.Getenv("MPS_NAMESPACE_OWNED") != "1" {
		t.Fatal("only the Root-created Linux namespace; no host/global resolver mutations")
	}
	if deadline, ok := t.Deadline(); !ok || time.Until(deadline) < 69*time.Minute || time.Until(deadline) > 71*time.Minute {
		t.Fatal("test requires -test.timeout70m (UI permits50m)")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 69*time.Minute)
	defer cancel()
	dir := mpsDirectory(t)
	peer := newMPSPeer(t, dir)
	s := newMPSMain(ctx, t, dir, peer.ca, peer.proxy.URL)
	defer func() {
		s.record("mps_peer_on_return", map[string]any{"test_failed": t.Failed(), "peer": peer.report()})
	}()
	first := mpsLoad(t, os.Getenv("MPS_WORKER_BINARY"))
	update := mpsLoad(t, os.Getenv("MPS_UPDATE_WORKER_BINARY"))
	if first.version != "1.4" || update.version == first.version {
		t.Fatal("original1.4 and distinct manifest-only update required")
	}
	repo := mpsRepo(t, first)
	peer.allowArtifact(repo.server.URL)
	s.installMPS(repo, false)
	initialPID := s.workersMPS()[mpsSource]
	if initialPID == 0 {
		t.Fatal("ordinary source process missing")
	}
	s.configMPS(mpsSource, map[string]any{})
	form := s.okMPS("GET", "/api/plugins/"+mpsSource+"/form", nil)
	mpsFormEnable(t, form, false)
	before, direct := peer.counts()
	page := s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	mpsHas(t, page, "插件未启用")
	if n, _ := peer.counts(); n != before {
		t.Fatal("disabled source page performed network")
	}
	dashboard := s.okMPS("GET", "/api/plugins/"+mpsSource+"/dashboard?key=", nil)
	mpsHas(t, dashboard, "服务状态正常")
	if mpsCard(t, dashboard, "请求速率") != "待刷新" {
		t.Fatal("first disabled direct dashboard replayed sample")
	}
	if n, d := peer.counts(); n != before+1 || d != direct {
		t.Fatal("disabled direct dashboard omitted HTTP or probed TLS", n, d)
	}
	// The source endpoint overlays raw saved config onto get_form defaults.
	// The truthy string remains raw in the form; state/page use its truth value.
	truthy := mpsConfig("false")
	s.okMPS("PUT", "/api/plugins/"+mpsSource, truthy)
	s.configMPS(mpsSource, truthy)
	mpsFormEnable(t, s.okMPS("GET", "/api/plugins/"+mpsSource+"/form", nil), "false")
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	mpsHas(t, page, "服务状态正常", "HTTP状态", "响应延迟", "活跃连接", "请求速率", "连接速率", "等待连接", "处理中连接", "请求/连接", "总请求数", "总连接数", "丢弃连接", "TLS证书", "连接明细", "服务探测", "Owned-MPS-Nginx")
	if got := mpsCard(t, page, "活跃连接"); got != "12" {
		t.Fatal("real fixed-source parser value", got)
	}
	if got := mpsCard(t, page, "TLS证书"); !strings.Contains(got, " 天") {
		t.Fatal("native verifiedTLS443 did not produce source cert", got)
	}
	_, warmDirect := peer.counts()
	if warmDirect <= direct {
		t.Fatal("details omitted nativeTLS direct probe")
	}
	s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	if _, d := peer.counts(); d != warmDirect {
		t.Fatal("source TLS cache not used")
	}
	// Real public handler deadline propagation: six seconds exceeds neither
	// source's20-second read-idle nor caller45-second deadline.
	peer.set("slow6", true)
	s.okMPS("POST", "/api/plugins/"+mpsSource+"/reload", map[string]any{})
	started := time.Now()
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	value := mpsCard(t, page, "响应延迟")
	seconds, e := strconv.ParseFloat(strings.TrimSuffix(value, " 秒"), 64)
	if e != nil || seconds < 6 || time.Since(started) < 6*time.Second {
		t.Fatal("ordinary Main used short timeout or lost source elapsed", value, e)
	}
	s.record("mps_actual_over5s_handler", map[string]any{"wall_ms": time.Since(started).Milliseconds(), "source_latency": value, "source_idle_timeout_seconds": 20, "caller_timeout_seconds": 45})
	peer.set("ok", true)
	// Failure and success TLS caches: origin HTTP deliberately still accepts
	// its untrusted cert, while the separate native TLS probe rejects it.
	peer.set("ok", false)
	s.okMPS("POST", "/api/plugins/"+mpsSource+"/reload", map[string]any{})
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	mpsHas(t, page, "服务状态正常")
	if mpsCard(t, page, "TLS证书") != "异常" {
		t.Fatal("source independent TLS did not fail")
	}
	_, failedDirect := peer.counts()
	s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	peer.set("ok", true)
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	if _, d := peer.counts(); d != failedDirect || mpsCard(t, page, "TLS证书") != "异常" {
		t.Fatal("source failure cache dropped before init")
	}
	s.okMPS("POST", "/api/plugins/"+mpsSource+"/reload", map[string]any{})
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	if !strings.Contains(mpsCard(t, page, "TLS证书"), " 天") {
		t.Fatal("reload did not clear nativeTLS failure cache")
	}
	// HTTP failures still retain source error trees. A later valid request
	// demonstrates cached sample recovery without fabricating a success body.
	peer.set("503", true)
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	mpsHas(t, page, "无法连接服务器")
	if mpsCard(t, page, "HTTP状态") != "503" {
		t.Fatal("source Response bool lost")
	}
	peer.set("broken", true)
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	mpsHas(t, page, "服务器状态格式异常：缺少活跃连接数据")
	beforeExceptionPID := s.workersMPS()[mpsSource]
	if beforeExceptionPID == 0 {
		t.Fatal("worker missing before source text exception")
	}
	beforeExceptionHTTP, beforeExceptionTLS := peer.counts()
	peer.set("undefined", true)
	status, errorBody, e := s.raw(ctx, "GET", "/api/plugins/"+mpsSource+"/page", nil)
	var emptyPage map[string]any
	if e != nil || status != http.StatusOK || json.Unmarshal(errorBody, &emptyPage) != nil || emptyPage == nil || len(emptyPage) != 0 {
		t.Fatal("source page endpoint must catch UnicodeError and return exact empty object", status, string(errorBody), e)
	}
	if pid := s.workersMPS()[mpsSource]; pid != beforeExceptionPID {
		t.Fatal("source text exception replaced/killed worker", beforeExceptionPID, pid)
	}
	peer.set("ok", true)
	page = s.okMPS("GET", "/api/plugins/"+mpsSource+"/page", nil)
	mpsHas(t, page, "服务状态正常", "Owned-MPS-Nginx")
	if mpsCard(t, page, "活跃连接") != "12" || s.workersMPS()[mpsSource] != beforeExceptionPID {
		t.Fatal("same worker did not recover real parsed source page after UnicodeError")
	}
	if n, d := peer.counts(); n != beforeExceptionHTTP+2 || d != beforeExceptionTLS {
		t.Fatal("exception/recovery source HTTP or cached TLS sequence changed", n-beforeExceptionHTTP, d-beforeExceptionTLS)
	}
	s.record("mps_source_page_exception_and_recovery", map[string]any{"exception_status": status, "exception_data": emptyPage, "same_worker_pid": beforeExceptionPID, "healthy_followup": "source normal alert + parsed active12, no reload", "owned_HTTP_delta": 2, "directTLS_delta": 0, "classification": "original page endpoint catches plugin method exception into empty object; HTTP200 alone is not success"})
	// More than64 calls and256 RPC through ordinary Main. Exact original
	// per-callback RPC accounting is separately bound to SDK95 worker evidence.
	batchBefore, batchDirect := peer.counts()
	var wg sync.WaitGroup
	fail := make(chan string, 9)
	var inFlight, peak, done, errorsCount atomic.Int32
	batchCall := func() bool {
		active := inFlight.Add(1)
		defer inFlight.Add(-1)
		for old := peak.Load(); active > old; old = peak.Load() {
			if peak.CompareAndSwap(old, active) {
				break
			}
		}
		status, raw, e := s.raw(ctx, "GET", "/api/plugins/"+mpsSource+"/dashboard?key=", nil)
		done.Add(1)
		if e != nil || status != 200 || !bytes.Contains(raw, []byte("服务状态正常")) {
			errorsCount.Add(1)
			fail <- fmt.Sprintf("status%d error%v", status, e)
			return false
		}
		return true
	}
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 20; j++ {
				if !batchCall() {
					return
				}
			}
		}()
	}
	wg.Wait()
	for i := 0; i < 5; i++ {
		if !batchCall() {
			break
		}
	}
	close(fail)
	for msg := range fail {
		t.Fatal("ordinary dashboard batch", msg)
	}
	if done.Load() != 165 || errorsCount.Load() != 0 || peak.Load() > 8 {
		t.Fatal("ordinary batch observations", done.Load(), errorsCount.Load(), peak.Load())
	}
	if n, d := peer.counts(); n != batchBefore+165 || d != batchDirect {
		t.Fatal("ordinary direct dashboard omitted/duplicated HTTP or included nativeTLS", n-batchBefore, d-batchDirect)
	}
	s.record("mps_main165_batch", map[string]any{"total": 165, "configured_parallel_width": 8, "actual_peak_inflight_HTTP": peak.Load(), "actual_done": done.Load(), "actual_errors": errorsCount.Load(), "actual_owned_HTTP_delta": 165, "directTLS_delta": 0, "RPC_classification": "ordinary Main API exposes no per-callback RPC counter; bound standalone SDK95 observation is separate, not renamed as Main telemetry", "RPC_inference_from_exact_worker_success_path": map[string]any{"per_call": 3, "total": 495, "classification": "source/code-derived, not measured Main pipe"}})
	nav := s.okMPS("GET", "/api/plugins/navigation", nil)
	if bytes.Contains(nav, []byte(mpsSource)) {
		t.Fatal("source Vuetify no-sidebar override gained sidebar")
	}
	jobs := s.okMPS("GET", "/api/v1/dashboard/schedule", nil)
	if bytes.Contains(jobs, []byte(mpsSource)) {
		t.Fatal("source no-service gained scheduler")
	}
	metadata := s.okMPS("GET", "/api/plugins/dashboard/meta", nil)
	if !bytes.Contains(metadata, []byte(mpsSource)) {
		t.Fatal("source inherited default dashboard metadata absent")
	}
	// Each clone has its own process, raw config and first sample.
	s.okMPS("POST", "/api/plugins/"+mpsSource+"/clone", map[string]any{"suffix": "Owned", "name": "Owned MPS twin"})
	pids := s.workersMPS()
	if pids[mpsClone] == 0 || pids[mpsClone] == pids[mpsSource] {
		t.Fatal("platform clone process identity", pids)
	}
	cloneConfig := mpsConfig(false)
	s.okMPS("PUT", "/api/plugins/"+mpsClone, cloneConfig)
	s.configMPS(mpsSource, truthy)
	cloneDashboard := s.okMPS("GET", "/api/plugins/"+mpsClone+"/dashboard?key=", nil)
	if mpsCard(t, cloneDashboard, "请求速率") != "待刷新" {
		t.Fatal("clone sample leaked from base")
	}
	s.configMPS(mpsClone, cloneConfig)
	// Reinit/stop under ordinary framework scope revocation cancels the caller;
	// direct source noopstop/inflight-refill semantics are independently tested.
	peer.set("hold", true)
	type activeResult struct {
		status int
		err    error
	}
	active := make(chan activeResult, 1)
	go func() {
		status, _, e := s.raw(ctx, "GET", "/api/plugins/"+mpsSource+"/page", nil)
		active <- activeResult{status, e}
	}()
	select {
	case <-peer.entered:
	case <-time.After(10 * time.Second):
		t.Fatal("active native request did not enter")
	}
	disabled := mpsConfig(false)
	s.okMPS("PUT", "/api/plugins/"+mpsSource, disabled)
	peer.set("ok", true)
	close(peer.release)
	select {
	case result := <-active:
		s.record("mps_active_reinit_completion", map[string]any{"status": result.status, "error_type": fmt.Sprintf("%T", result.err), "classification": "actual ordinary Main completion under platform reinit; source noopstop/refill proven separately; no asserted Python cancellation equivalence"})
	case <-time.After(10 * time.Second):
		t.Fatal("typed caller scope did not finish active request")
	}
	s.configMPS(mpsSource, disabled)
	beforePID := s.workersMPS()[mpsSource]
	s.okMPS("POST", "/api/plugins/"+mpsSource+"/reload", map[string]any{})
	if got := s.workersMPS()[mpsSource]; got == 0 || got == beforePID {
		t.Fatal("ordinary reload did not replace process")
	}
	s.configMPS(mpsSource, disabled)
	s.configMPS(mpsClone, cloneConfig)
	repo.change(update)
	s.installMPS(repo, true)
	s.record("mps_manifest_only_update", map[string]any{"from": first.version, "to": update.version, "worker_sha256": update.hash, "not_upstream_release": true})
	s.configMPS(mpsSource, disabled)
	s.configMPS(mpsClone, cloneConfig)
	// Root performs desktop/mobile controls, logs, clone and persisted dashboard
	// via actual frontend. Close pollers before writing ui-complete.
	if os.Getenv("MPS_UI_WAIT") != "" {
		s.okMPS("PUT", "/api/plugins/"+mpsSource, mpsConfig(true))
		public := os.Getenv("MPS_PUBLIC_URL")
		if public == "" {
			public = s.base
		}
		ready := map[string]any{"url": public, "username": ownedUser, "login": "ownedUser/ownedPassword fixture constants; no tokens/cookies in file", "source": mpsSource, "clone": mpsClone, "source_enabled": true, "clone_enabled": false, "data": "synthetic owned Nginx via fixed URI/namespace real TLS/DNS, not live public availability", "CA_file_scope": "owned same-inode public CA bound into container system trust", "continue_file": filepath.Join(dir, "ui-complete"), "require_before_continue": "leave polling pages/close UI source requests; driver then disables instances before cold restart", "UI_wait_minutes": 50, "global_timeout_minutes": 70}
		b, _ := json.MarshalIndent(ready, "", "  ")
		if e = os.WriteFile(filepath.Join(dir, "ui-ready.json"), append(b, '\n'), 0600); e != nil {
			t.Fatal(e)
		}
		s.record("mps_ui_ready", ready)
		t.Log("MPS UI_STAGE_READY", filepath.Join(dir, "ui-ready.json"))
		until := time.Now().Add(50 * time.Minute)
		for {
			if _, e = os.Stat(filepath.Join(dir, "ui-complete")); e == nil {
				break
			}
			if time.Now().After(until) {
				t.Fatal("50minute actual UI stage expired")
			}
			select {
			case <-ctx.Done():
				t.Fatal(ctx.Err())
			case <-time.After(time.Second):
			}
		}
	}
	s.okMPS("PUT", "/api/plugins/"+mpsSource, disabled)
	s.okMPS("PUT", "/api/plugins/"+mpsClone, cloneConfig)
	before, _ = peer.counts()
	s.stop()
	s.startMPS()
	time.Sleep(2100 * time.Millisecond)
	if n, _ := peer.counts(); n != before {
		t.Fatal("cold startup replayed ignored one-shot or started background probe", n, before)
	}
	s.configMPS(mpsSource, disabled)
	s.configMPS(mpsClone, cloneConfig)
	dashboard = s.okMPS("GET", "/api/plugins/"+mpsSource+"/dashboard?key=", nil)
	if mpsCard(t, dashboard, "请求速率") != "待刷新" {
		t.Fatal("cold persisted source sample")
	}
	s.okMPS("POST", "/api/plugins/"+mpsSource+"/reset", map[string]any{})
	s.configMPS(mpsSource, map[string]any{})
	s.configMPS(mpsClone, cloneConfig)
	s.okMPS("PUT", "/api/plugins/"+mpsSource, disabled)
	s.okMPS("POST", "/api/plugins/"+mpsClone+"/reset", map[string]any{})
	s.configMPS(mpsClone, map[string]any{})
	s.configMPS(mpsSource, disabled)
	s.okMPS("PUT", "/api/plugins/"+mpsClone, cloneConfig)
	raw := s.okMPS("DELETE", "/api/plugins/"+mpsClone, nil)
	if !bytes.Contains(raw, []byte(`"data_retained":false`)) {
		t.Fatal("clone purge declaration")
	}
	if _, e = os.Stat(filepath.Join(dir, "plugin-packages", mpsClone)); !os.IsNotExist(e) {
		t.Fatal("clone code not purged", e)
	}
	s.configMPS(mpsSource, disabled)
	raw = s.okMPS("DELETE", "/api/plugins/"+mpsSource, nil)
	if !bytes.Contains(raw, []byte(`"data_retained":true`)) {
		t.Fatal("base retention declaration")
	}
	s.configMPS(mpsSource, map[string]any{})
	if _, e = os.Stat(filepath.Join(dir, "plugin-packages", mpsSource)); e != nil {
		t.Fatal("base code retention", e)
	}
	s.installMPS(repo, false)
	s.configMPS(mpsSource, disabled)
	peer.assert(t)
	s.record("mps_peer_final", peer.report())
	s.record("mps_acceptance_complete", map[string]any{"classification": "ordinary Linux Main+fixedURI+owned hosts resolver/nativeTLS/strictproxy+standard business process", "source_worker_sha256": first.hash, "update_worker_sha256": update.hash, "not_public_service_availability": true, "not_production_config_migration": true})
	s.stop()
}
