//go:build removelink_business_acceptance

package integration

// This separately tagged driver uses ordinary cmd/server, the unchanged real
// RemoveLink worker, public import APIs and a real OwnedNotice module/receiver.
// Only synthetic cache/routing fixtures are seeded with Main stopped. It does
// not import App, replace HostCaller or write history/delete results directly.
import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
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
	"syscall"
	"testing"
	"time"
)

const rmBizNoticeID = "OwnedNotice"
const rmBizRecipient = "owned-removelink-recipient"

type rmBizHistory struct {
	ID     string `json:"id"`
	PlanID string `json:"plan_id"`
	Source string `json:"source"`
	Target string `json:"target"`
	Status string `json:"status"`
}
type rmBizPlan struct {
	ID    string `json:"id"`
	Files []struct {
		ID     string `json:"id"`
		Source string `json:"source"`
		Target string `json:"target"`
		Status string `json:"status"`
		Error  string `json:"error"`
	} `json:"files"`
}

func rmBizNotice(raw json.RawMessage, title, text string) error {
	var body struct {
		Kwargs struct {
			Message struct {
				Title   string            `json:"title"`
				Text    string            `json:"text"`
				MType   string            `json:"mtype"`
				Targets map[string]string `json:"targets"`
			} `json:"message"`
		} `json:"kwargs"`
	}
	if e := json.Unmarshal(raw, &body); e != nil {
		return e
	}
	m := body.Kwargs.Message
	if m.Title != title || m.Text != text || m.MType != "站点" || m.Targets["Telegram"] != rmBizRecipient {
		return fmt.Errorf("unexpected actual module delivery title/type/text/recipient")
	}
	return nil
}

