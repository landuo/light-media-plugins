package integration

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"io"
	"math/big"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

// The registered source URL is retained. All CONNECT traffic is instead
// delivered to this owned loopback TLS peer. The isolated Main process trusts
// only this additional public test CA; certificate verification stays enabled.
type ownedASIHTTPS struct {
	origin, proxy, caFile string
	mu                    sync.Mutex
	wire                  []map[string]string
	connections           []net.Conn
	connects              []string
	proxyRequests         []map[string]string
	nextAttendance        *ownedAttendanceGate
}

type ownedAttendanceGate struct {
	entered, release chan struct{}
	once             sync.Once
}

func (g *ownedAttendanceGate) unblock() { g.once.Do(func() { close(g.release) }) }
func (p *ownedASIHTTPS) blockAttendance(t *testing.T) *ownedAttendanceGate {
	t.Helper()
	g := &ownedAttendanceGate{entered: make(chan struct{}), release: make(chan struct{})}
	p.mu.Lock()
	if p.nextAttendance != nil {
		p.mu.Unlock()
		t.Fatal("unused owned attendance gate")
	}
	p.nextAttendance = g
	p.mu.Unlock()
	t.Cleanup(g.unblock)
	return g
}

func newOwnedASIHTTPS(t *testing.T, dir string) *ownedASIHTTPS {
	t.Helper()
	p := &ownedASIHTTPS{origin: "https://hhanclub.net"}
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	cert := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "Owned ASI acceptance CA"}, DNSNames: []string{"hhanclub.net"}, NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
	der, err := x509.CreateCertificate(rand.Reader, cert, cert, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	public := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})
	private, err := x509.MarshalECPrivateKey(key)
	if err != nil {
		t.Fatal(err)
	}
	pair, err := tls.X509KeyPair(public, pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: private}))
	if err != nil {
		t.Fatal(err)
	}
	p.caFile = filepath.Join(dir, "owned-ca.pem")
	if err = os.WriteFile(p.caFile, public, 0600); err != nil {
		t.Fatal(err)
	}
	peer := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		p.wire = append(p.wire, map[string]string{"method": r.Method, "path": r.URL.RequestURI(), "cookie": r.Header.Get("Cookie"), "ua": r.Header.Get("User-Agent"), "host": r.Host})
		var gate *ownedAttendanceGate
		if r.URL.Path == "/attendance.php" {
			gate = p.nextAttendance
			p.nextAttendance = nil
		}
		p.mu.Unlock()
		if gate != nil {
			close(gate.entered)
			select {
			case <-gate.release:
			case <-r.Context().Done():
				return
			}
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		switch r.URL.Path {
		case "/attendance.php":
			io.WriteString(w, `<html><body><a href="logout.php">退出登录</a><div>签到成功</div></body></html>`)
		case "/":
			io.WriteString(w, `<html><body><a href="logout.php">退出登录</a></body></html>`)
		case "/favicon.ico":
			w.Header().Set("Content-Type", "image/x-icon")
			w.Write([]byte{0, 0, 1, 0})
		default:
			http.NotFound(w, r)
		}
	}))
	peer.TLS = &tls.Config{Certificates: []tls.Certificate{pair}, MinVersion: tls.VersionTLS12}
	peer.StartTLS()
	proxy := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p.mu.Lock()
		p.connects = append(p.connects, r.Host)
		p.proxyRequests = append(p.proxyRequests, map[string]string{"method": r.Method, "host": r.Host, "uri": r.RequestURI})
		p.mu.Unlock()
		if r.Method != "CONNECT" || r.Host != "hhanclub.net:443" {
			http.Error(w, "owned target only", http.StatusForbidden)
			return
		}
		upstream, err := net.DialTimeout("tcp", peer.Listener.Addr().String(), 2*time.Second)
		if err != nil {
			http.Error(w, "owned loopback unavailable", 502)
			return
		}
		client, rw, err := w.(http.Hijacker).Hijack()
		if err != nil {
			upstream.Close()
			t.Error(err)
			return
		}
		p.mu.Lock()
		p.connections = append(p.connections, client, upstream)
		p.mu.Unlock()
		if _, err = rw.WriteString("HTTP/1.1 200 Connection Established\r\n\r\n"); err != nil {
			client.Close()
			upstream.Close()
			return
		}
		if err = rw.Flush(); err != nil {
			client.Close()
			upstream.Close()
			return
		}
		go func() { _, _ = io.Copy(upstream, rw); upstream.Close() }()
		_, _ = io.Copy(client, upstream)
		client.Close()
	}))
	p.proxy = proxy.URL
	t.Cleanup(func() {
		p.mu.Lock()
		for _, c := range p.connections {
			_ = c.Close()
		}
		p.mu.Unlock()
		proxy.Close()
		peer.Close()
	})
	return p
}

func (p *ownedASIHTTPS) snapshot() ([]map[string]string, []string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	wire := append([]map[string]string(nil), p.wire...)
	connects := append([]string(nil), p.connects...)
	return wire, connects
}

func (p *ownedASIHTTPS) proxySnapshot() []map[string]string {
	p.mu.Lock()
	defer p.mu.Unlock()
	return append([]map[string]string(nil), p.proxyRequests...)
}

func TestOwnedASIHTTPSFixturePreflight(t *testing.T) {
	p := newOwnedASIHTTPS(t, t.TempDir())
	ca, err := os.ReadFile(p.caFile)
	if err != nil {
		t.Fatal(err)
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(ca) {
		t.Fatal("public owned CA")
	}
	proxy, err := url.Parse(p.proxy)
	if err != nil {
		t.Fatal(err)
	}
	transport := &http.Transport{Proxy: http.ProxyURL(proxy), TLSClientConfig: &tls.Config{RootCAs: roots, MinVersion: tls.VersionTLS12}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 3 * time.Second}
	req, _ := http.NewRequest("GET", p.origin+"/attendance.php", nil)
	req.Header.Set("Cookie", "owned_session=synthetic")
	req.Header.Set("User-Agent", "Owned-ASI/1")
	r, err := client.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	body, err := io.ReadAll(r.Body)
	r.Body.Close()
	if err != nil || r.StatusCode != 200 || !r.TLS.HandshakeComplete || string(body) != `<html><body><a href="logout.php">退出登录</a><div>签到成功</div></body></html>` {
		t.Fatal("actual TLS peer response", err)
	}
	r, err = client.Get("https://foreign.example.net/")
	if r != nil {
		r.Body.Close()
	}
	if err == nil {
		t.Fatal("foreign CONNECT unexpectedly accepted")
	}
	wire, connects := p.snapshot()
	if len(wire) != 1 || wire[0]["cookie"] != "owned_session=synthetic" || wire[0]["ua"] != "Owned-ASI/1" || wire[0]["path"] != "/attendance.php" || len(connects) != 2 || connects[0] != "hhanclub.net:443" || connects[1] != "foreign.example.net:443" {
		t.Fatal("fixture actual physical path differs", wire, connects)
	}
}
