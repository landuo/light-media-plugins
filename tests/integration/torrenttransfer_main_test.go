package integration

// This opt-in driver uses the ordinary host executable and four owned real
// daemons. It never points at the user's existing downloaders or media files.
import (
	"archive/zip"
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"testing"
	"time"
)

type transferDaemon struct {
	ID, Name, Kind, URL string
	client              *http.Client
	session             string
	t                   *testing.T
}

func (d *transferDaemon) qb(method, endpoint string, values url.Values) []byte {
	d.t.Helper()
	var body io.Reader
	if values != nil {
		body = strings.NewReader(values.Encode())
	}
	req, err := http.NewRequest(method, d.URL+"/api/v2/"+endpoint, body)
	if err != nil {
		d.t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	r, err := d.client.Do(req)
	if err != nil {
		d.t.Fatal(err)
	}
	defer r.Body.Close()
	b, err := io.ReadAll(io.LimitReader(r.Body, 4<<20))
	if err != nil || r.StatusCode != 200 {
		d.t.Fatalf("owned qB %s %s status%d: %s %v", d.ID, endpoint, r.StatusCode, b, err)
	}
	return b
}

func (d *transferDaemon) tr(method string, args any) map[string]any {
	d.t.Helper()
	b, _ := json.Marshal(map[string]any{"method": method, "arguments": args})
	for attempt := 0; attempt < 2; attempt++ {
		req, _ := http.NewRequest("POST", d.URL+"/transmission/rpc", bytes.NewReader(b))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Transmission-Session-Id", d.session)
		r, err := d.client.Do(req)
		if err != nil {
			d.t.Fatal(err)
		}
		data, readErr := io.ReadAll(io.LimitReader(r.Body, 4<<20))
		r.Body.Close()
		if r.StatusCode == 409 {
			d.session = r.Header.Get("X-Transmission-Session-Id")
			continue
		}
		var out struct {
			Result    string         `json:"result"`
			Arguments map[string]any `json:"arguments"`
		}
		if readErr != nil || r.StatusCode != 200 || json.Unmarshal(data, &out) != nil || out.Result != "success" {
			d.t.Fatalf("owned TR %s %s HTTP%d: %s %v", d.ID, method, r.StatusCode, data, readErr)
		}
		return out.Arguments
	}
	d.t.Fatal("owned TR session negotiation failed")
	return nil
}

func (d *transferDaemon) rows(hash string) []map[string]any {
	d.t.Helper()
	var out []map[string]any
	if d.Kind == "qbittorrent" {
		raw := d.qb("POST", "torrents/info", url.Values{"hashes": {hash}})
		if err := json.Unmarshal(raw, &out); err != nil {
			d.t.Fatal(err)
		}
	} else {
		args := map[string]any{"ids": []string{hash}, "fields": []string{"hashString", "name", "status", "percentDone", "downloadDir", "labels", "error", "errorString"}}
		for _, item := range d.tr("torrent-get", args)["torrents"].([]any) {
			out = append(out, item.(map[string]any))
		}
	}
	return out
}

func (d *transferDaemon) add(raw []byte, hash, dir, label string) {
	d.t.Helper()
	if len(d.rows(hash)) != 0 {
		d.t.Fatal("owned fixture requires a new source hash, not a duplicate", d.ID, hash)
	}
	if d.Kind == "qbittorrent" {
		var data bytes.Buffer
		w := multipart.NewWriter(&data)
		for k, v := range map[string]string{"savepath": dir, "stopped": "true", "paused": "true", "skip_checking": "false", "tags": label} {
			if err := w.WriteField(k, v); err != nil {
				d.t.Fatal(err)
			}
		}
		part, _ := w.CreateFormFile("torrents", "owned.torrent")
		part.Write(raw)
		w.Close()
		req, _ := http.NewRequest("POST", d.URL+"/api/v2/torrents/add", &data)
		req.Header.Set("Content-Type", w.FormDataContentType())
		r, err := d.client.Do(req)
		if err != nil {
			d.t.Fatal(err)
		}
		b, _ := io.ReadAll(r.Body)
		r.Body.Close()
		if r.StatusCode != 200 || strings.TrimSpace(string(b)) != "Ok." {
			d.t.Fatalf("owned qB add HTTP%d: %s", r.StatusCode, b)
		}
		// qB can acknowledge add while checkingResumeData is still active;
		// recheck during that phase is silently ignored. Establish the
		// published paused task before requesting real byte verification.
		waitTransfer(d.t, "owned qB initial resume processing settles", 15*time.Second, func() bool {
			r := d.rows(hash)
			if len(r) != 1 {
				return false
			}
			s, _ := r[0]["state"].(string)
			return s == "stoppedDL" || s == "stoppedUP" || s == "pausedDL" || s == "pausedUP"
		})
		d.qb("POST", "torrents/recheck", url.Values{"hashes": {hash}})
	} else {
		added := d.tr("torrent-add", map[string]any{"metainfo": base64.StdEncoding.EncodeToString(raw), "download-dir": dir, "paused": true, "labels": []string{label}})
		if added["torrent-added"] == nil || added["torrent-duplicate"] != nil {
			d.t.Fatal("owned TR fixture was not newly added", hash)
		}
		// Installed vendor documents add(labels) as RPC17, change(labels) as
		// RPC16. The real3.00 fixture supports the latter; establish and read
		// back its source label instead of assuming torrent-add retained it.
		d.tr("torrent-set", map[string]any{"ids": []string{hash}, "labels": []string{label}})
		waitTransfer(d.t, "owned TR source label retained", 5*time.Second, func() bool {
			r := d.rows(hash)
			if len(r) != 1 {
				return false
			}
			labels, ok := r[0]["labels"].([]any)
			return ok && len(labels) == 1 && labels[0] == label
		})
		d.tr("torrent-verify", map[string]any{"ids": []string{hash}})
		waitTransfer(d.t, "real TR source verification", 30*time.Second, func() bool {
			rows := d.rows(hash)
			return len(rows) == 1 && rows[0]["percentDone"] == float64(1) && rows[0]["status"] == float64(0)
		})
		d.tr("torrent-start", map[string]any{"ids": []string{hash}})
	}
	waitTransfer(d.t, "real completed source", 15*time.Second, func() bool {
		if d.Kind == "qbittorrent" {
			// Source get_completed_torrents queries the completed filter and
			// checks amount_left/state too. qB's hashes-only snapshot can show
			// progress1 before its completed-filter membership is published.
			var rows []map[string]any
			if err := json.Unmarshal(d.qb("POST", "torrents/info", url.Values{"hashes": {hash}, "filter": {"completed"}}), &rows); err != nil {
				d.t.Fatal(err)
			}
			return len(rows) == 1 && rows[0]["progress"] == float64(1) && rows[0]["amount_left"] == float64(0) && (rows[0]["state"] == "stoppedUP" || rows[0]["state"] == "pausedUP")
		}
		r := d.rows(hash)
		if len(r) != 1 {
			return false
		}
		return r[0]["percentDone"] == float64(1) && r[0]["status"] == float64(6)
	})
}

func waitTransfer(t *testing.T, description string, timeout time.Duration, condition func() bool) {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for !condition() {
		if time.Now().After(deadline) {
			t.Fatal("timeout: " + description)
		}
		time.Sleep(100 * time.Millisecond)
	}
}

// The torrent is generated independently of the plugin's codec: canonical
// single-file v1 metadata, real SHA1 piece, private flag and no tracker.
func ownedTransferTorrent(t *testing.T, dir, name string) ([]byte, string) {
	t.Helper()
	payload := bytes.Repeat([]byte("light-media-owned-transfer/"+name+"\n"), 1024)
	piece := sha1.Sum(payload)
	info := []byte(fmt.Sprintf("d6:lengthi%de4:name%d:%s12:piece lengthi1048576e6:pieces20:", len(payload), len(name), name))
	info = append(info, piece[:]...)
	info = append(info, []byte("7:privatei1ee")...)
	hash := sha1.Sum(info)
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, name), payload, 0600); err != nil {
		t.Fatal(err)
	}
	raw := append([]byte("d4:info"), info...)
	raw = append(raw, 'e')
	return raw, hex.EncodeToString(hash[:])
}

