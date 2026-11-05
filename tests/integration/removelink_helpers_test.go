package integration

// Test-only ordinary main infrastructure. No App import, private worker method,
// host callback substitution, production directory, or durable cleanup delegate.
import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"
)

const rmOwnerMarker = "light-media-plugins/RemoveLink/ordinary-main/20261105/owned-only"
const rmUser = "removelink-owned"
const rmPassword = "RemoveLink-owned-20261105!"
const rmSource = "RemoveLink"
const rmClone = "RemoveLinkowned"

type rmMain struct {
	*mainHost
	root, files, home string
	allPIDs           map[int]bool
}

func rmFreshRoot(t *testing.T) string {
	t.Helper()
	dir := os.Getenv("REMOVELINK_RUNTIME_DIR")
	if dir == "" {
		dir = t.TempDir()
	}
	dir, e := filepath.Abs(dir)
	if e != nil {
		t.Fatal(e)
	}
	current := string(filepath.Separator)
	for _, part := range strings.Split(strings.TrimPrefix(dir, string(filepath.Separator)), string(filepath.Separator)) {
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		if os.IsNotExist(err) {
			break
		}
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode()&os.ModeSymlink != 0 {
			t.Fatal("owned main runtime must not traverse symlink", current)
		}
	}
	if e = os.MkdirAll(dir, 0700); e != nil {
		t.Fatal(e)
	}
	entries, e := os.ReadDir(dir)
	if e != nil || len(entries) != 0 {
		t.Fatal("fresh empty owned runtime required; do not reuse or point at production", dir, e)
	}
	if e = os.WriteFile(filepath.Join(dir, ".task-owned"), []byte(rmOwnerMarker), 0600); e != nil {
		t.Fatal(e)
	}
	return dir
}
func rmNewMain(t *testing.T) *rmMain {
	t.Helper()
	binary := os.Getenv("REMOVELINK_HOST_BINARY")
	if binary == "" {
		t.Skip("opt-in actual ordinary main requires REMOVELINK_HOST_BINARY; no acceptance executed")
	}
	if want := os.Getenv("REMOVELINK_EXPECT_HOST_SHA256"); want == "" || fileHash(t, binary) != want {
		t.Fatal("exact independently reviewed host ELF required before bootstrap")
	}
	root := rmFreshRoot(t)
	app := filepath.Join(root, "app")
	evidence := filepath.Join(root, "evidence")
	files := filepath.Join(root, "files")
	home := filepath.Join(files, "owned-home")
	for _, p := range []string{app, evidence, files, home} {
		if e := os.MkdirAll(p, 0700); e != nil {
			t.Fatal(e)
		}
	}
	addr := os.Getenv("REMOVELINK_LISTEN")
	if addr == "" {
		l, e := net.Listen("tcp", "127.0.0.1:0")
		if e != nil {
			t.Fatal(e)
		}
		addr = l.Addr().String()
		l.Close()
	}
	base := addr
	if strings.HasPrefix(base, "0.0.0.0:") {
		base = "127.0.0.1:" + strings.TrimPrefix(base, "0.0.0.0:")
	}
	jar, _ := cookiejar.New(nil)
	events, e := os.OpenFile(filepath.Join(evidence, "observations.jsonl"), os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if e != nil {
		t.Fatal(e)
	}
	h := &mainHost{t: t, binary: binary, dir: app, evidence: evidence, addr: addr, base: "http://" + base, client: &http.Client{Jar: jar, Timeout: 30 * time.Second}, events: events}
	s := &rmMain{mainHost: h, root: root, files: files, home: home, allPIDs: map[int]bool{}}
	t.Cleanup(func() { h.stop(); events.Close() })
	input, _ := json.Marshal(map[string]any{"username": rmUser, "password": rmPassword, "settings": map[string]any{"allowed_roots": []string{files}, "plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0}})
	cmd := exec.Command(binary, "--data-dir", app, "--bootstrap-stdin")
	cmd.Stdin = bytes.NewReader(input)
	cmd.Env = s.environment()
	cmd.Dir = root
	out, e := cmd.CombinedOutput()
	s.record("rm_bootstrap", map[string]any{"output": string(out), "error": fmt.Sprint(e)})
	if e != nil {
		t.Fatal("actual main bootstrap", e, string(out))
	}
	s.startRM()
	return s
}
func (s *rmMain) environment() []string {
	return []string{"PATH=" + os.Getenv("PATH"), "HOME=" + s.home, "TZ=Asia/Shanghai", "PLUGIN_MARKET=", "DEV=false", "LIGHT_MEDIA_SAFE_MODE=false"}
}
func (s *rmMain) startRM() {
	s.t.Helper()
	s.generation++
	f, e := os.Create(filepath.Join(s.evidence, fmt.Sprintf("host-%d.log", s.generation)))
	if e != nil {
		s.t.Fatal(e)
	}
	s.log = f
	s.cmd = exec.Command(s.binary, "--listen", s.addr, "--data-dir", s.dir)
	s.cmd.Dir = s.root
	s.cmd.Env = s.environment()
	s.cmd.Stdout = f
	s.cmd.Stderr = f
	if e = s.cmd.Start(); e != nil {
		s.t.Fatal(e)
	}
	s.wait = make(chan error, 1)
	go func(cmd *exec.Cmd) { s.wait <- cmd.Wait() }(s.cmd)
	rmWait(s.t, "ordinary main health", 30*time.Second, func() bool {
		r, e := s.client.Get(s.base + "/healthz")
		if e != nil {
			return false
		}
		r.Body.Close()
		return r.StatusCode == 200
	})
	s.record("rm_main_start", map[string]any{"pid": s.cmd.Process.Pid, "generation": s.generation, "binary_sha256": fileHash(s.t, s.binary), "HOME": s.home, "TZ": "Asia/Shanghai", "base": s.base})
	s.ok("POST", "/api/auth/login", map[string]any{"username": rmUser, "password": rmPassword})
}
func (s *rmMain) crashRM() {
	s.t.Helper()
	cmd := s.cmd
	s.cmd = nil
	if e := cmd.Process.Kill(); e != nil {
		s.t.Fatal(e)
	}
	e := <-s.wait
	s.log.Close()
	s.record("rm_owned_main_crash", map[string]any{"pid": cmd.Process.Pid, "expected_error": fmt.Sprint(e), "not_graceful_stop": true})
}
func rmWait(t *testing.T, what string, timeout time.Duration, ready func() bool) {
	t.Helper()
	end := time.Now().Add(timeout)
	for {
		if ready() {
			return
		}
		if time.Now().After(end) {
			t.Fatal("timed out", what)
		}
		time.Sleep(50 * time.Millisecond)
	}
}
func rmExists(p string) bool { _, e := os.Lstat(p); return e == nil }
func rmWrite(t *testing.T, p string) {
	t.Helper()
	if e := os.MkdirAll(filepath.Dir(p), 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(p, []byte("owned synthetic RemoveLink file:"+filepath.Base(p)), 0600); e != nil {
		t.Fatal(e)
	}
}
func rmLinks(t *testing.T, dir, name string, n int) (string, []string) {
	t.Helper()
	source := filepath.Join(dir, name+".mkv")
	rmWrite(t, source)
	links := []string{}
	for i := 0; i < n; i++ {
		p := filepath.Join(dir, fmt.Sprintf("%s-link-%03d.mkv", name, i))
		if e := os.Link(source, p); e != nil {
			t.Fatal(e)
		}
		links = append(links, p)
	}
	return source, links
}
func (s *rmMain) observeFiles(stage string, paths []string) {
	rows := []map[string]any{}
	for _, p := range paths {
		row := map[string]any{"path": p, "exists": rmExists(p)}
		if info, e := os.Lstat(p); e == nil {
			row["mode"] = info.Mode().String()
			row["bytes"] = info.Size()
			if stat, ok := info.Sys().(*syscall.Stat_t); ok {
				row["dev"] = fmt.Sprint(stat.Dev)
				row["inode"] = fmt.Sprint(stat.Ino)
				row["nlink"] = fmt.Sprint(stat.Nlink)
			}
			if info.Mode().IsRegular() {
				row["sha256"] = fileHash(s.t, p)
			}
		}
		rows = append(rows, row)
	}
	s.record("rm_files", map[string]any{"stage": stage, "files": rows})
}
func (s *rmMain) configRM(instance string, config map[string]any) {
	s.t.Helper()
	s.ok("PUT", "/api/plugins/"+instance, config)
	s.config(instance, config)
}
func rmConfig(dir string, delayed bool) map[string]any {
	return map[string]any{"enabled": true, "notify": false, "delete_scrap_infos": false, "delete_torrents": false, "delete_history": false, "delayed_deletion": delayed, "delay_seconds": 10, "monitor_dirs": dir, "exclude_dirs": "", "exclude_keywords": "", "custom_scrap_extensions": "", "monitor_strm_deletion": false, "strm_path_mappings": "", "owned_unknown": "source preserves unknown config; no one-shot feature"}
}
func (s *rmMain) workersRM() map[string]int {
	s.t.Helper()
	entries, e := os.ReadDir("/proc")
	if e != nil {
		s.t.Fatal(e)
	}
	out := map[string]int{}
	parent := s.cmd.Process.Pid
	for _, entry := range entries {
		pid, e := strconv.Atoi(entry.Name())
		if e != nil {
			continue
		}
		raw, e := os.ReadFile(filepath.Join("/proc", entry.Name(), "stat"))
		if e != nil {
			continue
		}
		at := strings.LastIndex(string(raw), ") ")
		if at < 0 {
			continue
		}
		fields := strings.Fields(string(raw)[at+2:])
		if len(fields) < 2 || fields[1] != strconv.Itoa(parent) {
			continue
		}
		cmd, e := os.ReadFile(filepath.Join("/proc", entry.Name(), "cmdline"))
		if e != nil {
			continue
		}
		text := strings.ReplaceAll(string(cmd), "\x00", " ")
		prefix := filepath.Join(s.dir, "plugin-packages") + "/"
		at = strings.Index(text, prefix)
		if at < 0 {
			continue
		}
		id := strings.SplitN(text[at+len(prefix):], "/", 2)[0]
		if id == rmSource || id == rmClone {
			out[id] = pid
			s.allPIDs[pid] = true
		}
	}
	s.record("rm_worker_pids", out)
	return out
}
func (s *rmMain) waitWorkerGone(pid int) {
	s.t.Helper()
	if pid == 0 {
		s.t.Fatal("missing observed worker PID")
	}
	rmWait(s.t, "actual worker joined", 15*time.Second, func() bool {
		_, err := os.Stat(filepath.Join("/proc", strconv.Itoa(pid)))
		return os.IsNotExist(err)
	})
}
func (s *rmMain) logsRM(instance string) string {
	raw := s.ok("GET", "/api/plugins/"+instance+"/logs?limit=500", nil)
	return string(raw)
}

func (s *rmMain) noInheritedModuleDiscovery(stage string) {
	s.t.Helper()
	raw, err := os.ReadFile(filepath.Join(s.dir, "logs", "app.jsonl"))
	if err != nil {
		s.t.Fatal(err)
	}
	// Fixed Manager.check_method skips RemoveLink's inherited pass before any
	// state lookup, including while stopping. Main5 retained 91 real failures
	// from the wrong declaration; they must not disappear behind a log filter.
	if bytes.Contains(raw, []byte(`"event":"module_declaration_failed"`)) {
		s.t.Fatal("inherited pass getter entered module discovery", stage)
	}
	s.record("rm_no_inherited_module_discovery", map[string]any{"stage": stage, "module_declaration_failed_count": 0, "complete_app_log_checked": true})
}
func (s *rmMain) queuedRM(instance, name string) {
	s.t.Helper()
	rmWait(s.t, "actual owned queued event "+name, 8*time.Second, func() bool { return strings.Contains(s.logsRM(instance), name+".mkv 加入延迟删除队列") })
}

type rmRelease struct {
	manifest                  map[string]any
	version, hash, workerHash string
	archive                   []byte
	inventory                 []map[string]any
}

func rmLoadRelease(t *testing.T, worker, frontend string) rmRelease {
	t.Helper()
	manifestRaw, e := exec.Command(worker, "--manifest").Output()
	var manifest map[string]any
	if e != nil || json.Unmarshal(manifestRaw, &manifest) != nil || manifest["plugin_id"] != rmSource {
		t.Fatal("actual RemoveLink manifest", e)
	}
	entry, ok := manifest["entry"].(string)
	if !ok {
		t.Fatal("actual worker entry")
	}
	binary, e := os.ReadFile(worker)
	if e != nil {
		t.Fatal(e)
	}
	files := map[string][]byte{entry: binary}
	e = filepath.WalkDir(frontend, func(p string, x os.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if x.IsDir() {
			return nil
		}
		if x.Type()&os.ModeSymlink != 0 {
			return fmt.Errorf("symlink frontend fixture forbidden")
		}
		rel, e := filepath.Rel(frontend, p)
		if e != nil {
			return e
		}
		data, e := os.ReadFile(p)
		files["frontend/"+filepath.ToSlash(rel)] = data
		return e
	})
	if e != nil {
		t.Fatal(e)
	}
	var buf bytes.Buffer
	archive := zip.NewWriter(&buf)
	inventory := []map[string]any{}
	names := make([]string, 0, len(files))
	for name := range files {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		data := files[name]
		header := &zip.FileHeader{Name: name, Method: zip.Deflate}
		header.SetMode(0644)
		if name == entry {
			header.SetMode(0755)
		}
		out, e := archive.CreateHeader(header)
		if e != nil {
			t.Fatal(e)
		}
		if _, e = out.Write(data); e != nil {
			t.Fatal(e)
		}
		sum := sha256.Sum256(data)
		inventory = append(inventory, map[string]any{"path": name, "size": len(data), "sha256": hex.EncodeToString(sum[:])})
	}
	if e = archive.Close(); e != nil {
		t.Fatal(e)
	}
	sum := sha256.Sum256(buf.Bytes())
	return rmRelease{manifest, manifest["version"].(string), hex.EncodeToString(sum[:]), fileHash(t, worker), buf.Bytes(), inventory}
}

type rmRepository struct {
	mu      sync.Mutex
	current rmRelease
	server  *httptest.Server
	hits    map[string]int
}

func rmRepo(t *testing.T, release rmRelease) *rmRepository {
	p := &rmRepository{current: release, hits: map[string]int{}}
	p.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		defer p.mu.Unlock()
		p.hits[r.URL.Path]++
		x := p.current
		switch r.URL.Path {
		case "/index":
			artifact := map[string]any{"platform": runtime.GOOS + "-" + runtime.GOARCH, "format": "zip", "url": p.server.URL + "/worker", "sha256": x.hash, "executable_sha256": x.workerHash, "size": len(x.archive), "files": x.inventory, "host_contract": "light-media.sdk-resources/v1"}
			_ = json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": rmSource, "current_version": x.version, "releases": []any{map[string]any{"version": x.version, "manifest": x.manifest, "artifacts": []any{artifact}}}})
		case "/worker":
			_, _ = w.Write(x.archive)
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(p.server.Close)
	return p
}
func (p *rmRepository) change(x rmRelease) { p.mu.Lock(); p.current = x; p.mu.Unlock() }
func (s *rmMain) installRM(p *rmRepository, force bool) {
	s.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": rmSource, "repo_url": p.server.URL + "/index", "force": force})
}
func (s *rmMain) frontendRM(instance string) {
	raw := s.ok("GET", "/api/plugins/"+instance+"/frontend", nil)
	var desc struct {
		EntryPath  string `json:"entry_path"`
		InstanceID string `json:"instance_id"`
	}
	if json.Unmarshal(raw, &desc) != nil || desc.InstanceID != instance || desc.EntryPath == "" {
		s.t.Fatal("real frontend descriptor", string(raw))
	}
	r, e := s.client.Get(s.base + "/api" + desc.EntryPath)
	if e != nil {
		s.t.Fatal(e)
	}
	defer r.Body.Close()
	data, e := io.ReadAll(r.Body)
	if e != nil || r.StatusCode != 200 || !bytes.Contains(data, []byte("export")) {
		s.t.Fatal("real packaged remoteEntry unavailable", e, r.StatusCode)
	}
	s.record("rm_frontend", map[string]any{"instance": instance, "entry": desc.EntryPath, "bytes": len(data), "sha256": fmt.Sprintf("%x", sha256.Sum256(data))})
	// These are the literal cache-hinted relative imports in the installed
	// source remoteEntry, including after the version-only update fixture.
	for _, leaf := range []string{"view.js?v=2.18", "style.css?v=2.18"} {
		target := strings.TrimSuffix(desc.EntryPath, "remoteEntry.js") + leaf
		response, err := s.client.Get(s.base + "/api" + target)
		if err != nil {
			s.t.Fatal(err)
		}
		body, err := io.ReadAll(response.Body)
		response.Body.Close()
		if err != nil || response.StatusCode != 200 || len(body) == 0 {
			s.t.Fatal("actual source relative frontend import unavailable", target, response.StatusCode, err)
		}
		s.record("rm_frontend_source_relative_import", map[string]any{"instance": instance, "asset": leaf, "bytes": len(body), "sha256": fmt.Sprintf("%x", sha256.Sum256(body))})
	}
}
