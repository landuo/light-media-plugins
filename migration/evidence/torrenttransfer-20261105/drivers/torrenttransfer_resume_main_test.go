package integration

// Continue only the unexecuted lifecycle after a coordinator UI-wait timeout.
// The earlier real transfers and failed driver exit remain separate evidence.
import (
	"bufio"
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestTorrentTransferResumeOwnedLifecycle(t *testing.T) {
	dir := os.Getenv("TORRENTTRANSFER_RESUME_DIR")
	if dir == "" {
		t.Skip("opt-in continuation of retained owned real-main data")
	}
	root := filepath.Dir(dir)
	marker, err := os.ReadFile(filepath.Join(root, ".task-owned"))
	if err != nil || string(marker) != "light-media-plugins/TorrentTransfer/20261105/owned-only" {
		t.Fatal("owned marker required")
	}
	previous, err := os.ReadFile(filepath.Join(dir, "evidence", "observations.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	configs := map[string]json.RawMessage{}
	var sourceData, cloneData map[string]json.RawMessage
	transfers := map[string]bool{}
	batch, timer, recovery, normalExit := false, false, false, false
	scanner := bufio.NewScanner(bytes.NewReader(previous))
	scanner.Buffer(make([]byte, 4096), 4<<20)
	for scanner.Scan() {
		var event struct {
			Event string          `json:"event"`
			Value json.RawMessage `json:"value"`
		}
		if json.Unmarshal(scanner.Bytes(), &event) != nil {
			t.Fatal("invalid retained event")
		}
		switch event.Event {
		case "http":
			var v struct {
				Method, Path string
				Response     json.RawMessage
			}
			if json.Unmarshal(event.Value, &v) != nil {
				t.Fatal("retained HTTP")
			}
			if v.Method == "GET" && (v.Path == "/api/plugins/TorrentTransfer" || v.Path == "/api/plugins/TorrentTransfermusic") {
				var wrap struct {
					Data json.RawMessage `json:"data"`
				}
				json.Unmarshal(v.Response, &wrap)
				if wrap.Data == nil {
					t.Fatal("retained config envelope missing")
				}
				configs[strings.TrimPrefix(v.Path, "/api/plugins/")] = wrap.Data
			}
		case "clone_isolation":
			var v struct {
				Source map[string]json.RawMessage `json:"source_data"`
				Clone  map[string]json.RawMessage `json:"clone_data"`
			}
			if json.Unmarshal(event.Value, &v) != nil {
				t.Fatal("retained namespace data")
			}
			sourceData, cloneData = v.Source, v.Clone
		case "actual_transfer":
			var v struct {
				From, To  string
				Preserved bool `json:"source_payload_preserved"`
			}
			json.Unmarshal(event.Value, &v)
			if !v.Preserved {
				t.Fatal("earlier transfer did not preserve payload")
			}
			transfers[v.From+"->"+v.To] = true
		case "real_batch_completed":
			var v struct {
				Count    int     `json:"torrents"`
				History  int     `json:"history_count"`
				Elapsed  float64 `json:"elapsed_seconds"`
				Verified bool    `json:"all_target_tasks_and_source_history_verified"`
			}
			json.Unmarshal(event.Value, &v)
			batch = v.Count == 100 && v.History == 106 && v.Elapsed >= 300 && v.Verified
		case "actual_private_recheck_timer":
			timer = true
		case "actual_backup_permission_recovery":
			recovery = true
		case "main_exit":
			var v struct {
				Error string `json:"error"`
			}
			json.Unmarshal(event.Value, &v)
			normalExit = v.Error == "<nil>"
		}
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}
	if len(transfers) != 4 || !batch || !timer || !recovery || !normalExit || len(sourceData) != 106 || len(cloneData) != 1 || len(configs) != 2 {
		t.Fatal("retained execution prerequisites incomplete")
	}
	processes, err := exec.Command("ps", "-eo", "pid=,args=").Output()
	if err != nil {
		t.Fatal(err)
	}
	for _, line := range strings.Split(string(processes), "\n") {
		if strings.Contains(line, filepath.Join(dir, "plugin-packages")+string(filepath.Separator)) {
			t.Fatal("previous worker still running before actual cold boot")
		}
	}
	evidence := filepath.Join(dir, "lifecycle-continuation-evidence")
	if err := os.Mkdir(evidence, 0700); err != nil {
		t.Fatal(err)
	}
	events, err := os.OpenFile(filepath.Join(evidence, "observations.jsonl"), os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	jar, _ := cookiejar.New(nil)
	h := &mainHost{t: t, binary: os.Getenv("CATEGORYEDITOR_HOST_BINARY"), dir: dir, evidence: evidence, addr: "127.0.0.1:36252", base: "http://127.0.0.1:36252", client: &http.Client{Jar: jar, Timeout: time.Minute}, events: events}
	if h.binary == "" {
		t.Fatal("ordinary host binary required")
	}
	t.Cleanup(func() { h.stop(); events.Close() })
	h.record("continuation_admission", map[string]any{"prior_driver_result": "failed solely at root browser coordination wait; never relabeled passed", "prior_observations_sha256": fileHash(t, filepath.Join(dir, "evidence", "observations.jsonl")), "four_real_transfers": true, "real_batch100": true, "bootstrap_skipped_existing_database_reused": true})
	h.start()
	assertData := func(id string, want map[string]json.RawMessage) {
		t.Helper()
		got, _ := json.Marshal(ownedTransferData(t, h, id))
		expected, _ := json.Marshal(want)
		if !bytes.Equal(got, expected) {
			t.Fatal("cold/reset namespace data mismatch", id)
		}
	}
	for id, cfg := range configs {
		h.config(id, cfg)
	}
	assertData("TorrentTransfer", sourceData)
	assertData("TorrentTransfermusic", cloneData)
	pids := transferWorkers(h)
	if len(pids) != 2 {
		t.Fatal("cold source/clone workers missing", pids)
	}
	time.Sleep(4 * time.Second) // Beyond the original3-second one-shot deadline.
	assertData("TorrentTransfer", sourceData)
	assertData("TorrentTransfermusic", cloneData)
	log, err := os.ReadFile(filepath.Join(evidence, "host-1.log"))
	if err != nil || bytes.Contains(log, []byte("开始转移做种任务")) {
		t.Fatal("cold boot replayed a disabled transfer", err)
	}
	var repair struct {
		RelativePath string `json:"relative_path"`
		Hash         string `json:"file_sha256"`
	}
	b, err := os.ReadFile(filepath.Join(dir, "evidence", "clone-repair-owned-result.json"))
	if err != nil || json.Unmarshal(b, &repair) != nil {
		t.Fatal("actual clone file proof required", err)
	}
	temp := filepath.Join(dir, repair.RelativePath)
	if fileHash(t, temp) != repair.Hash {
		t.Fatal("cold boot changed repaired clone file")
	}
	h.record("actual_cold_recovery", map[string]any{"worker_pids": pids, "source_history": 106, "clone_history": 1, "configs_equal": true, "four_second_no_replay": true, "clone_repaired_file_preserved": true})
	h.ok("POST", "/api/plugins/TorrentTransfermusic/reset", map[string]any{})
	if len(ownedTransferData(t, h, "TorrentTransfermusic")) != 0 {
		t.Fatal("reset retained clone values")
	}
	assertData("TorrentTransfer", sourceData)
	_, resetFileError := os.Stat(temp)
	h.ok("DELETE", "/api/plugins/TorrentTransfermusic", nil)
	if _, err := os.Stat(filepath.Join(dir, "plugin-packages", "TorrentTransfermusic")); !os.IsNotExist(err) {
		t.Fatal("clone code retained", err)
	}
	assertData("TorrentTransfer", sourceData)
	_, uninstallFileError := os.Stat(temp)
	worker := os.Getenv("TORRENTTRANSFER_UPDATE_WORKER_BINARY")
	binary, err := os.ReadFile(worker)
	if err != nil {
		t.Fatal(err)
	}
	manifest, err := exec.Command(worker, "--manifest").Output()
	if err != nil {
		t.Fatal(err)
	}
	var m map[string]any
	if json.Unmarshal(manifest, &m) != nil {
		t.Fatal("reinstall manifest")
	}
	var repo *httptest.Server
	repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/worker" {
			w.Write(binary)
			return
		}
		if r.URL.Path != "/index" {
			http.NotFound(w, r)
			return
		}
		sha := fileHash(t, worker)
		artifact := map[string]any{"platform": "linux-amd64", "format": "executable", "sha256": sha, "executable_sha256": sha, "size": len(binary), "host_contract": "light-media.sdk-resources/v1", "url": repo.URL + "/worker"}
		json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": "TorrentTransfer", "current_version": m["version"], "releases": []any{map[string]any{"version": m["version"], "manifest": m, "artifacts": []any{artifact}}}})
	}))
	defer repo.Close()
	h.ok("DELETE", "/api/plugins/TorrentTransfer", nil)
	h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": "TorrentTransfer", "repo_url": repo.URL + "/index"})
	h.config("TorrentTransfer", configs["TorrentTransfer"])
	assertData("TorrentTransfer", sourceData)
	h.record("actual_lifecycle_continuation_completed", map[string]any{"cold_boot": true, "clone_reset_isolated": true, "clone_uninstall_code_removed": true, "source_uninstall_data_retained": true, "reinstall_config_retained": true, "reset_private_temp_present": resetFileError == nil, "uninstall_private_temp_present": uninstallFileError == nil, "scope": "Actual ordinary main/SQLite/files/independent workers; pairs with immutable run6 real transfer and browser evidence. Earlier driver exit remains failure, not full green."})
}

