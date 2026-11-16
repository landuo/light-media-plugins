package app

import (
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
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

func ocrDomainCall(t *testing.T, p *originalPluginInstance, method string, input, out any) error {
	t.Helper()
	raw, e := json.Marshal(input)
	if e != nil {
		t.Fatal(e)
	}
	result, e := p.callOriginalMethod(context.Background(), method, raw)
	if e == nil && out != nil {
		e = json.Unmarshal(result.Result, out)
	}
	return e
}
func TestSourceOCRJSONDomainActualSDKWire(t *testing.T) {
	if runtime.GOOS != "linux" || os.Getuid() != 1000 || os.Getenv("OCR_DOMAIN_NETWORK_NONE") != "1" {
		t.Fatal("owned Linux UID1000 networknone required")
	}
	ifs, e := net.Interfaces()
	if e != nil {
		t.Fatal(e)
	}
	for _, v := range ifs {
		if v.Flags&net.FlagUp != 0 && v.Flags&net.FlagLoopback == 0 {
			t.Fatal("externalinterface")
		}
	}
	if e = os.MkdirAll("/config/tmp", 0700); e != nil {
		t.Fatal(e)
	}
	for _, k := range []string{"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"} {
		t.Setenv(k, "")
	}
	type wireRow struct {
		Method, Path, Host  string
		Cookie, UA, Referer *string
		Body                string
	}
	type failure struct{ Type, Message string }
	type operation struct {
		Value json.RawMessage
		Error *failure
	}
	type semanticRow struct {
		Name, Body  string
		HelperType  string `json:"helper_type"`
		Truth       bool
		HelperError *failure `json:"helper_error"`
		Operations  map[string]operation
		Wire        []wireRow
	}
	type flowRow struct {
		Name           string
		Site           map[string]any
		ValueJSON      string `json:"value_json"`
		Result         []any
		Error          *failure
		Wire           []wireRow
		ConnectTargets []string `json:"connect_targets"`
	}
	evidence := os.Getenv("OCR_DOMAIN_EVIDENCE_DIR")
	semantics := []semanticRow{}
	for _, name := range []string{"source.stdout", "depth-source.stdout", "empty-depth-source.stdout"} {
		raw, e := os.ReadFile(filepath.Join(evidence, name))
		if e != nil {
			t.Fatal(e)
		}
		var source struct{ Rows []semanticRow }
		if json.Unmarshal(raw, &source) != nil {
			t.Fatal("source semanticJSON")
		}
		semantics = append(semantics, source.Rows...)
	}
	if len(semantics) != 60 {
		t.Fatal(len(semantics))
	}
	raw, e := os.ReadFile(filepath.Join(evidence, "hdsky-source.stdout"))
	if e != nil {
		t.Fatal(e)
	}
	var flow struct{ Rows []flowRow }
	if json.Unmarshal(raw, &flow) != nil || len(flow.Rows) != 14 {
		t.Fatal("source14 full HDSky")
	}
	key, e := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	cert := &x509.Certificate{SerialNumber: big.NewInt(time.Now().UnixNano()), Subject: pkix.Name{CommonName: "Owned OCR JSON CA"}, NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature, DNSNames: []string{"hdsky.me"}}
	der, e := x509.CreateCertificate(rand.Reader, cert, cert, &key.PublicKey, key)
	if e != nil {
		t.Fatal(e)
	}
	ca := filepath.Join(t.TempDir(), "ca.pem")
	if e = os.WriteFile(ca, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), 0600); e != nil {
		t.Fatal(e)
	}
	t.Setenv("SSL_CERT_FILE", ca)
	var mu sync.Mutex
	seen := []wireRow{}
	connects := 0
	responseBody := ""
	flowMode := false
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		record := wireRow{Method: r.Method, Path: r.URL.RequestURI(), Host: r.Host, Body: string(body)}
		if v, ok := r.Header["Cookie"]; ok && len(v) > 0 {
			record.Cookie = &v[0]
		}
		if v, ok := r.Header["User-Agent"]; ok && len(v) > 0 {
			record.UA = &v[0]
		}
		if v, ok := r.Header["Referer"]; ok && len(v) > 0 {
			record.Referer = &v[0]
		}
		mu.Lock()
		seen = append(seen, record)
		data := responseBody
		isFlow := flowMode
		mu.Unlock()
		contentType := "application/json"
		switch {
		case r.URL.Path == "/captcha/base64":
		case r.URL.Path == "/submit":
			data = `{"success":true}`
		case isFlow && r.URL.Path == "/":
			data = "<html><body>Owned authenticated lab</body></html>"
			contentType = "text/html"
		case isFlow && r.URL.Path == "/image_code_ajax.php":
			data = `{"success":true,"code":"ownedhash"}`
		case isFlow && strings.HasPrefix(r.URL.Path, "/image.php"):
			data = "owned-image"
			contentType = "text/html"
		case isFlow && r.URL.Path == "/showup.php":
			data = `{"success":true}`
		default:
			t.Error("unexpected owned route", r.Method, r.URL.Path)
		}
		w.Header().Set("Content-Type", contentType)
		w.WriteHeader(200)
		io.WriteString(w, data)
	})
	image := httptest.NewUnstartedServer(handler)
	image.TLS = &tls.Config{Certificates: []tls.Certificate{{Certificate: [][]byte{der}, PrivateKey: key}}}
	image.StartTLS()
	defer image.Close()
	ocr := httptest.NewServer(handler)
	defer ocr.Close()
	t.Setenv("OCR_HOST", ocr.URL)
	proxy := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		connects++
		mu.Unlock()
		if r.Method != "CONNECT" || r.Host != "hdsky.me:443" {
			http.Error(w, "denied", 403)
			return
		}
		up, e := net.Dial("tcp", image.Listener.Addr().String())
		if e != nil {
			t.Error(e)
			return
		}
		down, buf, e := w.(http.Hijacker).Hijack()
		if e != nil {
			up.Close()
			t.Error(e)
			return
		}
		buf.WriteString("HTTP/1.1 200 Connection Established\r\n\r\n")
		buf.Flush()
		done := make(chan struct{})
		go func() { io.Copy(up, buf); up.Close(); close(done) }()
		io.Copy(down, up)
		down.Close()
		up.Close()
		<-done
	}))
	defer proxy.Close()
	a := newTestApp(t)
	cookie := setupTestAdmin(t, a)
	manifest := installOwnedResourceProcessWorker(t, a, cookie, os.Getenv("OCR_DOMAIN_FIXTURE_BINARY"))
	object := originalBaseSDKLoaded(t, a, manifest.PluginID)
	t.Setenv("HTTPS_PROXY", proxy.URL)
	t.Setenv("https_proxy", proxy.URL)
	t.Setenv("NO_PROXY", "127.0.0.1")
	t.Setenv("no_proxy", "127.0.0.1")
	observations := []map[string]any{}
	defer func() {
		raw, _ := json.MarshalIndent(observations, "", "  ")
		if out := os.Getenv("OCR_DOMAIN_OUTPUT"); out != "" {
			os.WriteFile(out, raw, 0600)
		}
	}()
	normalize := func(rows []wireRow, semantic bool) []wireRow {
		out := append([]wireRow{}, rows...)
		for i := range out {
			if out[i].Path == "/captcha/base64" {
				out[i].Host = "owned-ocr-service:ephemeral-port"
			}
			if semantic && out[i].Path == "/submit" {
				out[i].Host = "owned-source-submit-endpoint"
			}
		}
		return out
	}
	for _, r := range semantics {
		t.Run("semantic/"+r.Name, func(t *testing.T) {
			site := map[string]any{"id": 7, "name": "Owned", "url": "https://hdsky.me/", "ua": nil, "cookie": nil, "proxy": false}
			if e = ocrDomainCall(t, object, "set_custom", map[string]any{"enabled": true, "sites": []any{site}}, nil); e != nil {
				t.Fatal(e)
			}
			mu.Lock()
			seen = nil
			responseBody = r.Body
			flowMode = false
			before := connects
			mu.Unlock()
			var got struct {
				HelperError       string `json:"helper_error"`
				Type              string
				Truth             bool
				StrCodepoints     []int `json:"str_codepoints"`
				Repr              string
				Len               *int
				LenError          string `json:"len_error"`
				FormError         string `json:"form_error"`
				FormStatus        *int   `json:"form_status"`
				FormTransportNone bool   `json:"form_transport_none"`
			}
			e = ocrDomainCall(t, object, "ocr_domain", map[string]string{"mode": "semantic"}, &got)
			mu.Lock()
			wire := normalize(seen, true)
			calls := connects - before
			mu.Unlock()
			want := normalize(r.Wire, true)
			observations = append(observations, map[string]any{"kind": "semantic", "name": r.Name, "result": got, "call_error": fmt.Sprint(e), "actualwire": wire, "sourcewire": want, "connects": calls})
			if e != nil {
				t.Fatal(e)
			}
			if r.HelperError != nil {
				if got.HelperError != r.HelperError.Message {
					t.Fatal("source helper error", got.HelperError, r.HelperError)
				}
			} else {
				points, e := sourceSiteJSONCodepoints(r.Operations["str"].Value)
				if e != nil {
					t.Fatal(e)
				}
				expected := []int{}
				for _, p := range points {
					expected = append(expected, int(p))
				}
				var repr string
				json.Unmarshal(r.Operations["repr"].Value, &repr)
				if got.HelperError != "" || got.Type != r.HelperType || got.Truth != r.Truth || !reflect.DeepEqual(got.StrCodepoints, expected) || got.Repr != repr {
					t.Fatal("source semantic value differs", got.Type, r.HelperType, got.HelperError)
				}
				if failure := r.Operations["len"].Error; failure != nil {
					if got.LenError != failure.Message {
						t.Fatal("source len error", got.LenError, failure)
					}
				} else {
					var length int
					json.Unmarshal(r.Operations["len"].Value, &length)
					if got.Len == nil || *got.Len != length || got.LenError != "" {
						t.Fatal("source len differs", got.Len, length)
					}
				}
				if failure := r.Operations["form"].Error; failure != nil {
					if got.FormError != failure.Message {
						t.Fatal("source form error", got.FormError, failure)
					}
				} else if got.FormError != "" || got.FormStatus == nil || *got.FormStatus != 200 || got.FormTransportNone {
					t.Fatal("form not actually submitted", got.FormError, got.FormStatus, got.FormTransportNone)
				}
			}
			submits := 0
			for _, w := range want {
				if w.Path == "/submit" {
					submits++
				}
			}
			if !reflect.DeepEqual(wire, want) || calls != submits {
				t.Fatalf("source actual wire differs reqs%d/%d CONNECT%d/%d", len(wire), len(want), calls, submits)
			}
		})
	}
	for _, r := range flow.Rows {
		t.Run("hdsky/"+r.Name, func(t *testing.T) {
			if e = ocrDomainCall(t, object, "set_custom", map[string]any{"enabled": true, "sites": []any{r.Site}}, nil); e != nil {
				t.Fatal(e)
			}
			mu.Lock()
			seen = nil
			responseBody = `{"result":` + r.ValueJSON + `}`
			flowMode = true
			before := connects
			mu.Unlock()
			var got struct {
				State          bool
				Message, Error string
			}
			started := time.Now()
			e = ocrDomainCall(t, object, "ocr_domain", map[string]string{"mode": "hdsky"}, &got)
			mu.Lock()
			wire := normalize(seen, false)
			calls := connects - before
			mu.Unlock()
			want := normalize(r.Wire, false)
			observations = append(observations, map[string]any{"kind": "hdsky", "name": r.Name, "result": got, "call_error": fmt.Sprint(e), "actualwire": wire, "sourcewire": want, "connects": calls, "seconds": time.Since(started).Seconds()})
			if e != nil {
				t.Fatal(e)
			}
			if r.Error != nil {
				if got.Error != r.Error.Message {
					t.Fatal("original HDSky error", got.Error, r.Error)
				}
			} else if got.Error != "" || got.State != r.Result[0] || got.Message != r.Result[1] {
				t.Fatal("original HDSky result", got, r.Result)
			}
			if !reflect.DeepEqual(wire, want) || calls != len(r.ConnectTargets) {
				t.Fatalf("full source HDSky wire differs reqs%d/%d CONNECT%d/%d", len(wire), len(want), calls, len(r.ConnectTargets))
			}
		})
	}
}
