package integration

// Real cmd/server composition with owned native HTTP/TLS peers. The qB peer
// implements source query protocol only; it is explicitly not a qB daemon.
import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
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

const sdkImpactMarker = "light-media-plugins/SDK98Impact/20261105/owned-only"

var sdkImpactInstances = []string{"CategoryEditor", "TorrentTransfer", "TorrentTransfermusic", "SiteStatistic"}

func sdkImpactStart(s *ssMain, home string) {
	s.generation++
	f, e := os.Create(filepath.Join(s.evidence, fmt.Sprintf("host-%d.log", s.generation)))
	if e != nil {
		s.t.Fatal(e)
	}
	s.log = f
	cmd := exec.Command(s.binary, "--listen", s.addr, "--data-dir", s.dir)
	cmd.Env = append(s.environment(), "HOME="+home)
	cmd.Stdout = f
	cmd.Stderr = f
	if e = cmd.Start(); e != nil {
		s.t.Fatal(e)
	}
	s.cmd = cmd
	done := make(chan error, 1)
	s.wait = done
	go func() { done <- cmd.Wait() }()
	ssWait(s.t, "SDK98 actual Main health", 30*time.Second, func() bool {
		r, e := s.client.Get(s.base + "/healthz")
		if e != nil {
			return false
		}
		r.Body.Close()
		return r.StatusCode == 200
	})
	s.okSS("POST", "/api/auth/login", map[string]any{"username": ownedUser, "password": ownedPassword})
	s.record("sdk98_main_start", map[string]any{"pid": cmd.Process.Pid, "main_sha256": fileHash(s.t, s.binary), "HOME": "owned metadata path; no other provider environment inherited"})
}
func sdkImpactMain(t *testing.T, ctx context.Context, dir string, peer *ssPeer) *ssMain {
	t.Helper()
	ev := filepath.Join(dir, "evidence")
	if e := os.MkdirAll(ev, 0700); e != nil {
		t.Fatal(e)
	}
	events, e := os.OpenFile(filepath.Join(ev, "observations.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
	if e != nil {
		t.Fatal(e)
	}
	addr := os.Getenv("SDK98_IMPACT_LISTEN")
	if addr == "" {
		addr = "127.0.0.1:36257"
	}
	base := strings.Replace(addr, "0.0.0.0:", "127.0.0.1:", 1)
	jar, _ := cookiejar.New(nil)
	s := &ssMain{mainHost: &mainHost{t: t, binary: os.Getenv("SDK98_IMPACT_HOST_BINARY"), dir: dir, evidence: ev, addr: addr, base: "http://" + base, client: &http.Client{Jar: jar, Timeout: 90 * time.Second, Transport: &http.Transport{Proxy: nil}}, events: events}, ctx: ctx, caFile: peer.caFile, token: ssRandom(t)}
	s.secrets = []string{s.token, peer.cookie[ssTargets[0]], peer.cookie[ssTargets[1]]}
	home := filepath.Join(dir, "owned-home")
	if e = os.MkdirAll(home, 0700); e != nil {
		t.Fatal(e)
	}
	settings := map[string]any{"plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0, "read_site_messages": false, "allowed_roots": []string{dir}, "proxy_host": peer.proxy.URL, "api_token": s.token}
	body, _ := json.Marshal(map[string]any{"username": ownedUser, "password": ownedPassword, "settings": settings})
	cmd := exec.CommandContext(ctx, s.binary, "--data-dir", dir, "--bootstrap-stdin")
	cmd.Env = append(s.environment(), "HOME="+home)
	cmd.Stdin = bytes.NewReader(body)
	out, e := cmd.CombinedOutput()
	s.record("sdk98_bootstrap", map[string]any{"success": e == nil, "output_bytes": len(out), "credentials": "owned in-memory stdin, not recorded"})
	if e != nil {
		t.Fatal("bootstrap", e)
	}
	t.Cleanup(func() { s.stop(); events.Close() })
	sdkImpactStart(s, home)
	return s
}
func sdkImpactPIDs(t *testing.T, s *ssMain) map[string]int {
	t.Helper()
	dirs, e := os.ReadDir("/proc")
	if e != nil {
		t.Fatal(e)
	}
	out := map[string]int{}
	for _, d := range dirs {
		var pid int
		if _, e = fmt.Sscan(d.Name(), &pid); e != nil {
			continue
		}
		status, e := os.ReadFile(filepath.Join("/proc", d.Name(), "status"))
		if e != nil || !bytes.Contains(status, []byte(fmt.Sprintf("PPid:\t%d\n", s.cmd.Process.Pid))) {
			continue
		}
		raw, e := os.ReadFile(filepath.Join("/proc", d.Name(), "cmdline"))
		if e != nil {
			continue
		}
		path := strings.Split(string(raw), "\x00")[0]
		for _, id := range sdkImpactInstances {
			if strings.HasPrefix(path, filepath.Join(s.dir, "plugin-packages", id)+string(filepath.Separator)) {
				out[id] = pid
			}
		}
	}
	s.record("sdk98_workers", out)
	return out
}

type sdkImpactQB struct {
	mu        sync.Mutex
	completed int
	queries   []map[string]any
	writes    []string
	server    *httptest.Server
}

func sdkImpactQBPeer(t *testing.T) *sdkImpactQB {
	p := &sdkImpactQB{}
	p.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = r.ParseForm()
		p.mu.Lock()
		defer p.mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/v2/auth/login":
			w.Header().Set("Content-Type", "text/plain")
			fmt.Fprint(w, "Ok.")
		case "/api/v2/app/version":
			w.Header().Set("Content-Type", "text/plain")
			fmt.Fprint(w, "v5.1.2")
		case "/api/v2/app/webapiVersion":
			w.Header().Set("Content-Type", "text/plain")
			fmt.Fprint(w, "2.11")
		case "/api/v2/app/preferences":
			fmt.Fprint(w, `{"save_path":"/owned/"}`)
		case "/api/v2/torrents/info":
			p.queries = append(p.queries, map[string]any{"method": r.Method, "query_filter": r.URL.Query().Get("filter"), "form_filter": r.PostForm.Get("filter"), "hashes_present": r.PostForm.Has("hashes")})
			// The actual installed vendor's torrents_info uses _post_cast(data),
			// and the fixed f7 native source path sends the same POST form.
			if r.Method == http.MethodPost && r.PostForm.Get("filter") == "completed" && !r.PostForm.Has("hashes") {
				p.completed++
			}
			fmt.Fprint(w, `[]`)
		case "/api/v2/transfer/info":
			fmt.Fprint(w, `{"connection_status":"connected","dl_info_speed":0,"up_info_speed":0}`)
		case "/api/v2/torrents/tags":
			fmt.Fprint(w, `[]`)
		default:
			p.writes = append(p.writes, r.Method+" "+r.URL.Path)
			http.Error(w, "no mutation in SDK impact peer", 409)
		}
	}))
	t.Cleanup(p.server.Close)
	return p
}
func (p *sdkImpactQB) count() int { p.mu.Lock(); defer p.mu.Unlock(); return p.completed }
func (p *sdkImpactQB) report() map[string]any {
	p.mu.Lock()
	defer p.mu.Unlock()
	return map[string]any{"classification": "owned HTTP source-qB protocol peer, not real qB daemon/full transfer proof", "completed_queries": p.completed, "info_selectors": append([]map[string]any{}, p.queries...), "unexpected_or_mutation_requests": append([]string{}, p.writes...)}
}

