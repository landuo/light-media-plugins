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

// These checks consume ordinary HTTP responses; the local fixtures exercise
// their failure branches, while only the opt-in Main run proves host behavior.
func sdkImpactResponse(status int, raw json.RawMessage) (json.RawMessage, error) {
	if status != http.StatusOK || !json.Valid(raw) {
		return nil, fmt.Errorf("ordinary HTTP outcome: status %d, valid JSON %t", status, json.Valid(raw))
	}
	var envelope struct {
		Success *bool           `json:"success"`
		Data    json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal(raw, &envelope); err == nil {
		if envelope.Success != nil && !*envelope.Success {
			return nil, fmt.Errorf("ordinary host reported business failure")
		}
		if envelope.Data != nil {
			return envelope.Data, nil
		}
	}
	return raw, nil
}

func sdkImpactCreateSite(s *ssMain, config map[string]any) error {
	status, raw := s.httpSS("POST", "/api/sites/manage", config, nil)
	data, err := sdkImpactResponse(status, raw)
	if err != nil {
		return err
	}
	var result struct {
		Sites []struct {
			Config struct {
				ID      string `json:"id"`
				Name    string `json:"name"`
				BaseURL string `json:"base_url"`
				Domain  string `json:"domain"`
				Enabled bool   `json:"enabled"`
				Proxy   bool   `json:"proxy"`
			} `json:"config"`
			Credentials bool `json:"credential_configured"`
		} `json:"sites"`
	}
	if json.Unmarshal(data, &result) != nil {
		return fmt.Errorf("managed sites shape")
	}
	for _, row := range result.Sites {
		c := row.Config
		if c.ID == config["id"] && c.Name == config["name"] && strings.TrimRight(c.BaseURL, "/") == strings.TrimRight(config["base_url"].(string), "/") && c.Domain == config["domain"] && c.Enabled && c.Proxy && row.Credentials {
			return nil
		}
	}
	return fmt.Errorf("managed site canonical ID/config/credential state missing")
}

func sdkImpactSourceAPI(status int, raw json.RawMessage) error {
	var response struct {
		Success *bool                      `json:"success"`
		Message string                     `json:"message"`
		I18n    string                     `json:"message_i18n"`
		Data    map[string]json.RawMessage `json:"data"`
	}
	if status != http.StatusOK || json.Unmarshal(raw, &response) != nil || response.Success == nil || !*response.Success || response.Message != "站点 btschool.club 刷新成功" || response.I18n != response.Message || len(response.Data) != 19 {
		return fmt.Errorf("source API success/message/current DTO contract")
	}
	for key, want := range map[string]string{"upload": "2147483648", "download": "1073741824", "username": `" self "`, "userid": `"7"`, "seeding": "2", "seeding_size": "3072", "updated_time": "null", "err_msg": "null"} {
		if string(response.Data[key]) != want {
			return fmt.Errorf("source API current field %s differs", key)
		}
	}
	return nil
}

func sdkImpactRefreshAPI(s *ssMain) error {
	status, raw := s.apiSS("SiteStatistic", "btschool.club", "zh-CN", s.token, true)
	return sdkImpactSourceAPI(status, raw)
}

func sdkImpactViews(s *ssMain) error {
	for _, kind := range []string{"page", "dashboard?key="} {
		status, raw := s.httpSS("GET", "/api/plugins/SiteStatistic/"+kind, nil, nil)
		data, err := sdkImpactResponse(status, raw)
		var view struct {
			ID         string            `json:"id"`
			Key        string            `json:"key"`
			RenderMode string            `json:"render_mode"`
			Page       []json.RawMessage `json:"page"`
			Elements   []json.RawMessage `json:"elements"`
		}
		if err != nil || json.Unmarshal(data, &view) != nil || view.RenderMode != "vuetify" || !bytes.Contains(data, []byte("VApexChart")) || kind == "page" && (len(view.Page) == 0 || !bytes.Contains(data, []byte("SDK98 owned Nexus"))) || kind != "page" && (view.ID != "SiteStatistic" || view.Key != "" || len(view.Elements) == 0) {
			return fmt.Errorf("actual source %s missing chart/account: %v", kind, err)
		}
	}
	return nil
}

func sdkImpactAdmitService(s *ssMain, id string) error {
	status, raw := s.httpSS("POST", "/api/plugins/services/run", map[string]any{"instance_id": id, "service_id": "TorrentTransfer"}, nil)
	data, err := sdkImpactResponse(status, raw)
	if err != nil {
		return err
	}
	var ack struct{ Accepted, Success bool }
	if json.Unmarshal(data, &ack) != nil || !ack.Accepted || !ack.Success {
		return fmt.Errorf("ordinary manual service was not admitted: %s", id)
	}
	return nil
}

func sdkImpactServicesIdle(raw json.RawMessage) (bool, error) {
	var rows []struct {
		InstanceID string `json:"instance_id"`
		ServiceID  string `json:"service_id"`
		Status     string `json:"status"`
		CanRun     bool   `json:"can_run"`
	}
	if json.Unmarshal(raw, &rows) != nil {
		return false, fmt.Errorf("ordinary services shape")
	}
	found := map[string]bool{}
	for _, row := range rows {
		if row.ServiceID == "TorrentTransfer" && (row.InstanceID == "TorrentTransfer" || row.InstanceID == "TorrentTransfermusic") {
			found[row.InstanceID] = row.CanRun && row.Status == "等待"
		}
	}
	return found["TorrentTransfer"] && found["TorrentTransfermusic"], nil
}

func sdkImpactAwait(duration time.Duration, check func() (bool, error)) error {
	until := time.Now().Add(duration)
	for {
		ready, err := check()
		if err != nil || ready {
			return err
		}
		if time.Now().After(until) {
			return fmt.Errorf("bounded asynchronous observation timed out")
		}
		time.Sleep(100 * time.Millisecond)
	}
}

func sdkImpactSummaryReady(notices []map[string]any, receiptRows, before int) (bool, error) {
	if len(notices) > before+1 || receiptRows > 1 {
		return false, fmt.Errorf("duplicate summary or receipt")
	}
	if len(notices) != before+1 || receiptRows != 1 {
		return false, nil
	}
	n := notices[0]
	message, _ := n["message"].(string)
	if n["mtype"] != "站点" {
		return false, fmt.Errorf("source SiteMessage wire enum differs")
	}
	for _, text := range []string{"【汇总】", "SDK98 owned Nexus", "2.0G", "1.0G"} {
		if !strings.Contains(message, text) {
			return false, fmt.Errorf("source notice lacks %s", text)
		}
	}
	return true, nil
}

// Query only row metadata/digests in the owned database. Never read a key or
// unseal config/KV; authenticated public APIs remain the value assertions.
func sdkImpactStoredMetadata(s *ssMain) map[string]map[string]any {
	s.t.Helper()
	code := `import sqlite3,json,sys,hashlib
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
ids=['CategoryEditor','TorrentTransfer','TorrentTransfermusic','SiteStatistic']
out={}
for i,k,n,r,b in c.execute('SELECT instance_id,kind,item_key,revision,sealed FROM plugin_values ORDER BY instance_id,kind,item_key'):
 if i in ids: out[i+'/'+k+'/'+n]={'revision':r,'sealed_sha256':hashlib.sha256(b).hexdigest()}
print(json.dumps(out))`
	b, err := exec.CommandContext(s.ctx, "python3", "-c", code, filepath.Join(s.dir, "light-media.db")).Output()
	if err != nil {
		s.t.Fatal("owned readonly stored metadata", err)
	}
	var result map[string]map[string]any
	if json.Unmarshal(b, &result) != nil {
		s.t.Fatal("owned readonly stored metadata shape")
	}
	return result
}

func sdkImpactReceiptRows(rows map[string]map[string]any) int {
	if rows["SiteStatistic/data/last_notify"] != nil {
		return 1
	}
	return 0
}

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

// This is a pinned-handler response fixture, NOT an App or native acceptance
// test. It drives the very helpers used by the opt-in Main over real HTTP and
// proves that plausible HTTP200 failures cannot satisfy their business checks.
func TestSDK98ImpactRemainingHTTPContract(t *testing.T) {
	const dto = `{"domain":"btschool.club","username":" self ","userid":"7","user_level":"Power User","join_at":"2024-01-02T03:04:05","bonus":12.5,"upload":2147483648,"download":1073741824,"ratio":2,"seeding":2,"leeching":2,"seeding_size":3072,"leeching_size":0,"seeding_info":[[3,1024],[4,2048]],"message_unread":0,"message_unread_contents":[],"err_msg":null,"updated_day":"2026-11-05","updated_time":null}`
	const response = `{"success":true,"message":"站点 btschool.club 刷新成功","message_i18n":"站点 btschool.club 刷新成功","data":` + dto + `}`
	testCases := []struct {
		name, fault string
		want        string
	}{
		{"exact_routes_body_auth_and_source_fields", "", "pass"},
		{"site_404_is_not_saved", "site404", "site"},
		{"site_http200_empty_is_not_saved", "site_empty", "site"},
		{"site_wrong_canonical_identity", "site_id", "site"},
		{"page_http200_empty_is_not_data", "page_empty", "views"},
		{"dashboard_http200_empty_is_not_chart", "dashboard_empty", "views"},
		{"source_message_requires_domain", "api_short_message", "api"},
		{"source_current_DTO_not_old_daily", "api_old_data", "api"},
		{"source_missing_null_field_rejected", "api_missing_field", "api"},
		{"source_http200_empty_is_not_success", "api_empty", "api"},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			calls := []string{}
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				calls = append(calls, r.Method+" "+r.URL.Path)
				w.Header().Set("Content-Type", "application/json")
				if r.Header.Get("Origin") == "" {
					t.Error("ordinary HTTP helper lost Origin")
				}
				switch r.Method + " " + r.URL.Path {
				case "POST /api/sites/manage":
					var body map[string]any
					if json.NewDecoder(r.Body).Decode(&body) != nil || body["id"] != "sdk98-nexus" || body["cookie"] != "owned-cookie" || body["proxy"] != true {
						http.Error(w, "site request body mismatch", 422)
						return
					}
					if tc.fault == "site404" {
						http.NotFound(w, r)
						return
					}
					if tc.fault == "site_empty" {
						fmt.Fprint(w, `{"data":{}}`)
						return
					}
					id := "sdk98-nexus"
					if tc.fault == "site_id" {
						id = "wrong-canonical-ID"
					}
					fmt.Fprintf(w, `{"data":{"sites":[{"config":{"id":%q,"name":"SDK98 owned Nexus","base_url":"https://pt.btschool.club","domain":"btschool.club","proxy":true,"enabled":true},"credential_configured":true}]}}`, id)
				case "GET /api/plugins/SiteStatistic/page":
					if tc.fault == "page_empty" {
						fmt.Fprint(w, `{"data":{}}`)
					} else {
						fmt.Fprint(w, `{"data":{"render_mode":"vuetify","page":[{"component":"VApexChart","props":{"title":"SDK98 owned Nexus"}}]}}`)
					}
				case "GET /api/plugins/SiteStatistic/dashboard":
					if !r.URL.Query().Has("key") {
						http.Error(w, "missing explicit default key", 422)
						return
					}
					if tc.fault == "dashboard_empty" {
						fmt.Fprint(w, `{"data":{}}`)
					} else {
						fmt.Fprint(w, `{"data":{"id":"SiteStatistic","name":"站点数据统计","key":"","render_mode":"vuetify","cols":{},"attrs":{},"elements":[{"component":"VApexChart"}]}}`)
					}
				case "GET /api/v1/plugin/SiteStatistic/refresh_by_domain":
					q := r.URL.Query()
					if q.Get("domain") != "btschool.club" || q.Get("locale") != "zh-CN" || q.Get("apikey") != "owned-token" || r.Header.Get("X-API-KEY") != "owned-token" {
						http.Error(w, "source query/auth mismatch", 401)
						return
					}
					out := response
					switch tc.fault {
					case "api_short_message":
						out = strings.ReplaceAll(out, "站点 btschool.club 刷新成功", "刷新成功")
					case "api_old_data":
						out = strings.ReplaceAll(out, `"upload":2147483648`, `"upload":1`)
					case "api_missing_field":
						out = strings.ReplaceAll(out, `,"err_msg":null`, "")
					case "api_empty":
						out = `{"data":{}}`
					}
					fmt.Fprint(w, out)
				default:
					http.NotFound(w, r)
				}
			}))
			defer server.Close()
			s := sdkImpactHTTPFixture(t, server)
			config := map[string]any{"id": "sdk98-nexus", "name": "SDK98 owned Nexus", "base_url": "https://pt.btschool.club/", "domain": "btschool.club", "cookie": "owned-cookie", "proxy": true}
			stage := "pass"
			if err := sdkImpactCreateSite(s, config); err != nil {
				stage = "site"
			} else if err = sdkImpactViews(s); err != nil {
				stage = "views"
			} else if err = sdkImpactRefreshAPI(s); err != nil {
				stage = "api"
			}
			if stage != tc.want {
				t.Fatalf("failure classification %s, want %s; actual calls %v", stage, tc.want, calls)
			}
			// The old, unexecuted PUT-by-ID guess is explicitly rejected by this
			// independently pinned route. It cannot pass on a generic HTTP200.
			status, _ := s.httpSS("PUT", "/api/sites/manage/sdk98-nexus", config, nil)
			if status != http.StatusNotFound {
				t.Fatal("unrecognized route accepted")
			}
		})
	}
}

