package main

import (
	"context"
	"encoding/json"
	"testing"
)

func TestOwnedPlanUsesOnlyFiniteSDKAndConsumesSelf(t *testing.T) {
	calls := []string{}
	host := func(_ context.Context, method string, raw json.RawMessage) (json.RawMessage, error) {
		calls = append(calls, method+" "+string(raw))
		switch method {
		case "plugin.base.update_config":
			return json.RawMessage(`true`), nil
		case "plugin.base.save_data":
			return json.RawMessage(`null`), nil
		case "settings.write":
			return json.RawMessage(`{"schema_version":1,"key":"UserInstalledPlugins","value":["OwnedPuiFixture","PluginUnInstall"],"changed":true}`), nil
		}
		t.Fatalf("unapproved test fixture call %s", method)
		return nil, nil
	}
	raw := json.RawMessage(`{"seeds":[{"id":"PluginUnInstall","config":{"plugin_ids":["PluginUnInstall"]},"data":{"owned":true}}],"installed":["OwnedPuiFixture","PluginUnInstall"]}`)
	if _, err := handle(context.Background(), "init", raw, host); err != nil {
		t.Fatal(err)
	}
	if len(calls) != 4 {
		t.Fatal("exact finite calls", calls)
	}
	var last struct {
		Config map[string]any `json:"config"`
		Target *string        `json:"plugin_id"`
	}
	b := calls[3][len("plugin.base.update_config "):]
	if json.Unmarshal([]byte(b), &last) != nil || last.Config == nil || len(last.Config) != 0 || last.Target != nil {
		t.Fatal("instruction must be consumed in own namespace", calls)
	}
	calls = nil
	if _, err := handle(context.Background(), "init", json.RawMessage(`{}`), host); err != nil || len(calls) != 0 {
		t.Fatal("empty cold fixture never replays", err, calls)
	}
	calls = nil
	if _, err := handle(context.Background(), "init", json.RawMessage(`{"seeds":[{"id":"NotOwned","data":{"x":1}}]}`), host); err == nil || len(calls) != 0 {
		t.Fatal("foreign target accepted", err, calls)
	}
}
