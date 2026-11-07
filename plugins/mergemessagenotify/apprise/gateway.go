package apprise

import (
	"crypto/rand"
	"fmt"
	"net/http"
	"net/url"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"
)

// NotifyAppriseAPI in the pinned Apprise 1.9.9 source defines the gateway
// token, URL, form/JSON bodies, recursion headers and strict HTTP 200 result.
var gatewayToken = regexp.MustCompile(`^[A-Za-z0-9_İıſK-]{1,128}$`)
var gatewayNative = regexp.MustCompile(`(?i)^http(s?)://([A-Z0-9._-]+)(:[0-9]+)?(/[^?]+?)?/notify/([A-Z0-9_-]{1,32})/?(\?.+)?$`)

// The original asset has one UUID4 per process and starts recursion at zero.
var gatewaySourceID = sync.OnceValue(func() string {
	var id [16]byte
	_, _ = rand.Read(id[:])
	id[6] = id[6]&0x0f | 0x40
	id[8] = id[8]&0x3f | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", id[:4], id[4:6], id[6:8], id[8:10], id[10:])
})

type gatewayService struct {
	endpoint, method, overflow, format string
	headers                            [][2]string
	auth                               []any
	tags                               []string
	verify, emojis                     bool
	timeout                            [2]float64
}

func gatewayNativeURL(raw string) (string, bool) {
	match := gatewayNative.FindStringSubmatch(raw)
	if match == nil {
		return "", false
	}
	result := "apprise" + strings.ToLower(match[1]) + "://" + match[2] + match[3] + match[4] + "/" + match[5] + "/"
	if match[6] != "" {
		// The native parser prefixes an additional question mark to the
		// captured query, so the first query key retains a question mark.
		result += "?" + match[6]
	}
	return result, true
}

func parseGatewayService(raw string) (gatewayService, bool) {
	s := gatewayService{
		method: "form", overflow: "upstream", format: "text",
		headers: [][2]string{{"User-Agent", "Apprise"}}, verify: true,
		timeout: [2]float64{4, 30},
	}
	u, valid := parseSourceURL(raw)
	if !valid {
		return s, false
	}
	var token, fullPath string
	switch {
	case u.query["token"] != "":
		token = sourceUnquote(u.query["token"])
		fullPath = sourceUnquote(u.path)
	case u.query["to"] != "":
		token = sourceUnquote(u.query["to"])
		fullPath = sourceUnquote(u.path)
	default:
		// split_path unquotes its components and URLBase.__init__ unquotes
		// the rebuilt base path once more, but does not touch the token.
		parts := strings.FieldsFunc(u.path, func(r rune) bool {
			return strings.ContainsRune(" \t\r\n,\\/", r)
		})
		if len(parts) == 0 {
			return s, false
		}
		for i, part := range parts {
			parts[i] = sourceUnquote(part)
		}
		token = parts[len(parts)-1]
		fullPath = sourceUnquote(strings.Join(parts[:len(parts)-1], "/"))
	}
	// Python's final $ also matches just before a trailing newline.
	if !gatewayToken.MatchString(strings.TrimSuffix(token, "\n")) {
		return s, false
	}
	token = strings.TrimFunc(token, sourceSpace)
	scheme := "http"
	if u.scheme == "apprises" {
		scheme = "https"
	}
	s.endpoint = scheme + "://" + u.host + u.port
	if fullPath = strings.Trim(fullPath, "/"); fullPath != "" {
		s.endpoint += "/" + sourceQuote(fullPath, "/!$&'()*+,-.:;=@[]~%")
	}
	s.endpoint += "/notify/" + sourceQuote(token, "")
	if method := u.query["method"]; method != "" {
		s.method = strings.ToLower(sourceUnquote(method))
		if s.method != "json" && s.method != "form" {
			return s, false
		}
	}
	if u.user != nil && *u.user != "" {
		var password any
		if u.password != nil {
			password = *u.password
		}
		s.auth = []any{*u.user, password}
	}
	for _, header := range u.headers {
		s.headers = orderedPairSet(s.headers, header[0], header[1])
	}
	if tags := u.query["tags"]; tags != "" {
		s.tags = strings.FieldsFunc(tags, sourceListDelimiter)
		for i, tag := range s.tags {
			s.tags[i] = sourceUnquote(tag)
		}
		// URLBase.parse_list and NotifyAppriseAPI.__init__ each parse tags.
		s.tags = strings.FieldsFunc(strings.Join(s.tags, ","), sourceListDelimiter)
		slices.Sort(s.tags)
		s.tags = slices.Compact(s.tags)
	}
	for key, value := range u.query {
		switch key {
		case "verify":
			s.verify = parseBool(value, false)
		case "cto", "rto":
			if seconds, err := strconv.ParseFloat(value, 64); err == nil {
				if key == "cto" {
					s.timeout[0] = seconds
				} else {
					s.timeout[1] = seconds
				}
			}
		case "overflow":
			switch strings.ToLower(value) {
			case "upstream", "truncate", "split":
				s.overflow = strings.ToLower(value)
			}
		case "format":
			switch strings.ToLower(value) {
			case "text", "html", "markdown":
				s.format = strings.ToLower(value)
			}
		case "emojis":
			s.emojis = parseBool(value, false)
		case "tz":
			if value == "" {
				return s, false
			}
			if _, err := time.LoadLocation(value); err != nil {
				return s, false
			}
		}
	}
	return s, true
}

