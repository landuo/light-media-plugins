package mergemessagenotify

import (
	"context"
	"encoding/json"
	"errors"
	"sync"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
)

func Manifest() sdk.Manifest {
	return sdk.Manifest{
		SchemaVersion: 1,
		PluginID:      "MergeMessageNotify",
		Name:          "聚合消息通知",
		Description:   "聚合发送爱语飞飞和腾讯官方 QQ Bot 通知。",
		Icon:          "https://raw.githubusercontent.com/hotlcc/MoviePilot-Plugins-Third/main/icons/MergeMessageNotify_121.png",
		Author:        "hotlcc",
		AuthorURL:     "https://github.com/hotlcc",
		Version:       "1.20.3",
		PluginOrder:   66,
		Runtime:       "go-executable",
		Entry:         "merge-message-notify",
		HostAPIMin:    1,
		HostAPIMax:    1,
		Methods:       []string{"init", "get_state", "get_form", "get_render_mode", "listen_notice_message", "stop_service", "stop"},
		Capabilities: []string{
			sdk.BaseGetConfig, sdk.BaseUpdateConfig, sdk.BaseConfigSaveOrigin,
			sdk.NetworkProxyReadCapability, sdk.LogWriteCapability,
		},
		BroadcastHandlers: []sdk.BroadcastHandler{
			{Event: "notice.message", Method: "listen_notice_message"},
		},
		RuntimeSupport: &sdk.RuntimeSupport{Platforms: []string{"linux"}, StorageTypes: []string{"local"}},
	}
}

type Worker struct {
	plugin    *Plugin
	lifecycle sync.Mutex
}

type workerCallKey struct{}
type workerCall struct {
	host      sdk.HostCaller
	proxyOnce sync.Once
	proxy     sdk.NetworkProxySettingsV1
	proxyErr  error
}

func activeCall(ctx context.Context) *workerCall {
	call, _ := ctx.Value(workerCallKey{}).(*workerCall)
	return call
}

func (c *workerCall) proxySettings(ctx context.Context) (sdk.NetworkProxySettingsV1, error) {
	c.proxyOnce.Do(func() {
		c.proxy, c.proxyErr = (sdk.Network{Host: c.host}).ProxySettings(ctx)
	})
	return c.proxy, c.proxyErr
}

func NewWorker() *Worker {
	return &Worker{plugin: New(Host{
		SaveConfig: func(ctx context.Context, cfg map[string]any) (bool, error) {
			result, err := (sdk.Base{Host: activeCall(ctx).host}).UpdateConfig(ctx, cfg)
			return result != nil && *result, err
		},
		LoadConfig: func(ctx context.Context) (map[string]any, error) {
			raw, err := (sdk.Base{Host: activeCall(ctx).host}).GetConfig(ctx)
			if err != nil {
				return nil, err
			}
			return decodeConfig(raw)
		},
		HTTP: func(ctx context.Context, input Request) (Response, error) {
			proxy, err := activeCall(ctx).proxySettings(ctx)
			if err != nil {
				return Response{}, err
			}
			return (RequestsHTTP{Environment: proxy.Environment}).Send(ctx, input)
		},
		Log: func(ctx context.Context, level, message string) {
			_ = (sdk.Logger{Host: activeCall(ctx).host}).Log(ctx, sdk.LogLevel(level), message)
		},
	})}
}

func decodeConfig(raw json.RawMessage) (map[string]any, error) {
	decoded, err := Decode(raw)
	if err != nil || decoded == nil {
		return nil, err
	}
	config, ok := decoded.(map[string]any)
	if !ok {
		return nil, errors.New("invalid MergeMessageNotify configuration")
	}
	return config, nil
}

func (w *Worker) Handle(ctx context.Context, method string, raw json.RawMessage, host sdk.HostCaller) (json.RawMessage, error) {
	ctx = context.WithValue(ctx, workerCallKey{}, &workerCall{host: host})
	switch method {
	case "init":
		w.lifecycle.Lock()
		defer w.lifecycle.Unlock()
		config, err := decodeConfig(raw)
		if err != nil {
			return nil, err
		}
		saved, err := (sdk.Base{Host: host}).ConfigSaveOrigin(ctx)
		if err != nil {
			return nil, err
		}
		return nil, w.plugin.Init(ctx, config, saved)
	case "get_state":
		return json.Marshal(w.plugin.State())
	case "get_render_mode":
		return json.RawMessage(`["vuetify",null]`), nil
	case "get_form":
		w.lifecycle.Lock()
		defer w.lifecycle.Unlock()
		elements, defaults, err := w.plugin.Form(ctx)
		if err != nil {
			return nil, err
		}
		return json.Marshal([]any{elements, defaults})
	case "listen_notice_message":
		var input sdk.MutableEvent
		if err := json.Unmarshal(raw, &input); err != nil {
			return nil, err
		}
		if input.Type != "notice.message" {
			return nil, nil
		}
		fields, err := decodeConfig(input.Data)
		if err != nil {
			return nil, err
		}
		w.plugin.DispatchEvent(ctx, fields)
		return nil, nil
	case "stop_service", "stop":
		w.lifecycle.Lock()
		defer w.lifecycle.Unlock()
		w.plugin.Stop()
		return nil, nil
	default:
		return nil, errors.New("unsupported MergeMessageNotify method")
	}
}
