package integration

// Only opt-in ordinary cmd/server instrumentation. The fixture uses finite SDK
// capabilities in fresh owned namespaces; it is not a business implementation.
import (
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
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

const puiMarker = "light-media-plugins/PluginUnInstall/20261105/owned-only"
const puiID = "PluginUnInstall"
const puiProbe = "OwnedPuiFixture"
const puiMPS = "MPServerStatus"

type puiRelease struct {
	manifest      map[string]any
	binary        []byte
	hash, version string
}

func puiLoad(t *testing.T, path, id string, order int) puiRelease {
	t.Helper()
	raw, err := exec.Command(path, "--manifest").Output()
	if err != nil {
		t.Fatal("execute actual worker manifest", id, err)
	}
	var m map[string]any
	if json.Unmarshal(raw, &m) != nil || m["plugin_id"] != id {
		t.Fatal("actual manifest identity", id)
	}
	got := 0
	if n, ok := m["plugin_order"].(float64); ok {
		got = int(n)
	}
	if got != order {
		t.Fatal("actual executable class sort", id, got, order)
	}
	b, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	return puiRelease{m, b, fileHash(t, path), m["version"].(string)}
}

type puiRepository struct {
	mu       sync.Mutex
	release  puiRelease
	server   *httptest.Server
	requests []string
}

func puiRepo(t *testing.T, x puiRelease) *puiRepository {
	t.Helper()
	r := &puiRepository{release: x}
	r.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, q *http.Request) {
		r.mu.Lock()
		defer r.mu.Unlock()
		r.requests = append(r.requests, q.Method+" "+q.URL.Path)
		if q.Method != "GET" {
			http.Error(w, "method", 405)
			return
		}
		x := r.release
		switch q.URL.Path {
		case "/index":
			artifact := map[string]any{"platform": runtime.GOOS + "-" + runtime.GOARCH, "format": "executable", "sha256": x.hash, "executable_sha256": x.hash, "size": len(x.binary), "host_contract": "light-media.sdk-resources/v1", "url": r.server.URL + "/worker"}
			_ = json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": x.manifest["plugin_id"], "current_version": x.version, "releases": []any{map[string]any{"version": x.version, "manifest": x.manifest, "artifacts": []any{artifact}}}})
		case "/worker":
			_, _ = w.Write(x.binary)
		default:
			http.NotFound(w, q)
		}
	}))
	t.Cleanup(r.server.Close)
	return r
}
func (r *puiRepository) change(x puiRelease) { r.mu.Lock(); defer r.mu.Unlock(); r.release = x }

// Validate both transport and ordinary business outcome. A 200 false/empty
// envelope is not an installation, save, reload or uninstall success.
func puiResponse(status int, raw []byte, success bool) (json.RawMessage, error) {
	if status != 200 || !json.Valid(raw) {
		return nil, fmt.Errorf("HTTP outcome %d JSON=%t", status, json.Valid(raw))
	}
	var envelope map[string]json.RawMessage
	if json.Unmarshal(raw, &envelope) != nil || envelope == nil {
		return nil, fmt.Errorf("response object required")
	}
	if s := envelope["success"]; s != nil && string(s) != "true" {
		return nil, fmt.Errorf("host business failure")
	}
	data := json.RawMessage(raw)
	if v := envelope["data"]; v != nil {
		data = v
	}
	if success {
		var v struct {
			Success *bool `json:"success"`
		}
		if json.Unmarshal(data, &v) != nil || v.Success == nil || !*v.Success {
			return nil, fmt.Errorf("explicit business success missing")
		}
	}
	return data, nil
}
func puiEqual(a, b any) bool {
	ar, _ := json.Marshal(a)
	br, _ := json.Marshal(b)
	var av, bv any
	da := json.NewDecoder(bytes.NewReader(ar))
	da.UseNumber()
	db := json.NewDecoder(bytes.NewReader(br))
	db.UseNumber()
	if da.Decode(&av) != nil || db.Decode(&bv) != nil {
		return false
	}
	ar, _ = json.Marshal(av)
	br, _ = json.Marshal(bv)
	return bytes.Equal(ar, br)
}
func puiJSON(t *testing.T, raw json.RawMessage) any {
	t.Helper()
	var v any
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	if e := d.Decode(&v); e != nil {
		t.Fatal("JSON", e)
	}
	return v
}
func puiAssert(t *testing.T, got, want any, label string) {
	t.Helper()
	if !puiEqual(got, want) {
		t.Fatalf("%s: got %s want %s", label, puiEncode(got), puiEncode(want))
	}
}
func puiEncode(v any) []byte { r, _ := json.Marshal(v); return r }

