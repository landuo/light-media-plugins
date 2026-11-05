package integration

// These opt-in tests launch the unmodified host cmd/server executable. They do
// not import light-media/internal/app or call an in-process HTTP handler.
import (
	"bufio"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/cookiejar"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"
)

type mainHost struct {
	t                                 *testing.T
	binary, dir, evidence, addr, base string
	client                            *http.Client
	cmd                               *exec.Cmd
	wait                              chan error
	log                               *os.File
	events                            *os.File
	mu                                sync.Mutex
	generation                        int
}

const ownedUser = "category-owned"
const ownedPassword = "Category-owned-20261105!"

func newMainHost(t *testing.T) *mainHost {
	t.Helper()
	binary := os.Getenv("CATEGORYEDITOR_HOST_BINARY")
	if binary == "" {
		t.Skip("opt-in actual main test: CATEGORYEDITOR_HOST_BINARY is required; not executed acceptance")
	}
	dir := os.Getenv("CATEGORYEDITOR_RUNTIME_DIR")
	if dir == "" {
		dir = t.TempDir()
	} else {
		if err := os.MkdirAll(dir, 0700); err != nil {
			t.Fatal(err)
		}
	}
	evidence := filepath.Join(dir, "evidence")
	if err := os.MkdirAll(evidence, 0700); err != nil {
		t.Fatal(err)
	}
	addr := os.Getenv("CATEGORYEDITOR_LISTEN")
	if addr == "" {
		l, err := net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			t.Fatal(err)
		}
		addr = l.Addr().String()
		l.Close()
	}
	baseAddr := addr
	if strings.HasPrefix(baseAddr, "0.0.0.0:") {
		baseAddr = "127.0.0.1:" + strings.TrimPrefix(baseAddr, "0.0.0.0:")
	}
	jar, _ := cookiejar.New(nil)
	events, err := os.OpenFile(filepath.Join(evidence, "observations.jsonl"), os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0600)
	if err != nil {
		t.Fatal(err)
	}
	h := &mainHost{t: t, binary: binary, dir: dir, evidence: evidence, addr: addr, base: "http://" + baseAddr, client: &http.Client{Jar: jar, Timeout: 30 * time.Second}, events: events}
	t.Cleanup(func() { h.stop(); events.Close() })
	settings := map[string]any{"plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0, "allowed_roots": []string{dir}}
	input, _ := json.Marshal(map[string]any{"username": ownedUser, "password": ownedPassword, "settings": settings})
	cmd := exec.Command(binary, "--data-dir", dir, "--bootstrap-stdin")
	cmd.Stdin = bytes.NewReader(input)
	cmd.Env = h.env()
	out, err := cmd.CombinedOutput()
	h.record("bootstrap", map[string]any{"output": string(out), "error": fmt.Sprint(err)})
	if err != nil {
		t.Fatalf("bootstrap main: %s %v", out, err)
	}
	h.start()
	return h
}
func (h *mainHost) env() []string {
	return []string{"PATH=" + os.Getenv("PATH"), "TZ=Asia/Shanghai", "PLUGIN_MARKET=", "DEV=false", "LIGHT_MEDIA_SAFE_MODE=false"}
}
func (h *mainHost) record(event string, value any) {
	h.mu.Lock()
	defer h.mu.Unlock()
	raw, _ := json.Marshal(map[string]any{"at": time.Now().UTC().Format(time.RFC3339Nano), "event": event, "value": value})
	h.events.Write(append(raw, '\n'))
	h.events.Sync()
}
func (h *mainHost) start() {
	h.t.Helper()
	h.generation++
	file, err := os.Create(filepath.Join(h.evidence, fmt.Sprintf("host-%d.log", h.generation)))
	if err != nil {
		h.t.Fatal(err)
	}
	h.log = file
	h.cmd = exec.Command(h.binary, "--listen", h.addr, "--data-dir", h.dir)
	h.cmd.Env = h.env()
	h.cmd.Stdout = file
	h.cmd.Stderr = file
	if err = h.cmd.Start(); err != nil {
		h.t.Fatal(err)
	}
	h.wait = make(chan error, 1)
	go func(cmd *exec.Cmd) { h.wait <- cmd.Wait() }(h.cmd)
	deadline := time.Now().Add(30 * time.Second)
	for {
		r, e := h.client.Get(h.base + "/healthz")
		if e == nil {
			r.Body.Close()
			if r.StatusCode == 200 {
				break
			}
		}
		if time.Now().After(deadline) {
			h.t.Fatal("actual main did not become healthy")
		}
		time.Sleep(50 * time.Millisecond)
	}
	h.record("main_start", map[string]any{"pid": h.cmd.Process.Pid, "generation": h.generation, "base": h.base, "binary_sha256": fileHash(h.t, h.binary)})
	h.ok("POST", "/api/auth/login", map[string]any{"username": ownedUser, "password": ownedPassword})
}
func (h *mainHost) stop() {
	if h.cmd == nil {
		return
	}
	cmd := h.cmd
	h.cmd = nil
	cmd.Process.Signal(syscall.SIGTERM)
	select {
	case err := <-h.wait:
		h.record("main_exit", map[string]any{"pid": cmd.Process.Pid, "error": fmt.Sprint(err)})
		if err != nil {
			h.t.Errorf("main exit: %v", err)
		}
	case <-time.After(15 * time.Second):
		cmd.Process.Kill()
		<-h.wait
		h.t.Error("actual main required forced kill")
	}
	h.log.Close()
}
func (h *mainHost) request(method, path string, value any) (int, json.RawMessage) {
	h.t.Helper()
	var body []byte
	if value != nil {
		body, _ = json.Marshal(value)
	}
	req, err := http.NewRequest(method, h.base+path, bytes.NewReader(body))
	if err != nil {
		h.t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Origin", h.base)
	response, err := h.client.Do(req)
	if err != nil {
		h.t.Fatal(err)
	}
	defer response.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(response.Body, 4<<20))
	if err != nil {
		h.t.Fatal(err)
	}
	entry := map[string]any{"method": method, "path": path, "status": response.StatusCode, "response": json.RawMessage(raw)}
	if path != "/api/auth/login" {
		entry["request"] = json.RawMessage(body)
	}
	h.record("http", entry)
	var envelope struct {
		Data json.RawMessage `json:"data"`
	}
	if json.Unmarshal(raw, &envelope) == nil && envelope.Data != nil {
		return response.StatusCode, envelope.Data
	}
	return response.StatusCode, raw
}
func (h *mainHost) ok(method, path string, value any) json.RawMessage {
	h.t.Helper()
	status, raw := h.request(method, path, value)
	if status < 200 || status >= 300 {
		h.t.Fatalf("%s %s: HTTP%d %s", method, path, status, raw)
	}
	var result struct {
		Success *bool `json:"success"`
	}
	if json.Unmarshal(raw, &result) == nil && result.Success != nil && !*result.Success {
		h.t.Fatalf("business failure %s %s: %s", method, path, raw)
	}
	return raw
}
func (h *mainHost) config(id string, want any) {
	h.t.Helper()
	got := h.ok("GET", "/api/plugins/"+id, nil)
	expected, _ := json.Marshal(want)
	var a, b any
	json.Unmarshal(got, &a)
	json.Unmarshal(expected, &b)
	ga, _ := json.Marshal(a)
	gb, _ := json.Marshal(b)
	if !bytes.Equal(ga, gb) {
		h.t.Fatalf("config %s got=%s want=%s", id, got, expected)
	}
}
func (h *mainHost) policy(want string) {
	h.t.Helper()
	got, err := os.ReadFile(filepath.Join(h.dir, "category.yaml"))
	if err != nil || string(got) != want {
		h.t.Fatalf("global policy got=%q want=%q err=%v", got, want, err)
	}
	h.record("policy_bytes", map[string]any{"sha256": fmt.Sprintf("%x", sha256.Sum256(got)), "bytes": len(got)})
}
func (h *mainHost) categories(movie, tv []string) {
	h.t.Helper()
	raw := h.ok("GET", "/api/settings/rules", nil)
	var response struct {
		Categories map[string][]string `json:"categories"`
	}
	if json.Unmarshal(raw, &response) != nil {
		h.t.Fatal("category response", string(raw))
	}
	for key, want := range map[string][]string{"电影": movie, "电视剧": tv} {
		if fmt.Sprint(response.Categories[key]) != fmt.Sprint(want) {
			h.t.Fatalf("cached categories %s got=%v want=%v", key, response.Categories[key], want)
		}
	}
}
func (h *mainHost) message(want bool) {
	h.t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	req, _ := http.NewRequestWithContext(ctx, "GET", h.base+"/api/system/message?role=plugin", nil)
	req.Header.Set("Origin", h.base)
	req.Header.Set("Sec-Fetch-Site", "same-origin")
	r, err := h.client.Do(req)
	if err != nil {
		h.t.Fatal(err)
	}
	defer r.Body.Close()
	scanner := bufio.NewScanner(r.Body)
	if !scanner.Scan() {
		h.t.Fatal("message SSE unavailable", scanner.Err())
	}
	line := strings.TrimPrefix(scanner.Text(), "data: ")
	h.record("system_message", map[string]any{"status": r.StatusCode, "data": line})
	if want {
		if !strings.Contains(line, "二级分类策略已更新，请注意同步调整目录设置，插件将恢复关闭状态！") || !strings.Contains(line, "二级分类策略") {
			h.t.Fatalf("success message missing: %s", line)
		}
	} else if line != "" {
		h.t.Fatalf("unexpected message: %s", line)
	}
}
func (h *mainHost) workers() map[string]int {
	h.t.Helper()
	out, err := exec.Command("ps", "-axo", "pid=,ppid=,args=").Output()
	if err != nil {
		h.t.Fatal(err)
	}
	pids := map[string]int{}
	for _, line := range strings.Split(string(out), "\n") {
		fields := strings.Fields(line)
		if len(fields) < 3 {
			continue
		}
		if strings.Contains(strings.Join(fields[2:], " "), filepath.Join(h.dir, "plugin-packages")) {
			var pid int
			fmt.Sscan(fields[0], &pid)
			key := "CategoryEditor"
			if strings.Contains(line, "CategoryEditorowned") {
				key = "CategoryEditorowned"
			}
			pids[key] = pid
		}
	}
	h.record("worker_pids", pids)
	return pids
}
func fileHash(t *testing.T, path string) string {
	t.Helper()
	b, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}
