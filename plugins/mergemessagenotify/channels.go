package mergemessagenotify

import (
	"context"
	"errors"
	"net/url"
)

func (p *Plugin) send(ctx context.Context, c Channel, m Message, config map[string]any) (any, error) {
	if truth(m.RawType) {
		return nil, errors.New("通知类型无法识别")
	}
	get := func(key string) any { return config[key] }
	if m.Type != nil && truth(get("enable_notify_types")) {
		selected, err := contains(get("enable_notify_types"), m.Type.Name)
		if err != nil || !selected {
			return false, err
		}
	}
	if c.Key == "custom.qqbot" {
		return p.qqBot.send(ctx, p.host.HTTP, get, m)
	}
	token := get("token")
	if !truth(m.Title) || !truth(token) {
		return false, nil
	}
	if p.host.HTTP == nil {
		return nil, errChannelHTTP
	}
	result, err := p.host.HTTP(ctx, Request{
		Method: "post",
		URL:    "https://iyuu.cn/" + url.PathEscape(str(token)) + ".send",
		Kwargs: map[string]any{"params": url.Values{
			"text": {str(m.Title)}, "desp": {str(or(m.Text, m.Title))},
		}},
	})
	if err != nil {
		return nil, err
	}
	value, err := result.json()
	if err != nil {
		return nil, errors.New("爱语飞飞响应格式无效")
	}
	if !result.OK() && len(value) == 0 {
		return false, nil
	}
	return numberEq(value["errcode"], 0), nil
}
