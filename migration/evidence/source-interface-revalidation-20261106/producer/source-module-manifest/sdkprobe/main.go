// sdkprobe only starts owned workers without init, page/dashboard, network or
// source filesystem effects. It verifies real manifests/handshakes/method gates.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	plugins "github.com/landuo/light-media-plugins/internal/sdk"
	"os"
	"os/exec"
	"slices"
	"sync/atomic"
	"time"
)

type input struct {
	Oracle    string
	Artifacts []struct{ Family, Instance, Binary string }
}

func main() {
	if len(os.Args) != 2 {
		panic("owned input JSON required")
	}
	b, e := os.ReadFile(os.Args[1])
	if e != nil {
		panic(e)
	}
	var in input
	if e = json.Unmarshal(b, &in); e != nil {
		panic(e)
	}
	b, e = os.ReadFile(in.Oracle)
	if e != nil {
		panic(e)
	}
	var src struct {
		Inventory []struct {
			Plugin     string
			Interfaces map[string]struct {
				CheckMethod bool `json:"check_method"`
			}
		}
	}
	if e = json.Unmarshal(b, &src); e != nil {
		panic(e)
	}
	expected := map[string]map[string]bool{}
	for _, r := range src.Inventory {
		m := map[string]bool{}
		for k, v := range r.Interfaces {
			m[k] = v.CheckMethod
		}
		expected[r.Plugin] = m
	}
	out := []map[string]any{}
	for _, artifact := range in.Artifacts {
		raw, e := exec.Command(artifact.Binary, "--manifest").Output()
		if e != nil {
			panic(e)
		}
		var m plugins.Manifest
		if e = json.Unmarshal(raw, &m); e != nil || m.Validate() != nil {
			panic("worker manifest")
		}
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		client, e := (plugins.Runner{ConcurrentCalls: true, Timeout: 5 * time.Second}).Start(ctx, plugins.Command{Path: artifact.Binary}, m, plugins.SessionBinding{Identity: plugins.Identity{PluginID: m.PluginID, InstanceID: artifact.Instance, Version: m.Version}, Generation: 1})
		if e != nil {
			panic(e)
		}
		var callbacks atomic.Int64
		host := func(context.Context, plugins.Identity, string, json.RawMessage) (json.RawMessage, error) {
			callbacks.Add(1)
			return nil, errors.New("unexpected owned callback")
		}
		rejected := []string{}
		retained := []string{}
		for _, method := range []string{"get_module", "get_service", "get_command", "get_dashboard", "get_dashboard_meta"} {
			want, ok := expected[artifact.Family][method]
			if !ok {
				panic("source entry")
			}
			if slices.Contains(m.Methods, method) != want {
				panic(fmt.Sprintf("%s %s source/native declaration mismatch", artifact.Instance, method))
			}
			if want {
				retained = append(retained, method)
				continue
			}
			_, e := client.Call(ctx, method, json.RawMessage(`null`), host)
			var local *plugins.Error
			if !errors.As(e, &local) || local.Code != "invalid_invocation" {
				panic(fmt.Sprintf("omitted method reached business: %s %v", method, e))
			}
			rejected = append(rejected, method)
		}
		state, e := client.Call(ctx, "get_state", json.RawMessage(`null`), host)
		if e != nil || state.HostCalls != 0 {
			panic(fmt.Sprintf("fresh state %v", e))
		}
		if e := client.Stop(ctx); e != nil {
			panic(e)
		}
		cancel()
		if callbacks.Load() != 0 {
			panic("manifest probe unexpectedly used resource")
		}
		out = append(out, map[string]any{"family": artifact.Family, "instance": artifact.Instance, "manifest_plugin_id": m.PluginID, "version": m.Version, "omitted_before_business": rejected, "retained_without_invoking_business": retained, "fresh_state": state.Result, "host_callbacks": callbacks.Load(), "worker_joined": true})
	}
	if e := json.NewEncoder(os.Stdout).Encode(map[string]any{"classification": "actual independent compiled workers + immutable SDK98 protocol; no App artifact acquisition/discovery, no init/publicpage/dashboard/network", "observations": out}); e != nil {
		panic(e)
	}
}
