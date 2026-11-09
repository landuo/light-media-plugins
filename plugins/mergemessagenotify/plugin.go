package mergemessagenotify

import (
	"context"
	_ "embed"
	"errors"
	"strings"
	"sync"
)

//go:embed forms.json
var formsJSON []byte

var definitionsOnce sync.Once
var channelDefinitions = []Channel{
	{Key: "custom.iyuu", Name: "爱语飞飞"},
	{Key: "custom.qqbot", Name: "QQ Bot（腾讯官方）"},
}
var pluginElements []any

func formElements() []any {
	definitionsOnce.Do(func() {
		data, err := Decode(formsJSON)
		if err != nil {
			panic(err)
		}
		pluginElements = data.([]any)
	})
	return clone(pluginElements).([]any)
}

type Plugin struct {
	mu             sync.Mutex
	config, stored map[string]any
	registered     []Channel
	host           Host
	qqBot          qqBot
}

func New(host Host) *Plugin              { return &Plugin{host: host} }
func (p *Plugin) Config() map[string]any { p.mu.Lock(); defer p.mu.Unlock(); return cloneMap(p.config) }
func (p *Plugin) StoredConfig() map[string]any {
	p.mu.Lock()
	defer p.mu.Unlock()
	return cloneMap(p.stored)
}
func (p *Plugin) Channels() []Channel {
	p.mu.Lock()
	defer p.mu.Unlock()
	out := make([]Channel, len(p.registered))
	copy(out, p.registered)
	return out
}
func (p *Plugin) State() bool { p.mu.Lock(); defer p.mu.Unlock(); return truth(p.config["enable"]) }

// Init does not replay a test-once flag during startup/reload. saveRequest is a
// trusted caller-origin fact equivalent to the original stack predicate; it is
// never inferred from plugin configuration or an untrusted event field.
func (p *Plugin) Init(ctx context.Context, config map[string]any, saveRequest bool) error {
	p.mu.Lock()
	p.stored = cloneMap(config)
	p.config = cloneMap(config)
	if len(config) == 0 || (len(config) == 2 && config["enabled"] == false && config["enable"] == false) {
		p.config = nil
	}
	p.mu.Unlock()
	for _, c := range channelDefinitions {
		p.mu.Lock()
		for i, old := range p.registered {
			if old.Key == c.Key {
				p.registered = append(p.registered[:i], p.registered[i+1:]...)
				break
			}
		}
		p.mu.Unlock()
		if saveRequest {
			cfg := p.ComponentConfig(c.Key)
			if truth(cfg["test_once"]) {
				result, err := p.send(ctx, c, Message{Title: "测试消息", Text: "这是一条测试消息，您收到此消息表示您的渠道配置无误。"}, cfg)
				if err != nil {
					p.log(ctx, "ERROR", "测试消息发送失败: 渠道 = "+c.Name+"，"+err.Error())
				} else if !truth(result) {
					p.log(ctx, "WARNING", "测试消息发送失败: 渠道 = "+c.Name)
				} else {
					p.log(ctx, "INFO", "测试消息发送成功: 渠道 = "+c.Name)
				}
				cfg["test_once"] = false
				if _, e := p.UpdateComponent(ctx, c.Key, cfg); e != nil {
					continue
				}
			}
		}
		p.mu.Lock()
		p.registered = append(p.registered, c)
		p.mu.Unlock()
	}
	return nil
}
func (p *Plugin) Stop() { p.mu.Lock(); p.registered = nil; p.mu.Unlock() }
func (p *Plugin) ComponentConfig(key string) map[string]any {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.componentConfig(key)
}
func (p *Plugin) componentConfig(key string) map[string]any {
	out := map[string]any{}
	if key == "" {
		return out
	}
	prefix := key + "."
	for k, v := range p.config {
		if k != "" && strings.HasPrefix(k, prefix) {
			out[strings.TrimPrefix(k, prefix)] = clone(v)
		}
	}
	return out
}
func (p *Plugin) save(ctx context.Context, config map[string]any) (bool, error) {
	ok := true
	var err error
	if p.host.SaveConfig != nil {
		ok, err = p.host.SaveConfig(ctx, cloneMap(config))
	}
	if err != nil {
		return false, err
	}
	p.mu.Lock()
	p.stored = cloneMap(config)
	p.mu.Unlock()
	return ok, nil
}
func (p *Plugin) UpdateComponent(ctx context.Context, key string, config map[string]any) (bool, error) {
	if key == "" {
		return false, nil
	}
	p.mu.Lock()
	current := cloneMap(p.config)
	p.mu.Unlock()
	if len(current) == 0 && len(config) == 0 {
		return false, nil
	}
	if current == nil {
		current = map[string]any{}
	}
	prefix := key + "."
	for k := range current {
		if strings.HasPrefix(k, prefix) {
			delete(current, k)
		}
	}
	for k, v := range config {
		if k != "" {
			current[prefix+k] = clone(v)
		}
	}
	result, err := p.save(ctx, current)
	if err != nil {
		return false, err
	}
	p.mu.Lock()
	p.config = current
	p.mu.Unlock()
	return result, nil
}
func (p *Plugin) Form(ctx context.Context) ([]any, map[string]any, error) {
	elements := formElements()
	registered := p.Channels()
	data := map[string]any{"channel_strategy": "ALL_SELECTED", "custom.qqbot.target_type": "c2c"}
	keys := map[string]bool{}
	items := []any{}
	for _, c := range registered {
		keys[c.Key] = true
		items = append(items, map[string]any{"title": c.Name, "value": c.Key})
	}
	var walk func([]any) []any
	walk = func(elems []any) []any {
		r := []any{}
		for _, v := range elems {
			m := v.(map[string]any)
			props, _ := m["props"].(map[string]any)
			if model, _ := props["model"].(string); model == "enable_channels" {
				props["items"] = items
			}
			if value, _ := props["value"].(string); strings.HasPrefix(value, "_tab.") {
				if !keys[strings.TrimPrefix(value, "_tab.")] {
					continue
				}
			}
			if children, ok := m["content"].([]any); ok {
				m["content"] = walk(children)
			}
			r = append(r, m)
		}
		return r
	}
	elements = walk(elements)
	stored := p.StoredConfig()
	if p.host.LoadConfig != nil {
		var err error
		stored, err = p.host.LoadConfig(ctx)
		if err != nil {
			return nil, nil, err
		}
	}
	if stored == nil {
		stored = map[string]any{}
	}
	if _, exists := stored["channel_strategy"]; !exists {
		stored["channel_strategy"] = "ALL_SELECTED"
		if _, err := p.save(ctx, stored); err != nil {
			return nil, nil, err
		}
	}
	return elements, data, nil
}

func (p *Plugin) Send(ctx context.Context, key string, message Message) (any, error) {
	p.mu.Lock()
	for _, c := range p.registered {
		if c.Key == key {
			config := p.componentConfig(key)
			p.mu.Unlock()
			return p.send(ctx, c, message, config)
		}
	}
	p.mu.Unlock()
	return nil, errors.New("channel not registered")
}