func sourceListDelimiter(r rune) bool {
	return sourceSpace(r) || strings.ContainsRune("[];,", r)
}

func (s gatewayService) successful(status int) bool { return status == http.StatusOK }

func (s gatewayService) requests(title, body string) ([]Request, error) {
	if s.method == "json" && len(s.tags) != 0 {
		// The source adds tags after serializing the payload to a string.
		// Its caught TypeError fails this service without touching the wire.
		return nil, nil
	}
	return notificationRequests(title, body, s.emojis, s.overflow, s.format, s.request)
}

func (s gatewayService) request(title, body string) (Request, error) {
	fields := object{{"title", title}, {"body", body}, {"type", "info"}, {"format", s.format}}
	headers := slices.Clone(s.headers)
	var data []byte
	if s.method == "json" {
		var err error
		data, err = pythonJSON(fields)
		if err != nil {
			return Request{}, err
		}
		headers = orderedPairSet(headers, "Content-Type", "application/json")
	} else {
		var form strings.Builder
		for i, field := range fields {
			if i > 0 {
				form.WriteByte('&')
			}
			form.WriteString(field.key + "=" + url.QueryEscape(field.value.(string)))
		}
		for _, tag := range s.tags {
			form.WriteString("&tag=" + url.QueryEscape(tag))
		}
		data = []byte(form.String())
	}
	for _, header := range [][2]string{
		{"Accept", "application/json"},
		{"X-Apprise-ID", gatewaySourceID()},
		{"X-Apprise-Recursion-Count", "1"},
	} {
		headers = orderedPairSet(headers, header[0], header[1])
	}
	headerValues := make(map[string]string, len(headers)+1)
	hasContentType := false
	for _, header := range headers {
		headerValues[header[0]] = header[1]
		hasContentType = hasContentType || strings.EqualFold(header[0], "Content-Type")
	}
	if s.method == "form" && !hasContentType {
		contentType := "application/x-www-form-urlencoded"
		headers = append(headers, [2]string{"Content-Type", contentType})
		headerValues["Content-Type"] = contentType
	}
	return Request{
		Method: http.MethodPost, URL: s.endpoint, Data: data,
		Headers: headerValues, HeaderOrder: headers, Auth: s.auth,
		Verify: s.verify, Timeout: s.timeout,
	}, nil
}