func writeOwnedTransferBackup(t *testing.T, dir, hash string, raw []byte) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, hash+".torrent"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	// Source lines817..861 require a fastresume file when announce is absent.
	// Empty trackers are valid bencode and deliberately preserve our trackerless
	// owned torrent. These are generated backup fixtures, not production exports.
	if err := os.WriteFile(filepath.Join(dir, hash+".fastresume"), []byte("d8:trackerslee"), 0600); err != nil {
		t.Fatal(err)
	}
}

// Read only the owned application's encrypted data table. Python's stdlib
// SQLite is a test inspection dependency, never a plugin runtime. Encryption
// keys and encrypted blobs are not written to evidence or command arguments.
func ownedTransferData(t *testing.T, h *mainHost, instance string) map[string]json.RawMessage {
	t.Helper()
	code := `import sqlite3,json,base64,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
c.execute('PRAGMA query_only=ON')
print(json.dumps([[k,base64.b64encode(v).decode()] for k,v in c.execute("SELECT item_key,sealed FROM plugin_values WHERE instance_id=? AND kind='data' ORDER BY rowid",(sys.argv[2],))]))`
	b, err := exec.Command("python3", "-c", code, filepath.Join(h.dir, "light-media.db"), instance).Output()
	if err != nil {
		t.Fatal("owned read-only data inspection", err)
	}
	var rows [][2]string
	if err := json.Unmarshal(b, &rows); err != nil {
		t.Fatal(err)
	}
	key, err := os.ReadFile(filepath.Join(h.dir, "secret.key"))
	if err != nil {
		t.Fatal(err)
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		t.Fatal(err)
	}
	aead, _ := cipher.NewGCM(block)
	out := map[string]json.RawMessage{}
	for _, row := range rows {
		sealed, err := base64.StdEncoding.DecodeString(row[1])
		if err != nil || len(sealed) < aead.NonceSize() {
			t.Fatal("owned invalid sealed data")
		}
		aad, _ := json.Marshal([]string{"light-media/plugins/v1", "data", instance, row[0]})
		plain, err := aead.Open(nil, sealed[:aead.NonceSize()], sealed[aead.NonceSize():], aad)
		if err != nil {
			t.Fatal("owned data integrity", err)
		}
		out[row[0]] = plain
	}
	return out
}

