package integration

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sync"
	"testing"
	"time"
)

// TestCategoryEditorActualMain exercises the real cmd/server lifecycle with an
// independently built CategoryEditor worker and an owned artifact repository.
// All configuration, policy bytes, paths and credentials are synthetic.
func TestCategoryEditorActualMain(t *testing.T) {
	worker := os.Getenv("CATEGORYEDITOR_WORKER_BINARY")
	if worker == "" {
		t.Skip("opt-in main acceptance requires CATEGORYEDITOR_WORKER_BINARY; not executed acceptance")
	}
	h := newMainHost(t)
	type release struct {
		version  string
		manifest map[string]any
		binary   []byte
		hash     string
	}
	load := func(path string) release {
		t.Helper()
		raw, err := exec.Command(path, "--manifest").Output()
		if err != nil {
			t.Fatal(err)
		}
		var manifest map[string]any
		if json.Unmarshal(raw, &manifest) != nil {
			t.Fatal("worker manifest JSON")
		}
		bin, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		return release{manifest["version"].(string), manifest, bin, fileHash(t, path)}
	}
	first := load(worker)
	if first.version != "1.3" || first.manifest["plugin_id"] != "CategoryEditor" {
		t.Fatal("wrong initial business worker")
	}
	current := first
	var second release
	if path := os.Getenv("CATEGORYEDITOR_UPDATE_WORKER_BINARY"); path != "" {
		second = load(path)
		if second.version == first.version {
			t.Fatal("update fixture must have a genuinely different manifest version")
		}
	}
	var repoMu sync.Mutex
	hits := map[string]int{}
	var repo *httptest.Server
	repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		repoMu.Lock()
		defer repoMu.Unlock()
		hits[r.URL.Path]++
		switch r.URL.Path {
		case "/index":
			artifact := map[string]any{"platform": runtime.GOOS + "-" + runtime.GOARCH, "format": "executable", "sha256": current.hash, "executable_sha256": current.hash, "size": len(current.binary), "host_contract": "light-media.sdk-resources/v1", "url": repo.URL + "/worker"}
			json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": "CategoryEditor", "current_version": current.version, "releases": []any{map[string]any{"version": current.version, "manifest": current.manifest, "artifacts": []any{artifact}}}})
		case "/worker":
			w.Write(current.binary)
		default:
			http.NotFound(w, r)
		}
	}))
	defer repo.Close()
	install := func(id string, force bool, index string) {
		t.Helper()
		h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": id, "force": force, "repo_url": index})
	}
	save := func(id string, enabled bool, content string) {
		t.Helper()
		h.ok("PUT", "/api/plugins/"+id, map[string]any{"enabled": enabled, "content": content, "discard_on_success": "owned synthetic extra"})
	}
	const id = "CategoryEditor"
	const clone = "CategoryEditorowned"
	install(id, false, repo.URL+"/index")
	h.config(id, map[string]any{})
	h.message(false)
	raw := h.ok("GET", "/api/plugins/"+id+"/form", nil)
	var form struct {
		Model map[string]any  `json:"model"`
		Conf  json.RawMessage `json:"conf"`
	}
	if json.Unmarshal(raw, &form) != nil || form.Model["enabled"] != false {
		t.Fatal("actual default form", string(raw))
	}
	if path := os.Getenv("CATEGORYEDITOR_DEFAULT_PATH"); path != "" {
		want, err := os.ReadFile(path)
		if err != nil || form.Model["content"] != string(want) {
			t.Fatal("host bundled-default exact bytes differ", err)
		}
	}
	if !bytes.Contains(form.Conf, []byte("VAceEditor")) {
		t.Fatal("source AceEditor schema absent")
	}
	h.ok("GET", "/api/plugins/"+id+"/page", nil)
	pids := h.workers()
	if pids[id] == 0 {
		t.Fatal("independent actual worker PID missing")
	}
	before, err := os.ReadFile(filepath.Join(h.dir, "category.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	disabled := "# disabled synthetic editor draft\nmovie:\n  尚未应用: {}\ntv: {}\n"
	save(id, false, disabled)
	h.policy(string(before))
	h.config(id, map[string]any{"enabled": false, "content": disabled, "discard_on_success": "owned synthetic extra"})
	if h.workers()[id] != pids[id] {
		t.Fatal("disabled save replaced same worker")
	}
	h.message(false)
	content := "# owned synthetic UTF-8 / exact CRLF\r\nmovie:\n  云端电影:\n    original_language: 'zh'\n  外语后备: {}\ntv:\n  云端剧集: {}\n\n"
	save(id, true, content)
	h.policy(content)
	h.config(id, map[string]any{"enabled": false, "content": content})
	h.categories([]string{"云端电影", "外语后备"}, []string{"云端剧集"})
	h.message(true)
	h.message(false)
	if h.workers()[id] != pids[id] {
		t.Fatal("enabled save replaced retained worker")
	}
	badYAML := "movie:\n  [ordinary syntax error\n"
	save(id, true, badYAML)
	h.policy(badYAML)
	h.config(id, map[string]any{"enabled": false, "content": badYAML})
	h.categories([]string{"云端电影", "外语后备"}, []string{"云端剧集"})
	save(id, true, content)
	h.policy(content)
	// This is a real owned filesystem write denial, not a mocked HostCaller.
	if os.Geteuid() == 0 {
		t.Fatal("write-denial acceptance requires non-root execution")
	}
	if err = os.Chmod(filepath.Join(h.dir, "category.yaml"), 0400); err != nil {
		t.Fatal(err)
	}
	denied := "movie:\n  不应写入: {}\ntv: {}\n"
	status, failure := h.request("PUT", "/api/plugins/"+id, map[string]any{"enabled": true, "content": denied, "retained_on_failure": true})
	if status < 400 {
		t.Fatalf("real write failure hidden: %d %s", status, failure)
	}
	h.policy(content)
	h.config(id, map[string]any{"enabled": true, "content": denied, "retained_on_failure": true})
	h.categories([]string{"云端电影", "外语后备"}, []string{"云端剧集"})
	if h.workers()[id] != pids[id] {
		t.Fatal("failed same-instance init replaced worker")
	}
	if err = os.Chmod(filepath.Join(h.dir, "category.yaml"), 0600); err != nil {
		t.Fatal(err)
	}
	recovered := "movie:\n  恢复电影: {}\ntv:\n  恢复剧集: {}\n"
	save(id, true, recovered)
	h.policy(recovered)
	h.config(id, map[string]any{"enabled": false, "content": recovered})
	h.categories([]string{"恢复电影"}, []string{"恢复剧集"})
	h.ok("POST", "/api/plugins/"+id+"/clone", map[string]any{"suffix": "Owned"})
	cpids := h.workers()
	if cpids[id] != pids[id] || cpids[clone] == 0 || cpids[clone] == cpids[id] {
		t.Fatal("clone did not create isolated executable", cpids)
	}
	cloneContent := "movie:\n  分身共享全局电影: {}\ntv:\n  分身共享全局剧集: {}\n"
	save(clone, true, cloneContent)
	h.config(id, map[string]any{"enabled": false, "content": recovered})
	h.config(clone, map[string]any{"enabled": false, "content": cloneContent})
	h.policy(cloneContent)
	h.categories([]string{"分身共享全局电影"}, []string{"分身共享全局剧集"})
	for _, name := range []string{id, clone} {
		if _, e := os.Stat(filepath.Join(h.dir, "plugin-packages", name)); e != nil {
			t.Fatal("isolated code namespace missing", name, e)
		}
	}
	path := filepath.Join(h.dir, "category.yaml")
	frozen := time.Unix(981173106, 0)
	if err = os.Chtimes(path, frozen, frozen); err != nil {
		t.Fatal(err)
	}
	snap, _ := os.Stat(path)
	unchanged := func() {
		t.Helper()
		h.policy(cloneContent)
		after, e := os.Stat(path)
		if e != nil || !os.SameFile(snap, after) || !after.ModTime().Equal(frozen) {
			t.Fatal("disabled lifecycle replayed policy write", e)
		}
	}
	h.ok("POST", "/api/plugins/"+id+"/reload", map[string]any{})
	rpids := h.workers()
	if rpids[id] == pids[id] || rpids[clone] != cpids[clone] {
		t.Fatal("reload did not replace only source", rpids)
	}
	unchanged()
	install(id, true, repo.URL+"/index")
	unchanged()
	if second.version != "" {
		repoMu.Lock()
		current = second
		repoMu.Unlock()
		install(id, true, repo.URL+"/index")
		unchanged()
		h.record("version_update", map[string]any{"from": first.version, "to": second.version, "worker_sha256": second.hash, "fixture": "same CategoryEditor business implementation; only test executable manifest version differs"})
	}
	h.config(id, map[string]any{"enabled": false, "content": recovered})
	h.config(clone, map[string]any{"enabled": false, "content": cloneContent})
	// Root controls the real browser stage. The file contains synthetic-only test
	// credentials, never an exported user credential or application session.
	if os.Getenv("CATEGORYEDITOR_UI_WAIT") != "" {
		public := os.Getenv("CATEGORYEDITOR_PUBLIC_URL")
		if public == "" {
			public = h.base
		}
		ready := map[string]any{"url": public, "username": ownedUser, "password": ownedPassword, "pid": h.cmd.Process.Pid, "runtime_dir": h.dir, "continue_file": filepath.Join(h.dir, "ui-complete"), "category_source": recovered, "category_clone": cloneContent}
		data, _ := json.MarshalIndent(ready, "", "  ")
		if err = os.WriteFile(filepath.Join(h.dir, "ui-ready.json"), data, 0600); err != nil {
			t.Fatal(err)
		}
		h.record("ui_ready", map[string]any{"url": public, "pid": h.cmd.Process.Pid})
		t.Log("actual main ready for root browser", public)
		deadline := time.Now().Add(30 * time.Minute)
		for {
			if _, e := os.Stat(filepath.Join(h.dir, "ui-complete")); e == nil {
				break
			}
			if time.Now().After(deadline) {
				t.Fatal("root browser stage not completed within30minutes")
			}
			time.Sleep(500 * time.Millisecond)
		}
		// Browser changes are legitimate test inputs. Bind the cold assertions to
		// its saved disabled configs and actual policy, without guessing a draft.
		var sourceSaved struct {
			Enabled bool   `json:"enabled"`
			Content string `json:"content"`
		}
		if json.Unmarshal(h.ok("GET", "/api/plugins/"+id, nil), &sourceSaved) != nil || sourceSaved.Enabled {
			t.Fatal("browser must leave source apply switch disabled")
		}
		recovered = sourceSaved.Content
		policy, e := os.ReadFile(path)
		if e != nil {
			t.Fatal(e)
		}
		cloneContent = string(policy)
		snap, _ = os.Stat(path)
		frozen = snap.ModTime()
	}
	oldPID := h.cmd.Process.Pid
	oldWorkers := h.workers()
	h.stop()
	h.start()
	if h.cmd.Process.Pid == oldPID {
		t.Fatal("cold main PID did not change")
	}
	unchanged()
	h.message(false)
	newWorkers := h.workers()
	for _, name := range []string{id, clone} {
		if newWorkers[name] == 0 || newWorkers[name] == oldWorkers[name] {
			t.Fatal("cold worker PID did not change", name)
		}
	}
	h.ok("POST", "/api/plugins/"+clone+"/reset", map[string]any{})
	h.config(clone, map[string]any{})
	h.config(id, map[string]any{"enabled": false, "content": recovered})
	unchanged()
	save(clone, false, "owned disabled post-reset draft")
	h.ok("POST", "/api/plugins/"+clone+"/uninstall", map[string]any{})
	if status, _ := h.request("GET", "/api/plugins/"+clone+"/form", nil); status != 404 {
		t.Fatal("clone form remains loaded", status)
	}
	if _, e := os.Stat(filepath.Join(h.dir, "plugin-packages", clone)); !os.IsNotExist(e) {
		t.Fatal("clone code namespace retained", e)
	}
	unchanged()
	h.ok("DELETE", "/api/plugins/"+id, nil)
	if status, _ := h.request("GET", "/api/plugins/"+id+"/form", nil); status != 404 {
		t.Fatal("source form remains loaded", status)
	}
	install(id, false, repo.URL+"/index")
	h.config(id, map[string]any{"enabled": false, "content": recovered})
	unchanged()
	h.message(false)
	repoMu.Lock()
	defer repoMu.Unlock()
	h.record("artifact_acquisition", hits)
	if hits["/worker"] < 2 || hits["/index"] < 2 {
		t.Fatal("artifact acquisition/update not actual", hits)
	}
	t.Log("actual cmd/server+HTTP+independent SDK worker install/save/error/recovery/clone/reload/update/cold/reset/uninstall/reinstall passed", fmt.Sprint(hits))
}
