package apprise

import (
	"net/url"
	"regexp"
	"strings"
)

const joinEndpoint = "https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush"
const joinInfoIcon = "https://github.com/caronc/apprise/raw/master/apprise/assets/themes/default/apprise-info-72x72.png"

var joinDevice = regexp.MustCompile(`(?i)^[a-z0-9]{32}$`)
var joinGroup = regexp.MustCompile(`(?i)^(?:group\.)?(all|android|chrome|windows10|phone|tablet|pc)`)

type joinService struct {
	providerHTTPOptions
	key, priority string
	targets       []string
	includeImage  bool
}

func parseJoinService(raw string) (*joinService, bool) {
	u, valid := parseSourceURLWithHostVerification(raw, false)
	if !valid {
		return nil, false
	}
	key, targets := recipientCredentialAndTargets(u)
	if !joinDevice.MatchString(strings.TrimSuffix(key, "\n")) {
		return nil, false
	}
	s := &joinService{key: strings.TrimFunc(key, sourceSpace), priority: "0", targets: targets, includeImage: true}
	if !s.configure(u) {
		return nil, false
	}
	priority := strings.ToLower(sourceUnquote(u.query["priority"]))
	for _, pair := range [][2]string{{"l", "-2"}, {"m", "-1"}, {"n", "0"}, {"h", "1"}, {"e", "2"}, {"-2", "-2"}, {"-1", "-1"}, {"0", "0"}, {"1", "1"}, {"2", "2"}} {
		if strings.HasPrefix(priority, pair[0]) {
			s.priority = pair[1]
			break
		}
	}
	if value, specified := u.query["image"]; specified {
		s.includeImage = parseBool(value, false)
	}
	if len(s.targets) == 0 {
		s.targets = []string{"group.all"}
	}
	for i, target := range s.targets {
		if group := joinGroup.FindStringSubmatch(target); group != nil {
			s.targets[i] = "group." + strings.ToLower(group[1])
		}
	}
	return s, true
}

func (s *joinService) requests(title, body string) ([]Request, error) {
	chunks, err := notificationChunksWithBodyLimit(title, body, s.emojis, s.overflow, s.format, 1000)
	if err != nil {
		return nil, err
	}
	calls := make([]Request, 0, len(chunks)*len(s.targets))
	for _, chunk := range chunks {
		for _, target := range s.targets {
			key := "deviceNames"
			if joinGroup.MatchString(target) || joinDevice.MatchString(strings.TrimSuffix(target, "\n")) {
				key = "deviceId"
			}
			query := "apikey=" + url.QueryEscape(s.key) + "&priority=" + s.priority +
				"&title=" + url.QueryEscape(chunk.title) + "&text=" + url.QueryEscape(chunk.body) + "&" + key + "=" + url.QueryEscape(target)
			if s.includeImage {
				query += "&icon=" + url.QueryEscape(joinInfoIcon)
			}
			calls = append(calls, s.post(joinEndpoint+"?"+query, "application/x-www-form-urlencoded", nil))
		}
	}
	return calls, nil
}
