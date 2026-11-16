package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"

	plugins "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/sitestatistic"
)

// This is an actual independently executing worker. The host resources are
// synthetic, so this establishes lifecycle/IPC behavior, not App/site acceptance.
func TestStandaloneSourceReadOwnerCancellationAndNoopStop(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	work, _ := filepath.Abs("/Users/accidia/projects/light-media-plugins/work/sites-review-20261105/notification-wire-addon/sdk-observations")
	dir, e := os.MkdirTemp(work, "lifecycle-worker-")
	if e != nil {
		t.Fatal(e)
	}
	defer os.RemoveAll(dir)
	binary := filepath.Join(dir, "site-statistic")
	args := []string{"build", "-trimpath", "-buildvcs=false", "-o", binary}
	if workerRace {
		args = append(args, "-race")
	}
	if out, e := exec.CommandContext(ctx, "go", append(args, ".")...).CombinedOutput(); e != nil {
		t.Fatalf("build: %v %s", e, out)
	}
	observations := []map[string]any{}
	for _, scenario := range []string{"queued-owner-cancel", "active-owner-cancel", "active-noop-stop-reinit", "pending-one-shot-session-retire"} {
		t.Run(scenario, func(t *testing.T) {
			client, e := (plugins.Runner{Timeout: 5 * time.Second, ConcurrentCalls: true, RequireConcurrent: true}).Start(ctx, plugins.Command{Path: binary}, sitestatistic.Manifest(), plugins.SessionBinding{Identity: plugins.Identity{PluginID: "SiteStatistic", InstanceID: "SiteStatistic_lifecycle_owned", Version: "1.9.7"}, Generation: 1})
			if e != nil {
				t.Fatal(e)
			}
			defer func() {
				stop, done := context.WithTimeout(context.Background(), 3*time.Second)
				defer done()
				if e := client.Stop(stop); e != nil {
					t.Errorf("join worker: %v", e)
				}
			}()
			type submission struct {
				Method  string
				Payload json.RawMessage
			}
			queued := make(chan submission, 8)
			children := make(chan *plugins.PendingCall, 8)
			entered := make(chan struct{}, 1)
			release := make(chan struct{})
			queryCanceled := make(chan struct{}, 1)
			var queries atomic.Int32
			var allRefreshes atomic.Int32
			var host plugins.HostHandler
			host = func(call context.Context, _ plugins.Identity, method string, raw json.RawMessage) (json.RawMessage, error) {
				switch method {
				case plugins.BaseUpdateConfig:
					return json.RawMessage(`false`), nil
				case plugins.SitesSourceRefreshAllCapability:
					allRefreshes.Add(1)
					return json.Marshal(plugins.SiteSourceRefreshResultV1{SchemaVersion: 1, Data: json.RawMessage(`{}`)})
				case plugins.BackgroundSubmitCapability:
					var in submission
					if e := json.Unmarshal(raw, &in); e != nil {
						return nil, e
					}
					if scenario == "queued-owner-cancel" {
						queued <- in
					} else {
						child, e := client.StartCallWithAdmission(call, ctx, in.Method, in.Payload, host, plugins.CallOptions{CallerDeadlineOnly: true})
						if e != nil {
							return nil, e
						}
						children <- child
					}
					return json.RawMessage(`{"accepted":true}`), nil
				case plugins.SitesReadCapability:
					return json.Marshal(plugins.SiteHostResultV1{SchemaVersion: 1, Items: []plugins.SiteHostRowV1{{ID: "owned", Name: "Owned", Domain: "owned.invalid", Enabled: true}}})
				case plugins.SitesSourceAccountsCapability:
					var in plugins.SiteAccountHostRequestV1
					_ = json.Unmarshal(raw, &in)
					if !in.Latest {
						if queries.Add(1) == 1 {
							entered <- struct{}{}
						}
						select {
						case <-release:
						case <-call.Done():
							queryCanceled <- struct{}{}
							return nil, call.Err()
						}
					}
					day := "2026-10-16"
					if !in.Latest {
						day = in.Date
					}
					fields, _ := json.Marshal(map[string]any{"id": 1, "name": "Owned", "domain": "owned.invalid", "updated_day": day, "upload": 200.0, "download": 100.0, "bonus": 0.0, "err_msg": ""})
					return json.Marshal(plugins.SiteAccountHostResultV1{SchemaVersion: 1, Items: []plugins.SiteAccountHostRowV1{{SiteID: "owned", Fields: fields}}})
				}
				return nil, errors.New("unexpected lifecycle resource " + method)
			}
			if scenario == "pending-one-shot-session-retire" {
				if _, e := client.CallWithOptions(ctx, "init", json.RawMessage(`{"enabled":false,"onlyonce":true}`), host, plugins.CallOptions{CallerDeadlineOnly: true}); e != nil {
					t.Fatal(e)
				}
				child := <-children
				stop, done := context.WithTimeout(context.Background(), 3*time.Second)
				defer done()
				if e := client.Stop(stop); e != nil {
					t.Fatal("retire did not join pending one-shot", e)
				}
				if _, e := child.Wait(); e == nil || allRefreshes.Load() != 0 {
					t.Fatal("retired pending one-shot performed source refresh", e, allRefreshes.Load())
				}
				observations = append(observations, map[string]any{"scenario": scenario, "all_refreshes": allRefreshes.Load(), "retirement_joined": true})
				return
			}
			owner, e := client.StartCall(ctx, "get_page", json.RawMessage(`null`), host, plugins.CallOptions{CallerDeadlineOnly: true})
			if e != nil {
				t.Fatal(e)
			}
			waitOwner := make(chan error, 1)
			go func() { _, e := owner.Wait(); waitOwner <- e }()
			if scenario == "queued-owner-cancel" {
				var in submission
				select {
				case in = <-queued:
				case <-ctx.Done():
					t.Fatal(ctx.Err())
				}
				owner.Cancel()
				if e := <-waitOwner; e == nil {
					t.Fatal("canceled owner reported success")
				}
				late, e := client.StartCall(ctx, in.Method, in.Payload, host, plugins.CallOptions{CallerDeadlineOnly: true})
				if e != nil {
					t.Fatal(e)
				}
				out, e := late.Wait()
				if e != nil || out.HostCalls != 0 || queries.Load() != 0 {
					t.Fatal("sealed queued pass replayed", out, e, queries.Load())
				}
			} else {
				select {
				case <-entered:
				case <-ctx.Done():
					t.Fatal(ctx.Err())
				}
				if scenario == "active-owner-cancel" {
					owner.Cancel()
					if e := <-waitOwner; e == nil {
						t.Fatal("canceled owner reported success")
					}
					select {
					case <-queryCanceled:
					case <-ctx.Done():
						t.Fatal("active read scope was not revoked", ctx.Err())
					}
				} else {
					for _, in := range []struct{ method, raw string }{{"stop_service", "null"}, {"init", `{"enabled":false,"onlyonce":false}`}} {
						if _, e := client.CallWithOptions(ctx, in.method, json.RawMessage(in.raw), host, plugins.CallOptions{CallerDeadlineOnly: true}); e != nil {
							t.Fatal(in.method, e)
						}
					}
					select {
					case e := <-waitOwner:
						t.Fatal("noop stop/reinit ended the source read pass", e)
					default:
					}
					close(release)
					if e := <-waitOwner; e != nil {
						t.Fatal("whole page did not finish", e)
					}
				}
				child := <-children
				out, e := child.Wait()
				if (e != nil) != (scenario == "active-owner-cancel") || out.HostCalls > 64 || queries.Load() != 1 {
					t.Fatal("active child failed to finish once", out, e, queries.Load())
				}
			}
			// The same session remains usable after the operation, not only a
			// new worker that could hide a leaked invocation or retired caller.
			if _, e := client.CallWithOptions(ctx, "get_state", json.RawMessage(`null`), host, plugins.CallOptions{CallerDeadlineOnly: true}); e != nil {
				t.Fatal("same worker unavailable", e)
			}
			observations = append(observations, map[string]any{"scenario": scenario, "queries": queries.Load(), "same_worker_usable": true})
		})
	}
	raw, _ := json.MarshalIndent(map[string]any{"kind": "actual-independent-executable-SDK-worker-with-synthetic-resources", "worker_race_instrumented": workerRace, "observations": observations}, "", "  ")
	if e := os.WriteFile(filepath.Join(work, "sdk-worker-lifecycle-observations.json"), append(raw, '\n'), 0600); e != nil {
		t.Fatal(e)
	}
}
