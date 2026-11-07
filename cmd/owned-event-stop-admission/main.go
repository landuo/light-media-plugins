package main

import (
	"context"
	"encoding/json"
	"fmt"
	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"time"
)

var fixtureID = "OwnedEventStopA"

func main() {
	m := sdk.Manifest{ManagedPublicServices: true, SchemaVersion: 1, PluginID: fixtureID, Name: fixtureID, Version: "1.0", Runtime: "go-executable", Entry: "owned-stop-order", HostAPIMin: 1, HostAPIMax: 1, Methods: []string{"init", "get_state", "get_service", "on_event", "close", "stop_service", "stop"}, Capabilities: append(sdk.BaseMethods(), sdk.EventSendCapability), BroadcastHandlers: []sdk.BroadcastHandler{{Event: "owned.stop.broadcast", Method: "on_event"}}}
	if len(os.Args) == 2 && os.Args[1] == "--manifest" {
		_ = json.NewEncoder(os.Stdout).Encode(m)
		return
	}
	handle := func(ctx context.Context, method string, raw json.RawMessage, host sdk.HostCaller) (json.RawMessage, error) {
		if method == "get_state" {
			return json.RawMessage(`true`), nil
		}
		if method == "get_service" {
			return json.RawMessage(`[]`), nil
		}
		if method == "init" || method == "stop" {
			return json.RawMessage(`null`), nil
		}
		b := sdk.Base{Host: host}
		cfgRaw, e := b.GetConfig(ctx)
		if e != nil {
			return nil, e
		}
		var cfg struct {
			Endpoint string `json:"owned_trace_endpoint"`
		}
		if e = json.Unmarshal(cfgRaw, &cfg); e != nil {
			return nil, e
		}
		trace := func(phase string, sendOK bool) error {
			u, e := url.Parse(cfg.Endpoint)
			if e != nil || u.Scheme != "http" || u.User != nil || net.ParseIP(u.Hostname()) == nil || !net.ParseIP(u.Hostname()).IsLoopback() {
				return fmt.Errorf("owned peer requires literal loopback")
			}
			u.Path = "/" + fixtureID + "/" + phase
			u.RawQuery = url.Values{"send_ok": {fmt.Sprint(sendOK)}}.Encode()
			c := http.Client{Timeout: 8 * time.Second, Transport: &http.Transport{Proxy: nil}, CheckRedirect: func(*http.Request, []*http.Request) error { return fmt.Errorf("owned redirect denied") }}
			defer c.CloseIdleConnections()
			req, e := http.NewRequestWithContext(ctx, "GET", u.String(), nil)
			if e != nil {
				return e
			}
			r, e := c.Do(req)
			if e != nil {
				return e
			}
			_, e = io.Copy(io.Discard, r.Body)
			r.Body.Close()
			if e != nil || r.StatusCode != 200 {
				return fmt.Errorf("owned trace failed")
			}
			return nil
		}
		switch method {
		case "close":
			sent := true
			if fixtureID == "OwnedEventStopA" {
				_, e = sdk.SendEvent(ctx, host, sdk.EventSendRequest{Kind: sdk.BroadcastEventKind, Type: "owned.stop.broadcast", Data: json.RawMessage(`{"phase":"during_A_close"}`)})
				sent = e == nil
			}
			if e = trace("close", sent); e != nil {
				return nil, e
			}
			if e = b.SaveData(ctx, "actual_close", map[string]any{"id": fixtureID, "send_ok": sent}); e != nil {
				return nil, e
			}
		case "stop_service":
			if e = trace("stop_service", true); e != nil {
				return nil, e
			}
		case "on_event":
			var event struct {
				Data struct {
					Phase string `json:"phase"`
				} `json:"data"`
			}
			if e = json.Unmarshal(raw, &event); e != nil {
				return nil, e
			}
			if fixtureID == "OwnedEventStopA" && event.Data.Phase == "preexisting" {
				return json.RawMessage(`null`), nil
			}
			if e = trace(event.Data.Phase, true); e != nil {
				return nil, e
			}
			if e = b.SaveData(ctx, "event_"+event.Data.Phase, map[string]any{"id": fixtureID, "phase": event.Data.Phase}); e != nil {
				return nil, e
			}
		}
		return json.RawMessage(`null`), nil
	}
	if e := sdk.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, m, handle); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
