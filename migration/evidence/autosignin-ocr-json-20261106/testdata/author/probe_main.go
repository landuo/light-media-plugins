package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/autosignin"
	"os"
)

func manifest() sdk.Manifest {
	return sdk.Manifest{SchemaVersion: 1, PluginID: "OwnedOCRValueDomain", Name: "Owned source OCR fixture", Version: "1.0", Runtime: "go-executable", Entry: "owned-ocr-domain", HostAPIMin: 1, HostAPIMax: 1, Methods: []string{"init", "get_state", "get_api", "get_command", "get_service", "stop", "stop_service", "close", "ocr_domain", "set_custom", "custom_config", "source_credentials", "source_request", "source_request_raw", "source_ocr_raw"}, Capabilities: []string{sdk.BaseGetConfig, sdk.BaseUpdateConfig, sdk.SitesSourceCustomConfigCapability, sdk.SitesSourceCredentialsCapability, sdk.SitesSourceRequestCapability, sdk.CaptchaOCRTextCapability, sdk.LogWriteCapability}}
}
func handle(ctx context.Context, method string, raw json.RawMessage, host sdk.HostCaller) (json.RawMessage, error) {
	s := sdk.Sites{Host: host}
	switch method {
	case "init", "stop", "stop_service", "close":
		return json.RawMessage(`null`), nil
	case "get_state":
		return json.RawMessage(`false`), nil
	case "get_api", "get_service", "get_command":
		return json.RawMessage(`[]`), nil
	case "ocr_domain":
		return autosignin.OwnedOCRValueDomain(ctx, host, raw)
	case "set_custom":
		v, e := (sdk.Base{Host: host}).UpdateConfig(ctx, json.RawMessage(raw), "CustomSites")
		if e != nil {
			return nil, e
		}
		return json.Marshal(v)
	case "custom_config":
		v, e := s.SourceCustomConfig(ctx)
		if e != nil {
			return nil, e
		}
		return json.Marshal(v)
	case "source_credentials":
		var in sdk.SiteSourceReferenceRequestV1
		if e := json.Unmarshal(raw, &in); e != nil {
			return nil, e
		}
		v, e := s.SourceCredentials(ctx, in.Reference)
		if e != nil {
			return nil, e
		}
		return json.Marshal(v)
	case "source_ocr_raw":
		return host(ctx, sdk.CaptchaOCRTextCapability, raw)
	case "source_request_raw":
		return host(ctx, sdk.SitesSourceRequestCapability, raw)
	case "source_request":
		var in sdk.SiteSourceHTTPRequestV1
		if e := json.Unmarshal(raw, &in); e != nil {
			return nil, e
		}
		v, e := s.SourceRequest(ctx, in)
		if e != nil {
			return nil, e
		}
		return json.Marshal(v)
	}
	return nil, errors.New("unsupported owned method")
}
func main() {
	if len(os.Args) == 2 && os.Args[1] == "--manifest" {
		json.NewEncoder(os.Stdout).Encode(manifest())
		return
	}
	if e := sdk.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, manifest(), handle); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