func transferWorkers(h *mainHost) map[string]int {
	h.t.Helper()
	raw, err := exec.Command("ps", "-eo", "pid=,ppid=,args=").Output()
	if err != nil {
		h.t.Fatal(err)
	}
	pids := map[string]int{}
	for _, line := range strings.Split(string(raw), "\n") {
		fields := strings.Fields(line)
		if len(fields) < 3 {
			continue
		}
		var pid, parent int
		fmt.Sscan(fields[0], &pid)
		fmt.Sscan(fields[1], &parent)
		if h.cmd == nil || parent != h.cmd.Process.Pid {
			continue
		}
		for _, id := range []string{"TorrentTransfer", "TorrentTransfermusic"} {
			if strings.Contains(strings.Join(fields[2:], " "), filepath.Join(h.dir, "plugin-packages", id)+string(filepath.Separator)) {
				pids[id] = pid
			}
		}
	}
	h.record("actual_transfer_worker_pids", pids)
	return pids
}

// Dependency preflight is recorded separately from plugin acceptance. It runs
// before the final host SDK contract is frozen, using only disposable daemons.
func TestTorrentTransferOwnedDaemonPreflight(t *testing.T) {
	root := os.Getenv("TORRENTTRANSFER_OWNED_ROOT")
	if root == "" {
		t.Skip("owned real-daemon preflight not configured")
	}
	marker, err := os.ReadFile(filepath.Join(root, ".task-owned"))
	if err != nil || string(marker) != "light-media-plugins/TorrentTransfer/20261105/owned-only" {
		t.Fatal("owned infrastructure marker required")
	}
	client := &http.Client{Timeout: 15 * time.Second}
	var observations []map[string]any
	for i, kind := range []string{"qbittorrent", "transmission"} {
		port := 36301 + 2*i
		d := transferDaemon{ID: "owned-preflight-" + kind, Name: "owned-preflight-" + kind, Kind: kind, URL: fmt.Sprintf("http://127.0.0.1:%d", port), client: client, t: t}
		dir := filepath.Join(root, "payload")
		name := "owned-preflight-" + kind + ".bin"
		if token := os.Getenv("TORRENTTRANSFER_PREFLIGHT_TOKEN"); token != "" {
			name = "owned-preflight-" + token + "-" + kind + ".bin"
		}
		raw, hash := ownedTransferTorrent(t, dir, name)
		d.add(raw, hash, dir, "owned-preflight")
		row := d.rows(hash)[0]
		observations = append(observations, map[string]any{"kind": kind, "hash": hash, "row": row, "payload_present": true, "payload_sha256": fileHash(t, filepath.Join(dir, name))})
	}
	b, _ := json.MarshalIndent(map[string]any{"classification": "real disposable daemon dependency preflight; no host/plugin execution or acceptance", "observations": observations}, "", "  ")
	name := "daemon-payload-preflight.json"
	if token := os.Getenv("TORRENTTRANSFER_PREFLIGHT_TOKEN"); token != "" {
		if filepath.Base(token) != token || token == "." || token == ".." {
			t.Fatal("invalid owned preflight token")
		}
		name = "daemon-payload-preflight-" + token + ".json"
	}
	if err := os.WriteFile(filepath.Join(root, name), b, 0600); err != nil {
		t.Fatal(err)
	}
}

