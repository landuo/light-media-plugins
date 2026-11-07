package mergemessagenotify

import (
	"context"
	"encoding/json"
	"fmt"
)

type object = map[string]any

type message struct {
	title, text, notificationType any
	fields                        object
}

type channel struct {
	name string
	send func(context.Context, message) (bool, error)
}

func truth(value any) bool {
	switch value := value.(type) {
	case nil:
		return false
	case bool:
		return value
	case string:
		return value != ""
	case json.Number:
		n, _ := value.Float64()
		return n != 0
	case float64:
		return value != 0
	case []any:
		return len(value) != 0
	case object:
		return len(value) != 0
	default:
		return true
	}
}

// routeNotice follows the source NoticeMessage handler. Each attempt receives
// the same original event fields, including the MoviePilot v1 type alias.
func routeNotice(ctx context.Context, config, fields object, registered map[string]channel, log func(string, string)) {
	if !truth(config["enable"]) || len(fields) == 0 {
		return
	}
	log("INFO", "监听到发送消息通知事件")
	selected := config["enable_channels"]
	const abort = "发送消息通知事件监听任务执行中止: "
	if !truth(selected) {
		log("WARNING", abort+"没有启用任何渠道")
		return
	}
	if truth(fields["channel"]) {
		log("WARNING", abort+"忽略系统渠道的消息")
		return
	}
	in := message{title: fields["title"], text: fields["text"], notificationType: fields["type"], fields: fields}
	if !truth(in.title) && !truth(in.text) {
		log("WARNING", abort+"标题和内容不允许同时为空")
		return
	}
	if !truth(in.notificationType) {
		in.notificationType = fields["mtype"]
	}
	keys, ok := selected.([]any)
	if !ok {
		log("ERROR", "发送消息通知事件监听任务执行异常: 启用渠道应为列表")
		return
	}
	ordered := config["channel_strategy"] == "ORDER_SUCCESS_ONE"
	var succeeded, failed int
	for _, key := range keys {
		id, _ := key.(string)
		if id == "" {
			continue
		}
		out, exists := registered[id]
		if !exists {
			continue
		}
		success, err := out.send(ctx, in)
		switch {
		case err != nil:
			failed++
			log("ERROR", "消息发送执行异常: 渠道 = "+out.name)
		case success:
			succeeded++
			log("INFO", "消息发送执行完成: 渠道 = "+out.name+" success = True")
		default:
			failed++
			log("INFO", "消息发送执行完成: 渠道 = "+out.name+" success = False")
		}
		if ordered && succeeded > 0 {
			break
		}
	}
	log("INFO", fmt.Sprintf("发送消息通知事件监听任务执行成功: 成功渠道数 = %d, 失败渠道数 = %d", succeeded, failed))
}
