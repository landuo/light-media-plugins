// Package mergemessagenotify ports installed MergeMessageNotify 1.20.3
// (hotlcc). Original source and checksums are bound in migration/ledger.json.
package mergemessagenotify

import (
	"context"
	"errors"
)

type NotificationType struct {
	Name  string
	Value string
}

var NotificationTypes = []NotificationType{{"Download", "资源下载"}, {"Organize", "整理入库"}, {"Subscribe", "订阅"}, {"SiteMessage", "站点"}, {"MediaServer", "媒体服务器"}, {"Manual", "手动处理"}, {"Plugin", "插件"}, {"Other", "其它"}}

func NotifyType(name string) *NotificationType {
	for _, t := range NotificationTypes {
		if t.Name == name {
			return &t
		}
	}
	return nil
}

type Message struct {
	Title   any               `json:"title"`
	Text    any               `json:"text"`
	Type    *NotificationType `json:"-"`
	RawType any               `json:"-"`
	Ext     map[string]any    `json:"ext_info,omitempty"`
}

// Request records Python requests kwargs exactly, including absence vs None,
// bytes vs text and JSON vs form data. The host authorizes each destination.
type Request struct {
	Method string
	URL    string
	Kwargs map[string]any
}
type Response struct {
	Status    int
	JSON      any
	JSONError bool
	Text      string
	Content   []byte
}

func (r Response) OK() bool { return r.Status < 400 }
func (r Response) json() (map[string]any, error) {
	if r.JSONError {
		return nil, errors.New("ValueError")
	}
	v := r.JSON
	if !truth(v) {
		return map[string]any{}, nil
	}
	m, ok := v.(map[string]any)
	if !ok {
		return nil, errors.New("AttributeError")
	}
	return m, nil
}

type Host struct {
	HTTP       func(context.Context, Request) (Response, error)
	SaveConfig func(context.Context, map[string]any) (bool, error)
	LoadConfig func(context.Context) (map[string]any, error)
	Log        func(context.Context, string, string)
}

type Channel struct {
	Key, Name string
}
type Attempt struct {
	Key    string
	Result any
	Error  string
}
type Dispatch struct {
	Attempts        []Attempt
	Success, Failed int
	Ignored         bool
	Error           string
}
