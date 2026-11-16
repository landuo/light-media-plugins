package removelink

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestIndependentUnknownHomeInitialScrapAndDelayedFinally(t *testing.T) {
	raw, err := os.ReadFile("/Users/accidia/projects/light-media-plugins/work/sites-review-20261105/removelink-family-review/current58/unknown-home-catch-source-oracle.json")
	if err != nil {
		t.Fatal(err)
	}
	var source struct {
		Cases []struct {
			Input    oracleCase
			Expected map[string]json.RawMessage
		}
	}
	if err = json.Unmarshal(raw, &source); err != nil {
		t.Fatal(err)
	}
	for _, r := range source.Cases {
		t.Run(r.Input.Name, func(t *testing.T) {
			got := runOracle(t, r.Input).(map[string]any)
			for _, key := range []string{"error", "files", "queue", "logged_errors", "state"} {
				a, _ := json.Marshal(got[key])
				var want any
				if err := json.Unmarshal(r.Expected[key], &want); err != nil {
					t.Fatal(err)
				}
				b, _ := json.Marshal(want)
				if string(a) != string(b) {
					t.Errorf("source %s=%s; Go=%s", key, b, a)
				}
			}
		})
	}
}
func TestIndependentHomeRuntimeKillsOnlyFailedObserver(t *testing.T) {
	f := startProtocol(t)
	bad, good := filepath.Join(f.root, "bad"), filepath.Join(f.root, "good")
	child := filepath.Join(good, "child")
	for _, p := range []string{bad, child} {
		if err := os.MkdirAll(p, 0700); err != nil {
			t.Fatal(err)
		}
	}
	file := filepath.Join(bad, "owned.mkv")
	if err := os.WriteFile(file, []byte("owned"), 0600); err != nil {
		t.Fatal(err)
	}
	f.call("init", map[string]any{"enabled": true, "monitor_dirs": bad + "\n" + good, "exclude_dirs": "~__lm_review_no_such_user_20261106__/protected", "delete_scrap_infos": true, "delete_torrents": true, "delayed_deletion": false})
	if err := os.Remove(file); err != nil {
		t.Fatal(err)
	}
	concurrencyInject(f, bad, "deleted", file, 1760000001, false)
	concurrencyEventually(t, f, func() bool {
		r := f.call("test_snapshot", nil)
		var s struct {
			Closed bool `json:"watch_closed"`
			Lanes  []struct {
				Path   string
				Closed bool
			} `json:"watch_lanes"`
		}
		if json.Unmarshal(r.Result, &s) != nil {
			t.Fatal("snapshot")
		}
		failed, sibling := false, false
		for _, lane := range s.Lanes {
			if lane.Path == bad {
				failed = lane.Closed
			}
			if lane.Path == good {
				sibling = !lane.Closed
			}
		}
		return !s.Closed && failed && sibling
	})
	if err := os.Remove(child); err != nil {
		t.Fatal(err)
	}
	concurrencyInject(f, good, "deleted", child, 1760000001, true)
	concurrencyEventually(t, f, func() bool { return concurrencyHasEvent(f, child) })
}
