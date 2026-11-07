package mergemessagenotify

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"reflect"
	"testing"
)

func TestSourceNoticeRouting(t *testing.T) {
	raw, err := os.ReadFile("testdata/source-routing.json")
	if err != nil {
		t.Fatal(err)
	}
	type attempt struct {
		Channel string `json:"channel"`
		Title   any    `json:"title"`
		Text    any    `json:"text"`
		Type    any    `json:"type"`
		Fields  object `json:"fields"`
	}
	var fixture struct {
		Cases []struct {
			Name   string
			Config object
			Fields object
			Calls  []attempt
			Logs   [][2]string
		}
	}
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatal(err)
	}
	if len(fixture.Cases) == 0 {
		t.Fatal("missing original observations")
	}
	for _, row := range fixture.Cases {
		t.Run(row.Name, func(t *testing.T) {
			calls := []attempt{}
			logs := [][2]string{}
			newChannel := func(name string, ok bool, err error) channel {
				return channel{name: name, send: func(_ context.Context, in message) (bool, error) {
					calls = append(calls, attempt{name, in.title, in.text, in.notificationType, in.fields})
					return ok, err
				}}
			}
			registered := map[string]channel{
				"first":  newChannel("first", true, nil),
				"second": newChannel("second", false, nil),
				"broken": newChannel("broken", false, errors.New("synthetic failure")),
			}
			routeNotice(t.Context(), row.Config, row.Fields, registered, func(level, message string) {
				logs = append(logs, [2]string{level, message})
			})
			if !reflect.DeepEqual(calls, row.Calls) || !reflect.DeepEqual(logs, row.Logs) {
				t.Fatalf("calls = %#v, want %#v\nlogs = %v, want %v", calls, row.Calls, logs, row.Logs)
			}
		})
	}
}
