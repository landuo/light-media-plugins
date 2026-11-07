package apprise

import (
	"context"
	"net/http"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"time"
)

const appriseInfoIcon72 = "https://github.com/caronc/apprise/raw/master/apprise/assets/themes/default/apprise-info-72x72.png"

var alphanumericToken32 = regexp.MustCompile(`(?i)^[a-z0-9]{32}$`)

type providerHTTPOptions struct {
	overflow, format string
	emojis, verify   bool
	timeout          [2]float64
	throttle         providerThrottle
}

func (s *providerHTTPOptions) configure(u sourceURL) bool {
	s.overflow, s.format = "upstream", "text"
	s.verify, s.timeout = true, [2]float64{4, 4}
	if value, ok := u.query["verify"]; ok {
		s.verify = parseBool(value, false)
	}
	for i, name := range []string{"cto", "rto"} {
		if seconds, err := strconv.ParseFloat(u.query[name], 64); err == nil {
			s.timeout[i] = seconds
		}
	}
	switch value := strings.ToLower(u.query["format"]); value {
	case "text", "html", "markdown":
		s.format = value
	}
	switch value := strings.ToLower(u.query["overflow"]); value {
	case "upstream", "truncate", "split":
		s.overflow = value
	}
	s.emojis = parseBool(u.query["emojis"], false)
	if value, ok := u.query["store"]; ok && !parseBool(value, false) {
		// These providers expose read-only URL identities in NotifyBase.
		return false
	}
	if value, ok := u.query["tz"]; ok {
		if value == "" {
			return false
		}
		if _, err := time.LoadLocation(value); err != nil {
			return false
		}
	}
	return true
}

func (s *providerHTTPOptions) waitToSend(ctx context.Context) error {
	return s.throttle.wait(ctx, 5500*time.Millisecond)
}

func (s *providerHTTPOptions) successful(status int) bool { return status == http.StatusOK }

func (s *providerHTTPOptions) post(endpoint, contentType string, data []byte) Request {
	return Request{
		Method: http.MethodPost, URL: endpoint, Data: data,
		Headers:     map[string]string{"User-Agent": "Apprise", "Content-Type": contentType},
		HeaderOrder: [][2]string{{"User-Agent", "Apprise"}, {"Content-Type", contentType}},
		Verify:      s.verify, Timeout: s.timeout,
	}
}

// Join and IFTTT both read the credential from the authority. With userinfo
// present, the hostname becomes another recipient before constructor sorting.
func recipientCredentialAndTargets(u sourceURL) (string, []string) {
	credential := u.host
	var targets []string
	if u.rawUser != nil && *u.rawUser != "" {
		credential = *u.user
		targets = append(targets, strings.FieldsFunc(u.host, sourceListDelimiter)...)
	}
	for _, part := range strings.FieldsFunc(u.path, func(r rune) bool {
		return strings.ContainsRune(" \t\r\n,\\/", r)
	}) {
		targets = append(targets, strings.FieldsFunc(sourceUnquote(part), sourceListDelimiter)...)
	}
	for _, part := range strings.FieldsFunc(u.query["to"], sourceListDelimiter) {
		targets = append(targets, strings.FieldsFunc(sourceUnquote(part), sourceListDelimiter)...)
	}
	slices.Sort(targets)
	return credential, slices.Compact(targets)
}

func titlelessNotificationChunks(title, body string, options *providerHTTPOptions, bodyLimit int) ([]notificationChunk, error) {
	tidy, err := notificationChunks(title, body, options.emojis, "upstream", options.format)
	if err != nil {
		return nil, err
	}
	title, body = tidy[0].title, tidy[0].body
	if title != "" {
		if options.format == "html" {
			title = "<b>" + title + "</b><br />"
		}
		body = title + "\r\n" + body
	}
	return splitNotificationChunks("", body, options.overflow, options.format, 0, bodyLimit), nil
}
