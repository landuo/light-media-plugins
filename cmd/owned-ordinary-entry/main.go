package main

import (
	"context"
	"encoding/json"
	"fmt"
	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"os"
	"strconv"
)

func main() {
	m := sdk.Manifest{ManagedPublicServices: true, SchemaVersion: 1, PluginID: "OwnedOrdinaryEntry", Name: "Owned ordinary entry", Version: "1.0", Runtime: "go-executable", Entry: "worker", HostAPIMin: 1, HostAPIMax: 1, Methods: []string{"init", "get_state", "get_service", "get_api", "event", "work", "http", "child", "close", "stop_service", "stop"}, Capabilities: append(sdk.BaseMethods(), sdk.BackgroundSubmitCapability, sdk.EventSendCapability, sdk.NetworkGetCapability, sdk.ServiceProgressCapability), BroadcastHandlers: []sdk.BroadcastHandler{{Event: "owned.progress", Method: "work"}, {Event: "owned.failure", Method: "event"}}, APIs: []sdk.HTTPAPI{{Key: "owned", Path: "/owned", Methods: []string{"GET"}, Auth: "apikey"}}}
	if len(os.Args) == 2 && os.Args[1] == "--manifest" {
		json.NewEncoder(os.Stdout).Encode(m)
		return
	}
	handle := func(ctx context.Context, method string, raw json.RawMessage, host sdk.HostCaller) (json.RawMessage, error) {
		b := sdk.Base{Host: host}
		switch method {
		case "get_state":
			return json.RawMessage(`true`), nil
		case "get_service":
			return json.RawMessage(`[]`), nil
		case "get_api":
			return json.Marshal(m.APIs)
		case "child":
			if e := b.SaveData(ctx, "mechanical_child", map[string]int{"pid": os.Getpid()}); e != nil {
				return nil, e
			}
		case "work", "event", "http":
			if method == "work" {
				var event struct {
					Type string `json:"type"`
				}
				_ = json.Unmarshal(raw, &event)
				if event.Type == "owned.progress" {
					e := sdk.UpdateServiceProgress(ctx, host, sdk.ServiceProgressUpdate{Text: new("event must not own scheduler progress")})
					return json.RawMessage(`null`), b.SaveData(ctx, "progress_denied", e != nil)
				}
			}
			cfgRaw, e := b.GetConfig(ctx)
			if e != nil {
				return nil, e
			}
			var cfg struct {
				URL     string `json:"url"`
				Invalid bool   `json:"invalid"`
			}
			if e = json.Unmarshal(cfgRaw, &cfg); e != nil {
				return nil, e
			}
			if method == "work" {
				if _, e = sdk.SendEvent(ctx, host, sdk.EventSendRequest{Kind: sdk.BroadcastEventKind, Type: "owned.progress", Data: json.RawMessage(`{}`)}); e != nil {
					return nil, e
				}
			}
			out, e := (sdk.Network{Host: host}).Get(ctx, sdk.NetworkGetRequestV1{URL: cfg.URL + "?pid=" + strconv.Itoa(os.Getpid())})
			if e != nil {
				return nil, e
			}
			if out.Response == nil || out.Response.StatusCode != 200 {
				return nil, fmt.Errorf("owned HTTP failed")
			}
			if method == "event" {
				return nil, fmt.Errorf("owned handler failure")
			}
			if method == "http" {
				if e = (sdk.Manager{Host: host}).Submit(ctx, "child", nil); e != nil {
					return nil, e
				}
				status := 200
				if cfg.Invalid {
					status = 0
				}
				return json.Marshal(sdk.HTTPResponse{Status: status, Headers: map[string]string{"Content-Type": "application/json"}, Body: []byte(`{"success":true}`)})
			}
		}
		return json.RawMessage(`null`), nil
	}
	if e := sdk.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, m, handle); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