func sdkImpactHTTPFixture(t *testing.T, server *httptest.Server) *ssMain {
	t.Helper()
	dir := t.TempDir()
	if root := os.Getenv("SDK98_IMPACT_HTTP_OBSERVATIONS"); root != "" {
		dir = filepath.Join(root, strings.ReplaceAll(t.Name(), "/", "_"))
		if err := os.MkdirAll(dir, 0700); err != nil {
			t.Fatal(err)
		}
	}
	f, err := os.Create(filepath.Join(dir, "http-observations.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { f.Close() })
	return &ssMain{mainHost: &mainHost{t: t, base: server.URL, client: server.Client(), events: f}, ctx: context.Background(), token: "owned-token", secrets: []string{"owned-token", "owned-cookie"}}
}

func TestSDK98ImpactAsyncHTTPCompletion(t *testing.T) {
	var mu sync.Mutex
	admitted := map[string]bool{}
	queries := 0
	observedBusy := false
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		mu.Lock()
		defer mu.Unlock()
		switch r.Method + " " + r.URL.Path {
		case "POST /api/plugins/services/run":
			var input struct {
				InstanceID string `json:"instance_id"`
				ServiceID  string `json:"service_id"`
			}
			_ = json.NewDecoder(r.Body).Decode(&input)
			if input.ServiceID != "TorrentTransfer" || input.InstanceID != "TorrentTransfer" && input.InstanceID != "TorrentTransfermusic" || admitted[input.InstanceID] {
				http.Error(w, "invalid/repeated admission", 409)
				return
			}
			admitted[input.InstanceID] = true
			fmt.Fprint(w, `{"data":{"accepted":true,"success":true}}`)
		case "GET /api/plugins/services":
			if queries == 0 {
				observedBusy = true
				fmt.Fprint(w, `{"data":[{"instance_id":"TorrentTransfer","service_id":"TorrentTransfer","status":"正在运行","can_run":false},{"instance_id":"TorrentTransfermusic","service_id":"TorrentTransfer","status":"正在运行","can_run":false}]}`)
				queries = 2 // Deliberately only after the first busy observation.
				return
			}
			fmt.Fprint(w, `{"data":[{"instance_id":"TorrentTransfer","service_id":"TorrentTransfer","status":"等待","can_run":true},{"instance_id":"TorrentTransfermusic","service_id":"TorrentTransfer","status":"等待","can_run":true}]}`)
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	s := sdkImpactHTTPFixture(t, server)
	for _, id := range []string{"TorrentTransfer", "TorrentTransfermusic"} {
		if err := sdkImpactAdmitService(s, id); err != nil {
			t.Fatal(err)
		}
	}
	mu.Lock()
	premature := queries
	mu.Unlock()
	if premature != 0 {
		t.Fatal("fixture did not separate admission from execution")
	}
	if err := sdkImpactAwait(time.Second, func() (bool, error) {
		status, raw := s.httpSS("GET", "/api/plugins/services", nil, nil)
		data, err := sdkImpactResponse(status, raw)
		if err != nil {
			return false, err
		}
		return sdkImpactServicesIdle(data)
	}); err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	defer mu.Unlock()
	if !observedBusy || len(admitted) != 2 || queries != 2 {
		t.Fatal("manual owner completion was not observed separately")
	}
}

func TestSDK98ImpactDelayedNotificationHTTP(t *testing.T) {
	mu := sync.Mutex{}
	calls := 0
	receipt := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		if r.Method != "GET" || r.URL.Path != "/api/notifications" {
			http.NotFound(w, r)
			return
		}
		calls++
		if calls == 1 {
			fmt.Fprint(w, `{"data":{"items":[],"unread":0}}`)
			return
		}
		if calls > 2 {
			receipt = 1 // Notice storage alone is also insufficient.
		}
		fmt.Fprint(w, `{"data":{"items":[{"title":"站点数据统计","message":"【汇总】SDK98 owned Nexus 上传2.0G 下载1.0G","mtype":"站点"}],"unread":1}}`)
	}))
	defer server.Close()
	s := sdkImpactHTTPFixture(t, server)
	if err := sdkImpactAwait(time.Second, func() (bool, error) {
		notices := s.noticesSS()
		mu.Lock()
		r := receipt
		mu.Unlock()
		return sdkImpactSummaryReady(notices, r, 0)
	}); err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	completedCalls := calls
	mu.Unlock()
	if completedCalls < 3 {
		t.Fatal("did not wait for independent notification and receipt")
	}
	for _, bad := range []map[string]any{{"mtype": "站点消息", "message": "【汇总】SDK98 owned Nexus 上传2.0G 下载1.0G"}, {"mtype": "站点", "message": "HTTP200"}} {
		if ready, err := sdkImpactSummaryReady([]map[string]any{bad}, 1, 0); err == nil || ready {
			t.Fatal("invalid wire notice accepted", bad)
		}
	}
}