// Exact host crypto formats from noticeID/noticeSeal/PluginStore.seal. The
// private app key never leaves memory, argv or this owned private data dir.
func rmBizPreference(key []byte, kind, name string, value any) (string, []byte, error) {
	if len(key) != 32 {
		return "", nil, errors.New("owned key length")
	}
	vars, _ := json.Marshal([]any{kind, name})
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte("plugin-notice/v1/preference\x00"))
	mac.Write(vars)
	token := hex.EncodeToString(mac.Sum(nil))
	plain, e := json.Marshal(map[string]any{"Kind": kind, "Key": name, "Value": value})
	if e != nil {
		return "", nil, e
	}
	block, e := aes.NewCipher(key)
	if e != nil {
		return "", nil, e
	}
	g, e := cipher.NewGCM(block)
	if e != nil {
		return "", nil, e
	}
	nonce := make([]byte, g.NonceSize())
	if _, e = rand.Read(nonce); e != nil {
		return "", nil, e
	}
	aad, _ := json.Marshal([]string{"light-media/plugins/v1", "notice_journal", token, "preference"})
	return token, g.Seal(nonce, nonce, plain, aad), nil
}
func rmBizSeed(t *testing.T, s *rmMain) {
	t.Helper()
	if s.cmd != nil {
		t.Fatal("fixture seed requires stopped ordinary Main")
	}
	marker, e := os.ReadFile(filepath.Join(s.root, ".task-owned"))
	if e != nil || string(marker) != rmOwnerMarker {
		t.Fatal("owned marker required before fixture seed")
	}
	for _, name := range []string{"secret.key", "light-media.db", "instance.lock"} {
		f := filepath.Join(s.dir, name)
		st, e := os.Lstat(f)
		if e != nil || !st.Mode().IsRegular() || st.Mode()&os.ModeSymlink != 0 {
			t.Fatal("owned regular fixture path", name, e)
		}
	}
	if st, e := os.Stat(filepath.Join(s.dir, "secret.key")); e != nil || st.Mode().Perm() != 0600 {
		t.Fatal("owned secret key must remain private0600")
	}
	if e := os.Chmod(filepath.Join(s.dir, "light-media.db"), 0600); e != nil {
		t.Fatal(e)
	}
	lock, e := os.OpenFile(filepath.Join(s.dir, "instance.lock"), os.O_RDWR, 0600)
	if e != nil {
		t.Fatal(e)
	}
	defer lock.Close()
	if e = syscall.Flock(int(lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		t.Fatal("Main still owns DB lock", e)
	}
	defer syscall.Flock(int(lock.Fd()), syscall.LOCK_UN)
	key, e := os.ReadFile(filepath.Join(s.dir, "secret.key"))
	if e != nil {
		t.Fatal(e)
	}
	defer func() {
		for i := range key {
			key[i] = 0
		}
	}()
	rows := []map[string]any{}
	for _, x := range []struct {
		kind, name string
		value      any
	}{{"switch", "站点", "admin"}, {"user", rmUser, map[string]any{"Telegram": rmBizRecipient}}, {"window", "", []any{}}} {
		token, sealed, e := rmBizPreference(key, x.kind, x.name, x.value)
		if e != nil {
			t.Fatal(e)
		}
		rows = append(rows, map[string]any{"kind": x.kind, "token": token, "sealed": base64.StdEncoding.EncodeToString(sealed)})
	}
	caches := []map[string]any{}
	for i := int64(770001); i <= 770004; i++ {
		value := map[string]any{"at": time.Now().UTC(), "data": map[string]any{"id": i, "media_type": "movie", "title": fmt.Sprintf("Owned business %d", i), "original_title": "Owned business", "year": 2024, "original_language": "en", "origin_country": []string{"US"}, "category_metadata_known": true, "genres": []any{}, "cast": []any{}}}
		caches = append(caches, map[string]any{"id": fmt.Sprintf("media:movie:%d", i), "value": value})
	}
	data, _ := json.Marshal(map[string]any{"preferences": rows, "caches": caches})
	script := `import sys,json,sqlite3,base64,datetime
x=json.load(sys.stdin)
c=sqlite3.connect(sys.argv[1]);c.execute('PRAGMA busy_timeout=5000')
assert c.execute('select count(*) from admin').fetchone()[0]==1
with c:
 for r in x['preferences']: c.execute('INSERT INTO plugin_notice_preferences(kind,token,sealed) VALUES(?,?,?) ON CONFLICT(kind,token) DO UPDATE SET sealed=excluded.sealed',(r['kind'],r['token'],base64.b64decode(r['sealed'])))
 for r in x['caches']: c.execute('INSERT INTO records(kind,id,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at',('cache',r['id'],json.dumps(r['value'],ensure_ascii=False,separators=(',',':')),datetime.datetime.now(datetime.timezone.utc).isoformat()))
c.close();print(json.dumps({'synthetic_cache_rows':len(x['caches']),'encrypted_notice_preferences':len(x['preferences'])}))`
	cmd := exec.Command("python3", "-c", script, filepath.Join(s.dir, "light-media.db"))
	cmd.Stdin = bytes.NewReader(data)
	out, e := cmd.CombinedOutput()
	if e != nil {
		t.Fatal("owned stopped-Main fixture seed", e)
	}
	s.record("rm_business_fixture_seed", map[string]any{"classification": "test environment preparation with Main stopped/own exclusive lock; not public UI configuration acceptance", "result": json.RawMessage(out), "metadata_network": "synthetic fresh catalog cache; no real TMDB", "routing": "站点 to owned user/Telegram recipient; no production channel", "private_key_or_DB_published": false})
}
func rmBizRows(t *testing.T, s *rmMain) []rmBizHistory {
	t.Helper()
	var page struct {
		Items []rmBizHistory `json:"items"`
		Total int            `json:"total"`
	}
	raw := s.ok("GET", "/api/history/transfers?page_size=100", nil)
	if json.Unmarshal(raw, &page) != nil || page.Total != len(page.Items) {
		t.Fatal("actual history page", string(raw))
	}
	return page.Items
}
func rmBizHas(rows []rmBizHistory, id string) bool {
	for _, r := range rows {
		if r.ID == id {
			return true
		}
	}
	return false
}
func rmBizImport(t *testing.T, s *rmMain, source, target string, id int64) rmBizHistory {
	t.Helper()
	rmWrite(t, source)
	if e := os.MkdirAll(target, 0700); e != nil {
		t.Fatal(e)
	}
	raw := s.ok("POST", "/api/import/preview", map[string]any{"media_type": "movie", "tmdb_id": id, "target_path": target, "mode": "hardlink", "renaming": false, "scraping": false, "library_type_folder": false, "files": []any{map[string]any{"path": source}}})
	var plan rmBizPlan
	if json.Unmarshal(raw, &plan) != nil || plan.ID == "" || len(plan.Files) != 1 || plan.Files[0].Status != "ready" {
		t.Fatal("real public import preview not ready", string(raw))
	}
	submitted := s.ok("POST", "/api/import/execute", map[string]any{"plan_id": plan.ID})
	var job struct {
		ID string `json:"id"`
	}
	if json.Unmarshal(submitted, &job) != nil || job.ID == "" {
		t.Fatal("real import submission", string(submitted))
	}
	var current rmBizPlan
	rmWait(t, "real public import job and SQLitehistory", 30*time.Second, func() bool {
		var plans []rmBizPlan
		if json.Unmarshal(s.ok("GET", "/api/import/plans", nil), &plans) != nil {
			t.Fatal("import plan response")
		}
		for _, v := range plans {
			if v.ID == plan.ID {
				current = v
			}
		}
		return len(current.Files) == 1 && (current.Files[0].Status == "imported" || current.Files[0].Status == "already_imported" || current.Files[0].Status == "error")
	})
	if current.Files[0].Status == "error" {
		t.Fatal("ordinary import failed", current.Files[0].Error)
	}
	rmWait(t, "public import job final success", 30*time.Second, func() bool {
		var state struct {
			Job struct {
				State string `json:"state"`
			} `json:"job"`
		}
		raw := s.ok("GET", "/api/jobs/"+job.ID, nil)
		if json.Unmarshal(raw, &state) != nil {
			t.Fatal("job status JSON")
		}
		if state.Job.State == "failed" {
			t.Fatal("import job failed", string(raw))
		}
		return state.Job.State == "succeeded"
	})
	for _, row := range rmBizRows(t, s) {
		if row.Source == source {
			if row.Status != "success" || row.Target != current.Files[0].Target || row.PlanID != plan.ID {
				t.Fatal("actual import/history identity mismatch", row)
			}
			a, e := os.Stat(source)
			if e != nil {
				t.Fatal(e)
			}
			b, e := os.Stat(row.Target)
			if e != nil || !os.SameFile(a, b) {
				t.Fatal("public import did not create real hardlink", e)
			}
			s.record("rm_business_public_import", map[string]any{"history": row, "job_id": job.ID, "source_and_target_same_inode": true})
			return row
		}
	}
	t.Fatal("submitted successful import has no exact source history", source)
	return rmBizHistory{}
}
func rmBizPhysical(t *testing.T, paths []string) map[string]string {
	t.Helper()
	out := map[string]string{}
	for _, p := range paths {
		b, e := os.ReadFile(p)
		if e != nil {
			t.Fatal(e)
		}
		sum := sha256.Sum256(b)
		out[p] = hex.EncodeToString(sum[:])
	}
	return out
}
func rmBizPreserved(t *testing.T, want map[string]string) {
	t.Helper()
	for p, sum := range want {
		b, e := os.ReadFile(p)
		if e != nil {
			t.Fatal("unrelated physical removed", p, e)
		}
		got := sha256.Sum256(b)
		if hex.EncodeToString(got[:]) != sum {
			t.Fatal("unrelated physical changed", p)
		}
	}
}
func rmBizMissing(paths []string) bool {
	for _, p := range paths {
		if rmExists(p) {
			return false
		}
	}
	return true
}
func rmBizIndexSnapshot(t *testing.T, s *rmMain) map[string]string {
	t.Helper()
	script := `import sys,sqlite3,json,hashlib
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
out={}
for kind,id,payload in c.execute("SELECT kind,id,payload FROM records WHERE kind IN ('asset','managed_file','import_plan') ORDER BY kind,id"):
 if isinstance(payload,str): payload=payload.encode()
 out[kind+'/'+id]=hashlib.sha256(payload).hexdigest()
c.close();print(json.dumps(out))`
	out, e := exec.Command("python3", "-c", script, filepath.Join(s.dir, "light-media.db")).CombinedOutput()
	if e != nil {
		t.Fatal("readonly owned index snapshot", e)
	}
	var rows map[string]string
	if json.Unmarshal(out, &rows) != nil {
		t.Fatal("index snapshot JSON")
	}
	return rows
}

func rmBizAudit(t *testing.T, s *rmMain, selected, unrelated []rmBizHistory) {
	t.Helper()
	var plans []rmBizPlan
	if json.Unmarshal(s.ok("GET", "/api/import/plans", nil), &plans) != nil {
		t.Fatal("audit plans")
	}
	planIDs := map[string]bool{}
	for _, p := range plans {
		planIDs[p.ID] = true
	}
	for _, x := range append(append([]rmBizHistory{}, selected...), unrelated...) {
		if !planIDs[x.PlanID] {
			t.Fatal("history removal erased audit import plan", x.PlanID)
		}
	}
	script := `import sys,sqlite3,json
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
print(json.dumps({'hidden_ids':[r[0] for r in c.execute("SELECT id FROM records WHERE kind='transfer_history_hidden' ORDER BY id")],'plan_ids':[r[0] for r in c.execute("SELECT id FROM records WHERE kind='import_plan' ORDER BY id")],'assets':[{'id':v.get('id'),'path':v.get('path'),'state':v.get('state')} for v in (json.loads(r[0]) for r in c.execute("SELECT payload FROM records WHERE kind='asset'"))],'managed':[{'path':v.get('path'),'asset_id':v.get('asset_id')} for v in (json.loads(r[0]) for r in c.execute("SELECT payload FROM records WHERE kind='managed_file'"))],'pending_notice_rows':c.execute("SELECT count(*) FROM plugin_message_queue WHERE state='queued'").fetchone()[0]}));c.close()`
	out, e := exec.Command("python3", "-c", script, filepath.Join(s.dir, "light-media.db")).CombinedOutput()
	if e != nil {
		t.Fatal("readonly owned SQLite audit", e)
	}
	var db struct {
		Hidden []string `json:"hidden_ids"`
		Plans  []string `json:"plan_ids"`
		Assets []struct {
			ID    string `json:"id"`
			Path  string `json:"path"`
			State string `json:"state"`
		} `json:"assets"`
		Managed []struct {
			Path    string `json:"path"`
			AssetID string `json:"asset_id"`
		} `json:"managed"`
		Pending int `json:"pending_notice_rows"`
	}
	if json.Unmarshal(out, &db) != nil {
		t.Fatal("SQLite audit JSON")
	}
	for _, x := range selected {
		found := false
		for _, id := range db.Hidden {
			if id == x.ID {
				found = true
			}
		}
		if !found {
			t.Fatal("real Rlk SDK delete did not persist history hidden identity", x.ID)
		}
	}
	for _, x := range unrelated {
		for _, id := range db.Hidden {
			if id == x.ID {
				t.Fatal("unrelated history hidden", x.ID)
			}
		}
	}
	for _, x := range selected {
		assetFound, managedFound := false, false
		for _, a := range db.Assets {
			if a.Path == x.Target {
				assetFound = true
			}
		}
		for _, m := range db.Managed {
			if m.Path == x.Target {
				managedFound = true
			}
		}
		if !assetFound || !managedFound {
			t.Fatal("standalone storage deleted asset/managed index", x.Target, assetFound, managedFound)
		}
	}
	if db.Pending != 0 {
		t.Fatal("success receipt still queued", db.Pending)
	}
	s.record("rm_business_sqlite_audit", json.RawMessage(out))
}

func rmBizAllWorkerPIDs(t *testing.T, s *rmMain) map[int]string {
	t.Helper()
	if s.cmd == nil {
		t.Fatal("worker snapshot requires live Main")
	}
	out := map[int]string{}
	entries, e := os.ReadDir("/proc")
	if e != nil {
		t.Fatal(e)
	}
	for _, x := range entries {
		pid, e := strconv.Atoi(x.Name())
		if e != nil {
			continue
		}
		raw, e := os.ReadFile(filepath.Join("/proc", x.Name(), "stat"))
		if e != nil {
			continue
		}
		at := strings.LastIndex(string(raw), ") ")
		if at < 0 {
			continue
		}
		fields := strings.Fields(string(raw)[at+2:])
		if len(fields) < 2 || fields[1] != strconv.Itoa(s.cmd.Process.Pid) {
			continue
		}
		cmd, e := os.ReadFile(filepath.Join("/proc", x.Name(), "cmdline"))
		if e != nil {
			continue
		}
		prefix := filepath.Join(s.dir, "plugin-packages") + "/"
		at = strings.Index(string(cmd), prefix)
		if at < 0 {
			continue
		}
		id := strings.SplitN(string(cmd)[at+len(prefix):], "/", 2)[0]
		out[pid] = id
	}
	s.record("rm_business_all_worker_pids", out)
	return out
}

func TestRemoveLinkBusinessNoticeContracts(t *testing.T) {
	good := map[string]any{"kwargs": map[string]any{"message": map[string]any{"mtype": "站点", "title": "🧹 媒体文件清理", "text": "owned exact source summary", "targets": map[string]any{"Telegram": rmBizRecipient}}}}
	b, _ := json.Marshal(good)
	if e := rmBizNotice(b, "🧹 媒体文件清理", "owned exact source summary"); e != nil {
		t.Fatal(e)
	}
	for _, field := range []string{"mtype", "title", "text", "targets"} {
		t.Run(field, func(t *testing.T) {
			var v map[string]any
			json.Unmarshal(b, &v)
			v["kwargs"].(map[string]any)["message"].(map[string]any)[field] = "wrong"
			raw, _ := json.Marshal(v)
			if rmBizNotice(raw, "🧹 媒体文件清理", "owned exact source summary") == nil {
				t.Fatal("incorrect actual notice accepted", field)
			}
		})
	}
}
func TestRemoveLinkBusinessActualMain(t *testing.T) {
	if os.Getenv("REMOVELINK_BUSINESS_MAIN") != "1" {
		t.Skip("opt-in separate business Main not executed")
	}
	if runtime.GOOS != "linux" || os.Geteuid() == 0 {
		t.Fatal("owned Linux UID1000 required")
	}
	for _, key := range []string{"REMOVELINK_HOST_BINARY", "REMOVELINK_EXPECT_HOST_SHA256", "REMOVELINK_WORKER_BINARY", "REMOVELINK_EXPECT_WORKER_SHA256", "REMOVELINK_FRONTEND_DIR", "REMOVELINK_RUNTIME_DIR", "REMOVELINK_NOTICE_WORKER_BINARY", "REMOVELINK_EXPECT_NOTICE_SHA256"} {
		if os.Getenv(key) == "" {
			t.Fatal("required exact owned business input", key)
		}
	}
	worker, notice := os.Getenv("REMOVELINK_WORKER_BINARY"), os.Getenv("REMOVELINK_NOTICE_WORKER_BINARY")
	if fileHash(t, worker) != os.Getenv("REMOVELINK_EXPECT_WORKER_SHA256") || fileHash(t, notice) != os.Getenv("REMOVELINK_EXPECT_NOTICE_SHA256") {
		t.Fatal("actual business worker hashes differ from explicit expected values")
	}
	release := rmLoadRelease(t, worker, os.Getenv("REMOVELINK_FRONTEND_DIR"))
	if release.version != "2.18" {
		t.Fatal("current production Rlk2.18 required")
	}
	noticeRelease := puiLoad(t, notice, rmBizNoticeID, 0)
	s := rmNewMain(t)
	s.stop()
	rmBizSeed(t, s)
	s.startRM()
	// Generate real SQLite histories through public preview/execute, before
	// installing any module provider that changes source recognition routing.
	hard := filepath.Join(s.files, "hardlink")
	src := filepath.Join(hard, "source", "OwnedSource.1080p.mkv")
	library := filepath.Join(hard, "library")
	selectedSrc := rmBizImport(t, s, src, library, 770001)
	unrelatedSrc := rmBizImport(t, s, filepath.Join(hard, "source", "OwnedSource.1080p-extra.mkv"), library, 770002)
	strmDir := filepath.Join(s.files, "strm")
	remoteDir := filepath.Join(s.files, "strm-media")
	destSource := filepath.Join(s.files, "import-source", "OwnedFilm.1080p.mkv")
	selectedDest := rmBizImport(t, s, destSource, remoteDir, 770003)
	unrelatedDest := rmBizImport(t, s, filepath.Join(s.files, "import-source", "UnrelatedFilm.mkv"), remoteDir, 770004)
	library = filepath.Dir(selectedSrc.Target)
	remoteDir = filepath.Dir(selectedDest.Target)
	if filepath.Base(selectedDest.Target) != "OwnedFilm.1080p.mkv" {
		t.Fatal("preserved filename fixture required for exact STRM stem", selectedDest.Target)
	}
	beforeIndexes := rmBizIndexSnapshot(t, s)
	noticeRepo := puiRepo(t, noticeRelease)
	s.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": rmBizNoticeID, "repo_url": noticeRepo.server.URL + "/index"})
	var receiveMu sync.Mutex
	received := []json.RawMessage{}
	var receiverFailed atomic.Int64
	sink := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b, e := io.ReadAll(io.LimitReader(r.Body, 1<<20))
		if e != nil || r.Method != "POST" || !json.Valid(b) {
			receiverFailed.Add(1)
			w.WriteHeader(400)
			return
		}
		receiveMu.Lock()
		received = append(received, append(json.RawMessage(nil), b...))
		receiveMu.Unlock()
		s.record("rm_business_actual_notice_receiver", json.RawMessage(b))
		w.WriteHeader(204)
	}))
	defer sink.Close()
	s.ok("PUT", "/api/plugins/"+rmBizNoticeID, map[string]any{"enabled": true, "endpoint": sink.URL, "fail": false, "event_delay_ms": 0})
	repo := rmRepo(t, release)
	s.installRM(repo, false)
	pid := s.workersRM()[rmSource]
	if pid == 0 {
		t.Fatal("real installed RemoveLink worker missing")
	}
	s.record("rm_business_inputs", map[string]any{"host_sha256": fileHash(t, s.binary), "Rlk_sha256": release.workerHash, "notice_sha256": noticeRelease.hash, "source_case": "hardlink exactsrc + STRM exactdest, real public-import SQLite history, real module receiver", "source_business_network": "none; synthetic cache only"})
	// Initial source and alias scraps exercise exact complete-stem matching;
	// empty child has only two scrap files, while parent negatives prevent an
	// incidental empty-folder sweep from hiding wrong custom-suffix matching.
	child := filepath.Join(library, "cleanup-child")
	childAlias := filepath.Join(child, "ChildAlias.mkv")
	if e := os.MkdirAll(child, 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.Link(src, childAlias); e != nil {
		t.Fatal(e)
	}
	removed := []string{selectedSrc.Target, childAlias, child}
	for _, base := range []string{src, selectedSrc.Target} {
		stem := strings.TrimSuffix(base, filepath.Ext(base))
		for _, suffix := range []string{".nfo", ".OWN", "-mediainfo.JSON"} {
			x := stem + suffix
			rmWrite(t, x)
			removed = append(removed, x)
		}
	}
	for _, base := range []string{src, selectedSrc.Target} {
		dir := strings.TrimSuffix(base, filepath.Ext(base)) + ".trickplay"
		rmWrite(t, filepath.Join(dir, "nested", "frame.jpg"))
		removed = append(removed, dir)
	}
	for _, suffix := range []string{".nfo", ".OWN"} {
		rmWrite(t, filepath.Join(child, "ChildAlias"+suffix))
	}
	keep := []string{filepath.Join(hard, "source", "keep.bin"), filepath.Join(hard, "source", "Other.OWN"), filepath.Join(library, "keep.bin"), filepath.Join(library, "Other.OWN"), unrelatedSrc.Source, unrelatedSrc.Target, destSource, unrelatedDest.Source, unrelatedDest.Target}
	for _, x := range keep[:4] {
		rmWrite(t, x)
	}
	for _, dir := range []string{filepath.Join(filepath.Dir(src), "Other.trickplay"), filepath.Join(library, "Other.trickplay")} {
		control := filepath.Join(dir, "keep.bin")
		rmWrite(t, control)
		keep = append(keep, control)
	}
	preserved := rmBizPhysical(t, keep)
	cfg := rmConfig(hard, false)
	cfg["notify"] = true
	cfg["delete_history"] = true
	cfg["delete_torrents"] = true
	cfg["delete_scrap_infos"] = true
	cfg["custom_scrap_extensions"] = "OWN，-mediainfo.JSON"
	s.configRM(rmSource, cfg)
	if e := os.Remove(src); e != nil {
		t.Fatal(e)
	}
	s.record("rm_business_external_source_delete", map[string]any{"source": src})
	rmWait(t, "Rlk actual src match/delete/scrap/emptychild", 20*time.Second, func() bool { return rmBizMissing(removed) && !rmBizHas(rmBizRows(t, s), selectedSrc.ID) })
	rmBizPreserved(t, preserved)
	if !rmBizHas(rmBizRows(t, s), unrelatedSrc.ID) {
		t.Fatal("source-prefix unrelated row deleted")
	}
	hardText := "⚡ 立即删除完成\n\n🗂️ 源文件：" + src + "\n🔗 删除了 2 个硬链接文件\n📝 已清理转移记录\n🌱 已联动删除种子\n🖼️ 已清理刮削文件"
	directoryText := "🗑️ 清理空目录：" + child
	rmWait(t, "two actual hardlink/directory notice receipts", 10*time.Second, func() bool { receiveMu.Lock(); defer receiveMu.Unlock(); return len(received) >= 2 })
	receiveMu.Lock()
	firstReceipts := append([]json.RawMessage(nil), received...)
	receiveMu.Unlock()
	if len(firstReceipts) != 2 {
		t.Fatal("unexpected hardlink notice count", len(firstReceipts))
	}
	matched := map[string]bool{}
	for _, b := range firstReceipts {
		if rmBizNotice(b, "🧹 媒体文件清理", hardText) == nil {
			matched["summary"] = true
		} else if rmBizNotice(b, "📁 目录清理", directoryText) == nil {
			matched["directory"] = true
		} else {
			t.Fatal("unexpected hardlink source notice", string(b))
		}
	}
	if !matched["summary"] || !matched["directory"] {
		t.Fatal("missing actual success notice type")
	}
	s.record("rm_business_hardlink_complete", map[string]any{"deleted_exact_source_history": selectedSrc, "unrelated_history_retained": unrelatedSrc, "aliases_deleted": 2, "empty_child_removed": child, "notice_success_receipts": 2, "source_event": "src-only without hash; summary text is not proof of real torrent deletion"})
	// STRM lookup must select an actual history by the mapped video's target.
	strm := filepath.Join(strmDir, "OwnedFilm.strm")
	rmWrite(t, strm)
	strmRemoved := []string{selectedDest.Target}
	for _, suffix := range []string{".nfo", ".OWN", "-mediainfo.JSON"} {
		x := filepath.Join(strmDir, "OwnedFilm"+suffix)
		rmWrite(t, x)
		strmRemoved = append(strmRemoved, x)
	}
	for _, suffix := range []string{".nfo", ".OWN", "-mediainfo.JSON"} {
		x := strings.TrimSuffix(selectedDest.Target, ".mkv") + suffix
		rmWrite(t, x)
		strmRemoved = append(strmRemoved, x)
	}
	poster := filepath.Join(remoteDir, "poster.jpg")
	rmWrite(t, poster)
	strmRemoved = append(strmRemoved, poster)
	strmKeep := []string{filepath.Join(strmDir, "keep.bin"), filepath.Join(strmDir, "Other.OWN"), filepath.Join(remoteDir, "keep.bin"), filepath.Join(remoteDir, "Other.OWN"), filepath.Join(remoteDir, "OwnedFilm.nfo"), destSource, unrelatedDest.Source, unrelatedDest.Target}
	for _, x := range strmKeep[:5] {
		rmWrite(t, x)
	}
	strmPreserved := rmBizPhysical(t, strmKeep)
	strmCfg := rmConfig("", false)
	strmCfg["notify"] = true
	strmCfg["delete_history"] = true
	strmCfg["delete_scrap_infos"] = true
	strmCfg["custom_scrap_extensions"] = "OWN，-mediainfo.JSON"
	strmCfg["monitor_strm_deletion"] = true
	strmCfg["strm_path_mappings"] = strmDir + ":local:" + remoteDir
	s.configRM(rmSource, strmCfg)
	if s.workersRM()[rmSource] != pid {
		t.Fatal("same-instance reconfiguration replaced Rlk worker")
	}
	if e := os.Remove(strm); e != nil {
		t.Fatal(e)
	}
	rmWait(t, "Rlk actual STRM dest history/scrap", 20*time.Second, func() bool { return rmBizMissing(strmRemoved) && !rmBizHas(rmBizRows(t, s), selectedDest.ID) })
	rmBizPreserved(t, strmPreserved)
	rows := rmBizRows(t, s)
	if !rmBizHas(rows, unrelatedDest.ID) || !rmBizHas(rows, unrelatedSrc.ID) {
		t.Fatal("unrelated src/dest history changed")
	}
	strmText := "✅ 清理完成\n\n🗂️ STRM 文件：" + strm + "\n🗑️ 已删除网盘文件：[local] " + selectedDest.Target + "\n📝 已清理转移记录\n🖼️ 已清理刮削文件（本地+网盘 4 个）"
	rmWait(t, "actual STRM notice receiver", 10*time.Second, func() bool { receiveMu.Lock(); defer receiveMu.Unlock(); return len(received) >= 3 })
	receiveMu.Lock()
	all := append([]json.RawMessage(nil), received...)
	receiveMu.Unlock()
	if len(all) != 3 || rmBizNotice(all[2], "🧹 媒体文件清理", strmText) != nil || receiverFailed.Load() != 0 {
		t.Fatal("actual STRM notice/receiver failure count", len(all), receiverFailed.Load())
	}
	rmBizAudit(t, s, []rmBizHistory{selectedSrc, selectedDest}, []rmBizHistory{unrelatedSrc, unrelatedDest})
	afterIndexes := rmBizIndexSnapshot(t, s)
	if !puiEqual(beforeIndexes, afterIndexes) {
		t.Fatal("storage cleanup changed retained asset/managed/audit payloads")
	}
	s.record("rm_business_index_retention", map[string]any{"before": beforeIndexes, "after": afterIndexes, "asset_managed_file_import_plan_payloads_byte_identical": true, "physical_deletion_is_not_index_removal": true})
	s.noInheritedModuleDiscovery("business-chain")
	appLog, e := os.ReadFile(filepath.Join(s.dir, "logs", "app.jsonl"))
	if e != nil {
		t.Fatal(e)
	}
	for _, event := range []string{"notification_failed", "module_call_failed"} {
		if bytes.Contains(appLog, []byte(`"event":"`+event+`"`)) {
			t.Fatal("real notice module failure in complete log", event)
		}
	}
	s.record("rm_business_strm_complete", map[string]any{"deleted_exact_dest_history": selectedDest, "unrelated_history_retained": unrelatedDest, "custom_suffixes": ".own/-mediainfo.json", "short_nfo_retained": filepath.Join(remoteDir, "OwnedFilm.nfo"), "remote_scraps_deleted": 4, "actual_notice_success_total": len(all), "receiver_failure_count": receiverFailed.Load(), "audit_plans_retained": true, "ordinary_Main": true})
	allWorkers := rmBizAllWorkerPIDs(t, s)
	if len(allWorkers) != 2 {
		t.Fatal("expected exactly productionRlk + realOwnedNotice", allWorkers)
	}
	s.stop()
	for p := range allWorkers {
		s.waitWorkerGone(p)
	}
	s.record("rm_business_complete", map[string]any{"two_real_history_selectors": "src,dest", "real_OwnedNotice_module_to_loopback": true, "source_only_fixture_seed": "catalog cache and encrypted routing before Main, never history/worker effect", "real_torrent_deletion": "not asserted; only source src event without hash", "all_observed_workers_joined": len(allWorkers)})
}
