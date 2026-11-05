package main

import (
	"context"
	"encoding/json"
	"errors"
	"github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/torrenttransfer"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sync"
	"testing"
	"time"
)

// Real worker/concurrent SDK transport with synthetic host resources only.
func TestPersistentExecutableOwnsOneShotAndJoins(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	work, e := filepath.Abs("/Users/accidia/projects/light-media-plugins/work/migration-20261105/sdk98-impact-20261105/variant95/tt-cmd")
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
	binary := filepath.Join(dir, "torrent-transfer")
	build := exec.CommandContext(ctx, "go", "build", "-trimpath", "-buildvcs=false", "-o", binary, ".")
	if out, e := build.CombinedOutput(); e != nil {
		t.Fatalf("build: %v\n%s", e, out)
	}
	manifest := torrenttransfer.Manifest()
	var emitted plugins.Manifest
	output, e := exec.CommandContext(ctx, binary, "--manifest").Output()
	if e != nil {
		t.Fatal(e)
	}
	if e = json.Unmarshal(output, &emitted); e != nil || !reflect.DeepEqual(emitted, manifest) {
		t.Fatal("manifest differs", e)
	}
	identity := plugins.Identity{PluginID: "TorrentTransfer", InstanceID: "TorrentTransfermusic", Version: "1.10.3"}
	client, e := (plugins.Runner{Timeout: 5 * time.Second, ConcurrentCalls: true, RequireConcurrent: true}).Start(ctx, plugins.Command{Path: binary}, manifest, plugins.SessionBinding{Identity: identity, Generation: 1})
	if e != nil {
		t.Fatal(e)
	}
	defer func() {
		c, x := context.WithTimeout(context.Background(), 3*time.Second)
		defer x()
		if e := client.Stop(c); e != nil {
			t.Errorf("stop/join: %v", e)
		}
	}()
	var mu sync.Mutex
	var pending *plugins.PendingCall
	parentCalls := []string{}
	childCalls := []string{}
	observed := make(chan struct{}, 1)
	child := func(c context.Context, got plugins.Identity, m string, raw json.RawMessage) (json.RawMessage, error) {
		if got != identity || c.Err() != nil {
			return nil, errors.New("invalid child scope")
		}
		mu.Lock()
		childCalls = append(childCalls, m)
		mu.Unlock()
		switch m {
		case plugins.DownloaderConfigurationsReadCapability:
			return json.Marshal(plugins.DownloaderConfigurationsV1{SchemaVersion: 1, Downloaders: []plugins.BrushDownloaderReferenceV1{{ID: "source", Name: "Source", Kind: "qbittorrent", Enabled: true}, {ID: "target", Name: "Target", Kind: "transmission", Enabled: true}}})
		case plugins.DownloaderSourceConnectionCapability:
			var in plugins.DownloaderConnectionRequestV1
			_ = json.Unmarshal(raw, &in)
			kind := "qbittorrent"
			if in.DownloaderID == "target" {
				kind = "transmission"
			}
			return json.Marshal(plugins.DownloaderSourceConnectionV1{DownloaderConnectionV1: plugins.DownloaderConnectionV1{SchemaVersion: 1, DownloaderID: in.DownloaderID, Kind: kind}, Exists: true})
		case plugins.DownloaderSourceCompletedCapability:
			select {
			case observed <- struct{}{}:
			default:
			}
			return json.Marshal(plugins.DownloaderSourceTasksResultV1{DownloaderTasksV1: plugins.DownloaderTasksV1{SchemaVersion: 1, DownloaderID: "source", Kind: "qbittorrent", Tasks: []plugins.DownloaderTaskV1{}}})
		case plugins.LogWriteCapability:
			return json.RawMessage(`null`), nil
		}
		return nil, errors.New("unexpected child resource")
	}
	parent := func(c context.Context, got plugins.Identity, m string, raw json.RawMessage) (json.RawMessage, error) {
		if got != identity || c.Err() != nil {
			return nil, errors.New("invalid parent scope")
		}
		mu.Lock()
		parentCalls = append(parentCalls, m)
		mu.Unlock()
		switch m {
		case plugins.BaseUpdateConfig:
			var in struct {
				Config map[string]any `json:"config"`
			}
			_ = json.Unmarshal(raw, &in)
			if in.Config["onlyonce"] != false {
				return nil, errors.New("one-shot not reset")
			}
			return json.RawMessage(`false`), nil
		case plugins.BackgroundSubmitCapability:
			var in struct {
				Method  string          `json:"method"`
				Payload json.RawMessage `json:"payload"`
			}
			if e := json.Unmarshal(raw, &in); e != nil {
				return nil, e
			}
			next, e := client.StartCallWithAdmission(c, ctx, in.Method, in.Payload, child, plugins.CallOptions{CallerDeadlineOnly: true})
			if e != nil {
				return nil, e
			}
			mu.Lock()
			pending = next
			mu.Unlock()
			return json.RawMessage(`{"accepted":true}`), nil
		case plugins.LogWriteCapability:
			return json.RawMessage(`null`), nil
		}
		return nil, errors.New("unexpected parent resource")
	}
	cfg, _ := json.Marshal(map[string]any{"enabled": false, "onlyonce": true, "autostart": false, "fromdownloader": "Source", "todownloader": "Target", "fromtorrentpath": dir})
	start := time.Now()
	if _, e = client.Call(ctx, "init", cfg, parent); e != nil {
		t.Fatal(e)
	}
	select {
	case <-observed:
		if time.Since(start) < 2900*time.Millisecond {
			t.Fatal("early one-shot")
		}
	case <-time.After(8 * time.Second):
		t.Fatal("one-shot never ran")
	}
	mu.Lock()
	pc, cc, job := append([]string{}, parentCalls...), append([]string{}, childCalls...), pending
	mu.Unlock()
	if len(cc) == 0 || !reflect.DeepEqual(pc, []string{plugins.LogWriteCapability, plugins.BaseUpdateConfig, plugins.BackgroundSubmitCapability}) {
		t.Fatal("callback ownership/order", pc, cc)
	}
	if out, e := client.Call(ctx, "get_state", json.RawMessage(`null`), nil); e != nil || string(out.Result) != "false" {
		t.Fatal("one-shot enabled recurring state", e)
	}
	if _, e = client.Call(ctx, "stop_service", json.RawMessage(`null`), nil); e != nil {
		t.Fatal(e)
	}
	done := make(chan error, 1)
	go func() { _, e := job.Wait(); done <- e }()
	select {
	case e := <-done:
		if e != nil {
			t.Fatal(e)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("private scheduler not joined")
	}
	if _, e = client.Call(ctx, "init", json.RawMessage(`{}`), nil); e != nil {
		t.Fatal("falsey reinit", e)
	}
	if out, e := client.Call(ctx, "get_page", json.RawMessage(`null`), nil); e != nil || string(out.Result) != "null" {
		t.Fatal("unexpected page", e)
	}
}
