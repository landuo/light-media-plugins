package mergemessagenotify

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/landuo/light-media-plugins/internal/requestsproxy"
)

type RequestsHTTP struct {
	Environment []string
}

var errChannelHTTP = errors.New("通知渠道 HTTP 请求失败")

func (h RequestsHTTP) Send(ctx context.Context, input Request) (Response, error) {
	target, err := url.Parse(input.URL)
	if err != nil || target.Scheme != "https" || target.User != nil || target.Fragment != "" {
		return Response{}, errChannelHTTP
	}
	switch target.Host {
	case "iyuu.cn", "bots.qq.com", "api.sgroup.qq.com", "sandbox.api.sgroup.qq.com":
	default:
		return Response{}, errChannelHTTP
	}
	if params, ok := input.Kwargs["params"].(url.Values); ok {
		target.RawQuery = params.Encode()
	}
	var body []byte
	if value := input.Kwargs["json"]; value != nil {
		body, err = json.Marshal(value)
		if err != nil {
			return Response{}, errChannelHTTP
		}
	}
	req, err := http.NewRequestWithContext(ctx, strings.ToUpper(input.Method), target.String(), bytes.NewReader(body))
	if err != nil {
		return Response{}, errChannelHTTP
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if headers, ok := input.Kwargs["headers"].(map[string]any); ok {
		for key, value := range headers {
			text, ok := value.(string)
			if !ok {
				return Response{}, errChannelHTTP
			}
			req.Header.Set(key, text)
		}
	}
	base := http.DefaultTransport.(*http.Transport).Clone()
	transport, err := requestsproxy.NewRequestsProxyTransport(base, h.Environment, nil, target)
	if err != nil {
		return Response{}, errChannelHTTP
	}
	defer transport.CloseIdleConnections()
	timeout := 12 * time.Second
	if seconds, ok := input.Kwargs["timeout"].(int); ok && seconds > 0 {
		timeout = time.Duration(seconds) * time.Second
	}
	client := http.Client{
		Transport: transport,
		Timeout:   timeout,
		// Never forward credentials or resend a message after a redirect.
		CheckRedirect: func(*http.Request, []*http.Request) error { return errChannelHTTP },
	}
	reply, err := client.Do(req)
	if err != nil {
		if ctx.Err() != nil {
			return Response{}, ctx.Err()
		}
		return Response{}, errChannelHTTP
	}
	defer reply.Body.Close()
	const maxReply = 1 << 20
	content, err := io.ReadAll(io.LimitReader(reply.Body, maxReply+1))
	if err != nil || len(content) > maxReply {
		return Response{}, errChannelHTTP
	}
	value, decodeErr := Decode(content)
	return Response{Status: reply.StatusCode, JSON: value, JSONError: decodeErr != nil, Text: string(content), Content: content}, nil
}