func TestTorrentTransferActualMainDaemons(t *testing.T) {
	worker := os.Getenv("TORRENTTRANSFER_WORKER_BINARY")
	root := os.Getenv("TORRENTTRANSFER_OWNED_ROOT")
	if worker == "" || root == "" {
		t.Skip("opt-in actual main+owned qB/TR daemons; not executed acceptance")
	}
	marker, err := os.ReadFile(filepath.Join(root, ".task-owned"))
	if err != nil || string(marker) != "light-media-plugins/TorrentTransfer/20261105/owned-only" {
		t.Fatal("exact owned infrastructure marker required")
	}
	h := newMainHost(t)                 // Shared real-main driver; the CATEGORYEDITOR_* env names are historical.
	h.client.Timeout = 10 * time.Minute // Original manual scheduler waits for the whole synchronous job.
	runToken := filepath.Base(h.dir)
	client := &http.Client{Timeout: 15 * time.Second}
	daemons := []*transferDaemon{
		{"owned-qb-source", "Owned qB source", "qbittorrent", "http://127.0.0.1:36301", client, "", t},
		{"owned-qb-target", "Owned qB target", "qbittorrent", "http://127.0.0.1:36302", client, "", t},
		{"owned-tr-source", "Owned TR source", "transmission", "http://127.0.0.1:36303", client, "", t},
		{"owned-tr-target", "Owned TR target", "transmission", "http://127.0.0.1:36304", client, "", t},
	}
	settings := []any{}
	for _, d := range daemons {
		settings = append(settings, map[string]any{"id": d.ID, "name": d.Name, "kind": d.Kind, "base_url": d.URL, "enabled": true})
		if d.Kind == "qbittorrent" {
			h.record("real_daemon", map[string]any{"id": d.ID, "version": string(d.qb("GET", "app/version", nil))})
		} else {
			h.record("real_daemon", map[string]any{"id": d.ID, "version": d.tr("session-get", nil)["version"]})
		}
	}
	h.ok("PUT", "/api/settings", map[string]any{"downloaders": settings, "allowed_roots": []string{h.dir}, "plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0})
	backup := filepath.Join(h.dir, "backups")
	if err := os.MkdirAll(backup, 0700); err != nil {
		t.Fatal(err)
	}
	bin, err := os.ReadFile(worker)
	if err != nil {
		t.Fatal(err)
	}
	manifestBytes, err := exec.Command(worker, "--manifest").Output()
	if err != nil {
		t.Fatal(err)
	}
	var manifest map[string]any
	if json.Unmarshal(manifestBytes, &manifest) != nil || manifest["plugin_id"] != "TorrentTransfer" || manifest["version"] != "1.10.3" {
		t.Fatal("actual TorrentTransfer1.10.3 executable manifest required")
	}
	var repo *httptest.Server
	var repoMu sync.Mutex
	version := "1.10.3"
	artifactHash := fileHash(t, worker)
	executableHash := artifactHash
	artifactFormat := "executable"
	var artifactFiles []map[string]any
	if path := os.Getenv("TORRENTTRANSFER_PACKAGE_ZIP"); path != "" {
		archive, err := zip.OpenReader(path)
		if err != nil {
			t.Fatal(err)
		}
		found := false
		for _, file := range archive.File {
			reader, err := file.Open()
			if err != nil {
				t.Fatal(err)
			}
			content, err := io.ReadAll(io.LimitReader(reader, 128<<20))
			reader.Close()
			if err != nil {
				t.Fatal(err)
			}
			if file.Name == manifest["entry"] {
				if !bytes.Equal(content, bin) {
					t.Fatal("packaged worker differs from frozen worker")
				}
				found = true
			}
			artifactFiles = append(artifactFiles, map[string]any{"path": file.Name, "size": len(content), "sha256": fmt.Sprintf("%x", sha256.Sum256(content))})
		}
		archive.Close()
		if !found {
			t.Fatal("package lacks worker")
		}
		bin, err = os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		artifactHash, artifactFormat = fileHash(t, path), "zip"
		h.record("packaged_install_input", map[string]any{"archive_sha256": artifactHash, "worker_sha256": executableHash, "files": artifactFiles})
	}
	repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		repoMu.Lock()
		defer repoMu.Unlock()
		switch r.URL.Path {
		case "/index":
			artifact := map[string]any{"platform": runtime.GOOS + "-" + runtime.GOARCH, "format": artifactFormat, "sha256": artifactHash, "executable_sha256": executableHash, "size": len(bin), "host_contract": "light-media.sdk-resources/v1", "url": repo.URL + "/worker"}
			if artifactFormat == "zip" {
				artifact["files"] = artifactFiles
			}
			json.NewEncoder(w).Encode(map[string]any{"schema_version": 1, "plugin_id": "TorrentTransfer", "current_version": version, "releases": []any{map[string]any{"version": version, "manifest": manifest, "artifacts": []any{artifact}}}})
		case "/worker":
			w.Write(bin)
		default:
			http.NotFound(w, r)
		}
	}))
	defer repo.Close()
	const id, clone = "TorrentTransfer", "TorrentTransfermusic"
	install := func(force bool) {
		h.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": id, "force": force, "repo_url": repo.URL + "/index"})
	}
	install(false)
	form := h.ok("GET", "/api/plugins/"+id+"/form", nil)
	if !bytes.Contains(form, []byte("Owned qB source")) || !bytes.Contains(form, []byte("Owned TR target")) || !bytes.Contains(form, []byte("skipverify")) {
		t.Fatal("source dynamic downloader form incomplete", string(form))
	}
	initialPID := transferWorkers(h)[id]
	if initialPID == 0 {
		t.Fatal("actual persistent worker not started")
	}
	configFor := func(from, to *transferDaemon, tag string) map[string]any {
		return map[string]any{"enabled": true, "onlyonce": false, "cron": "0 0 1 1 *", "notify": false, "nolabels": "", "includelabels": tag, "includecategory": "", "frompath": "", "topath": "", "fromdownloader": from.Name, "todownloader": to.Name, "deletesource": false, "deleteduplicate": false, "fromtorrentpath": backup, "nopaths": "", "autostart": false, "skipverify": false, "transferemptylabel": false, "add_torrent_tags": "owned-destination", "remainoldcat": false, "remainoldtag": true}
	}
	var finalConfig map[string]any
	var sourceKeys []string
	for index, pair := range [][2]int{{0, 1}, {0, 3}, {2, 1}, {2, 3}} {
		from, to := daemons[pair[0]], daemons[pair[1]]
		name := fmt.Sprintf("owned-%s-transfer-%d.bin", runToken, index)
		payloadDir := filepath.Join(root, "payload")
		raw, hash := ownedTransferTorrent(t, payloadDir, name)
		beforeHash := fileHash(t, filepath.Join(payloadDir, name))
		if len(to.rows(hash)) != 0 {
			t.Fatal("owned fixture target is not empty", to.ID, hash)
		}
		writeOwnedTransferBackup(t, backup, hash, raw)
		tag := fmt.Sprintf("owned-%s-source-%d", runToken, index)
		from.add(raw, hash, payloadDir, tag)
		cfg := configFor(from, to, tag)
		cfg["deletesource"] = index == 1 // Confirm source-task-only deletion leaves exact real bytes.
		cfg["skipverify"] = index == 0
		cfg["onlyonce"] = index == 3 // Actual3-second private one-shot and auto-clear.
		h.ok("PUT", "/api/plugins/"+id, cfg)
		if index != 3 {
			h.ok("POST", "/api/plugins/services/run", map[string]any{"instance_id": id, "service_id": "TorrentTransfer"})
		}
		key := from.Name + "-" + hash
		waitTransfer(t, "actual host data+target daemon", 40*time.Second, func() bool {
			return len(to.rows(hash)) == 1 && ownedTransferData(t, h, id)[key] != nil
		})
		data := ownedTransferData(t, h, id)
		var entry map[string]any
		if json.Unmarshal(data[key], &entry) != nil || entry["to_download"] != to.Name || entry["to_download_id"] != hash || entry["delete_source"] != (index == 1) || entry["delete_duplicate"] != false {
			t.Fatalf("actual durable source history mismatch: %s", data[key])
		}
		if afterHash := fileHash(t, filepath.Join(payloadDir, name)); afterHash != beforeHash {
			t.Fatal("source payload bytes changed", beforeHash, afterHash)
		}
		if (len(from.rows(hash)) == 0) != (index == 1) {
			t.Fatal("source task-only delete did not match option")
		}
		waitTransfer(t, "target real verification settles while paused", 30*time.Second, func() bool {
			r := to.rows(hash)
			if len(r) != 1 {
				return false
			}
			if to.Kind == "qbittorrent" {
				return (r[0]["state"] == "stoppedUP" || r[0]["state"] == "pausedUP") && r[0]["progress"] == float64(1)
			}
			return r[0]["status"] == float64(0) && r[0]["percentDone"] == float64(1)
		})
		target := to.rows(hash)[0]
		cfg["onlyonce"] = false
		h.config(id, cfg)
		sourceKeys = append(sourceKeys, key)
		finalConfig = cfg
		h.record("actual_transfer", map[string]any{"from": from.Kind, "to": to.Kind, "hash": hash, "history": entry, "target": target, "source_payload_before_sha256": beforeHash, "source_payload_sha256": fileHash(t, filepath.Join(payloadDir, name)), "source_payload_preserved": true})
	}
	if transferWorkers(h)[id] != initialPID {
		t.Fatal("ordinary config/init unexpectedly replaced persistent worker")
	}
	// Source lines879..919 and 935..988: an incomplete target remains queued;
	// after its owned bytes arrive and verification completes, the genuine
	// private30-second check starts it. We never invoke check_recheck directly.
	{
		from, to := daemons[0], daemons[1]
		payloadDir, targetDir := filepath.Join(root, "payload"), filepath.Join(root, "autostart-target")
		name := "owned-" + runToken + "-private-timer.bin"
		tag := "owned-" + runToken + "-private-timer"
		raw, hash := ownedTransferTorrent(t, payloadDir, name)
		writeOwnedTransferBackup(t, backup, hash, raw)
		if err := os.MkdirAll(targetDir, 0700); err != nil {
			t.Fatal(err)
		}
		if len(to.rows(hash)) != 0 {
			t.Fatal("timer fixture target is not empty")
		}
		from.add(raw, hash, payloadDir, tag)
		cfg := configFor(from, to, tag)
		cfg["autostart"], cfg["frompath"], cfg["topath"] = true, payloadDir, targetDir
		h.ok("PUT", "/api/plugins/"+id, cfg)
		h.ok("GET", "/api/v1/system/runscheduler?jobid=TorrentTransfer_TorrentTransfer", nil)
		key := from.Name + "-" + hash
		waitTransfer(t, "incomplete target retained for private timer", 15*time.Second, func() bool {
			rows := to.rows(hash)
			return len(rows) == 1 && rows[0]["progress"] == float64(0) && rows[0]["state"] == "stoppedDL" && ownedTransferData(t, h, id)[key] != nil
		})
		payload, err := os.ReadFile(filepath.Join(payloadDir, name))
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(targetDir, name), payload, 0600); err != nil {
			t.Fatal(err)
		}
		readyAt := time.Now()
		to.qb("POST", "torrents/recheck", url.Values{"hashes": {hash}})
		waitTransfer(t, "actual private timer starts verified target", 45*time.Second, func() bool {
			rows := to.rows(hash)
			if len(rows) != 1 {
				return false
			}
			state, _ := rows[0]["state"].(string)
			return rows[0]["progress"] == float64(1) && (state == "stalledUP" || state == "uploading" || state == "queuedUP" || state == "forcedUP")
		})
		sourceKeys = append(sourceKeys, key)
		h.record("actual_private_recheck_timer", map[string]any{"hash": hash, "target": to.rows(hash)[0], "elapsed_after_owned_file_arrival_seconds": time.Since(readyAt).Seconds(), "direct_plugin_check_invoked": false, "payload_sha256": fileHash(t, filepath.Join(targetDir, name))})
		finalConfig = cfg
	}
	// Source read_bytes at807/867 is outside its parse exception handlers.
	// Linux EACCES must fail this pass with no target/history, and the same
	// persistent worker must recover after the owned backup becomes readable.
	{
		if os.Geteuid() == 0 {
			t.Fatal("read-permission acceptance requires non-root Linux execution")
		}
		from, to := daemons[0], daemons[1]
		raw, hash := ownedTransferTorrent(t, filepath.Join(root, "payload"), "owned-"+runToken+"-read-failure.bin")
		writeOwnedTransferBackup(t, backup, hash, raw)
		path := filepath.Join(backup, hash+".torrent")
		if err := os.Chmod(path, 0000); err != nil {
			t.Fatal(err)
		}
		defer os.Chmod(path, 0600)
		if _, err := os.ReadFile(path); !os.IsPermission(err) {
			t.Fatalf("owned EACCES precondition failed: %v", err)
		}
		if len(to.rows(hash)) != 0 {
			t.Fatal("EACCES fixture target is not empty")
		}
		from.add(raw, hash, filepath.Join(root, "payload"), "owned-"+runToken+"-read-failure")
		cfg := configFor(from, to, "owned-"+runToken+"-read-failure")
		cfg["skipverify"] = true
		h.ok("PUT", "/api/plugins/"+id, cfg)
		h.ok("GET", "/api/v1/system/runscheduler?jobid=TorrentTransfer_TorrentTransfer", nil)
		services := h.ok("GET", "/api/plugins/services", nil)
		if !bytes.Contains(services, []byte(`"status":"failed"`)) || len(to.rows(hash)) != 0 || ownedTransferData(t, h, id)[from.Name+"-"+hash] != nil {
			t.Fatal("read failure was acknowledged without actual failed progress/no-write evidence", string(services))
		}
		h.record("actual_backup_permission_failure", map[string]any{"hash": hash, "mode": "0000", "target_absent": true, "history_absent": true, "services": json.RawMessage(services)})
		if err := os.Chmod(path, 0600); err != nil {
			t.Fatal(err)
		}
		h.ok("GET", "/api/v1/system/runscheduler?jobid=TorrentTransfer_TorrentTransfer", nil)
		key := from.Name + "-" + hash
		if len(to.rows(hash)) != 1 || ownedTransferData(t, h, id)[key] == nil || transferWorkers(h)[id] != initialPID {
			t.Fatal("same-worker EACCES recovery failed")
		}
		sourceKeys = append(sourceKeys, key)
		h.record("actual_backup_permission_recovery", map[string]any{"hash": hash, "same_pid": initialPID, "mode": "0600", "target": to.rows(hash)[0]})
		finalConfig = cfg
	}
	// This is deliberately real wall-clock execution: the original qB marker
	// lookup sleeps three seconds before its first query, once per torrent.
	// A zero-delay protocol peer cannot prove a >90s parent call stays alive.
	if os.Getenv("TORRENTTRANSFER_REAL_BATCH") != "" {
		baselineCount := len(sourceKeys)
		batchTag := "owned-" + runToken + "-real-batch"
		batch := configFor(daemons[0], daemons[1], batchTag)
		batch["skipverify"] = true
		var hashes []string
		for index := 0; index < 100; index++ {
			raw, hash := ownedTransferTorrent(t, filepath.Join(root, "payload"), fmt.Sprintf("owned-%s-real-batch-%03d.bin", runToken, index))
			writeOwnedTransferBackup(t, backup, hash, raw)
			if len(daemons[1].rows(hash)) != 0 {
				t.Fatal("batch fixture target is not empty")
			}
			daemons[0].add(raw, hash, filepath.Join(root, "payload"), batchTag)
			hashes = append(hashes, hash)
			sourceKeys = append(sourceKeys, daemons[0].Name+"-"+hash)
		}
		h.ok("PUT", "/api/plugins/"+id, batch)
		started := time.Now()
		done := make(chan struct{})
		go func() {
			defer close(done)
			h.ok("GET", "/api/v1/system/runscheduler?jobid=TorrentTransfer_TorrentTransfer", nil)
		}()
		waitTransfer(t, "real batch first three durable results", 40*time.Second, func() bool {
			return len(ownedTransferData(t, h, id)) >= baselineCount+3
		})
		var services []struct {
			Instance string `json:"instance_id"`
			Service  string `json:"service_id"`
			Status   string `json:"status"`
			CanRun   bool   `json:"can_run"`
		}
		if json.Unmarshal(h.ok("GET", "/api/plugins/services", nil), &services) != nil {
			t.Fatal("actual service list malformed")
		}
		running := false
		for _, s := range services {
			if s.Instance == id && s.Service == "TorrentTransfer" && s.Status == "正在运行" && !s.CanRun {
				running = true
			}
		}
		if !running {
			t.Fatal("batch parent service completed before its cursor")
		}
		select {
		case <-done:
			t.Fatal("original synchronous manual scheduler returned before complete batch")
		default:
		}
		h.record("real_batch_running", map[string]any{"completed": len(ownedTransferData(t, h, id)) - baselineCount, "parent_not_returned": true, "public_running": true})
		select {
		case <-done:
		case <-time.After(9 * time.Minute):
			t.Fatal("real batch manual scheduler did not finish")
		}
		data := ownedTransferData(t, h, id)
		if len(data) != baselineCount+100 {
			t.Fatalf("real batch incomplete: %d/%d data entries", len(data), baselineCount+100)
		}
		for _, hash := range hashes {
			key := daemons[0].Name + "-" + hash
			var value map[string]any
			if json.Unmarshal(data[key], &value) != nil || value["to_download_id"] != hash || len(daemons[1].rows(hash)) != 1 || len(daemons[0].rows(hash)) != 1 {
				t.Fatal("real batch task/history/source mismatch", hash)
			}
		}
		h.record("real_batch_completed", map[string]any{"torrents": len(hashes), "elapsed_seconds": time.Since(started).Seconds(), "hashes": hashes, "history_count": len(data), "real_source_lookup_sleep_seconds_per_torrent": 3, "all_source_tasks_preserved": true, "all_target_tasks_and_source_history_verified": true})
		finalConfig = batch
	}
	h.ok("POST", "/api/plugins/"+id+"/clone", map[string]any{"suffix": "music"})
	clonePID := transferWorkers(h)[clone]
	if clonePID == 0 || clonePID == initialPID || len(ownedTransferData(t, h, clone)) != 0 {
		t.Fatal("platform clone did not isolate identity/data")
	}
	cloneTag := "owned-" + runToken + "-clone-source"
	cloneConfig := configFor(daemons[0], daemons[1], cloneTag)
	cloneConfig["skipverify"] = "true" // Actual source wire-compatible string, not silently rejected.
	raw, hash := ownedTransferTorrent(t, filepath.Join(root, "payload"), "owned-"+runToken+"-music.bin")
	writeOwnedTransferBackup(t, backup, hash, raw)
	if len(daemons[1].rows(hash)) != 0 {
		t.Fatal("clone fixture target is not empty")
	}
	daemons[0].add(raw, hash, filepath.Join(root, "payload"), cloneTag)
	h.ok("PUT", "/api/plugins/"+clone, cloneConfig)
	h.ok("POST", "/api/plugins/services/run", map[string]any{"instance_id": clone, "service_id": "TorrentTransfer"})
	waitTransfer(t, "clone real target/history", 30*time.Second, func() bool { return len(ownedTransferData(t, h, clone)) == 1 && len(daemons[1].rows(hash)) == 1 })
	h.config(id, finalConfig)
	if len(ownedTransferData(t, h, id)) != len(sourceKeys) {
		t.Fatal("clone wrote source data namespace")
	}
	h.record("clone_isolation", map[string]any{"source_pid": initialPID, "clone_pid": clonePID, "source_data": ownedTransferData(t, h, id), "clone_data": ownedTransferData(t, h, clone)})
	// Ordinary configuration validation resets the persisted enable/once flags.
	bad := configFor(daemons[0], daemons[1], "owned-no-side-effects")
	bad["fromtorrentpath"] = filepath.Join(h.dir, "not-created")
	bad["onlyonce"] = true
	h.ok("PUT", "/api/plugins/"+id, bad)
	bad["enabled"], bad["onlyonce"] = false, false
	h.config(id, bad)
	finalConfig["enabled"] = false
	cloneConfig["enabled"] = false
	h.ok("PUT", "/api/plugins/"+id, finalConfig)
	h.ok("PUT", "/api/plugins/"+clone, cloneConfig)
	sourceData, cloneData := ownedTransferData(t, h, id), ownedTransferData(t, h, clone)
	h.ok("POST", "/api/plugins/"+id+"/reload", map[string]any{})
	if transferWorkers(h)[id] == initialPID || transferWorkers(h)[clone] != clonePID {
		t.Fatal("reload changed wrong instance PID")
	}
	install(true)
	// Updating is an explicit test manifest fixture, never an upstream release claim.
	if update := os.Getenv("TORRENTTRANSFER_UPDATE_WORKER_BINARY"); update != "" {
		newManifest, err := exec.Command(update, "--manifest").Output()
		var m map[string]any
		if err != nil || json.Unmarshal(newManifest, &m) != nil || m["plugin_id"] != id || m["version"] == version {
			t.Fatal("invalid update fixture")
		}
		newBin, err := os.ReadFile(update)
		if err != nil {
			t.Fatal(err)
		}
		repoMu.Lock()
		manifest, bin, version, artifactHash = m, newBin, m["version"].(string), fileHash(t, update)
		executableHash, artifactFormat, artifactFiles = artifactHash, "executable", nil
		repoMu.Unlock()
		install(true)
		h.record("manifest_only_update", map[string]any{"version": version, "sha256": artifactHash, "not_upstream_release": true})
	}
	h.config(id, finalConfig)
	h.config(clone, cloneConfig)
	if os.Getenv("TORRENTTRANSFER_UI_WAIT") != "" {
		public := os.Getenv("TORRENTTRANSFER_PUBLIC_URL")
		if public == "" {
			public = h.base
		}
		ready, _ := json.Marshal(map[string]any{"url": public, "username": ownedUser, "password": ownedPassword, "pid": h.cmd.Process.Pid, "continue_file": filepath.Join(h.dir, "ui-complete"), "source": id, "clone": clone})
		if err := os.WriteFile(filepath.Join(h.dir, "ui-ready.json"), ready, 0600); err != nil {
			t.Fatal(err)
		}
		h.record("ui_ready", map[string]any{"url": public, "pid": h.cmd.Process.Pid})
		waitTransfer(t, "root actual browser completion", 20*time.Minute, func() bool { _, e := os.Stat(filepath.Join(h.dir, "ui-complete")); return e == nil })
	}
	before := transferWorkers(h)
	h.stop()
	h.start()
	after := transferWorkers(h)
	for _, instance := range []string{id, clone} {
		if before[instance] == after[instance] || after[instance] == 0 {
			t.Fatal("cold restart retained old/missing worker", instance, before, after)
		}
	}
	assertData := func(instance string, want map[string]json.RawMessage) {
		t.Helper()
		a, _ := json.Marshal(ownedTransferData(t, h, instance))
		b, _ := json.Marshal(want)
		if !bytes.Equal(a, b) {
			t.Fatal("durable data changed unexpectedly", instance, string(a), string(b))
		}
	}
	assertData(id, sourceData)
	assertData(clone, cloneData)
	h.config(id, finalConfig)
	h.config(clone, cloneConfig)
	h.ok("POST", "/api/plugins/"+clone+"/reset", map[string]any{})
	if len(ownedTransferData(t, h, clone)) != 0 {
		t.Fatal("reset retained clone data")
	}
	assertData(id, sourceData)
	h.ok("DELETE", "/api/plugins/"+clone, nil)
	if _, err := os.Stat(filepath.Join(h.dir, "plugin-packages", clone)); !os.IsNotExist(err) {
		t.Fatal("clone code retained after uninstall", err)
	}
	assertData(id, sourceData)
	h.ok("DELETE", "/api/plugins/"+id, nil)
	install(false)
	h.config(id, finalConfig)
	// Actual MP uninstall only deletes config/KV/code for is_clone. A base
	// plugin retains configuration and history for reinstall.
	assertData(id, sourceData)
	sort.Strings(sourceKeys)
	h.record("acceptance_completed", map[string]any{"source_history_keys": sourceKeys, "cold_before": before, "cold_after": after, "scope": "actual main, four owned real daemons, synthetic torrent/payload files only; not private configuration migration or production deployment"})
}