func TestSDK98ImpactQBPeerSourcePostSelector(t *testing.T) {
	p := sdkImpactQBPeer(t)
	response, e := http.Post(p.server.URL+"/api/v2/torrents/info", "application/x-www-form-urlencoded", strings.NewReader("filter=completed"))
	if e != nil {
		t.Fatal(e)
	}
	response.Body.Close()
	if response.StatusCode != 200 || p.count() != 1 {
		t.Fatal("actual source POST form was not counted", p.report())
	}
	response, e = http.Get(p.server.URL + "/api/v2/torrents/info?filter=completed")
	if e != nil {
		t.Fatal(e)
	}
	response.Body.Close()
	if p.count() != 1 {
		t.Fatal("URL query incorrectly counted as the source POST selector", p.report())
	}
}
func sdkImpactTTConfig(from, to, backup string, once bool) map[string]any {
	return map[string]any{"enabled": true, "onlyonce": once, "cron": "0 0 1 1 *", "notify": false, "nolabels": "", "includelabels": "", "includecategory": "", "frompath": "", "topath": "", "fromdownloader": from, "todownloader": to, "deletesource": false, "deleteduplicate": false, "fromtorrentpath": backup, "nopaths": "", "autostart": false, "skipverify": false, "transferemptylabel": false, "add_torrent_tags": "", "remainoldcat": false, "remainoldtag": true}
}
func TestSDK98ImpactOrdinaryMainFourInstances(t *testing.T) {
	if os.Getenv("SDK98_IMPACT_HOST_BINARY") == "" {
		t.Skip("opt-in actual Linux Main4instance dependency regression; not executed by compilation")
	}
	if runtime.GOOS != "linux" || os.Getuid() != 1000 {
		t.Fatal("owned Linux uid1000 only")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Minute)
	defer cancel()
	dir := os.Getenv("SDK98_IMPACT_RUNTIME_DIR")
	if !filepath.IsAbs(dir) {
		t.Fatal("new absolute owned runtime required")
	}
	if e := os.MkdirAll(dir, 0700); e != nil {
		t.Fatal(e)
	}
	marker := filepath.Join(dir, ".task-owned")
	if raw, e := os.ReadFile(marker); e == nil {
		if string(raw) != sdkImpactMarker {
			t.Fatal("foreign marker")
		}
	} else if os.IsNotExist(e) {
		if e = os.WriteFile(marker, []byte(sdkImpactMarker), 0600); e != nil {
			t.Fatal(e)
		}
	} else {
		t.Fatal(e)
	}
	for _, n := range []string{"light-media.db", "evidence", "plugin-packages"} {
		if _, e := os.Stat(filepath.Join(dir, n)); !os.IsNotExist(e) {
			t.Fatal("fresh runtime required", n, e)
		}
	}
	peer := ssNewPeer(t, dir)
	qb := sdkImpactQBPeer(t)
	s := sdkImpactMain(t, ctx, dir, peer)
	defer func() {
		s.record("sdk98_impact_on_return", map[string]any{"test_failed": t.Failed(), "qb": qb.report(), "Nexus": peer.report()})
	}()
	for _, family := range []struct{ id, key string }{{"CategoryEditor", "SDK98_IMPACT_CATEGORY_BINARY"}, {"TorrentTransfer", "SDK98_IMPACT_TORRENT_BINARY"}, {"SiteStatistic", "SDK98_IMPACT_SITE_BINARY"}} {
		path := os.Getenv(family.key)
		if path == "" {
			t.Fatal(family.key)
		}
		release := ssLoadRelease(t, path, family.id)
		repo := ssRepo(t, release)
		s.installSS(family.id, repo, false)
	}
	s.okSS("POST", "/api/plugins/TorrentTransfer/clone", map[string]any{"suffix": "music", "name": "SDK98 impact music"})
	pids := sdkImpactPIDs(t, s)
	seen := map[int]bool{}
	for _, id := range sdkImpactInstances {
		pid := pids[id]
		if pid == 0 || seen[pid] {
			t.Fatal("four independent actual processes", pids)
		}
		seen[pid] = true
	}
	content := "movie:\n  SDK98电影: {}\ntv:\n  SDK98剧集: {}\n"
	s.okSS("PUT", "/api/plugins/CategoryEditor", map[string]any{"enabled": true, "content": content})
	s.configSS("CategoryEditor", map[string]any{"enabled": false, "content": content})
	s.categories([]string{"SDK98电影"}, []string{"SDK98剧集"})
	// Real native source HTTP queries, without a live/production daemon or any add.
	refs := []any{}
	for i, name := range []string{"SDK98 qB source", "SDK98 qB target"} {
		refs = append(refs, map[string]any{"id": fmt.Sprint("sdk98-qb-", i), "name": name, "kind": "qbittorrent", "base_url": qb.server.URL, "enabled": true})
	}
	s.okSS("PUT", "/api/settings", map[string]any{"downloaders": refs, "allowed_roots": []string{dir}, "proxy_host": peer.proxy.URL, "api_token": s.token, "plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0, "read_site_messages": false})
	backup := filepath.Join(dir, "backups")
	if e := os.MkdirAll(backup, 0700); e != nil {
		t.Fatal(e)
	}
	before := qb.count()
	configs := map[string]map[string]any{"TorrentTransfer": sdkImpactTTConfig("SDK98 qB source", "SDK98 qB target", backup, true), "TorrentTransfermusic": sdkImpactTTConfig("SDK98 qB target", "SDK98 qB source", backup, true)}
	for _, id := range []string{"TorrentTransfer", "TorrentTransfermusic"} {
		s.okSS("PUT", "/api/plugins/"+id, configs[id])
		configs[id]["onlyonce"] = false
		s.configSS(id, configs[id])
		form := s.okSS("GET", "/api/plugins/"+id+"/form", nil)
		if !bytes.Contains(form, []byte("SDK98 qB source")) {
			t.Fatal("actual dynamic TT form")
		}
	}
	ssWait(t, "two real private one-shot source queries", 25*time.Second, func() bool { return qb.count() >= before+2 })
	for _, id := range []string{"TorrentTransfer", "TorrentTransfermusic"} {
		s.okSS("POST", "/api/plugins/services/run", map[string]any{"instance_id": id, "service_id": "TorrentTransfer"})
	}
	if qb.count() < before+4 {
		t.Fatal("ordinary manual service did not query source")
	}
	// Actual known Nexus source chain -> SQLite -> per-site/global event -> message.
	site := map[string]any{"id": "sdk98-nexus", "name": "SDK98 owned Nexus", "kind": "nexusphp", "base_url": "https://" + ssTargets[0] + "/", "domain": "btschool.club", "cookie": peer.cookie[ssTargets[0]], "ua": "Owned-SDK98-UA", "proxy": true, "enabled": true, "pri": 1}
	s.okSS("PUT", "/api/sites/manage/sdk98-nexus", site)
	evBefore := s.dbSS().Events["*"]
	cfg := ssConfig(true, true, "all", "total")
	s.okSS("PUT", "/api/plugins/SiteStatistic", cfg)
	ssWait(t, "real source refresh_all global event", 30*time.Second, func() bool { return s.dbSS().Events["*"] > evBefore })
	cfg["onlyonce"] = false
	s.configSS("SiteStatistic", cfg)
	page := s.okSS("GET", "/api/plugins/SiteStatistic/page", nil)
	if !bytes.Contains(page, []byte("SDK98 owned Nexus")) {
		t.Fatal("source SQLite page missing owned account")
	}
	dashboard := s.okSS("GET", "/api/plugins/SiteStatistic/dashboard?key=", nil)
	if !bytes.Contains(dashboard, []byte("VApexChart")) {
		t.Fatal("actual source dashboard absent")
	}
	status, raw := s.apiSS("SiteStatistic", "btschool.club", "zh-CN", s.token, true)
	ssAssertAPI(t, status, raw, true, "刷新成功")
	if len(s.noticesSS()) == 0 {
		t.Fatal("global source event did not reach real notice storage")
	}
	// Reload while TT private timers exist exercises nonconsumer drain/join.
	for _, id := range sdkImpactInstances {
		old := sdkImpactPIDs(t, s)[id]
		started := time.Now()
		s.okSS("POST", "/api/plugins/"+id+"/reload", map[string]any{})
		if sdkImpactPIDs(t, s)[id] == old || time.Since(started) > 10*time.Second {
			t.Fatal("ordinary reload/drain did not replace worker", id)
		}
	}
	for _, id := range []string{"TorrentTransfer", "TorrentTransfermusic"} {
		configs[id]["enabled"] = false
		s.okSS("PUT", "/api/plugins/"+id, configs[id])
		s.configSS(id, configs[id])
	}
	cfg["enabled"] = false
	s.okSS("PUT", "/api/plugins/SiteStatistic", cfg)
	categoryPath := filepath.Join(dir, "category.yaml")
	snap, e := os.Stat(categoryPath)
	if e != nil {
		t.Fatal(e)
	}
	before = qb.count()
	s.stop()
	sdkImpactStart(s, filepath.Join(dir, "owned-home"))
	time.Sleep(2100 * time.Millisecond)
	if qb.count() != before {
		t.Fatal("cold replayed cleared one-shot")
	}
	after, e := os.Stat(categoryPath)
	if e != nil || !os.SameFile(snap, after) || !snap.ModTime().Equal(after.ModTime()) {
		t.Fatal("cold replayed Category apply")
	}
	for _, id := range []string{"TorrentTransfer", "TorrentTransfermusic"} {
		s.configSS(id, configs[id])
	}
	s.configSS("SiteStatistic", cfg)
	s.configSS("CategoryEditor", map[string]any{"enabled": false, "content": content})
	for _, id := range sdkImpactInstances {
		if sdkImpactPIDs(t, s)[id] == 0 {
			t.Fatal("cold instance missing", id)
		}
	}
	peer.assert(t)
	qb.mu.Lock()
	bad := len(qb.writes)
	qb.mu.Unlock()
	if bad != 0 {
		t.Fatal("unexpected qB mutations/protocol", qb.report())
	}
	s.record("sdk98_four_instance_complete", map[string]any{"classification": "ordinary f7 Main with currentSDK98 accepted workers; actual settings/files/SQLite/API/event/notification/clone/cold; owned Nexus native HTTPS and qB HTTP protocol peer, NOT real qB transfer or previous migration replay", "instances": sdkImpactInstances, "Nexus": peer.report(), "qB": qb.report(), "database_facts": s.dbSS()})
	s.stop()
}
