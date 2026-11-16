package removelink

import (
	"encoding/json"
	"os"
	osuser "os/user"
	"path/filepath"
	"testing"
	"time"
)

type independentDelayedGateOps struct {
	*fixtureOps
	task             string
	entered, release chan struct{}
}

func (o *independentDelayedGateOps) Exists(path string) bool {
	if path == o.task {
		close(o.entered)
		<-o.release
	}
	return o.fixtureOps.Exists(path)
}
func TestIndependentCreatedDuringDelayedExistsKeepsOldLinks(t *testing.T) {
	root := t.TempDir()
	a := filepath.Join(root, "a.mkv")
	b := filepath.Join(root, "b.mkv")
	c := filepath.Join(root, "new.mkv")
	if err := os.WriteFile(a, []byte("owned"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Link(a, b); err != nil {
		t.Fatal(err)
	}
	ops := &independentDelayedGateOps{fixtureOps: &fixtureOps{root: root}, task: a, entered: make(chan struct{}), release: make(chan struct{})}
	id, err := ops.Stat(a)
	if err != nil {
		t.Fatal(err)
	}
	id.Added = time.Unix(0, 0)
	m := New(ops)
	m.Config.Delayed = true
	m.Config.Delay = 30
	m.Now = func() time.Time { return time.Unix(132, 0) }
	m.State = []Tracked{{Path: b, Identity: id}}
	m.Queue = []*Task{{Path: a, Identity: id, At: time.Unix(100, 0)}}
	if err := os.Remove(a); err != nil {
		t.Fatal(err)
	}
	done := make(chan struct{})
	go func() { m.Tick(); close(done) }()
	<-ops.entered
	if err := os.Link(b, c); err != nil {
		close(ops.release)
		t.Fatal(err)
	}
	created := make(chan error, 1)
	go func() { created <- m.Created(c, false) }()
	early := false
	select {
	case err := <-created:
		early = err == nil
	case <-time.After(100 * time.Millisecond):
	}
	close(ops.release)
	<-done
	if !early {
		if err := <-created; err != nil {
			t.Fatal(err)
		}
	}
	_, oldErr := os.Stat(b)
	_, newErr := os.Stat(c)
	t.Logf("actual3.12 expected created-before-release=true old=true new=true; Go early=%v oldErr=%v newErr=%v", early, oldErr, newErr)
	if !early || oldErr != nil || newErr != nil {
		t.Fatal("whole Tick lock suppresses source on_created→recent-rehardlink protection")
	}
}

func TestIndependentOneObserverErrorDoesNotStopSiblingDirectoryEvents(t *testing.T) {
	f := startProtocolMode(t, true)
	one := filepath.Join(f.root, "one")
	two := filepath.Join(f.root, "two")
	child := filepath.Join(two, "child")
	file := filepath.Join(one, "a.mkv")
	for _, p := range []string{one, child} {
		if err := os.MkdirAll(p, 0700); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(file, []byte("owned"), 0600); err != nil {
		t.Fatal(err)
	}
	f.call("init", map[string]any{"enabled": true, "monitor_dirs": one + "\n" + two, "exclude_keywords": 1, "delete_torrents": true, "delayed_deletion": false})
	if err := os.Remove(file); err != nil {
		t.Fatal(err)
	}
	time.Sleep(1800 * time.Millisecond)
	if err := os.Remove(child); err != nil {
		t.Fatal(err)
	}
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		found := false
		f.mu.Lock()
		for _, row := range f.trace {
			if row["op"] == "event" && row["path"] == child {
				found = true
			}
		}
		f.mu.Unlock()
		if found {
			return
		}
		time.Sleep(25 * time.Millisecond)
	}
	t.Fatal("actual original watchdog first observer AttributeError leaves second observer delivering directory deleted event; Go closes aggregate watch")
}

func TestIndependentSourceNamedHomeProtection(t *testing.T) {
	// Actual source expands own UID65534 username, independent of custom HOME.
	// Development OS may give nobody a different home; preserve that local passwd fact.
	u, err := osuser.Lookup("nobody")
	if err != nil {
		t.Fatal(err)
	}
	c := NewConfig()
	c.Exclude = "~nobody/owned-protected"
	target := filepath.Join(u.HomeDir, "owned-protected/item.mkv")
	if !c.Excluded(target, "/independent-current-home") {
		t.Fatalf("source named-user expansion from passwd is ignored: user=nobody passwdhome=%s configured=%s target=%s", u.HomeDir, c.Exclude, target)
	}
}

func TestIndependentDelayOverflowBeforeStop(t *testing.T) {
	for _, value := range []string{"1e400", "-1e400"} {
		c := NewConfig()
		c.Delay = 77
		err := c.Apply(json.RawMessage(`{"enabled":false,"delay_seconds":` + value + `}`))
		if err == nil || c.Delay != 77 {
			t.Errorf("actual3.12 init raises OverflowError before stop; value=%s Go error=%v delay=%d", value, err, c.Delay)
		}
	}
}

func TestIndependentWorkerUnlinkNoParentReadPrecondition(t *testing.T) {
	f := startProtocol(t)
	root := filepath.Join(f.root, "m")
	locked := filepath.Join(root, "no-read")
	if err := os.MkdirAll(locked, 0700); err != nil {
		t.Fatal(err)
	}
	a, b, keep := filepath.Join(root, "source.mkv"), filepath.Join(locked, "selected.mkv"), filepath.Join(f.root, "retained.mkv")
	if err := os.WriteFile(a, []byte("owned-content"), 0600); err != nil {
		t.Fatal(err)
	}
	for _, p := range []string{b, keep} {
		if err := os.Link(a, p); err != nil {
			t.Fatal(err)
		}
	}
	f.call("init", map[string]any{"enabled": true, "monitor_dirs": root, "delayed_deletion": false})
	if err := os.Chmod(locked, 0300); err != nil {
		t.Fatal(err)
	}
	defer os.Chmod(locked, 0700)
	if _, err := os.ReadDir(locked); err == nil {
		t.Skip("requires nonroot directory-read permission enforcement")
	}
	if err := os.Remove(a); err != nil {
		t.Fatal(err)
	}
	f.mu.Lock()
	before := len(f.calls)
	f.mu.Unlock()
	f.call("test_event", map[string]any{"Kind": "deleted", "Path": a, "Mode": "hardlink", "At": 1760000001})
	if _, err := os.Lstat(b); !os.IsNotExist(err) {
		t.Fatal("source unlink only needs parent write/search", err)
	}
	if got, err := os.ReadFile(keep); err != nil || string(got) != "owned-content" {
		t.Fatal("retained same-inode content changed", string(got), err)
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	for _, c := range f.calls[before:] {
		if c.Method == "storage.files.list" && c.Path == locked {
			t.Fatal("unlink introduced parent list precondition", c)
		}
	}
}

func TestIndependentDirectoryListLogUsesPythonRepr(t *testing.T) {
	raw, err := os.ReadFile("/Users/accidia/projects/light-media-plugins/work/sites-review-20261105/removelink-family-review/current57/log-repr-source-oracle.json")
	if err != nil {
		t.Fatal(err)
	}
	var suite struct {
		Cases []struct {
			Input    oracleCase
			Expected struct {
				Logs [][2]string `json:"logs"`
			}
		} `json:"cases"`
	}
	if err := json.Unmarshal(raw, &suite); err != nil {
		t.Fatal(err)
	}
	if len(suite.Cases) != 3 {
		t.Fatal("wrong source case count")
	}
	for _, row := range suite.Cases {
		t.Run(row.Input.Name, func(t *testing.T) {
			got := runSourceLogOracle(t, row.Input).(map[string]any)["logs"]
			a, _ := json.Marshal(row.Expected.Logs)
			b, _ := json.Marshal(got)
			if string(a) != string(b) {
				t.Fatalf("actual3.12 source logs %s; current Go %s", a, b)
			}
		})
	}
}

func TestIndependentOverflowKeepsEarlierCustomExtensionAssignment(t *testing.T) {
	raw, err := os.ReadFile("/Users/accidia/projects/light-media-plugins/work/sites-review-20261105/removelink-family-review/current57/partial-config-source-oracle.json")
	if err != nil {
		t.Fatal(err)
	}
	var suite struct {
		Cases []struct {
			Name, Custom, RawDelay string
			Parsed                 []string `json:"parsed_extensions"`
			Delay                  int
		} `json:"cases"`
	}
	// Preserve the source fixture's exact raw JSON delay spelling.
	var data map[string]json.RawMessage
	if err = json.Unmarshal(raw, &data); err != nil {
		t.Fatal(err)
	}
	var rows []struct {
		Name     string   `json:"name"`
		Custom   string   `json:"custom"`
		RawDelay string   `json:"raw_delay_json"`
		Parsed   []string `json:"parsed_extensions"`
		Delay    int      `json:"delay"`
	}
	if err = json.Unmarshal(data["cases"], &rows); err != nil {
		t.Fatal(err)
	}
	_ = suite
	for _, r := range rows {
		t.Run(r.Name, func(t *testing.T) {
			c := NewConfig()
			c.Delay = 77
			c.Extensions = []string{".old"}
			custom, _ := json.Marshal(r.Custom)
			err := c.Apply(json.RawMessage(`{"enabled":false,"custom_scrap_extensions":` + string(custom) + `,"delay_seconds":` + r.RawDelay + `}`))
			got, _ := json.Marshal(c.Extensions)
			want, _ := json.Marshal(r.Parsed)
			if err == nil || c.Delay != r.Delay || string(got) != string(want) {
				t.Fatalf("source partial assignment: extensions=%s delay=%d err=%v, expected extensions=%s delay=%d", got, c.Delay, err, want, r.Delay)
			}
		})
	}
}
