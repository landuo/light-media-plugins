package mediaserverrefresh

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/removelink"
)

func activeServers(ctx context.Context, host sdk.MediaHost, logger sdk.Logger, names []string) ([]sdk.MediaServer, error) {
	if len(names) == 0 {
		_ = logger.Log(ctx, sdk.LogWarning, "尚未配置媒体服务器，请检查配置")
		return nil, nil
	}
	servers, err := host.Servers(ctx, sdk.MediaServersRequest{Names: names, Probe: true, ConnectivityOnly: true})
	if err != nil {
		return nil, err
	}
	if len(servers) == 0 {
		_ = logger.Log(ctx, sdk.LogWarning, "获取媒体服务器实例失败，请检查配置")
		return nil, nil
	}
	active := make([]sdk.MediaServer, 0, len(servers))
	for _, server := range servers {
		if server.Connected != nil && *server.Connected {
			active = append(active, server)
		} else {
			_ = logger.Log(ctx, sdk.LogWarning, fmt.Sprintf("媒体服务器 %s 未连接，请检查配置", server.Name))
		}
	}
	if len(active) == 0 {
		_ = logger.Log(ctx, sdk.LogWarning, "没有已连接的媒体服务器，请检查配置")
	}
	return active, nil
}

func (p *Plugin) refresh(ctx context.Context, raw json.RawMessage, caller sdk.HostCaller) error {
	config := p.configuration()
	if !removelink.Truth(config.Enabled) {
		return nil
	}
	var event *sdk.MutableEvent
	if err := json.Unmarshal(raw, &event); err != nil || event == nil {
		return err
	}
	data, err := removelink.Decode(event.Data)
	if err != nil || !removelink.Truth(data) {
		return err
	}
	host, logger := sdk.MediaHost{Host: caller}, sdk.Logger{Host: caller}
	active, err := activeServers(ctx, host, logger, config.MediaServers)
	if err != nil || len(active) == 0 {
		return err
	}
	var eventData struct {
		Transfer *struct {
			Target *struct {
				Path string `json:"path"`
			} `json:"target_diritem"`
		} `json:"transferinfo"`
		Media *struct {
			Title    *string         `json:"title"`
			Year     json.RawMessage `json:"year"`
			Type     *string         `json:"type"`
			Category *string         `json:"category"`
		} `json:"mediainfo"`
	}
	if err := json.Unmarshal(event.Data, &eventData); err != nil {
		return err
	}
	if eventData.Transfer == nil || eventData.Transfer.Target == nil || eventData.Transfer.Target.Path == "" {
		return nil
	}
	if eventData.Media == nil {
		return errors.New("transfer event has no mediainfo")
	}
	media := eventData.Media
	item := sdk.MediaRefreshItem{
		Title: media.Title, Year: media.Year, Type: media.Type, Category: media.Category,
		TargetPath: &eventData.Transfer.Target.Path,
	}
	items := []sdk.MediaRefreshItem{item}
	if removelink.Truth(config.Delay) {
		_ = logger.Log(ctx, sdk.LogInfo, fmt.Sprintf("延迟 %v 秒后刷新媒体库... ", config.Delay))
		items, err = p.debounce(ctx, config.Delay, item)
		if err != nil || items == nil {
			return err
		}
	}

	active, err = activeServers(ctx, host, logger, p.configuration().MediaServers)
	if err != nil {
		return err
	}
	if len(active) == 0 {
		return errors.New("no connected media server when refreshing")
	}
	for _, server := range active {
		request := sdk.MediaRefreshRequest{Name: server.Name}
		switch server.Type {
		case "fnos", "trimemedia", "emby", "plex":
			request.Items = items
		case "jellyfin":
			request.Root = true
		default:
			_ = logger.Log(ctx, sdk.LogWarning, fmt.Sprintf("%s 不支持刷新", server.Name))
			continue
		}
		if _, err := host.Refresh(ctx, request); err != nil {
			return err
		}
	}
	return nil
}

func delaySeconds(delay any) (float64, error) {
	switch value := delay.(type) {
	case float64:
		return value, nil
	case string:
		return strconv.ParseFloat(strings.TrimSpace(value), 64)
	case bool:
		return 1, nil // Called only for a truthy delay.
	default:
		return 0, errors.New("invalid media refresh delay")
	}
}

func wallSeconds() float64 {
	now := time.Now()
	return float64(now.Unix()) + float64(now.Nanosecond())/float64(time.Second)
}

func (p *Plugin) debounce(ctx context.Context, delay any, item sdk.MediaRefreshItem) ([]sdk.MediaRefreshItem, error) {
	p.mu.Lock()
	p.pending = append(p.pending, item)
	seconds, err := delaySeconds(delay)
	if err != nil {
		p.mu.Unlock()
		return nil, err
	}
	p.deadline = wallSeconds() + seconds
	if p.inDelay {
		p.mu.Unlock()
		return nil, nil
	}
	p.inDelay = true
	tick := time.NewTicker(time.Second)
	defer tick.Stop()
	for wallSeconds() < p.deadline {
		p.mu.Unlock()
		select {
		case <-ctx.Done():
			p.mu.Lock()
			p.inDelay = false
			p.mu.Unlock()
			return nil, ctx.Err()
		case <-tick.C:
		}
		p.mu.Lock()
	}
	items := p.pending
	p.pending = nil
	p.inDelay = false
	p.mu.Unlock()
	return items, nil
}
