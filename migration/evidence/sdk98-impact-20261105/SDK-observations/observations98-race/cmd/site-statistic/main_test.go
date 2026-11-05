package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	plugins "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/sitestatistic"
)

// Real executable/SDK admission and default budgets; resources are synthetic.
func TestStandaloneWorkerFreshDateBudgetsAndRealOneShot(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	work, e := filepath.Abs("/Users/accidia/projects/light-media-plugins/work/migration-20261105/sdk98-impact-20261105/variant98/site-observations")
	if e != nil {
		t.Fatal(e)
	}
	if e = os.MkdirAll(work, 0700); e != nil {
		t.Fatal(e)
	}
	dir, e := os.MkdirTemp(work, "worker-test-")
	if e != nil {
		t.Fatal(e)
	}
	defer os.RemoveAll(dir)
	binary := filepath.Join(dir, "site-statistic")
	args := []string{"build", "-trimpath", "-buildvcs=false", "-o", binary}
	if workerRace {
		args = append(args, "-race")
	}
	args = append(args, ".")
	if out, e := exec.CommandContext(ctx, "go", args...).CombinedOutput(); e != nil {
		t.Fatalf("build %v: %s", e, out)
	}
	manifest := sitestatistic.Manifest()
	raw, e := exec.CommandContext(ctx, binary, "--manifest").Output()
	if e != nil {
		t.Fatal(e)
	}
	var actual plugins.Manifest
	if e = json.Unmarshal(raw, &actual); e != nil || !reflect.DeepEqual(actual, manifest) {
		t.Fatal("manifest", e)
	}
	identity := plugins.Identity{PluginID: "SiteStatistic", InstanceID: "SiteStatistic_owned_clone", Version: "1.9.7"}
	client, e := (plugins.Runner{Timeout: 5 * time.Second, ConcurrentCalls: true, RequireConcurrent: true}).Start(ctx, plugins.Command{Path: binary}, manifest, plugins.SessionBinding{Identity: identity, Generation: 1})
	if e != nil {
		t.Fatal(e)
	}
	defer func() {
		stop, done := context.WithTimeout(context.Background(), 3*time.Second)
		defer done()
		if e := client.Stop(stop); e != nil {
			t.Errorf("stop %v", e)
		}
	}()
	type phase struct {
		Method     string `json:"method"`
		Calls      int    `json:"host_calls"`
		Error      string `json:"error"`
		Start, End time.Time
	}
	var mu sync.Mutex
	phases := []phase{}
	events := []map[string]any{}
	totalRPC, dates, allCalls := 0, 0, 0
	admitted, completed := 0, 0
	latest := []plugins.SiteAccountHostRowV1{}
	at := time.Date(2026, 10, 16, 0, 0, 0, 0, time.UTC)
	for i := 0; i < 40; i++ {
		day := at.AddDate(0, 0, -8*i).Format("2006-01-02")
		fields, _ := json.Marshal(map[string]any{"id": i + 1, "name": fmt.Sprintf("Owned %03d", i), "domain": "owned.invalid", "updated_day": day, "username": "owned", "user_level": "User", "upload": float64(4000 - i), "download": 100.0, "ratio": 2.0, "bonus": 1.0, "seeding": 2.0, "seeding_size": 1024.0, "err_msg": ""})
		latest = append(latest, plugins.SiteAccountHostRowV1{SiteID: "owned-site", Fields: fields})
	}
	shot := make(chan time.Time, 2)
	var phaseHost func(string, *atomic.Bool) plugins.HostHandler
	phaseHost = func(label string, alive *atomic.Bool) plugins.HostHandler {
		return func(call context.Context, got plugins.Identity, method string, raw json.RawMessage) (json.RawMessage, error) {
			if got != identity || call.Err() != nil || !alive.Load() {
				return nil, errors.New("expired or wrong caller scope")
			}
			mu.Lock()
			totalRPC++
			events = append(events, map[string]any{"kind": "rpc", "phase": label, "method": method, "at": time.Now().UTC()})
			mu.Unlock()
			if method == plugins.BackgroundSubmitCapability {
				var in struct {
					Method  string
					Payload json.RawMessage
				}
				if e := json.Unmarshal(raw, &in); e != nil {
					return nil, e
				}
				fresh := new(atomic.Bool)
				fresh.Store(true)
				start := time.Now()
				mu.Lock()
				admitted++
				events = append(events, map[string]any{"kind": "child.admit", "phase": in.Method, "at": start})
				mu.Unlock()
				pending, e := client.StartCallWithAdmission(call, ctx, in.Method, in.Payload, phaseHost(in.Method, fresh), plugins.CallOptions{CallerDeadlineOnly: true})
				if e != nil {
					fresh.Store(false)
					return nil, e
				}
				go func() {
					out, e := pending.Wait()
					fresh.Store(false)
					message := ""
					if e != nil {
						message = e.Error()
					}
					mu.Lock()
					completed++
					phases = append(phases, phase{in.Method, out.HostCalls, message, start, time.Now()})
					events = append(events, map[string]any{"kind": "child.complete", "phase": in.Method, "at": time.Now()})
					mu.Unlock()
				}()
				return json.RawMessage(`{"accepted":true}`), nil
			}
			switch method {
			case plugins.SitesSourceAccountsCapability:
				var in plugins.SiteAccountHostRequestV1
				_ = json.Unmarshal(raw, &in)
				items := []plugins.SiteAccountHostRowV1{}
				if in.Latest {
					items = latest
				} else {
					mu.Lock()
					dates++
					mu.Unlock()
				}
				return json.Marshal(plugins.SiteAccountHostResultV1{SchemaVersion: 1, Items: items})
			case plugins.SitesReadCapability:
				return json.Marshal(plugins.SiteHostResultV1{SchemaVersion: 1, Items: []plugins.SiteHostRowV1{{ID: "owned-site", SourceID: 7, Domain: "owned.invalid", Name: "Owned", Enabled: true}}})
			case plugins.BaseUpdateConfig:
				return json.RawMessage(`false`), nil
			case plugins.SitesSourceRefreshAllCapability:
				mu.Lock()
				allCalls++
				mu.Unlock()
				shot <- time.Now()
				return json.Marshal(plugins.SiteSourceRefreshResultV1{SchemaVersion: 1, Data: json.RawMessage(`{}`)})
			case plugins.LogWriteCapability:
				return json.RawMessage(`null`), nil
			}
			return nil, errors.New("unexpected resource " + method)
		}
	}
	call := func(method string, input any) plugins.RunResult {
		t.Helper()
		payload, _ := json.Marshal(input)
		alive := new(atomic.Bool)
		alive.Store(true)
		start := time.Now()
		out, e := client.CallWithOptions(ctx, method, payload, phaseHost("owner:"+method, alive), plugins.CallOptions{CallerDeadlineOnly: true})
		alive.Store(false)
		if e != nil {
			t.Fatal(method, e)
		}
		mu.Lock()
		phases = append(phases, phase{method, out.HostCalls, "", start, time.Now()})
		events = append(events, map[string]any{"kind": "owner.complete", "phase": method, "at": time.Now()})
		mu.Unlock()
		return out
	}
	call("init", map[string]any{"enabled": true, "onlyonce": false})
	page := call("get_page", nil)
	if len(page.Result) == 0 {
		t.Fatal("no source page")
	}
	mu.Lock()
	if dates != 280 || totalRPC <= 256 {
		t.Fatal("source per-date pass not exercised", dates, totalRPC)
	}
	mu.Unlock()
	started := time.Now()
	call("init", map[string]any{"enabled": false, "onlyonce": true})
	call("stop_service", nil)
	select {
	case observed := <-shot:
		if observed.Sub(started) < 2900*time.Millisecond {
			t.Fatal("source date ran before three seconds", observed.Sub(started))
		}
	case <-ctx.Done():
		t.Fatal("source date lost after noop stop", ctx.Err())
	}
	deadline := time.Now().Add(3 * time.Second)
	for {
		mu.Lock()
		done := completed == admitted
		mu.Unlock()
		if done {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("child completion not joined")
		}
		time.Sleep(time.Millisecond)
	}
	mu.Lock()
	defer mu.Unlock()
	max := 0
	for _, p := range phases {
		if p.Calls > max {
			max = p.Calls
		}
		if p.Calls > 64 || p.Error != "" {
			t.Fatal("phase exceeded default budget or failed", p)
		}
	}
	if allCalls != 1 {
		t.Fatal("all refresh replayed", allCalls)
	}
	observation := map[string]any{"kind": "actual-independent-executable-SDK-worker-with-synthetic-resources", "worker_race_instrumented": workerRace, "default_max_host_calls": 64, "observed_max_host_calls": max, "total_rpc": totalRPC, "date_queries": dates, "returned_phases": phases, "events": events, "one_shot_clock": "real three seconds;no clock overlay"}
	data, _ := json.MarshalIndent(observation, "", "  ")
	if e := os.WriteFile(filepath.Join(work, "sdk-worker-observations.json"), append(data, '\n'), 0600); e != nil {
		t.Fatal(e)
	}
}
