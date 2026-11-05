package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/mpserverstatus"
)

// Real executable worker + unchanged SDK admission/budgets + real owned
// HTTPS and strict CONNECT proxy. The HostHandler resources/identity are
// synthetic; this is not ordinary Main/browser/platform clone acceptance.
func TestStandaloneNativeWorkerBudgetsAndLifecycle(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	work, e := filepath.Abs("../../work/migration-20261105/mpserverstatus-preparation")
	if e != nil {
		t.Fatal(e)
	}
	if e = os.MkdirAll(work, 0700); e != nil {
		t.Fatal(e)
	}
	dir, e := os.MkdirTemp(work, "worker-")
	if e != nil {
		t.Fatal(e)
	}
	defer os.RemoveAll(dir)
	binary := filepath.Join(dir, "mp-server-status")
	args := []string{"build", "-trimpath", "-buildvcs=false", "-o", binary}
	if workerRace {
		args = append(args, "-race")
	}
	args = append(args, ".")
	if out, e := exec.CommandContext(ctx, "go", args...).CombinedOutput(); e != nil {
		t.Fatalf("build %v: %s", e, out)
	}
	raw, e := exec.CommandContext(ctx, binary, "--manifest").Output()
	if e != nil {
		t.Fatal(e)
	}
	var actual sdk.Manifest
	if e = json.Unmarshal(raw, &actual); e != nil || !reflect.DeepEqual(actual, mpserverstatus.Manifest()) {
		t.Fatal("manifest", e)
	}
	var networkRequests, unexpected, late atomic.Int32
	var blocked, retireBlock atomic.Bool
	retireEntered := make(chan struct{}, 1)
	retireClosed := make(chan struct{}, 1)
	entered := make(chan struct{}, 1)
	release := make(chan struct{})
	peer := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Host != "movie-pilot.org" || r.URL.Path != "/status" || r.Header.Get("Authorization") != "" || r.Header.Get("Cookie") != "" {
			unexpected.Add(1)
			http.Error(w, "unexpected", 400)
			return
		}
		if r.Header.Get("Accept-Encoding") != "gzip, deflate, br" || r.Header.Get("User-Agent") != "python-urllib3/2.7.0" {
			unexpected.Add(1)
		}
		id := networkRequests.Add(1)
		if retireBlock.Load() {
			select {
			case retireEntered <- struct{}{}:
			default:
			}
			<-r.Context().Done()
			select {
			case retireClosed <- struct{}{}:
			default:
			}
			return
		}
		if blocked.Load() {
			select {
			case entered <- struct{}{}:
			default:
			}
			select {
			case <-r.Context().Done():
				return
			case <-release:
			}
		}
		w.Header().Set("Content-Type", "text/plain")
		_, _ = fmt.Fprintf(w, "Active connections: 12\nserver accepts handled requests\n1000 995 %d\nReading: 2 Writing: 3 Waiting: 7\n", 12345+id)
	}))
	defer peer.Close()
	var socketMu sync.Mutex
	sockets := []net.Conn{}
	proxy := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "CONNECT" || r.Host != "movie-pilot.org:443" {
			unexpected.Add(1)
			http.Error(w, "denied", 403)
			return
		}
		upstream, e := net.Dial("tcp", peer.Listener.Addr().String())
		if e != nil {
			http.Error(w, "owned peer unavailable", 502)
			return
		}
		connection, rw, e := w.(http.Hijacker).Hijack()
		if e != nil {
			upstream.Close()
			return
		}
		socketMu.Lock()
		sockets = append(sockets, connection, upstream)
		socketMu.Unlock()
		_, _ = rw.WriteString("HTTP/1.1 200 Connection Established\r\n\r\n")
		_ = rw.Flush()
		go func() { defer connection.Close(); defer upstream.Close(); _, _ = io.Copy(upstream, connection) }()
		_, _ = io.Copy(connection, upstream)
		connection.Close()
		upstream.Close()
	}))
	defer proxy.Close()
	defer func() {
		socketMu.Lock()
		defer socketMu.Unlock()
		for _, c := range sockets {
			_ = c.Close()
		}
	}()
	identity := sdk.Identity{PluginID: "MPServerStatus", InstanceID: "MPServerStatus_owned_clone", Version: mpserverstatus.Version}
	start := func(generation int64) *sdk.Client {
		t.Helper()
		client, e := (sdk.Runner{Timeout: 5 * time.Second, ConcurrentCalls: true, RequireConcurrent: true}).Start(ctx, sdk.Command{Path: binary}, actual, sdk.SessionBinding{Identity: identity, Generation: generation})
		if e != nil {
			t.Fatal(e)
		}
		return client
	}
	client := start(1)
	stop := func(c *sdk.Client) {
		t.Helper()
		shutdown, done := context.WithTimeout(context.Background(), 3*time.Second)
		defer done()
		if e := c.Stop(shutdown); e != nil {
			t.Error(e)
		}
	}
	defer func() {
		if client != nil {
			stop(client)
		}
	}()
	type observation struct {
		Method     string `json:"method"`
		SDKRPC     int    `json:"sdk_result_host_calls"`
		RPC        int    `json:"host_calls"`
		Start, End time.Time
	}
	var mu sync.Mutex
	observations := []observation{}
	totalRPC := 0
	invoke := func(callCtx context.Context, method string, input any) (sdk.RunResult, error) {
		data, _ := json.Marshal(input)
		alive := new(atomic.Bool)
		alive.Store(true)
		begin := time.Now()
		var phaseRPC atomic.Int32
		host := func(call context.Context, got sdk.Identity, method string, raw json.RawMessage) (json.RawMessage, error) {
			if got != identity || !alive.Load() || call.Err() != nil {
				late.Add(1)
				return nil, errors.New("expired or incorrect source scope")
			}
			mu.Lock()
			totalRPC++
			phaseRPC.Add(1)
			mu.Unlock()
			switch method {
			case sdk.NetworkProxyReadCapability:
				return json.Marshal(sdk.NetworkProxySettingsV1{SchemaVersion: 1, Proxies: map[string]string{"https": "http://must-not-use.invalid:9"}, Environment: []string{"https_proxy=" + proxy.URL, "no_proxy="}})
			case sdk.LogWriteCapability:
				var entry sdk.LogEntryV1
				if e := json.Unmarshal(raw, &entry); e != nil {
					return nil, e
				}
				if e := entry.Validate(); e != nil {
					return nil, e
				}
				return json.RawMessage(`null`), nil
			}
			return nil, errors.New("unexpected resource " + method)
		}
		out, e := client.CallWithOptions(callCtx, method, data, host, sdk.CallOptions{CallerDeadlineOnly: true})
		alive.Store(false)
		mu.Lock()
		observations = append(observations, observation{Method: method, RPC: int(phaseRPC.Load()), SDKRPC: out.HostCalls, Start: begin, End: time.Now()})
		mu.Unlock()
		return out, e
	}
	call := func(method string, input any) sdk.RunResult {
		t.Helper()
		out, e := invoke(ctx, method, input)
		if e != nil {
			t.Fatal(method, e)
		}
		return out
	}
	call("init", map[string]any{"enable": true, "onlyonce": true})
	form := call("get_form", nil)
	if !strings.Contains(string(form.Result), `"enable":true`) {
		t.Fatal(string(form.Result))
	}
	first := call("get_dashboard", nil)
	if !strings.Contains(string(first.Result), "待刷新") {
		t.Fatal("first sample replayed", string(first.Result))
	}
	// More than the SDK's original lifetime 256 RPC and 64 callbacks, without
	// changing budgets or introducing private executors/background admissions.
	var wg sync.WaitGroup
	failures := make(chan error, 8)
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 20; j++ {
				out, e := invoke(ctx, "get_dashboard", nil)
				if e != nil {
					failures <- e
					return
				}
				if !strings.Contains(string(out.Result), "服务状态正常") {
					failures <- fmt.Errorf("not a business success: %s", out.Result)
					return
				}
			}
		}()
	}
	wg.Wait()
	close(failures)
	for e := range failures {
		t.Error(e)
	}
	call("init", map[string]any{"enable": false})
	before := networkRequests.Load()
	page := call("get_page", nil)
	if !strings.Contains(string(page.Result), "插件未启用") || networkRequests.Load() != before {
		t.Fatal("disabled page probed")
	}
	call("get_dashboard", nil)
	if networkRequests.Load() != before+1 {
		t.Fatal("source disabled dashboard incorrectly gated")
	}
	// A source stop method returns immediately and leaves an already executing
	// request alone; reinit also does not cancel it. Scope retirement does.
	blocked.Store(true)
	pendingBegin := time.Now()
	var pendingRPC atomic.Int32
	pendingAlive := new(atomic.Bool)
	pendingAlive.Store(true)
	pending, e := client.StartCallWithAdmission(ctx, ctx, "get_dashboard", nil, func(call context.Context, got sdk.Identity, method string, raw json.RawMessage) (json.RawMessage, error) {
		if got != identity || call.Err() != nil || !pendingAlive.Load() {
			late.Add(1)
			return nil, errors.New("expired or incorrect pending scope")
		}
		mu.Lock()
		totalRPC++
		pendingRPC.Add(1)
		mu.Unlock()
		switch method {
		case sdk.NetworkProxyReadCapability:
			return json.Marshal(sdk.NetworkProxySettingsV1{SchemaVersion: 1, Environment: []string{"https_proxy=" + proxy.URL}})
		case sdk.LogWriteCapability:
			return json.RawMessage(`null`), nil
		}
		return nil, errors.New("unexpected")
	}, sdk.CallOptions{CallerDeadlineOnly: true})
	if e != nil {
		t.Fatal(e)
	}
	select {
	case <-entered:
	case <-ctx.Done():
		t.Fatal(ctx.Err())
	}
	call("stop_service", nil)
	call("init", map[string]any{"enable": false})
	close(release)
	out, e := pending.Wait()
	pendingAlive.Store(false)
	mu.Lock()
	observations = append(observations, observation{Method: "get_dashboard_pending_reinit", RPC: int(pendingRPC.Load()), SDKRPC: out.HostCalls, Start: pendingBegin, End: time.Now()})
	mu.Unlock()
	if e != nil || !strings.Contains(string(out.Result), "服务状态正常") {
		t.Fatal("source active request lost after stop/reinit", e)
	}
	blocked.Store(false)
	stop(client)
	client = nil
	// New worker generation starts with no old sample, callback or identity
	// state. It still serves the source dashboard without the page enable gate.
	client = start(2)
	call("init", map[string]any{"enable": false})
	fresh := call("get_dashboard", nil)
	if !strings.Contains(string(fresh.Result), "待刷新") {
		t.Fatal("cold sample replay")
	}
	// Retiring the worker must revoke an active native network call and close
	// its owned tunnel. There are no source timer queues/background callbacks.
	retireBlock.Store(true)
	retired := make(chan error, 1)
	go func() { _, e := invoke(ctx, "get_dashboard", nil); retired <- e }()
	select {
	case <-retireEntered:
	case <-ctx.Done():
		t.Fatal(ctx.Err())
	}
	stop(client)
	select {
	case e := <-retired:
		if e == nil {
			t.Fatal("retired call reported success")
		}
	case <-time.After(time.Second):
		t.Fatal("active native request survived worker retirement")
	}
	client = nil
	select {
	case <-retireClosed:
	case <-time.After(time.Second):
		t.Fatal("worker retirement left owned HTTP socket alive")
	}
	if unexpected.Load() != 0 || late.Load() != 0 {
		t.Fatal("unowned network or expired HostCaller", unexpected.Load(), late.Load())
	}
	mu.Lock()
	defer mu.Unlock()
	max := 0
	sumRPC := 0
	for _, o := range observations {
		sumRPC += o.RPC
		if o.RPC > max {
			max = o.RPC
		}
		if o.RPC > 64 {
			t.Fatal("unchanged per-call budget exceeded", o)
		}
	}
	if sumRPC != totalRPC {
		t.Fatal("callback RPC accounting incomplete", sumRPC, totalRPC)
	}
	if totalRPC <= 256 || len(observations) <= 64 || max != 3 {
		t.Fatal("insufficient actual SDK budget observations", totalRPC, len(observations), max)
	}
	evidence := map[string]any{"classification": "real standalone executable and original SDK budgets; real owned TLS+strict CONNECT; synthetic HostHandler/instance binding; no ordinary Main/browser acceptance", "host_calls": totalRPC, "calls": len(observations), "max_host_calls": max, "owned_http_requests": networkRequests.Load(), "unexpected_network": unexpected.Load(), "expired_host_calls": late.Load(), "observations": observations}
	encoded, _ := json.MarshalIndent(evidence, "", "  ")
	filename := "worker-budget-observations-normal.json"
	if workerRace {
		filename = "worker-budget-observations-race.json"
	}
	if e = os.WriteFile(filepath.Join(work, filename), append(encoded, '\n'), 0600); e != nil {
		t.Fatal(e)
	}
}
