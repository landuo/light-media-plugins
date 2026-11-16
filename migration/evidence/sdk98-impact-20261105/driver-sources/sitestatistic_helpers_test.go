package integration

// Owned infrastructure for the opt-in SiteStatistic ordinary cmd/server test.
// No production app import, global transport override, DNS override or trust edit.
import (
	"bytes"
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"math/big"
	"net"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

const ssOwnedMarker = "light-media-plugins/SiteStatistic/20261105/owned-only"
const ssSource = "SiteStatistic"
const ssClone = "SiteStatisticowned"

var ssTargets = []string{"pt.btschool.club", "hdsky.me"}

type ssMain struct {
	*mainHost
	caFile, token string
	secrets       []string
	ctx           context.Context
}

func ssRandom(t *testing.T) string {
	t.Helper()
	b := make([]byte, 24)
	if _, e := rand.Read(b); e != nil {
		t.Fatal(e)
	}
	return hex.EncodeToString(b)
}
func ssOwnedDirectory(t *testing.T) string {
	t.Helper()
	dir := os.Getenv("SITESTATISTIC_RUNTIME_DIR")
	if dir == "" {
		dir = t.TempDir()
	}
	var err error
	if dir, err = filepath.Abs(dir); err != nil {
		t.Fatal(err)
	}
	if e := os.MkdirAll(dir, 0700); e != nil {
		t.Fatal(e)
	}
	marker := filepath.Join(dir, ".task-owned")
	if raw, e := os.ReadFile(marker); e == nil {
		if string(raw) != ssOwnedMarker {
			t.Fatal("foreign runtime marker")
		}
	} else if !os.IsNotExist(e) {
		t.Fatal(e)
	} else {
		entries, e := os.ReadDir(dir)
		if e != nil || len(entries) != 0 {
			t.Fatal("unmarked runtime must be a new empty directory", e)
		}
		if e = os.WriteFile(marker, []byte(ssOwnedMarker), 0600); e != nil {
			t.Fatal(e)
		}
	}
	if _, e := os.Stat(filepath.Join(dir, "light-media.db")); !os.IsNotExist(e) {
		t.Fatal("fresh owned runtime required; do not reuse an earlier DB")
	}
	return dir
}
func ssNewMain(ctx context.Context, t *testing.T, dir, caFile, proxy string) *ssMain {
	t.Helper()
	binary := os.Getenv("SITESTATISTIC_HOST_BINARY")
	if binary == "" {
		t.Fatal("SITESTATISTIC_HOST_BINARY required")
	}
	evidence := filepath.Join(dir, "evidence")
	if e := os.MkdirAll(evidence, 0700); e != nil {
		t.Fatal(e)
	}
	addr := os.Getenv("SITESTATISTIC_LISTEN")
	if addr == "" {
		addr = "127.0.0.1:36253"
	}
	baseAddr := addr
	if strings.HasPrefix(addr, "0.0.0.0:") {
		baseAddr = "127.0.0.1:" + strings.TrimPrefix(addr, "0.0.0.0:")
	}
	jar, _ := cookiejar.New(nil)
	events, e := os.OpenFile(filepath.Join(evidence, "observations.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
	if e != nil {
		t.Fatal(e)
	}
	s := &ssMain{mainHost: &mainHost{t: t, binary: binary, dir: dir, evidence: evidence, addr: addr, base: "http://" + baseAddr, client: &http.Client{Jar: jar, Timeout: 90 * time.Second}, events: events}, caFile: caFile, token: ssRandom(t)}
	s.ctx = ctx
	s.secrets = []string{s.token}
	t.Cleanup(func() { s.stop(); events.Close() })
	settings := map[string]any{"plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0, "read_site_messages": false, "allowed_roots": []string{dir}, "proxy_host": proxy, "api_token": s.token}
	body, _ := json.Marshal(map[string]any{"username": ownedUser, "password": ownedPassword, "settings": settings})
	cmd := exec.CommandContext(ctx, binary, "--data-dir", dir, "--bootstrap-stdin")
	cmd.Stdin = bytes.NewReader(body)
	cmd.Env = s.environment()
	out, e := cmd.CombinedOutput()
	s.record("ss_bootstrap", map[string]any{"success": e == nil, "output_bytes": len(out), "test_credentials": "stdin only; API token omitted"})
	if e != nil {
		t.Fatal("owned bootstrap failed", e)
	}
	s.startSS()
	return s
}
func (s *ssMain) environment() []string { return append(s.mainHost.env(), "SSL_CERT_FILE="+s.caFile) }
func (s *ssMain) startSS() {
	s.t.Helper()
	s.generation++
	f, e := os.Create(filepath.Join(s.evidence, fmt.Sprintf("host-%d.log", s.generation)))
	if e != nil {
		s.t.Fatal(e)
	}
	s.log = f
	cmd := exec.Command(s.binary, "--listen", s.addr, "--data-dir", s.dir)
	cmd.Env = s.environment()
	cmd.Stdout = f
	cmd.Stderr = f
	if e = cmd.Start(); e != nil {
		s.t.Fatal(e)
	}
	s.cmd = cmd
	done := make(chan error, 1)
	s.wait = done
	go func() { done <- cmd.Wait() }()
	ssWait(s.t, "ordinary main health", 30*time.Second, func() bool {
		r, e := s.client.Get(s.base + "/healthz")
		if e != nil {
			return false
		}
		r.Body.Close()
		return r.StatusCode == 200
	})
	s.record("ss_main_start", map[string]any{"pid": cmd.Process.Pid, "generation": s.generation, "binary_sha256": fileHash(s.t, s.binary), "CA_scope": "only this bootstrap/main child environment; TLS verification enabled"})
	s.okSS("POST", "/api/auth/login", map[string]any{"username": ownedUser, "password": ownedPassword})
}
func ssClean(v any) any {
	switch x := v.(type) {
	case map[string]any:
		out := map[string]any{}
		for k, v := range x {
			switch strings.ToLower(k) {
			case "password", "cookie", "api_key", "apikey", "api_token", "token", "authorization", "headers", "sealed", "secret", "protected_content":
				continue
			}
			out[k] = ssClean(v)
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, v := range x {
			out[i] = ssClean(v)
		}
		return out
	}
	return v
}
func (s *ssMain) httpSS(method, path string, value any, headers map[string]string) (int, json.RawMessage) {
	s.t.Helper()
	var body []byte
	if value != nil {
		body, _ = json.Marshal(value)
	}
	req, e := http.NewRequestWithContext(s.ctx, method, s.base+path, bytes.NewReader(body))
	if e != nil {
		s.t.Fatal(e)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Origin", s.base)
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	r, e := s.client.Do(req)
	if e != nil {
		s.t.Fatal("owned HTTP request failed", method, req.URL.Path, fmt.Sprintf("%T", e))
	}
	defer r.Body.Close()
	raw, e := io.ReadAll(io.LimitReader(r.Body, 16<<20))
	if e != nil {
		s.t.Fatal(e)
	}
	var cleanResponse any
	safeResponse := string(raw)
	for _, secret := range s.secrets {
		if secret != "" {
			safeResponse = strings.ReplaceAll(safeResponse, secret, "[redacted]")
		}
	}
	_ = json.Unmarshal([]byte(safeResponse), &cleanResponse)
	entry := map[string]any{"method": method, "path": req.URL.Path, "status": r.StatusCode, "response": ssClean(cleanResponse)}
	if req.URL.Path != "/api/auth/login" {
		var v any
		_ = json.Unmarshal(body, &v)
		entry["request"] = ssClean(v)
	}
	// Never record raw query, request headers, cookies, token or credentials.
	s.record("ss_http", entry)
	return r.StatusCode, raw
}
func ssData(t *testing.T, raw json.RawMessage) json.RawMessage {
	t.Helper()
	var x struct{ Data json.RawMessage }
	if json.Unmarshal(raw, &x) == nil && x.Data != nil {
		return x.Data
	}
	return raw
}
func (s *ssMain) okSS(method, path string, value any) json.RawMessage {
	s.t.Helper()
	status, raw := s.httpSS(method, path, value, nil)
	if status < 200 || status >= 300 {
		s.t.Fatalf("owned %s %s HTTP%d", method, strings.Split(path, "?")[0], status)
	}
	var x struct{ Success *bool }
	_ = json.Unmarshal(raw, &x)
	if x.Success != nil && !*x.Success {
		s.t.Fatal("ordinary host business failure", method, strings.Split(path, "?")[0], string(raw))
	}
	return ssData(s.t, raw)
}
func ssWait(t *testing.T, what string, duration time.Duration, condition func() bool) {
	t.Helper()
	until := time.Now().Add(duration)
	for !condition() {
		if time.Now().After(until) {
			t.Fatal("timeout: " + what)
		}
		time.Sleep(100 * time.Millisecond)
	}
}
func (s *ssMain) configSS(id string, want any) {
	s.t.Helper()
	got := s.okSS("GET", "/api/plugins/"+id, nil)
	expected, _ := json.Marshal(want)
	if !ssJSONEqual(got, expected) {
		s.t.Fatal("configuration mismatch", id, string(got), string(expected))
	}
}
func ssJSONEqual(a, b []byte) bool {
	decode := func(raw []byte) any {
		d := json.NewDecoder(bytes.NewReader(raw))
		d.UseNumber()
		var v any
		_ = d.Decode(&v)
		return v
	}
	aa, _ := json.Marshal(decode(a))
	bb, _ := json.Marshal(decode(b))
	return bytes.Equal(aa, bb)
}
func (s *ssMain) apiSS(instance, domain, locale, key string, headerGood bool) (int, json.RawMessage) {
	query := url.Values{"domain": {domain}, "apikey": {key}}
	if locale != "" {
		query.Set("locale", locale)
	}
	headers := map[string]string{}
	if headerGood {
		headers["X-API-KEY"] = s.token
	}
	return s.httpSS("GET", "/api/v1/plugin/"+instance+"/refresh_by_domain?"+query.Encode(), nil, headers)
}
func (s *ssMain) kvSS(instance string) map[string]json.RawMessage {
	s.t.Helper()
	code := `import sqlite3,json,base64,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
print(json.dumps([[k,base64.b64encode(v).decode()] for k,v in c.execute("SELECT item_key,sealed FROM plugin_values WHERE instance_id=? AND kind='data' ORDER BY rowid",(sys.argv[2],))]))`
	b, e := exec.CommandContext(s.ctx, "python3", "-c", code, filepath.Join(s.dir, "light-media.db"), instance).Output()
	if e != nil {
		s.t.Fatal("owned readonly KV query", e)
	}
	var rows [][2]string
	if e = json.Unmarshal(b, &rows); e != nil {
		s.t.Fatal(e)
	}
	key, e := os.ReadFile(filepath.Join(s.dir, "secret.key"))
	if e != nil {
		s.t.Fatal(e)
	}
	block, e := aes.NewCipher(key)
	if e != nil {
		s.t.Fatal(e)
	}
	aead, _ := cipher.NewGCM(block)
	out := map[string]json.RawMessage{}
	for _, row := range rows {
		sealed, e := base64.StdEncoding.DecodeString(row[1])
		if e != nil || len(sealed) < aead.NonceSize() {
			s.t.Fatal("owned KV cipher")
		}
		aad, _ := json.Marshal([]string{"light-media/plugins/v1", "data", instance, row[0]})
		plain, e := aead.Open(nil, sealed[:aead.NonceSize()], sealed[aead.NonceSize():], aad)
		if e != nil {
			s.t.Fatal("owned KV integrity", e)
		}
		out[row[0]] = plain
	}
	return out
}

type ssDBView struct {
	Events     map[string]int `json:"events"`
	Records    map[string]int `json:"records"`
	ConfigRows map[string]int `json:"config_rows"`
}

func (s *ssMain) dbSS() ssDBView {
	s.t.Helper()
	code := `import sqlite3,json,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
e={}
for raw, in c.execute('SELECT payload FROM domain_events ORDER BY rowid'):
 d=json.loads(raw)
 if d.get('event_type')=='site.refreshed':
  k=str(d.get('site_id'));e[k]=e.get(k,0)+1
print(json.dumps({'events':e,'records':dict(c.execute("SELECT kind,count(*) FROM records WHERE kind LIKE 'site%' GROUP BY kind")),'config_rows':dict(c.execute("SELECT instance_id,count(*) FROM plugin_values WHERE kind='config' GROUP BY instance_id"))}))`
	b, e := exec.CommandContext(s.ctx, "python3", "-c", code, filepath.Join(s.dir, "light-media.db")).Output()
	if e != nil {
		s.t.Fatal("owned readonly SQLite facts", e)
	}
	var out ssDBView
	if e = json.Unmarshal(b, &out); e != nil {
		s.t.Fatal(e)
	}
	return out
}
func (s *ssMain) workersSS() map[string]int {
	s.t.Helper()
	raw, e := exec.Command("ps", "-eo", "pid=,ppid=,args=").Output()
	if e != nil {
		s.t.Fatal(e)
	}
	out := map[string]int{}
	for _, line := range strings.Split(string(raw), "\n") {
		f := strings.Fields(line)
		if len(f) < 3 {
			continue
		}
		var pid, parent int
		fmt.Sscan(f[0], &pid)
		fmt.Sscan(f[1], &parent)
		if s.cmd == nil || parent != s.cmd.Process.Pid {
			continue
		}
		for _, id := range []string{ssSource, ssClone} {
			if strings.Contains(strings.Join(f[2:], " "), filepath.Join(s.dir, "plugin-packages", id)+string(filepath.Separator)) {
				out[id] = pid
			}
		}
	}
	s.record("ss_worker_pids", out)
	return out
}
func (s *ssMain) noticesSS() []map[string]any {
	s.t.Helper()
	raw := s.okSS("GET", "/api/notifications", nil)
	var x struct{ Items []map[string]any }
	if json.Unmarshal(raw, &x) != nil {
		s.t.Fatal("notifications shape")
	}
	out := []map[string]any{}
	for _, n := range x.Items {
		if n["title"] == "站点数据统计" {
			out = append(out, n)
		}
	}
	return out
}

// The two configured public hostnames are never resolved or contacted. Every
// successful CONNECT dials the one literal owned loopback listener below.
type ssPeer struct {
	mu                 sync.Mutex
	mode               map[string]string
	upload             map[string]int
	requests, connects []string
	artifactFallbacks  int
	unexpected         []string
	cookie             map[string]string
	caFile             string
	tls, proxy         *httptest.Server
	connections        map[net.Conn]bool
}

func ssNewPeer(t *testing.T, dir string) *ssPeer {
	t.Helper()
	rootKey, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	now := time.Now()
	root := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "owned SiteStatistic oracle CA"}, NotBefore: now.Add(-time.Minute), NotAfter: now.Add(3 * time.Hour), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature}
	rootDER, e := x509.CreateCertificate(rand.Reader, root, root, &rootKey.PublicKey, rootKey)
	if e != nil {
		t.Fatal(e)
	}
	leafKey, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	leaf := &x509.Certificate{SerialNumber: big.NewInt(2), DNSNames: ssTargets, Subject: pkix.Name{CommonName: ssTargets[0]}, NotBefore: now.Add(-time.Minute), NotAfter: now.Add(3 * time.Hour), KeyUsage: x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
	leafDER, e := x509.CreateCertificate(rand.Reader, leaf, root, &leafKey.PublicKey, rootKey)
	if e != nil {
		t.Fatal(e)
	}
	caFile := filepath.Join(dir, "owned-site-ca.pem")
	if e = os.WriteFile(caFile, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: rootDER}), 0600); e != nil {
		t.Fatal(e)
	}
	p := &ssPeer{mode: map[string]string{}, upload: map[string]int{}, cookie: map[string]string{}, caFile: caFile, connections: map[net.Conn]bool{}}
	for _, host := range ssTargets {
		p.mode[host] = "normal"
		p.upload[host] = 2
		p.cookie[host] = "owned-session=" + ssRandom(t)
	}
	p.tls = httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		defer p.mu.Unlock()
		p.requests = append(p.requests, r.Host+r.URL.RequestURI())
		host := r.Host
		cookie := r.Header.Get("Cookie")
		if p.cookie[host] == "" || (r.URL.Path != "/favicon.ico" && cookie != p.cookie[host]) || (cookie != "" && cookie != p.cookie[host]) {
			p.unexpected = append(p.unexpected, "origin/cookie mismatch")
			http.Error(w, "owned credential mismatch", 403)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		switch r.URL.Path {
		case "/":
			if p.mode[host] == "error" {
				fmt.Fprint(w, `<input type="password">`)
			} else {
				fmt.Fprintf(w, `<a href="logout.php">out</a><a href="userdetails.php?id=7"><b> self </b></a><div>上传量：%d GB 下载量：1 GB 分享率：2.00 下载中：2 <i>end</i></div><a href="mybonus.php">12.5</a>`, p.upload[host])
			}
		case "/userdetails.php":
			fmt.Fprint(w, `<table><tr><td>等级</td><td><img title="Power User"></td></tr><tr><td>加入日期</td><td>2024-01-02T03:04:05 (2 years ago)</td></tr></table>`)
		case "/getusertorrentlistajax.php":
			if p.mode[host] == "null" {
				fmt.Fprint(w, `<table class="torrents"><tr><td>name</td><td>大小</td><td>type</td><td>在做种</td></tr><tr><td>a</td><td>1 B</td><td>v</td><td>1</td></tr><tr><td>b</td><td>2 B</td><td>v</td><td></td></tr></table>`)
			} else {
				fmt.Fprint(w, `<table class="torrents"><tr><td>名称</td><td>大小</td><td>类型</td><td>在做种</td></tr><tr><td>owned</td><td>1024 B</td><td>video</td><td><b><a>3</a></b></td></tr><tr><td>owned</td><td>2048 B</td><td>video</td><td><b><a>4</a></b></td></tr></table>`)
			}
		case "/favicon.ico":
			w.WriteHeader(404)
		default:
			p.unexpected = append(p.unexpected, "unexpected owned path "+r.URL.Path)
			http.NotFound(w, r)
		}
	}))
	p.tls.TLS = &tls.Config{MinVersion: tls.VersionTLS12, Certificates: []tls.Certificate{{Certificate: [][]byte{leafDER, rootDER}, PrivateKey: leafKey}}}
	p.tls.StartTLS()
	target := p.tls.Listener.Addr().String()
	p.proxy = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		allowed := r.Method == http.MethodConnect && (r.Host == ssTargets[0]+":443" || r.Host == ssTargets[1]+":443")
		p.mu.Lock()
		if r.Method == http.MethodConnect {
			p.connects = append(p.connects, r.Host)
		}
		if !allowed {
			// The ordinary artifact helper first tries configured PROXY and
			// then its existing direct environment GET fallback. Deny even our
			// loopback index here; it can only fall back to that owned URL.
			if r.Method == http.MethodGet && r.URL.Scheme == "http" && r.URL.Hostname() == "127.0.0.1" && (r.URL.Path == "/index" || r.URL.Path == "/worker") {
				p.artifactFallbacks++
			} else {
				p.unexpected = append(p.unexpected, "denied non-owned proxy target")
			}
		}
		p.mu.Unlock()
		if !allowed {
			http.Error(w, "owned targets only", 403)
			return
		}
		upstream, e := net.DialTimeout("tcp", target, 3*time.Second)
		if e != nil {
			http.Error(w, "owned peer unavailable", 502)
			return
		}
		client, rw, e := w.(http.Hijacker).Hijack()
		if e != nil {
			upstream.Close()
			return
		}
		p.mu.Lock()
		p.connections[client] = true
		p.connections[upstream] = true
		p.mu.Unlock()
		defer func() {
			client.Close()
			upstream.Close()
			p.mu.Lock()
			delete(p.connections, client)
			delete(p.connections, upstream)
			p.mu.Unlock()
		}()
		if _, e = rw.WriteString("HTTP/1.1 200 Connection Established\r\n\r\n"); e != nil {
			return
		}
		if e = rw.Flush(); e != nil {
			return
		}
		go func() { _, _ = io.Copy(upstream, rw); upstream.Close() }()
		_, _ = io.Copy(client, upstream)
	}))
	t.Cleanup(func() {
		p.mu.Lock()
		for c := range p.connections {
			c.Close()
		}
		p.mu.Unlock()
		p.proxy.Close()
		p.tls.Close()
	})
	return p
}
func (p *ssPeer) set(host, mode string, upload int) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.mode[host] = mode
	p.upload[host] = upload
}
func (p *ssPeer) count() int { p.mu.Lock(); defer p.mu.Unlock(); return len(p.requests) }
func (p *ssPeer) report() map[string]any {
	p.mu.Lock()
	defer p.mu.Unlock()
	return map[string]any{"requests": append([]string{}, p.requests...), "connects": append([]string{}, p.connects...), "owned_artifact_http_denials_for_existing_direct_fallback": p.artifactFallbacks, "unexpected": append([]string{}, p.unexpected...), "TLS": "verified CA+two DNS SANs; no TLS bypass", "routing": "strict CONNECT maps only two literal authorities to one owned loopback listener; no target DNS or external dial"}
}
func (p *ssPeer) assert(t *testing.T) {
	t.Helper()
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.unexpected) != 0 || len(p.connects) == 0 {
		t.Fatal("owned network boundary failed", p.unexpected, len(p.connects))
	}
}