type puiMain struct {
	*mainHost
	token   string
	allPIDs map[int]bool
}

func puiNewMain(t *testing.T) *puiMain {
	t.Helper()
	binary := os.Getenv("PLUGINUNINSTALL_HOST_BINARY")
	if binary == "" {
		t.Skip("opt-in actual Main; compile-only unless PLUGINUNINSTALL_HOST_BINARY supplied")
	}
	if runtime.GOOS != "linux" || os.Geteuid() != 1000 {
		t.Fatal("ordinary permissions require the owned native Linux uid1000 process")
	}
	dir := os.Getenv("PLUGINUNINSTALL_RUNTIME_DIR")
	if dir == "" {
		dir = t.TempDir()
	}
	dir, e := filepath.Abs(dir)
	if e != nil {
		t.Fatal(e)
	}
	if e = os.MkdirAll(dir, 0700); e != nil {
		t.Fatal(e)
	}
	marker := filepath.Join(dir, ".task-owned")
	if b, e := os.ReadFile(marker); e == nil {
		if string(b) != puiMarker {
			t.Fatal("foreign marker")
		}
	} else if os.IsNotExist(e) {
		entries, e := os.ReadDir(dir)
		if e != nil || len(entries) != 0 {
			t.Fatal("new empty owned runtime required", e)
		}
		if e = os.WriteFile(marker, []byte(puiMarker), 0600); e != nil {
			t.Fatal(e)
		}
	} else {
		t.Fatal(e)
	}
	// Do not inspect/decrypt a DB. Refuse any previous run before bootstrapping.
	for _, name := range []string{"light-media.db", "plugin-packages", "evidence"} {
		if _, e := os.Lstat(filepath.Join(dir, name)); !os.IsNotExist(e) {
			t.Fatal("fresh child runtime required", name, e)
		}
	}
	ev := filepath.Join(dir, "evidence")
	if e = os.Mkdir(ev, 0700); e != nil {
		t.Fatal(e)
	}
	events, e := os.OpenFile(filepath.Join(ev, "observations.jsonl"), os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		t.Fatal(e)
	}
	addr := os.Getenv("PLUGINUNINSTALL_LISTEN")
	if addr == "" {
		addr = "0.0.0.0:36258"
	}
	base := addr
	if strings.HasPrefix(base, "0.0.0.0:") {
		base = "127.0.0.1:" + strings.TrimPrefix(base, "0.0.0.0:")
	}
	jar, _ := cookiejar.New(nil)
	h := &mainHost{t: t, binary: binary, dir: dir, evidence: ev, addr: addr, base: "http://" + base, client: &http.Client{Jar: jar, Timeout: 90 * time.Second, Transport: &http.Transport{Proxy: nil}}, events: events}
	b := make([]byte, 24)
	if _, e = rand.Read(b); e != nil {
		t.Fatal(e)
	}
	s := &puiMain{mainHost: h, token: hex.EncodeToString(b), allPIDs: map[int]bool{}}
	t.Cleanup(func() { h.stop(); events.Close() })
	settings := map[string]any{"plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0, "allowed_roots": []string{dir}, "api_token": s.token}
	input, _ := json.Marshal(map[string]any{"username": ownedUser, "password": ownedPassword, "settings": settings})
	cmd := exec.Command(binary, "--data-dir", dir, "--bootstrap-stdin")
	cmd.Env = h.env()
	cmd.Stdin = bytes.NewReader(input)
	out, e := cmd.CombinedOutput()
	h.record("bootstrap", map[string]any{"output": strings.ReplaceAll(string(out), s.token, "[redacted]"), "error": fmt.Sprint(e)})
	if e != nil {
		t.Fatal("bootstrap failed", e)
	}
	h.start()
	return s
}
func (s *puiMain) http(method, path string, v any) (int, json.RawMessage) {
	s.t.Helper()
	var body []byte
	if v != nil {
		body = puiEncode(v)
	}
	q, e := http.NewRequest(method, s.base+path, bytes.NewReader(body))
	if e != nil {
		s.t.Fatal(e)
	}
	q.Header.Set("Content-Type", "application/json")
	q.Header.Set("Origin", s.base)
	if strings.HasPrefix(path, "/api/v1/plugin/") {
		q.Header.Set("X-API-KEY", s.token)
	}
	r, e := s.client.Do(q)
	if e != nil {
		s.t.Fatal("ordinary HTTP", method, strings.Split(path, "?")[0], e)
	}
	defer r.Body.Close()
	raw, e := io.ReadAll(io.LimitReader(r.Body, 4<<20))
	if e != nil {
		s.t.Fatal(e)
	}
	safe := bytes.ReplaceAll(raw, []byte(s.token), []byte("[redacted]"))
	s.record("pui_http", map[string]any{"method": method, "path": strings.Split(path, "?")[0], "status": r.StatusCode, "request": json.RawMessage(body), "response": json.RawMessage(safe)})
	return r.StatusCode, raw
}
func (s *puiMain) read(path string) json.RawMessage {
	s.t.Helper()
	status, raw := s.http("GET", path, nil)
	v, e := puiResponse(status, raw, false)
	if e != nil {
		s.t.Fatal(path, e)
	}
	return v
}
func (s *puiMain) mutate(method, path string, v any) json.RawMessage {
	s.t.Helper()
	status, raw := s.http(method, path, v)
	data, e := puiResponse(status, raw, true)
	if e != nil {
		s.t.Fatal(method, path, e, string(raw))
	}
	return data
}
func (s *puiMain) install(id string, r *puiRepository, force bool) {
	s.t.Helper()
	s.mutate("POST", "/api/plugins/install", map[string]any{"plugin_id": id, "force": force, "repo_url": r.server.URL + "/index"})
	s.snapshot("")
}
func (s *puiMain) clone(source, suffix string) string {
	s.t.Helper()
	id := source + suffix
	data := s.mutate("POST", "/api/plugins/"+source+"/clone", map[string]any{"suffix": suffix, "name": "Owned " + id, "version": "owned"})
	var result struct {
		Created  bool   `json:"created"`
		Instance string `json:"instance_id"`
		Source   string `json:"source_instance_id"`
	}
	if json.Unmarshal(data, &result) != nil || !result.Created || result.Instance != id || result.Source != source {
		s.t.Fatal("clone actual identity", string(data))
	}
	s.snapshot("")
	return id
}

type puiState struct {
	Instance string `json:"instance_id"`
	Version  string `json:"version"`
	Loaded   bool   `json:"loaded"`
	Enabled  *bool  `json:"enabled"`
}
type puiSnapshot struct {
	Installed []puiState        `json:"installed"`
	Classes   []puiState        `json:"classes"`
	Running   []puiState        `json:"running"`
	Order     []string          `json:"installed_order"`
	Config    json.RawMessage   `json:"raw_config"`
	Data      json.RawMessage   `json:"raw_data"`
	DataPath  string            `json:"data_path"`
	PID       int               `json:"pid"`
	Local     []json.RawMessage `json:"local"`
}

func (s *puiMain) snapshot(target string) puiSnapshot {
	s.t.Helper()
	path := "/api/v1/plugin/" + puiProbe + "/inspect"
	if target != "" {
		path += "?target=" + target
	}
	raw := s.read(path)
	var v puiSnapshot
	if json.Unmarshal(raw, &v) != nil || v.PID == 0 || v.Order == nil || v.Running == nil || v.Classes == nil {
		s.t.Fatal("owned actual SDK observation missing", string(raw))
	}
	s.pids()
	return v
}
func (s *puiMain) seed(target string, config, data any) {
	s.t.Helper()
	row := map[string]any{"id": target}
	if config != nil {
		row["config"] = config
	}
	if data != nil {
		row["data"] = data
	}
	s.mutate("PUT", "/api/plugins/"+puiProbe, map[string]any{"seeds": []any{row}})
	puiAssert(s.t, puiJSON(s.t, s.read("/api/plugins/"+puiProbe)), map[string]any{}, "fixture instruction consumed; no cold replay")
}
func (s *puiMain) order(ids []string) {
	s.t.Helper()
	s.mutate("PUT", "/api/plugins/"+puiProbe, map[string]any{"installed": ids})
	puiAssert(s.t, s.snapshot("").Order, ids, "actual source installed order")
}
func puiHas(rows []puiState, id string) bool {
	for _, r := range rows {
		if r.Instance == id {
			return true
		}
	}
	return false
}
func (s *puiMain) maps(id string, installed, class, running bool) {
	s.t.Helper()
	v := s.snapshot("")
	if puiHas(v.Installed, id) != installed || puiHas(v.Classes, id) != class || puiHas(v.Running, id) != running {
		s.t.Fatalf("%s actual installed/class/running: %+v", id, v)
	}
	for _, r := range v.Running {
		if r.Instance == id && r.Enabled != nil && *r.Enabled {
			s.t.Fatal("PUI or disabled MPS unexpectedly true", id)
		}
	}
}
func (s *puiMain) stored(id string, config, data any) {
	s.t.Helper()
	v := s.snapshot(id)
	puiAssert(s.t, puiJSON(s.t, v.Config), config, "raw Base configuration "+id)
	puiAssert(s.t, puiJSON(s.t, v.Data), data, "raw Base KV "+id)
}
func (s *puiMain) config(id string, want any) {
	s.t.Helper()
	puiAssert(s.t, puiJSON(s.t, s.read("/api/plugins/"+id)), want, "public class-gated configuration "+id)
}
func (s *puiMain) code(id string, present bool) {
	s.t.Helper()
	_, e := os.Lstat(filepath.Join(s.dir, "plugin-packages", id))
	if present && e != nil || !present && !os.IsNotExist(e) {
		s.t.Fatal("actual owned code state", id, present, e)
	}
}
func (s *puiMain) dataFile(id string) string {
	s.t.Helper()
	path := s.snapshot(id).DataPath
	rel, e := filepath.Rel(s.dir, path)
	if e != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) || rel == "." {
		s.t.Fatal("finite Base data path escaped fresh owned runtime")
	}
	file := filepath.Join(path, "owned-plain-marker")
	if e = os.WriteFile(file, []byte("owned synthetic data file"), 0600); e != nil {
		s.t.Fatal(e)
	}
	return file
}
func (s *puiMain) pids() map[string]int {
	s.t.Helper()
	out := map[string]int{}
	entries, e := os.ReadDir("/proc")
	if e != nil {
		s.t.Fatal(e)
	}
	for _, d := range entries {
		var pid int
		if _, e = fmt.Sscan(d.Name(), &pid); e != nil {
			continue
		}
		exe, e := os.Readlink(filepath.Join("/proc", d.Name(), "exe"))
		if e != nil {
			continue
		}
		prefix := filepath.Join(s.dir, "plugin-packages") + string(filepath.Separator)
		if strings.HasPrefix(exe, prefix) {
			rel := strings.TrimPrefix(exe, prefix)
			id := strings.Split(rel, "/")[0]
			out[id] = pid
			s.allPIDs[pid] = true
		}
	}
	s.record("pui_worker_pids", out)
	return out
}
func (s *puiMain) waitDead(pid int) {
	s.t.Helper()
	if pid == 0 {
		s.t.Fatal("missing pre-operation actual PID")
	}
	deadline := time.Now().Add(15 * time.Second)
	for time.Now().Before(deadline) {
		if _, e := os.Stat(fmt.Sprintf("/proc/%d", pid)); os.IsNotExist(e) {
			return
		}
		time.Sleep(25 * time.Millisecond)
	}
	s.t.Fatal("old worker did not join", pid)
}
func (s *puiMain) cold() {
	s.t.Helper()
	old := s.pids()
	s.stop()
	for _, pid := range old {
		s.waitDead(pid)
	}
	s.start()
	s.snapshot("")
}
func puiKeepFile(t *testing.T, path string) {
	t.Helper()
	raw, e := os.ReadFile(path)
	if e != nil || string(raw) != "owned synthetic data file" {
		t.Fatal("source must retain ordinary data-path files", e)
	}
}
func puiForm(t *testing.T, raw json.RawMessage) (map[string]json.RawMessage, []string) {
	t.Helper()
	var v struct {
		Mode  string                     `json:"render_mode"`
		Conf  []any                      `json:"conf"`
		Model map[string]json.RawMessage `json:"model"`
	}
	if json.Unmarshal(raw, &v) != nil || v.Mode != "vuetify" || len(v.Conf) != 1 || v.Model == nil {
		t.Fatal("ordinary form shape", string(raw))
	}
	found := map[string]bool{}
	ids := []string{}
	var visit func(any)
	visit = func(n any) {
		switch x := n.(type) {
		case []any:
			for _, c := range x {
				visit(c)
			}
		case map[string]any:
			if p, ok := x["props"].(map[string]any); ok {
				if model, ok := p["model"].(string); ok {
					found[model] = true
					if model == "plugin_ids" {
						if x["component"] != "VSelect" || p["multiple"] != true || p["chips"] != true {
							t.Fatal("source select exact shape")
						}
						items, ok := p["items"].([]any)
						if !ok {
							t.Fatal("source dynamic items missing")
						}
						for _, item := range items {
							r, ok := item.(map[string]any)
							if !ok {
								t.Fatal("option object")
							}
							id, ok := r["value"].(string)
							if !ok || id == "" {
								t.Fatal("option ID")
							}
							ids = append(ids, id)
						}
					}
				}
			}
			for _, c := range x {
				visit(c)
			}
		}
	}
	visit(v.Conf)
	for _, key := range []string{"clear_config", "clear_data", "plugin_ids"} {
		if !found[key] {
			t.Fatal("missing source control", key)
		}
	}
	if len(found) != 3 {
		t.Fatal("invented source form controls", found)
	}
	return v.Model, ids
}
func puiContains(ids []string, id string) bool {
	for _, v := range ids {
		if v == id {
			return true
		}
	}
	return false
}
func (s *puiMain) barrier(victim string) {
	s.t.Helper()
	if os.Getenv("PLUGINUNINSTALL_SKIP_UI") == "1" {
		s.record("pui_ui_skipped", map[string]any{"actual_browser_acceptance": false})
		return
	}
	path := filepath.Join(s.dir, "ui-ready.private.json")
	public := os.Getenv("PLUGINUNINSTALL_PUBLIC_URL")
	if public == "" {
		public = s.base
	}
	ready := map[string]any{"base_url": public, "username": ownedUser, "password": ownedPassword, "source": puiID, "clone": puiID + "owned", "victim": victim, "steps": []string{"Open PluginUnInstall configuration; check dynamic self and clone options.", "Turn on both clear switches; select only the owned UI victim; save once.", "Verify victim gone, selection resets empty and both switches remain true; open clone separately.", "Write ui-continue marker after screenshots; no page/dashboard expected."}}
	if e := os.WriteFile(path, puiEncode(ready), 0600); e != nil {
		s.t.Fatal(e)
	}
	defer os.Remove(path)
	s.record("pui_ui_ready", map[string]any{"private_credentials": "outside evidence, mode0600", "source": puiID, "victim": victim, "timeout_seconds": 3000})
	deadline := time.Now().Add(50 * time.Minute)
	for time.Now().Before(deadline) {
		if _, e := os.Stat(filepath.Join(s.dir, "ui-continue")); e == nil {
			s.record("pui_ui_released", map[string]any{"by": "coordinator marker"})
			return
		}
		time.Sleep(time.Second)
	}
	s.t.Fatal("UI barrier timeout after 50 minutes")
}
