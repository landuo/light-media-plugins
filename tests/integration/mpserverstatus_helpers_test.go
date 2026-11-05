package integration

// Namespace-only infrastructure for ordinary Main. No business URL, resolver
// or TLS implementation is replaced. Root alone starts Docker/relay/browser.
import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
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
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

const mpsSource = "MPServerStatus"
const mpsClone = "MPServerStatusowned"
const mpsMarker = "light-media-plugins/MPServerStatus/20261105/owned-only"
const mpsTarget = "movie-pilot.org"

type mpsMain struct {
	*mainHost
	ctx           context.Context
	caFile, proxy string
}

func mpsDirectory(t *testing.T) string {
	t.Helper()
	dir := os.Getenv("MPS_RUNTIME_DIR")
	if dir == "" {
		t.Fatal("MPS_RUNTIME_DIR must identify the fresh owned container mount")
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
		if string(b) != mpsMarker {
			t.Fatal("foreign marker")
		}
	} else if os.IsNotExist(e) {
		if e = os.WriteFile(marker, []byte(mpsMarker), 0600); e != nil {
			t.Fatal(e)
		}
	} else {
		t.Fatal(e)
	}
	for _, name := range []string{"light-media.db", "evidence", "plugin-packages"} {
		if _, e = os.Stat(filepath.Join(dir, name)); !os.IsNotExist(e) {
			t.Fatal("fresh runtime required", name, e)
		}
	}
	return dir
}
func newMPSMain(ctx context.Context, t *testing.T, dir, ca, proxy string) *mpsMain {
	t.Helper()
	binary := os.Getenv("MPS_HOST_BINARY")
	if binary == "" {
		t.Fatal("MPS_HOST_BINARY required")
	}
	evidence := filepath.Join(dir, "evidence")
	if e := os.MkdirAll(evidence, 0700); e != nil {
		t.Fatal(e)
	}
	events, e := os.OpenFile(filepath.Join(evidence, "observations.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
	if e != nil {
		t.Fatal(e)
	}
	addr := os.Getenv("MPS_LISTEN")
	if addr == "" {
		addr = "0.0.0.0:36255"
	}
	base := addr
	if strings.HasPrefix(base, "0.0.0.0:") {
		base = "127.0.0.1:" + strings.TrimPrefix(base, "0.0.0.0:")
	}
	jar, _ := cookiejar.New(nil)
	h := &mpsMain{mainHost: &mainHost{t: t, binary: binary, dir: dir, evidence: evidence, addr: addr, base: "http://" + base, client: &http.Client{Jar: jar, Timeout: 45 * time.Second, Transport: &http.Transport{Proxy: nil}}, events: events}, ctx: ctx, caFile: ca, proxy: proxy}
	t.Cleanup(func() { h.stop(); events.Close() })
	settings := map[string]any{"plugin_markets": []string{}, "plugin_server_url": "", "plugin_statistic_share": false, "media_recognize_share": false, "site_data_refresh_hours": 0, "read_site_messages": false, "allowed_roots": []string{dir}}
	body, _ := json.Marshal(map[string]any{"username": ownedUser, "password": ownedPassword, "settings": settings})
	cmd := exec.CommandContext(ctx, binary, "--data-dir", dir, "--bootstrap-stdin")
	cmd.Env = h.environment()
	cmd.Stdin = bytes.NewReader(body)
	out, e := cmd.CombinedOutput()
	h.record("mps_bootstrap", map[string]any{"success": e == nil, "output_bytes": len(out), "credentials": "owned fixture stdin, never recorded"})
	if e != nil {
		t.Fatal("ordinary bootstrap", e)
	}
	h.startMPS()
	return h
}
func (h *mpsMain) environment() []string {
	return append(h.mainHost.env(), "SSL_CERT_FILE="+h.caFile, "https_proxy="+h.proxy, "no_proxy=")
}
func (h *mpsMain) startMPS() {
	h.t.Helper()
	h.generation++
	f, e := os.Create(filepath.Join(h.evidence, fmt.Sprintf("host-%d.log", h.generation)))
	if e != nil {
		h.t.Fatal(e)
	}
	h.log = f
	cmd := exec.Command(h.binary, "--listen", h.addr, "--data-dir", h.dir)
	cmd.Env = h.environment()
	cmd.Stdout = f
	cmd.Stderr = f
	if e = cmd.Start(); e != nil {
		h.t.Fatal(e)
	}
	h.cmd = cmd
	done := make(chan error, 1)
	h.wait = done
	go func() { done <- cmd.Wait() }()
	mpsWait(h.t, "ordinary Main health", 30*time.Second, func() bool {
		r, e := h.client.Get(h.base + "/healthz")
		if e != nil {
			return false
		}
		r.Body.Close()
		return r.StatusCode == 200
	})
	h.record("mps_main_start", map[string]any{"pid": cmd.Process.Pid, "generation": h.generation, "main_sha256": fileHash(h.t, h.binary), "trust": "owned container system-CA bind + main child SSL_CERT_FILE; no private keys, no host env contract edits"})
	h.okMPS("POST", "/api/auth/login", map[string]any{"username": ownedUser, "password": ownedPassword})
}
func mpsClean(v any) any {
	switch x := v.(type) {
	case map[string]any:
		out := map[string]any{}
		for k, v := range x {
			switch strings.ToLower(k) {
			case "password", "cookie", "token", "apikey", "api_key", "api_token", "authorization", "headers", "sealed", "secret":
				continue
			}
			out[k] = mpsClean(v)
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, v := range x {
			out[i] = mpsClean(v)
		}
		return out
	}
	return v
}
func (h *mpsMain) raw(ctx context.Context, method, path string, value any) (int, json.RawMessage, error) {
	body, _ := json.Marshal(value)
	if value == nil {
		body = nil
	}
	request, e := http.NewRequestWithContext(ctx, method, h.base+path, bytes.NewReader(body))
	if e != nil {
		return 0, nil, e
	}
	request.Header.Set("Origin", h.base)
	request.Header.Set("Content-Type", "application/json")
	response, e := h.client.Do(request)
	if e != nil {
		h.record("mps_http_error", map[string]any{"method": method, "path": request.URL.Path, "error_type": fmt.Sprintf("%T", e)})
		return 0, nil, e
	}
	defer response.Body.Close()
	raw, e := io.ReadAll(io.LimitReader(response.Body, 16<<20))
	if e != nil {
		return response.StatusCode, nil, e
	}
	var clean any
	_ = json.Unmarshal(raw, &clean)
	entry := map[string]any{"method": method, "path": request.URL.Path, "status": response.StatusCode, "response": mpsClean(clean)}
	if request.URL.Path != "/api/auth/login" {
		var in any
		_ = json.Unmarshal(body, &in)
		entry["request"] = mpsClean(in)
	}
	h.record("mps_http", entry)
	var envelope struct{ Data json.RawMessage }
	if json.Unmarshal(raw, &envelope) == nil && envelope.Data != nil {
		return response.StatusCode, envelope.Data, nil
	}
	return response.StatusCode, raw, nil
}
func (h *mpsMain) okMPS(method, path string, value any) json.RawMessage {
	h.t.Helper()
	status, raw, e := h.raw(h.ctx, method, path, value)
	if e != nil || status < 200 || status >= 300 {
		h.t.Fatalf("ordinary %s %s HTTP%d err=%v", method, strings.Split(path, "?")[0], status, e)
	}
	var result struct{ Success *bool }
	_ = json.Unmarshal(raw, &result)
	if result.Success != nil && !*result.Success {
		h.t.Fatal("ordinary business failure", method, path, string(raw))
	}
	return raw
}
func (h *mpsMain) configMPS(id string, want any) {
	h.t.Helper()
	got := h.okMPS("GET", "/api/plugins/"+id, nil)
	expected, _ := json.Marshal(want)
	var a, b any
	_ = json.Unmarshal(got, &a)
	_ = json.Unmarshal(expected, &b)
	x, _ := json.Marshal(a)
	y, _ := json.Marshal(b)
	if !bytes.Equal(x, y) {
		h.t.Fatal("source config mismatch", id, string(got), string(expected))
	}
}
func mpsWait(t *testing.T, name string, duration time.Duration, condition func() bool) {
	t.Helper()
	until := time.Now().Add(duration)
	for !condition() {
		if time.Now().After(until) {
			t.Fatal("timeout", name)
		}
		time.Sleep(50 * time.Millisecond)
	}
}
func (h *mpsMain) workersMPS() map[string]int {
	h.t.Helper()
	entries, e := os.ReadDir("/proc")
	if e != nil {
		h.t.Fatal("Linux container proc required", e)
	}
	out := map[string]int{}
	for _, entry := range entries {
		pid, e := strconv.Atoi(entry.Name())
		if e != nil {
			continue
		}
		status, e := os.ReadFile(filepath.Join("/proc", entry.Name(), "status"))
		if e != nil {
			continue
		}
		if !bytes.Contains(status, []byte(fmt.Sprintf("PPid:\t%d\n", h.cmd.Process.Pid))) {
			continue
		}
		command, e := os.ReadFile(filepath.Join("/proc", entry.Name(), "cmdline"))
		if e != nil {
			continue
		}
		parts := strings.Split(string(command), "\x00")
		if len(parts) == 0 {
			continue
		}
		relative, e := filepath.Rel(filepath.Join(h.dir, "plugin-packages"), parts[0])
		if e != nil || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
			continue
		}
		id := strings.Split(relative, string(filepath.Separator))[0]
		if strings.HasPrefix(id, mpsSource) {
			out[id] = pid
		}
	}
	h.record("mps_worker_pids", out)
	return out
}

type mpsPeer struct {
	artifactAuthority    string
	artifactDenials      int
	mu                   sync.Mutex
	valid                bool
	mode                 string
	requests             int
	handshakes           []map[string]any
	proxySources         map[string]bool
	connects             int
	unexpected           []string
	cert, bad, proxyCert tls.Certificate
	ca                   string
	server, proxy        *httptest.Server
	release              chan struct{}
	entered              chan struct{}
	sockets              map[net.Conn]bool
}

func newMPSPeer(t *testing.T, dir string) *mpsPeer {
	t.Helper()
	if os.Getenv("MPS_NAMESPACE_OWNED") != "1" {
		t.Fatal("Root isolated namespace required; no local/global hosts edits")
	}
	if os.Getuid() != 1000 {
		t.Fatal("owned container uid1000 required")
	}
	ips, e := net.LookupIP(mpsTarget)
	if e != nil || len(ips) != 1 || !ips[0].Equal(net.ParseIP("127.0.0.1")) {
		t.Fatal("fixed source target must resolve only owned namespace loopback", ips, e)
	}
	rootKey, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	now := time.Now()
	root := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "Owned MPS public probe CA"}, NotBefore: now.Add(-time.Minute), NotAfter: now.AddDate(1, 0, 0), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature}
	der, e := x509.CreateCertificate(rand.Reader, root, root, &rootKey.PublicKey, rootKey)
	if e != nil {
		t.Fatal(e)
	}
	makeCert := func(serial int64, signer *ecdsa.PrivateKey, parent *x509.Certificate) tls.Certificate {
		key, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		if e != nil {
			t.Fatal(e)
		}
		leaf := &x509.Certificate{SerialNumber: big.NewInt(serial), Subject: pkix.Name{CommonName: mpsTarget}, DNSNames: []string{mpsTarget, "localhost"}, IPAddresses: []net.IP{net.ParseIP("127.0.0.1")}, NotBefore: now.Add(-time.Minute), NotAfter: now.Add(90 * 24 * time.Hour), ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}, KeyUsage: x509.KeyUsageDigitalSignature}
		b, e := x509.CreateCertificate(rand.Reader, leaf, parent, &key.PublicKey, signer)
		if e != nil {
			t.Fatal(e)
		}
		return tls.Certificate{Certificate: [][]byte{b}, PrivateKey: key}
	}
	p := &mpsPeer{valid: true, mode: "ok", proxySources: map[string]bool{}, sockets: map[net.Conn]bool{}, release: make(chan struct{}), entered: make(chan struct{}, 1)}
	p.cert = makeCert(2, rootKey, root)
	p.proxyCert = makeCert(3, rootKey, root)
	badKey, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	badRoot := *root
	badRoot.Subject.CommonName = "Untrusted owned MPS CA"
	badRoot.SerialNumber = big.NewInt(9)
	p.bad = makeCert(10, badKey, &badRoot)
	ca := os.Getenv("MPS_OWNED_CA_FILE")
	if ca == "" {
		ca = filepath.Join(dir, "owned-ca.pem")
	}
	ca, e = filepath.Abs(ca)
	if e != nil {
		t.Fatal(e)
	}
	relative, e := filepath.Rel(dir, ca)
	if e != nil || strings.HasPrefix(relative, "..") {
		t.Fatal("public CA must be within new owned runtime")
	}
	before, e := os.Stat(ca)
	if e != nil {
		t.Fatal("Root must precreate CA file inode for read-only container system-CA bind", e)
	}
	f, e := os.OpenFile(ca, os.O_WRONLY|os.O_TRUNC, 0600)
	if e != nil {
		t.Fatal(e)
	}
	e = pem.Encode(f, &pem.Block{Type: "CERTIFICATE", Bytes: der})
	closeErr := f.Close()
	after, statErr := os.Stat(ca)
	if e != nil || closeErr != nil || statErr != nil || !os.SameFile(before, after) {
		t.Fatal("CA must be public PEM write to same inode, never rename", e, closeErr, statErr)
	}
	p.ca = ca
	p.server = httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		p.requests++
		sequence := p.requests
		mode := p.mode
		if r.Host != mpsTarget || r.URL.Path != "/status" || r.Header.Get("Authorization") != "" || r.Header.Get("Cookie") != "" || r.Header.Get("Proxy-Authorization") != "" {
			p.unexpected = append(p.unexpected, "noncanonical origin request")
		}
		p.mu.Unlock()
		if mode == "slow6" {
			select {
			case <-r.Context().Done():
				return
			case <-time.After(6 * time.Second):
			}
		}
		if mode == "hold" {
			select {
			case p.entered <- struct{}{}:
			default:
			}
			select {
			case <-p.release:
			case <-r.Context().Done():
				return
			}
		}
		w.Header().Set("Server", "Owned-MPS-Nginx")
		w.Header().Set("Content-Type", "text/plain")
		if mode == "undefined" {
			w.Header().Set("Content-Type", "text/plain; charset=undefined")
		}
		if mode == "503" {
			w.WriteHeader(503)
		}
		if mode == "broken" {
			_, _ = io.WriteString(w, "owned invalid status")
			return
		}
		_, _ = fmt.Fprintf(w, "Active connections: 12\nserver accepts handled requests\n%d %d %d\nReading:2 Writing:3 Waiting:7\n", 1000+sequence, 995+sequence, 12345+10*sequence)
	}))
	listener, e := net.Listen("tcp", "127.0.0.1:443")
	if e != nil {
		t.Fatal("isolated namespace low443bind required", e)
	}
	p.server.Listener = listener
	p.server.TLS = &tls.Config{Certificates: []tls.Certificate{p.cert}, GetCertificate: func(hello *tls.ClientHelloInfo) (*tls.Certificate, error) {
		p.mu.Lock()
		defer p.mu.Unlock()
		p.handshakes = append(p.handshakes, map[string]any{"at": time.Now().UTC(), "sni": hello.ServerName, "proxy_origin_leg": p.proxySources[hello.Conn.RemoteAddr().String()], "trusted_fixture": p.valid})
		if hello.ServerName != mpsTarget {
			p.unexpected = append(p.unexpected, "noncanonical TLS SNI")
		}
		if p.valid {
			return &p.cert, nil
		}
		return &p.bad, nil
	}}
	p.server.StartTLS()
	p.proxy = httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		if r.Method != "CONNECT" && r.URL.Host == p.artifactAuthority && (r.URL.Path == "/index" || r.URL.Path == "/worker") {
			p.artifactDenials++
			p.mu.Unlock()
			http.Error(w, "owned artifact uses existing direct fallback", 502)
			return
		}
		p.connects++
		if r.Method != "CONNECT" || r.Host != mpsTarget+":443" {
			p.unexpected = append(p.unexpected, "denied noncanonical CONNECT")
			p.mu.Unlock()
			http.Error(w, "denied", 403)
			return
		}
		p.mu.Unlock()
		upstream, e := net.Dial("tcp", "127.0.0.1:443")
		if e != nil {
			http.Error(w, "owned peer unavailable", 502)
			return
		}
		connection, rw, e := w.(http.Hijacker).Hijack()
		if e != nil {
			upstream.Close()
			return
		}
		p.mu.Lock()
		p.proxySources[upstream.LocalAddr().String()] = true
		p.sockets[connection] = true
		p.sockets[upstream] = true
		p.mu.Unlock()
		defer func() {
			connection.Close()
			upstream.Close()
			p.mu.Lock()
			delete(p.proxySources, upstream.LocalAddr().String())
			delete(p.sockets, connection)
			delete(p.sockets, upstream)
			p.mu.Unlock()
		}()
		_, _ = rw.WriteString("HTTP/1.1 200 Connection Established\r\n\r\n")
		_ = rw.Flush()
		go func() { _, _ = io.Copy(upstream, connection); upstream.Close() }()
		_, _ = io.Copy(connection, upstream)
	}))
	p.proxy.TLS = &tls.Config{Certificates: []tls.Certificate{p.proxyCert}}
	p.proxy.StartTLS()
	t.Cleanup(func() {
		p.mu.Lock()
		for c := range p.sockets {
			c.Close()
		}
		p.mu.Unlock()
		p.proxy.Close()
		p.server.Close()
	})
	return p
}
func (p *mpsPeer) set(mode string, valid bool) {
	p.mu.Lock()
	p.mode = mode
	p.valid = valid
	p.mu.Unlock()
}
func (p *mpsPeer) counts() (int, int) {
	p.mu.Lock()
	defer p.mu.Unlock()
	direct := 0
	for _, h := range p.handshakes {
		if !h["proxy_origin_leg"].(bool) {
			direct++
		}
	}
	return p.requests, direct
}
func (p *mpsPeer) report() map[string]any {
	p.mu.Lock()
	defer p.mu.Unlock()
	return map[string]any{"classification": "owned namespace hosts+real TLS443+strict HTTPS CONNECT; not public DNS/probe availability", "requests": p.requests, "connects": p.connects, "owned_artifact_denials_for_existing_direct_fallback": p.artifactDenials, "handshakes": append([]map[string]any{}, p.handshakes...), "unexpected": append([]string{}, p.unexpected...), "keys": "memory only; CA public file same inode; system trust bind only this container"}
}
func (p *mpsPeer) assert(t *testing.T) {
	t.Helper()
	p.mu.Lock()
	defer p.mu.Unlock()
	if len(p.unexpected) > 0 || p.requests == 0 || p.connects == 0 {
		t.Fatal("owned namespace network boundary", p.unexpected, p.requests, p.connects)
	}
}

func (p *mpsPeer) allowArtifact(raw string) {
	u, e := url.Parse(raw)
	if e != nil {
		panic(e)
	}
	p.mu.Lock()
	p.artifactAuthority = u.Host
	p.mu.Unlock()
}
