package integration

// Dependency regression only: actual accepted worker subprocesses, synthetic
// resource callbacks. Ordinary Main is a separate opt-in test below.
import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"sync"
	"testing"
	"time"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
)

func TestSDK98ImpactWireProxy(t *testing.T) {
	i := slices.Index(os.Args, "sdk98-impact-proxy")
	if i < 0 {
		return
	}
	if len(os.Args) != i+3 {
		os.Exit(2)
	}
	bin, base := os.Args[i+1], os.Args[i+2]
	in, e := os.Create(base + "-in.jsonl")
	if e != nil {
		os.Exit(2)
	}
	out, e := os.Create(base + "-out.jsonl")
	if e != nil {
		os.Exit(2)
	}
	cmd := exec.Command(bin)
	stdin, e := cmd.StdinPipe()
	if e != nil {
		os.Exit(2)
	}
	cmd.Stdout = io.MultiWriter(os.Stdout, out)
	cmd.Stderr = os.Stderr
	if e = cmd.Start(); e != nil {
		os.Exit(2)
	}
	go func() { _, _ = io.Copy(stdin, io.TeeReader(os.Stdin, in)); stdin.Close() }()
	e = cmd.Wait()
	out.Close()
	in.Close()
	if e != nil {
		os.Exit(2)
	}
	os.Exit(0)
}
func impactHomeManifest() sdk.Manifest {
	return sdk.Manifest{SchemaVersion: 1, PluginID: "SDKImpactHome", Name: "Owned HOME witness", Version: "1", Runtime: "go-executable", Entry: "home", HostAPIMin: 1, HostAPIMax: 1, Methods: []string{"invoke", "stop"}}
}
func TestSDK98ImpactHomeWorker(t *testing.T) {
	if !slices.Contains(os.Args, "sdk98-impact-home") {
		return
	}
	e := sdk.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, impactHomeManifest(), func(_ context.Context, method string, _ json.RawMessage, _ sdk.HostCaller) (json.RawMessage, error) {
		if method == "stop" {
			return json.RawMessage(`null`), nil
		}
		v, p := os.LookupEnv("HOME")
		_, secret := os.LookupEnv("SDK_IMPACT_SECRET")
		return json.Marshal(map[string]any{"present": p, "home": v, "secret": secret})
	})
	if e != nil {
		os.Exit(2)
	}
	os.Exit(0)
}
func TestSDK98ImpactActualProcesses(t *testing.T) {
	root := os.Getenv("SDK98_IMPACT_NATIVE_ROOT")
	if root == "" {
		t.Skip("opt-in actual worker dependency regression; not Main acceptance")
	}
	runnerVersion := os.Getenv("SDK98_IMPACT_RUNNER_VERSION")
	if runnerVersion != "95" && runnerVersion != "98" {
		t.Fatal("explicit Runner variant required")
	}
	output := filepath.Join(root, "runner"+runnerVersion)
	if e := os.MkdirAll(output, 0700); e != nil {
		t.Fatal(e)
	}
	exe, e := os.Executable()
	if e != nil {
		t.Fatal(e)
	}
	type phase struct {
		Method    string          `json:"method"`
		Result    json.RawMessage `json:"result"`
		Error     bool            `json:"error"`
		ErrorCode string          `json:"error_code"`
		Callbacks []string        `json:"callbacks"`
	}
	records := map[string]any{}
	for _, workerVersion := range []string{"95", "98"} {
		for _, instance := range []string{"CategoryEditor", "TorrentTransfer", "TorrentTransfermusic", "SiteStatistic"} {
			t.Run(workerVersion+"/"+instance, func(t *testing.T) {
				family, entry := instance, ""
				switch instance {
				case "CategoryEditor":
					entry = "category-editor"
				case "SiteStatistic":
					entry = "site-statistic"
				default:
					family = "TorrentTransfer"
					entry = "torrent-transfer"
				}
				bin := filepath.Join(root, "native"+workerVersion, entry)
				raw, e := exec.Command(bin, "--manifest").Output()
				if e != nil {
					t.Fatal(e)
				}
				var manifest sdk.Manifest
				if json.Unmarshal(raw, &manifest) != nil || manifest.PluginID != family || slices.Contains(manifest.Capabilities, "plugin.cleanup.submit") {
					t.Fatal("nonconsumer manifest")
				}
				ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
				defer cancel()
				wire := filepath.Join(output, workerVersion+"-"+instance)
				client, e := (sdk.Runner{Timeout: 3 * time.Second, ConcurrentCalls: true}).Start(ctx, sdk.Command{Path: exe, Args: []string{"-test.run=^TestSDK98ImpactWireProxy$", "--", "sdk98-impact-proxy", bin, wire}}, manifest, sdk.SessionBinding{Identity: sdk.Identity{PluginID: family, InstanceID: instance, Version: manifest.Version}, Generation: 1})
				if e != nil {
					t.Fatal(e)
				}
				stopped := false
				defer func() {
					if !stopped {
						_ = client.Stop(ctx)
					}
				}()
				phases := []phase{}
				var mu sync.Mutex
				call := func(method string, payload json.RawMessage, fail, block bool) error {
					current := phase{Method: method, Callbacks: []string{}}
					callCtx, done := context.WithCancel(ctx)
					defer done()
					entered := make(chan struct{}, 1)
					host := func(hctx context.Context, identity sdk.Identity, method string, in json.RawMessage) (json.RawMessage, error) {
						if hctx.Err() != nil || identity.InstanceID != instance {
							return nil, errors.New("expired or wrong identity")
						}
						mu.Lock()
						current.Callbacks = append(current.Callbacks, method)
						mu.Unlock()
						if block {
							select {
							case entered <- struct{}{}:
							default:
							}
							<-hctx.Done()
							return nil, hctx.Err()
						}
						if fail {
							return nil, errors.New("owned source resource failure")
						}
						switch method {
						case sdk.CategoryDefaultCapability:
							return json.Marshal("movie: owned\n")
						case sdk.CategoryApplyCapability, sdk.SystemMessagePutCapability, sdk.LogWriteCapability:
							return json.RawMessage(`null`), nil
						case sdk.BaseUpdateConfig:
							return json.RawMessage(`true`), nil
						case sdk.DownloaderConfigurationsReadCapability:
							return json.RawMessage(`{"schema_version":1,"downloaders":[]}`), nil
						case sdk.SitesSourceAccountsCapability:
							return json.RawMessage(`{"schema_version":1,"items":[]}`), nil
						case sdk.SitesReadCapability:
							return json.RawMessage(`{"schema_version":1,"items":[]}`), nil
						default:
							return nil, fmt.Errorf("unexpected impact resource %s", method)
						}
					}
					type result struct {
						out sdk.RunResult
						err error
					}
					ch := make(chan result, 1)
					go func() { o, e := client.Call(callCtx, method, payload, host); ch <- result{o, e} }()
					if block {
						select {
						case <-entered:
							done()
						case <-time.After(3 * time.Second):
							t.Fatal("owned callback not reached")
						}
					}
					r := <-ch
					current.Result = r.out.Result
					current.Error = r.err != nil
					if r.err != nil {
						current.ErrorCode = r.err.Error()
					}
					phases = append(phases, current)
					return r.err
				}
				if e = call("init", json.RawMessage(`{}`), false, false); e != nil {
					t.Fatal(e)
				}
				for _, method := range []string{"get_state", "get_form"} {
					if e = call(method, nil, false, false); e != nil {
						t.Fatal(method, e)
					}
				}
				failureMethod := "get_form"
				payload := json.RawMessage(nil)
				if family == "CategoryEditor" {
					failureMethod = "init"
					payload = json.RawMessage(`{"enabled":true,"content":"movie: owned\n"}`)
				}
				if family == "SiteStatistic" {
					failureMethod = "get_page"
				}
				if e = call(failureMethod, payload, true, false); e == nil {
					t.Fatal("resource failure swallowed")
				}
				if family != "CategoryEditor" {
					if e = call(failureMethod, nil, false, true); e == nil {
						t.Fatal("caller cancellation swallowed")
					}
				}
				if e = call("get_state", nil, false, false); e != nil {
					t.Fatal("same worker not usable after resource failure/cancel", e)
				}
				if slices.Contains(manifest.Methods, "stop_service") {
					if e = call("stop_service", nil, false, false); e != nil {
						t.Fatal(e)
					}
				}
				if e = client.Stop(ctx); e != nil {
					t.Fatal("stop join", e)
				}
				stopped = true
				for _, direction := range []string{"in", "out"} {
					b, e := os.ReadFile(wire + "-" + direction + ".jsonl")
					if e != nil {
						t.Fatal(e)
					}
					if bytes.Contains(b, []byte(`"cleanup_root"`)) || bytes.Contains(b, []byte(`"cleanup_continuation"`)) {
						t.Fatal("nonconsumer emitted new cleanup wire field")
					}
					if len(b) == 0 {
						t.Fatal("missing actual wire")
					}
				}
				records[workerVersion+"/"+instance] = phases
			})
		}
	}
	// HOME is the intended Runner difference; unrelated credentials stay stripped.
	homes := map[string]any{}
	for _, mode := range []string{"set", "empty", "absent"} {
		t.Run("HOME/"+mode, func(t *testing.T) {
			t.Setenv("HOME", "/owned/sdk98-impact-home")
			t.Setenv("SDK_IMPACT_SECRET", "synthetic-not-inherited")
			if mode == "empty" {
				t.Setenv("HOME", "")
			}
			if mode == "absent" {
				_ = os.Unsetenv("HOME")
			}
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			client, e := (sdk.Runner{Timeout: 2 * time.Second, ConcurrentCalls: true}).Start(ctx, sdk.Command{Path: exe, Args: []string{"-test.run=^TestSDK98ImpactHomeWorker$", "--", "sdk98-impact-home"}}, impactHomeManifest(), sdk.SessionBinding{Identity: sdk.Identity{PluginID: "SDKImpactHome", InstanceID: "OwnedHome", Version: "1"}, Generation: 1})
			if e != nil {
				t.Fatal(e)
			}
			out, e := client.Call(ctx, "invoke", nil, nil)
			if e != nil {
				t.Fatal(e)
			}
			var value map[string]any
			if json.Unmarshal(out.Result, &value) != nil {
				t.Fatal("HOME output")
			}
			wantPresent := runnerVersion == "98" && mode != "absent"
			if value["present"] != wantPresent || value["secret"] != false {
				t.Fatal(value)
			}
			want := ""
			if wantPresent && mode == "set" {
				want = "/owned/sdk98-impact-home"
			}
			if value["home"] != want {
				t.Fatal(value)
			}
			if e = client.Stop(ctx); e != nil {
				t.Fatal(e)
			}
			homes[mode] = value
		})
	}
	raw, _ := json.MarshalIndent(map[string]any{"classification": "actual accepted consumer process/wire with synthetic resources; NOT ordinary Main", "runner": runnerVersion, "records": records, "HOME": homes}, "", "  ")
	if e = os.WriteFile(filepath.Join(output, "observations.json"), append(raw, '\n'), 0600); e != nil {
		t.Fatal(e)
	}
	// Each runner's old/new worker semantic traces must agree; timing and random
	// transport IDs remain in raw wire files rather than being treated as state.
	for _, instance := range []string{"CategoryEditor", "TorrentTransfer", "TorrentTransfermusic", "SiteStatistic"} {
		a, _ := json.Marshal(records["95/"+instance])
		b, _ := json.Marshal(records["98/"+instance])
		if !bytes.Equal(a, b) {
			t.Fatal("old/new worker semantic trace differs", instance, string(a), string(b))
		}
	}
}
