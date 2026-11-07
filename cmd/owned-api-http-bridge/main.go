package main

// Owned verification worker. These are compiled constants, never worker-sent
// scope selectors or a runtime way to acquire source ownership.
import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
)

const bridgeManaged = true
const bridgeConcurrent = true
const bridgePrivate = false
const bridgeSelfRemove = false

func main() {
	m := sdk.Manifest{SchemaVersion: 1, PluginID: "OwnedAPIHTTPBridge", Name: "Owned API HTTP bridge", Version: "1.0", Runtime: "go-executable", Entry: "worker", HostAPIMin: 1, HostAPIMax: 1,
		ManagedPublicServices:   bridgeManaged,
		ManagedPrivateScheduler: bridgePrivate,
		Methods:                 []string{"init", "get_state", "get_service", "get_api", "http", "child", "default_root", "close", "stop_service", "stop"},
		Capabilities:            append(sdk.BaseMethods(), sdk.BackgroundSubmitCapability, sdk.NetworkGetCapability, sdk.PostMessageCapability),
		APIs:                    []sdk.HTTPAPI{{Key: "owned", Path: "/held", Methods: []string{"GET"}, Auth: "apikey"}}}
	if bridgeSelfRemove {
		m.Capabilities = append(m.Capabilities, sdk.PluginManagerControlCapability)
	}
	if len(os.Args) == 2 && os.Args[1] == "--manifest" {
		json.NewEncoder(os.Stdout).Encode(m)
		return
	}
	handle := func(ctx context.Context, method string, raw json.RawMessage, host sdk.HostCaller) (json.RawMessage, error) {
		b := sdk.Base{Host: host}
		switch method {
		case "init":
			var config struct {
				SelfRemove bool `json:"self_remove"`
			}
			if err := json.Unmarshal(raw, &config); err != nil {
				return nil, err
			}
			if bridgeSelfRemove && config.SelfRemove {
				result, err := (sdk.PluginHost{Host: host}).Control(ctx, "OwnedAPIHTTPBridge", "remove")
				if err != nil {
					return nil, err
				}
				if !result.Accepted || !result.Completed {
					return nil, fmt.Errorf("live initializer removal did not complete")
				}
			}
		case "get_state":
			return json.RawMessage(`false`), nil // API registration does not require enabled business.
		case "get_service":
			return json.RawMessage(`[]`), nil
		case "get_api":
			return json.Marshal(m.APIs)
		case "default_root":
			return json.RawMessage(`null`), (sdk.Manager{Host: host}).Submit(ctx, "child", nil)
		case "close", "stop_service":
			_, postErr := b.PostMessage(ctx, map[string]any{"channel": "Web", "title": "owned-http-bridge-" + method, "text": "owned source hook before message shutdown"})
			message := ""
			if postErr != nil {
				message = postErr.Error()
			}
			if err := b.SaveData(ctx, "hook_"+method, map[string]any{"pid": os.Getpid(), "post_error": message}); err != nil {
				return nil, err
			}
			return json.RawMessage(`null`), postErr
		case "http", "child":
			rawConfig, err := b.GetConfig(ctx)
			if err != nil {
				return nil, err
			}
			var config struct {
				URL      string `json:"url"`
				ChildURL string `json:"child_url"`
				Child    bool   `json:"child"`
				Invalid  bool   `json:"invalid"`
			}
			if err = json.Unmarshal(rawConfig, &config); err != nil {
				return nil, err
			}
			address := config.URL
			if method == "child" {
				address = config.ChildURL
			}
			out, err := (sdk.Network{Host: host}).Get(ctx, sdk.NetworkGetRequestV1{URL: address})
			if err != nil {
				return nil, err
			}
			if out.Response == nil || out.Response.StatusCode != 200 {
				return nil, fmt.Errorf("owned physical HTTP did not complete")
			}
			if err = b.SaveData(ctx, "late_"+method, map[string]any{"pid": os.Getpid(), "physical_http": true}); err != nil {
				return nil, err
			}
			if method == "http" {
				if config.Child {
					if err = (sdk.Manager{Host: host}).Submit(ctx, "child", nil); err != nil {
						return nil, err
					}
				}
				status := 200
				if config.Invalid {
					status = 0
				}
				return json.Marshal(sdk.HTTPResponse{Status: status, Headers: map[string]string{"Content-Type": "application/json"}, Body: []byte(`{"success":true}`)})
			}
		}
		return json.RawMessage(`null`), nil
	}
	var err error
	if bridgeConcurrent {
		err = sdk.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, m, handle)
	} else {
		err = sdk.Serve(context.Background(), os.Stdin, os.Stdout, m, handle)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
