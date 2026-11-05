// Independent target replay with owned file IO and synthetic resources only.
package main

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"unicode/utf8"

	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/categoryeditor"
)

type Step struct {
	Op           string          `json:"op"`
	Config       json.RawMessage `json:"config"`
	Fault        string          `json:"fault"`
	DefaultText  *string         `json:"default_text"`
	DefaultBytes *string         `json:"default_bytes"`
	UpdateReturn json.RawMessage `json:"update_return"`
}
type Case struct {
	ID    string `json:"id"`
	Steps []Step `json:"steps"`
}
type Event struct {
	Method  string          `json:"method"`
	Payload json.RawMessage `json:"payload"`
}
type Observation struct {
	Op          string            `json:"op"`
	Error       bool              `json:"error"`
	Result      json.RawMessage   `json:"result"`
	State       json.RawMessage   `json:"state"`
	Events      []Event           `json:"events"`
	FileHex     string            `json:"file_hex"`
	Messages    []json.RawMessage `json:"messages"`
	Updates     []json.RawMessage `json:"updates"`
	HelperCalls int               `json:"helper_calls"`
}
type Output struct {
	ID           string        `json:"id"`
	Observations []Observation `json:"observations"`
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}
func invalidSurrogate(raw []byte) bool {
	for i := 0; i < len(raw); i++ {
		if raw[i] != '\\' {
			continue
		}
		i++
		if i >= len(raw) || raw[i] != 'u' {
			continue
		}
		if i+4 >= len(raw) {
			return true
		}
		v, e := strconv.ParseUint(string(raw[i+1:i+5]), 16, 16)
		if e != nil {
			return true
		}
		i += 4
		if v >= 0xDC00 && v <= 0xDFFF {
			return true
		}
		if v < 0xD800 || v > 0xDBFF {
			continue
		}
		if i+6 >= len(raw) || raw[i+1] != '\\' || raw[i+2] != 'u' {
			return true
		}
		w, e := strconv.ParseUint(string(raw[i+3:i+7]), 16, 16)
		if e != nil || w < 0xDC00 || w > 0xDFFF {
			return true
		}
		i += 6
	}
	return false
}
func main() {
	here := "work/migration-20261105/category-review"
	raw, err := os.ReadFile(filepath.Join(here, "inputs.json"))
	check(err)
	var cases []Case
	check(json.Unmarshal(raw, &cases))
	outputs := []Output{}
	directory, err := os.MkdirTemp("", "target-owned-category-")
	check(err)
	defer os.RemoveAll(directory)
	for _, c := range cases {
		user := filepath.Join(directory, "user.yaml")
		def := filepath.Join(directory, "default.yaml")
		check(os.WriteFile(user, []byte("prior\n"), 0600))
		check(os.WriteFile(def, []byte("default-one\n"), 0600))
		p := categoryeditor.New()
		events := []Event{}
		messages := []json.RawMessage{}
		updates := []json.RawMessage{}
		output := Output{ID: c.ID, Observations: []Observation{}}
		for _, step := range c.Steps {
			if step.DefaultText != nil {
				check(os.WriteFile(def, []byte(*step.DefaultText), 0600))
			}
			if step.DefaultBytes != nil {
				b, e := hex.DecodeString(*step.DefaultBytes)
				check(e)
				check(os.WriteFile(def, b, 0600))
			}
			events = []Event{}
			helpers := 0
			host := func(ctx context.Context, method string, payload json.RawMessage) (json.RawMessage, error) {
				short := map[string]string{sdk.CategoryDefaultCapability: "default", sdk.CategoryApplyCapability: "apply", sdk.SystemMessagePutCapability: "message", sdk.BaseUpdateConfig: "update"}[method]
				if short == "" {
					return nil, fmt.Errorf("unexpected callback %s", method)
				}
				events = append(events, Event{short, append(json.RawMessage{}, payload...)})
				if short == step.Fault {
					return nil, fmt.Errorf("synthetic %s failure", short)
				}
				switch short {
				case "default":
					b, e := os.ReadFile(def)
					if e != nil {
						return nil, e
					}
					if !utf8.Valid(b) {
						return nil, fmt.Errorf("not UTF8")
					}
					return json.Marshal(string(b))
				case "apply":
					var fields map[string]json.RawMessage
					if e := json.Unmarshal(payload, &fields); e != nil {
						return nil, e
					}
					v := fields["content"]
					var text string
					if len(v) == 0 || string(v) == "null" {
						return nil, fmt.Errorf("content not text")
					}
					if e := json.Unmarshal(v, &text); e != nil {
						return nil, e
					}
					file, e := os.OpenFile(user, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0600)
					if e != nil {
						return nil, e
					}
					if invalidSurrogate(v) {
						file.Close()
						return nil, fmt.Errorf("unpaired surrogate")
					}
					_, e = file.WriteString(text)
					closeErr := file.Close()
					if e != nil {
						return nil, e
					}
					if closeErr != nil {
						return nil, closeErr
					}
					helpers++
					if step.Fault == "helper" {
						return nil, fmt.Errorf("synthetic helper failure")
					}
					return json.RawMessage(`null`), nil
				case "message":
					messages = append(messages, append(json.RawMessage{}, payload...))
					return json.RawMessage(`null`), nil
				case "update":
					var fields map[string]json.RawMessage
					if e := json.Unmarshal(payload, &fields); e != nil {
						return nil, e
					}
					updates = append(updates, append(json.RawMessage{}, fields["config"]...))
					if len(step.UpdateReturn) > 0 {
						return step.UpdateReturn, nil
					}
					return json.RawMessage(`true`), nil
				}
				panic("unreachable")
			}
			result, callErr := p.Handle(context.Background(), step.Op, step.Config, host)
			if len(result) == 0 {
				result = json.RawMessage(`null`)
			}
			state, stateErr := p.Handle(context.Background(), "get_state", nil, nil)
			check(stateErr)
			contents, e := os.ReadFile(user)
			check(e)
			output.Observations = append(output.Observations, Observation{step.Op, callErr != nil, result, state, append([]Event{}, events...), hex.EncodeToString(contents), append([]json.RawMessage{}, messages...), append([]json.RawMessage{}, updates...), helpers})
		}
		outputs = append(outputs, output)
	}
	raw, err = json.MarshalIndent(map[string]any{"resource_kind": "synthetic callbacks; owned file IO; no real host", "cases": outputs}, "", "  ")
	check(err)
	check(os.WriteFile(filepath.Join(here, "target-observations.json"), append(raw, '\n'), 0600))
	fmt.Printf("target cases=%d\n", len(outputs))
}