func TestTorrentTransferRetainedDataAndUninstallTail(t *testing.T) {
	dir := os.Getenv("TORRENTTRANSFER_RETENTION_TAIL_DIR")
	if dir == "" {
		t.Skip("opt-in retained actual-main source-contract correction")
	}
	root := filepath.Dir(dir)
	marker, err := os.ReadFile(filepath.Join(root, ".task-owned"))
	if err != nil || string(marker) != "light-media-plugins/TorrentTransfer/20261105/owned-only" {
		t.Fatal("owned marker")
	}
	priorFailure, err := os.ReadFile(filepath.Join(root, "main-run-6-lifecycle-continuation.log"))
	if err != nil || !bytes.Contains(priorFailure, []byte("uninstall/reinstall retained source data")) {
		t.Fatal("expected separately retained wrong-assertion run required")
	}
	raw, err := os.ReadFile(filepath.Join(dir, "evidence", "observations.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	configs := map[string]json.RawMessage{}
	var sourceData map[string]json.RawMessage
	scanner := bufio.NewScanner(bytes.NewReader(raw))
	scanner.Buffer(make([]byte, 4096), 4<<20)
	for scanner.Scan() {
		var event struct {
			Event string          `json:"event"`
			Value json.RawMessage `json:"value"`
		}
		if json.Unmarshal(scanner.Bytes(), &event) != nil {
			t.Fatal("retained event")
		}
		if event.Event == "clone_isolation" {
			var v struct {
				Source map[string]json.RawMessage `json:"source_data"`
			}
			json.Unmarshal(event.Value, &v)
			sourceData = v.Source
		}
		if event.Event == "http" {
			var v struct {
				Method, Path string
				Response     json.RawMessage
			}
			json.Unmarshal(event.Value, &v)
			if v.Method == "GET" && (v.Path == "/api/plugins/TorrentTransfer" || v.Path == "/api/plugins/TorrentTransfermusic") {
				var wrap struct {
					Data json.RawMessage `json:"data"`
				}
				json.Unmarshal(v.Response, &wrap)
				configs[strings.TrimPrefix(v.Path, "/api/plugins/")] = wrap.Data
			}
		}
	}
	if scanner.Err() != nil || len(sourceData) != 106 || len(configs) != 2 {
		t.Fatal("retained expected source state incomplete")
	}
	evidence := filepath.Join(dir, "retention-tail-evidence")
	if err := os.Mkdir(evidence, 0700); err != nil {
		t.Fatal(err)
	}
	events, err := os.OpenFile(filepath.Join(evidence, "observations.jsonl"), os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	jar, _ := cookiejar.New(nil)
	h := &mainHost{t: t, binary: os.Getenv("CATEGORYEDITOR_HOST_BINARY"), dir: dir, evidence: evidence, addr: "127.0.0.1:36252", base: "http://127.0.0.1:36252", client: &http.Client{Jar: jar, Timeout: time.Minute}, events: events}
	t.Cleanup(func() { h.stop(); events.Close() })
	h.record("source_retention_expectation_correction", map[string]any{"source": "actual app/api/endpoints/plugin.py uninstall993..1030; independent tt-uninstall-source oracle", "expected": "base retains config/data/code; clone deletes config/data/code; Base data-path files retained", "previous_failure": "wrong harness expected cleared base KV; not a product fix or relabeled passing run"})
	h.start()
	assertSource := func() {
		t.Helper()
		got, _ := json.Marshal(ownedTransferData(t, h, "TorrentTransfer"))
		want, _ := json.Marshal(sourceData)
		if !bytes.Equal(got, want) {
			t.Fatal("retained106source records changed")
		}
	}
	assertSource()
	h.config("TorrentTransfer", configs["TorrentTransfer"])
	if _, err := os.Stat(filepath.Join(dir, "plugin-packages", "TorrentTransfermusic")); !os.IsNotExist(err) {
		t.Fatal("previous clone uninstall retained code")
	}
	if len(ownedTransferData(t, h, "TorrentTransfermusic")) != 0 {
		t.Fatal("previous clone reset/uninstall retained data")
	}
	// Recreate this same platform clone and give it one real history row, so
	// uninstall is checked with nonempty config/data independently of reset.
	h.ok("POST", "/api/plugins/TorrentTransfer/clone", map[string]any{"suffix": "music"})
	var repair struct {
		Hash         string `json:"hash"`
		RelativePath string `json:"relative_path"`
		SHA          string `json:"file_sha256"`
	}
	b, err := os.ReadFile(filepath.Join(dir, "evidence", "clone-repair-owned-result.json"))
	if err != nil || json.Unmarshal(b, &repair) != nil {
		t.Fatal("repair fixture evidence required")
	}
	d := &transferDaemon{ID: "owned-qb-target", Name: "Owned qB target", Kind: "qbittorrent", URL: "http://127.0.0.1:36302", client: &http.Client{Timeout: 15 * time.Second}, t: t}
	rows := d.rows(repair.Hash)
	if len(rows) != 1 || rows[0]["name"] != "owned-main-run-6-music.bin" {
		t.Fatal("owned exact target task precondition")
	}
	d.qb("POST", "torrents/delete", map[string][]string{"hashes": {repair.Hash}, "deleteFiles": {"false"}})
	var cloneConfig map[string]any
	if json.Unmarshal(configs["TorrentTransfermusic"], &cloneConfig) != nil {
		t.Fatal("clone config")
	}
	cloneConfig["onlyonce"] = true
	h.ok("PUT", "/api/plugins/TorrentTransfermusic", cloneConfig)
	waitTransfer(t, "recreated clone performs actual real transfer", 30*time.Second, func() bool {
		return len(d.rows(repair.Hash)) == 1 && len(ownedTransferData(t, h, "TorrentTransfermusic")) == 1
	})
	cloneConfig["onlyonce"] = false
	h.config("TorrentTransfermusic", cloneConfig)
	assertSource()
	temp := filepath.Join(dir, repair.RelativePath)
	if fileHash(t, temp) != repair.SHA {
		t.Fatal("recreated clone repair output changed")
	}
	h.ok("DELETE", "/api/plugins/TorrentTransfermusic", nil)
	if len(ownedTransferData(t, h, "TorrentTransfermusic")) != 0 {
		t.Fatal("clone uninstall retained nonempty data")
	}
	if _, err := os.Stat(filepath.Join(dir, "plugin-packages", "TorrentTransfermusic")); !os.IsNotExist(err) {
		t.Fatal("clone uninstall retained code")
	}
	if fileHash(t, temp) != repair.SHA {
		t.Fatal("clone uninstall removed Base data-path temporary file")
	}
	assertSource()
	h.record("nonempty_clone_uninstall", map[string]any{"actual_transfer_history_before": 1, "clone_history_after": 0, "clone_code_removed": true, "private_data_path_file_retained": true, "source106unchanged": true})
	worker := os.Getenv("TORRENTTRANSFER_UPDATE_WORKER_BINARY")
	binary, err := os.ReadFile(worker)
	if err != nil {
		t.Fatal(err)
	}
	manifest, err := exec.Command(worker, "--manifest").Output()
	if err != nil {
		t.Fatal(err)
	}
	var m map[string]any
	if json.Unmarshal(manifest, &m) != nil {
		t.Fatal("manifest")
	}
	var repo *httptest.Server
	repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/worker" {
			w.Write(binary)
			return
		}
		if r.URL.Path != "/index" {
			http.NotFound(w, r)
			return
		}
		sha := fileHash(t, worker)
		artifact := map[string]any{"platform": "linux-amd64", "format": "executable", "sha256": sha, "executable_sha256": sha, "size": len(binary), "host_contract": "light-media.sdk-resources/v1", "url": repo.URL + "/worker"}
		json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": "TorrentTransfer", "current_version": m["version"], "releases": []any{map[string]any{"version": m["version"], "manifest": m, "artifacts": []any{artifact}}}})
	}))
	defer repo.Close()
	h.ok("DELETE", "/api/plugins/TorrentTransfer", nil)
	assertSource()
	if _, err := os.Stat(filepath.Join(dir, "plugin-packages", "TorrentTransfer", "torrent-transfer")); err != nil {
		t.Fatal("base uninstall removed retained code", err)
	}
	if len(transferWorkers(h)) != 0 {
		t.Fatal("base uninstall did not stop worker")
	}
	h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": "TorrentTransfer", "repo_url": repo.URL + "/index"})
	h.config("TorrentTransfer", configs["TorrentTransfer"])
	assertSource()
	h.record("retained_base_uninstall_reinstall_passed", map[string]any{"source_config_retained": true, "source106data_retained": true, "source_code_retained": true, "uninstall_stopped_worker": true, "reinstall_loaded_worker": transferWorkers(h)["TorrentTransfer"] > 0, "scope": "Pairs with run6 actual transfer/browser and separate cold/reset continuation. All earlier failed test exits remain failed; source-derived corrected base retention and nonempty clone deletion executed here."})
}
