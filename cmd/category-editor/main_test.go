package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"slices"
	"testing"
	"time"

	plugins "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/categoryeditor"
)

// This starts the actual executable and standard SDK transport with synthetic
// resources. It is not an application/category-file/notification E2E test.
func TestWorkerProtocolSmoke(t *testing.T) {
	if runtime.GOOS != "linux" || runtime.GOARCH != "amd64" {
		t.Skip("the supported worker build target is linux/amd64")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	binary := filepath.Join(t.TempDir(), "category-editor")
	build := exec.CommandContext(ctx, "go", "build", "-trimpath", "-buildvcs=false", "-o", binary, ".")
	build.Env = append(os.Environ(), "GOOS=linux", "GOARCH=amd64", "CGO_ENABLED=0")
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build worker: %v\n%s", err, output)
	}
	manifest := categoryeditor.Manifest()
	output, err := exec.CommandContext(ctx, binary, "--manifest").Output()
	if err != nil {
		t.Fatal(err)
	}
	var emitted plugins.Manifest
	if err := json.Unmarshal(output, &emitted); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(emitted, manifest) || emitted.Entry != "category-editor" {
		t.Fatalf("executable manifest differs: %+v", emitted)
	}

	identity := plugins.Identity{PluginID: "CategoryEditor", InstanceID: "synthetic-category", Version: "1.3"}
	client, err := (plugins.Runner{Timeout: 5 * time.Second}).Start(ctx, plugins.Command{Path: binary}, manifest, plugins.SessionBinding{Identity: identity, Generation: 1})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		stopCtx, stopCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer stopCancel()
		if err := client.Stop(stopCtx); err != nil {
			t.Errorf("stop/join worker: %v", err)
		}
	})

	var methods []string
	var payloads []json.RawMessage
	failMethod := ""
	defaultText := "movie: synthetic-default-one\n"
	host := func(callCtx context.Context, got plugins.Identity, method string, raw json.RawMessage) (json.RawMessage, error) {
		if callCtx.Err() != nil || got != identity {
			return nil, errors.New("invalid synthetic callback scope")
		}
		methods = append(methods, method)
		payloads = append(payloads, slices.Clone(raw))
		if method == failMethod {
			return nil, errors.New("synthetic resource failure")
		}
		switch method {
		case plugins.CategoryDefaultCapability:
			return json.Marshal(defaultText)
		case plugins.CategoryApplyCapability, plugins.SystemMessagePutCapability:
			return json.RawMessage(`null`), nil
		case plugins.BaseUpdateConfig:
			return json.RawMessage(`false`), nil // Return value is deliberately ignored.
		default:
			return nil, errors.New("unexpected synthetic resource")
		}
	}
	call := func(method, payload string) plugins.RunResult {
		t.Helper()
		result, err := client.Call(ctx, method, json.RawMessage(payload), host)
		if err != nil {
			t.Fatalf("%s: %v", method, err)
		}
		return result
	}
	state := func(want string) {
		t.Helper()
		if got := string(call("get_state", `null`).Result); got != want {
			t.Fatalf("state = %s, want %s", got, want)
		}
	}
	state(`false`)
	failMethod = plugins.CategoryApplyCapability
	if _, err := client.Call(ctx, "init", json.RawMessage(`{"enabled":"retained","content":"synthetic"}`), host); err == nil {
		t.Fatal("failed host callback unexpectedly succeeded")
	}
	if !reflect.DeepEqual(methods, []string{plugins.CategoryApplyCapability}) {
		t.Fatalf("effects continued after failure: %v", methods)
	}
	state(`"retained"`)
	call("init", `{}`)
	state(`"retained"`) // Same object survives failure and falsey reinitialization.
	if len(methods) != 1 {
		t.Fatalf("falsey reinit performed callbacks: %v", methods)
	}

	failMethod, methods, payloads = "", nil, nil
	result := call("init", `{"enabled":true,"content":"movie: synthetic\n","unrelated":1}`)
	wantMethods := []string{plugins.CategoryApplyCapability, plugins.SystemMessagePutCapability, plugins.BaseUpdateConfig}
	if result.HostCalls != 3 || !reflect.DeepEqual(methods, wantMethods) {
		t.Fatalf("callback order/count = %v/%d", methods, result.HostCalls)
	}
	var update map[string]any
	if err := json.Unmarshal(payloads[2], &update); err != nil {
		t.Fatal(err)
	}
	wantUpdate := map[string]any{"config": map[string]any{"enabled": false, "content": "movie: synthetic\n"}}
	if !reflect.DeepEqual(update, wantUpdate) {
		t.Fatalf("configuration replacement = %s", payloads[2])
	}
	state(`false`)

	for _, text := range []string{"movie: synthetic-default-one\n", "movie: synthetic-default-two\n"} {
		defaultText = text
		result := call("get_form", `null`)
		var form []json.RawMessage
		if err := json.Unmarshal(result.Result, &form); err != nil || len(form) != 2 {
			t.Fatalf("form tuple: %s (%v)", result.Result, err)
		}
		var defaults map[string]any
		if err := json.Unmarshal(form[1], &defaults); err != nil {
			t.Fatal(err)
		}
		if result.HostCalls != 1 || defaults["content"] != text || defaults["enabled"] != false {
			t.Fatalf("default resource not freshly read: %s", form[1])
		}
	}
	before := len(methods)
	call("close", `null`)
	call("stop_service", `null`)
	if err := client.Stop(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := client.Call(ctx, "get_form", json.RawMessage(`null`), host); err == nil {
		t.Fatal("stopped worker accepted a call")
	}
	if len(methods) != before {
		t.Fatalf("cleanup or stopped call performed effects: %v", methods[before:])
	}
}
