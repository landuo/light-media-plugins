// Owned test instrumentation, not a migrated business plugin. Installed only in
// the fresh PluginUnInstall Main acceptance instance, using finite public SDK.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
)

func manifest() sdk.Manifest {
	return sdk.Manifest{SchemaVersion: 1, PluginID: "OwnedPuiFixture", Name: "Owned PUI fixture", Version: "1", Runtime: "go-executable", Entry: "owned-pui-fixture", PluginOrder: 0, HostAPIMin: 1, HostAPIMax: 1,
		Methods:      []string{"init", "get_state", "get_form", "get_api", "http", "get_service", "get_command", "get_page", "get_dashboard", "get_render_mode", "stop_service", "close", "stop"},
		Capabilities: []string{sdk.BaseGetInstanceMetadata, sdk.BaseGetConfig, sdk.BaseUpdateConfig, sdk.BaseGetData, sdk.BaseSaveData, sdk.BaseGetDataPath, sdk.PluginManagerReadCapability, sdk.SettingsReadCapability, sdk.SettingsWriteCapability},
		APIs:         []sdk.HTTPAPI{{Key: "inspect", Path: "/inspect", Methods: []string{"GET"}, Auth: "apikey", Query: []sdk.HTTPParameter{{Name: "target", Kind: "string"}}}}, RuntimeSupport: &sdk.RuntimeSupport{Platforms: []string{"linux"}, StorageTypes: []string{"local"}}}
}
func owned(id string) bool {
	return id == "MPServerStatus" || strings.HasPrefix(id, "PluginUnInstall") || strings.HasPrefix(id, "OwnedPuiFixture")
}

type seed struct {
	ID     string          `json:"id"`
	Config json.RawMessage `json:"config"`
	Data   json.RawMessage `json:"data"`
}

func handle(ctx context.Context, method string, raw json.RawMessage, host sdk.HostCaller) (json.RawMessage, error) {
	b := sdk.Base{Host: host}
	switch method {
	case "init":
		var plan struct {
			Seeds     []seed          `json:"seeds"`
			Installed json.RawMessage `json:"installed"`
		}
		if len(raw) > 0 && string(raw) != "null" {
			if e := json.Unmarshal(raw, &plan); e != nil {
				return nil, e
			}
		}
		if len(plan.Seeds) == 0 && plan.Installed == nil {
			return json.RawMessage(`null`), nil
		}
		for _, s := range plan.Seeds {
			if !owned(s.ID) {
				return nil, errors.New("test fixture target is not owned")
			}
			if s.Config != nil {
				if _, e := b.UpdateConfig(ctx, s.Config, s.ID); e != nil {
					return nil, e
				}
			}
			if s.Data != nil {
				if e := b.SaveData(ctx, "owned-data", s.Data, s.ID); e != nil {
					return nil, e
				}
			}
		}
		if plan.Installed != nil {
			var ids []string
			if json.Unmarshal(plan.Installed, &ids) != nil {
				return nil, errors.New("owned installed plan is not string list")
			}
			for _, id := range ids {
				if !owned(id) {
					return nil, errors.New("installed fixture ID not owned")
				}
			}
			if _, e := (sdk.SystemSettings{Host: host}).Set(ctx, "UserInstalledPlugins", plan.Installed); e != nil {
				return nil, e
			}
		}
		_, e := b.UpdateConfig(ctx, map[string]any{})
		return json.RawMessage(`null`), e // Fixture instruction is consumed; never replays on cold start.
	case "get_state":
		return json.RawMessage(`false`), nil
	case "get_form":
		return json.RawMessage(`[[],{}]`), nil
	case "get_api":
		return json.Marshal(manifest().APIs)
	case "get_render_mode":
		return json.RawMessage(`["vuetify",null]`), nil
	case "http":
		var req sdk.HTTPRequest
		if e := json.Unmarshal(raw, &req); e != nil {
			return nil, e
		}
		if req.Key != "inspect" {
			return nil, errors.New("unknown owned API")
		}
		target := req.LastQuery("target")
		if target != "" && !owned(target) {
			return nil, errors.New("inspect target is not owned")
		}
		manager := sdk.PluginHost{Host: host}
		views := map[string]any{}
		for _, view := range []string{"installed", "classes", "running"} {
			rows, e := manager.Read(ctx, sdk.PluginManagerRequest{View: view, IncludeState: view == "running"})
			if e != nil {
				return nil, e
			}
			views[view] = rows
		}
		local, e := manager.Local(ctx)
		if e != nil {
			return nil, e
		}
		views["local"] = local
		value, e := (sdk.SystemSettings{Host: host}).Get(ctx, "UserInstalledPlugins")
		if e != nil {
			return nil, e
		}
		views["installed_order"] = value.Value
		metadata, e := b.GetInstanceMetadata(ctx)
		if e != nil {
			return nil, e
		}
		views["caller"] = metadata
		views["pid"] = os.Getpid()
		if target != "" {
			config, e := b.GetConfig(ctx, target)
			if e != nil {
				return nil, e
			}
			key := "owned-data"
			data, e := b.GetData(ctx, &key, target)
			if e != nil {
				return nil, e
			}
			views["raw_config"] = config
			views["raw_data"] = data
			path, e := b.GetDataPath(ctx, target)
			if e != nil {
				return nil, e
			}
			views["data_path"] = path
		}
		return sdk.JSONHTTPResponse(200, views)
	case "get_service", "get_command", "get_page", "get_dashboard", "stop_service", "close", "stop":
		return json.RawMessage(`null`), nil
	}
	return nil, errors.New("unsupported owned fixture method")
}
func main() {
	m := manifest()
	if e := m.Validate(); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(2)
	}
	if len(os.Args) == 2 && os.Args[1] == "--manifest" {
		_ = json.NewEncoder(os.Stdout).Encode(m)
		return
	}
	if e := sdk.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, m, handle); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