func TestSDK98ImpactReloadAndConfigHTTP(t *testing.T) {
	// This fixture checks methods, paths, complete raw config values and
	// instance isolation. Actual PID replacement/join is exclusive to Main.
	configs := map[string]json.RawMessage{}
	reloads := map[string]int{}
	mu := sync.Mutex{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/plugins/"), "/")
		id := parts[0]
		valid := false
		for _, known := range sdkImpactInstances {
			valid = valid || id == known
		}
		if !strings.HasPrefix(r.URL.Path, "/api/plugins/") || !valid {
			http.NotFound(w, r)
			return
		}
		switch {
		case r.Method == "PUT" && len(parts) == 1:
			var body json.RawMessage
			if json.NewDecoder(r.Body).Decode(&body) != nil || len(body) == 0 || body[0] != '{' {
				http.Error(w, "config must be a raw object", 422)
				return
			}
			configs[id] = body
			fmt.Fprint(w, `{"data":{"success":true}}`)
		case r.Method == "POST" && len(parts) == 2 && parts[1] == "reload":
			reloads[id]++
			fmt.Fprint(w, `{"data":{"success":true}}`)
		case r.Method == "GET" && len(parts) == 1:
			if configs[id] == nil {
				fmt.Fprint(w, `{"data":{}}`)
				return
			}
			fmt.Fprintf(w, `{"data":%s}`, configs[id])
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	s := sdkImpactHTTPFixture(t, server)
	for _, id := range sdkImpactInstances {
		cfg := map[string]any{"enabled": false, "onlyonce": false, "owned_instance": id, "source_extra": []any{nil, false, "false", 0}}
		s.okSS("PUT", "/api/plugins/"+id, cfg)
		s.okSS("POST", "/api/plugins/"+id+"/reload", map[string]any{})
		s.configSS(id, cfg)
	}
	mu.Lock()
	defer mu.Unlock()
	if len(reloads) != 4 || len(configs) != 4 {
		t.Fatal("config/reload fixture lost independent instance identities")
	}
	for _, id := range sdkImpactInstances {
		if reloads[id] != 1 {
			t.Fatal("reload repeated", id)
		}
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
		if err := sdkImpactAdmitService(s, id); err != nil {
			t.Fatal(err)
		}
	}
	// The modern POST endpoint acknowledges admission (wait=false). A query
	// and the real scheduler's idle state are the eventual completion facts.
	ssWait(t, "two ordinary manual source queries", 25*time.Second, func() bool { return qb.count() >= before+4 })
	var settled json.RawMessage
	ssWait(t, "both ordinary manual service owners finished", 25*time.Second, func() bool {
		settled = s.okSS("GET", "/api/plugins/services", nil)
		ready, err := sdkImpactServicesIdle(settled)
		if err != nil {
			t.Fatal(err)
		}
		return ready
	})
	s.record("sdk98_manual_services_completed", map[string]any{"admission_is_not_completion": true, "actual_source_completed_queries": qb.count(), "required_queries": before + 4, "settled_public_services": settled})
	// Actual known Nexus source chain -> SQLite -> per-site/global event -> message.
	site := map[string]any{"id": "sdk98-nexus", "name": "SDK98 owned Nexus", "kind": "nexusphp", "base_url": "https://" + ssTargets[0] + "/", "domain": "btschool.club", "cookie": peer.cookie[ssTargets[0]], "ua": "Owned-SDK98-UA", "proxy": true, "enabled": true, "pri": 1}
	if err := sdkImpactCreateSite(s, site); err != nil {
		t.Fatal(err)
	}
	ssWait(t, "ordinary site-created source cache reaches SQLite", 30*time.Second, func() bool {
		return bytes.Contains(ssHistory(t, s, "sdk98-nexus"), []byte("self"))
	})
	lastCount, quietSince := peer.count(), time.Now()
	ssWait(t, "site-created requests settle before all-refresh baseline", 10*time.Second, func() bool {
		if n := peer.count(); n != lastCount {
			lastCount, quietSince = n, time.Now()
		}
		return time.Since(quietSince) > 1200*time.Millisecond
	})
	if len(s.noticesSS()) != 0 || sdkImpactReceiptRows(sdkImpactStoredMetadata(s)) != 0 {
		t.Fatal("disabled source received a global summary")
	}
	beforeDB := s.dbSS()
	beforeNotices := len(s.noticesSS())
	cfg := ssConfig(true, true, "all", "total")
	s.okSS("PUT", "/api/plugins/SiteStatistic", cfg)
	ssWait(t, "real source refresh_all global event", 30*time.Second, func() bool { return s.dbSS().Events["*"] == beforeDB.Events["*"]+1 })
	if err := sdkImpactAwait(15*time.Second, func() (bool, error) {
		return sdkImpactSummaryReady(s.noticesSS(), sdkImpactReceiptRows(sdkImpactStoredMetadata(s)), beforeNotices)
	}); err != nil {
		t.Fatal("ordinary global event/notice/receipt completion", err)
	}
	if s.dbSS().Events["sdk98-nexus"] != beforeDB.Events["sdk98-nexus"]+1 {
		t.Fatal("all refresh missing exact per-site fact")
	}
	cfg["onlyonce"] = false
	s.configSS("SiteStatistic", cfg)
	if err := sdkImpactViews(s); err != nil {
		t.Fatal(err)
	}
	apiBefore := s.dbSS()
	if err := sdkImpactRefreshAPI(s); err != nil {
		t.Fatal(err)
	}
	apiAfter := s.dbSS()
	if apiAfter.Events["sdk98-nexus"] != apiBefore.Events["sdk98-nexus"]+1 || apiAfter.Events["*"] != apiBefore.Events["*"] || len(s.noticesSS()) != beforeNotices+1 {
		t.Fatal("single source API facts became a global refresh/summary")
	}
	// Reload while TT private timers exist exercises nonconsumer drain/join.
	for _, id := range sdkImpactInstances {
		old := sdkImpactPIDs(t, s)[id]
		started := time.Now()
		s.okSS("POST", "/api/plugins/"+id+"/reload", map[string]any{})
		pid := sdkImpactPIDs(t, s)[id]
		_, oldErr := os.Stat(filepath.Join("/proc", fmt.Sprint(old)))
		if pid == 0 || pid == old || !os.IsNotExist(oldErr) || time.Since(started) > 15*time.Second {
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
	s.configSS("SiteStatistic", cfg)
	coldFacts, coldNotices := s.dbSS(), len(s.noticesSS())
	coldRows := sdkImpactStoredMetadata(s)
	coldRowsRaw, _ := json.Marshal(coldRows)
	coldPIDs := sdkImpactPIDs(t, s)
	categoryPath := filepath.Join(dir, "category.yaml")
	snap, e := os.Stat(categoryPath)
	if e != nil {
		t.Fatal(e)
	}
	before = qb.count()
	s.stop()
	for id, pid := range coldPIDs {
		if _, err := os.Stat(filepath.Join("/proc", fmt.Sprint(pid))); !os.IsNotExist(err) {
			t.Fatal("ordinary Main stop left worker", id, pid)
		}
	}
	sdkImpactStart(s, filepath.Join(dir, "owned-home"))
	newPIDs := sdkImpactPIDs(t, s)
	for _, id := range sdkImpactInstances {
		if newPIDs[id] == 0 || newPIDs[id] == coldPIDs[id] {
			t.Fatal("cold instance process identity", id, coldPIDs, newPIDs)
		}
	}
	// Source date jobs fire after three seconds; observing less cannot exclude
	// a replay. Match the accepted Site ordinary Main's 3500ms quiet window.
	time.Sleep(3500 * time.Millisecond)
	if qb.count() != before {
		t.Fatal("cold replayed cleared one-shot")
	}
	newRowsRaw, _ := json.Marshal(sdkImpactStoredMetadata(s))
	if s.dbSS().Events["*"] != coldFacts.Events["*"] || len(s.noticesSS()) != coldNotices || !bytes.Equal(coldRowsRaw, newRowsRaw) {
		t.Fatal("cold source event/notice/stored namespace changed")
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
