package removelink

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	plugins "github.com/landuo/light-media-plugins/internal/sdk"
)

type idleObserver struct {
	events chan fileEvent
	once   sync.Once
}

func (w *idleObserver) Events() <-chan fileEvent { return w.events }
func (w *idleObserver) Close()                   { w.once.Do(func() { close(w.events) }) }
func protocolManifest() plugins.Manifest {
	m := Manifest()
	m.PluginID = "RemoveLinkProtocolFixture"
	m.Entry = "remove-link-protocol-fixture"
	m.Methods = append(m.Methods, "test_event", "test_snapshot", "test_tick")
	return m
}
func TestProtocolFixtureWorker(t *testing.T) {
	if !strings.Contains(strings.Join(os.Args, " "), "removelink-sdk-fixture") {
		return
	}
	p := NewPlugin()
	native := strings.Contains(strings.Join(os.Args, " "), "--native-observer")
	if !native {
		p.newObserver = func(Watch) (observer, error) { return &idleObserver{events: make(chan fileEvent)}, nil }
	}
	var clockMu sync.Mutex
	now := time.Unix(1760000000, 0)
	if !native {
		p.machine.Now = func() time.Time { clockMu.Lock(); defer clockMu.Unlock(); return now }
	}
	handle := func(ctx context.Context, m string, raw json.RawMessage, h plugins.HostCaller) (json.RawMessage, error) {
		switch m {
		case "test_event":
			var in struct {
				Kind, Path, Dest, Mode string
				Directory              bool
				At                     int64
			}
			if e := json.Unmarshal(raw, &in); e != nil {
				return nil, e
			}
			clockMu.Lock()
			now = time.Unix(in.At, 0)
			clockMu.Unlock()
			return nil, p.run(ctx, h, func(_ *sdkOps) error {
				switch in.Kind {
				case "created":
					return p.machine.Created(in.Path, in.Directory)
				case "deleted":
					return p.machine.Deleted(in.Path, in.Mode, in.Directory)
				case "moved":
					return p.machine.Moved(in.Path, in.Dest, in.Mode, in.Directory)
				}
				return errors.New("invalid fixture event")
			})
		case "test_tick":
			var at int64
			_ = json.Unmarshal(raw, &at)
			clockMu.Lock()
			now = time.Unix(at, 0)
			clockMu.Unlock()
			return nil, p.run(ctx, h, func(_ *sdkOps) error { p.machine.Tick(); return nil })
		case "test_snapshot", "close":
			p.machine.mu.Lock()
			defer p.machine.mu.Unlock()
			p.mu.Lock()
			passes := len(p.passes)
			p.mu.Unlock()
			return json.Marshal(map[string]any{"state": p.machine.State, "queue": p.machine.Queue, "passes": passes, "enabled": p.machine.currentConfig().Enabled})
		}
		return p.Handle(ctx, m, raw, h)
	}
	if e := plugins.ServeConcurrent(context.Background(), os.Stdin, os.Stdout, protocolManifest(), handle); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(2)
	}
	os.Exit(0)
}

type protocolPhase struct {
	Method string
	Calls  int
	Error  string
	Done   bool
}
type protocolFixture struct {
	t                *testing.T
	ctx              context.Context
	cancel           context.CancelFunc
	client           *plugins.Client
	id               plugins.Identity
	root             string
	mu               sync.Mutex
	phases           []*protocolPhase
	trace            []map[string]any
	reject           string
	rejected         bool
	block            string
	blockAfter       bool
	declineDelete    string
	historyReads     []plugins.TransferHistoryRequestV1
	entered, release chan struct{}
	canceled         chan struct{}
	blockOnce        sync.Once
}

func startProtocol(t *testing.T) *protocolFixture {
	return startProtocolMode(t, false)
}
func startProtocolMode(t *testing.T, native bool) *protocolFixture {
	return startProtocolIdentity(t, native, "OwnedRemoveLink", 1)
}
func startProtocolIdentity(t *testing.T, native bool, instance string, generation int64) *protocolFixture {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	exe, e := os.Executable()
	if e != nil {
		t.Fatal(e)
	}
	m := protocolManifest()
	id := plugins.Identity{PluginID: m.PluginID, InstanceID: instance, Version: m.Version}
	args := []string{"-test.run=^TestProtocolFixtureWorker$", "--", "removelink-sdk-fixture"}
	if native {
		args = append(args, "--native-observer")
	}
	c, e := (plugins.Runner{Timeout: 5 * time.Second, ConcurrentCalls: true, RequireConcurrent: true}).Start(ctx, plugins.Command{Path: exe, Args: args}, m, plugins.SessionBinding{Identity: id, Generation: generation})
	if e != nil {
		cancel()
		t.Fatal(e)
	}
	f := &protocolFixture{t: t, ctx: ctx, cancel: cancel, client: c, id: id, root: t.TempDir(), trace: []map[string]any{}, entered: make(chan struct{}), release: make(chan struct{}), canceled: make(chan struct{})}
	if e := os.WriteFile(filepath.Join(f.root, ".fixture-owner"), []byte("owned synthetic"), 0600); e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() {
		stop, x := context.WithTimeout(context.Background(), 4*time.Second)
		defer x()
		_ = c.Stop(stop)
		cancel()
	})
	return f
}
func (f *protocolFixture) phase(method string) plugins.HostHandler {
	p := &protocolPhase{Method: method}
	f.mu.Lock()
	f.phases = append(f.phases, p)
	f.mu.Unlock()
	return func(ctx context.Context, id plugins.Identity, m string, r json.RawMessage) (json.RawMessage, error) {
		if id != f.id || ctx.Err() != nil {
			return nil, errors.New("fixture scope revoked")
		}
		f.mu.Lock()
		p.Calls++
		reject := f.reject == m && !f.rejected
		if reject {
			f.rejected = true
		}
		block := f.block == m
		after := f.blockAfter
		f.mu.Unlock()
		if reject {
			return nil, errors.New("synthetic transient authority rejection")
		}
		wait := func() {
			f.blockOnce.Do(func() {
				close(f.entered)
				select {
				case <-f.release:
				case <-ctx.Done():
					close(f.canceled)
				}
			})
		}
		if block && !after {
			wait()
			if e := ctx.Err(); e != nil {
				return nil, e
			}
		}
		out, e := f.host(ctx, m, r)
		if block && after {
			wait()
			if x := ctx.Err(); x != nil {
				return nil, x
			}
		}
		return out, e
	}
}
func (f *protocolFixture) host(ctx context.Context, m string, raw json.RawMessage) (json.RawMessage, error) {
	if m == plugins.BackgroundSubmitCapability || m == plugins.CleanupSubmitCapability {
		var in struct {
			Method  string
			Payload json.RawMessage
		}
		if e := json.Unmarshal(raw, &in); e != nil {
			return nil, e
		}
		h := f.phase(in.Method)
		var pending *plugins.PendingCall
		var e error
		if m == plugins.CleanupSubmitCapability {
			pending, e = f.client.StartCleanupContinuationWithAdmission(ctx, in.Method, in.Payload, h)
		} else {
			pending, e = f.client.StartCallWithAdmission(ctx, f.ctx, in.Method, in.Payload, h, plugins.CallOptions{CallerDeadlineOnly: true})
		}
		if e != nil {
			return nil, e
		}
		go func() { _, _ = pending.Wait() }()
		return json.RawMessage(`{"accepted":true}`), nil
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	if m == plugins.StorageExistsCapability || m == plugins.StorageListCapability || m == plugins.StorageDeleteCapability {
		var in plugins.StorageFilesRequest
		if e := json.Unmarshal(raw, &in); e != nil || in.FileItem == nil {
			return nil, errors.New("fixture invalid fileitem")
		}
		var item Item
		b, _ := json.Marshal(in.FileItem)
		_ = json.Unmarshal(b, &item)
		rel, e := filepath.Rel(f.root, item.Path)
		if e != nil || rel == ".." || strings.HasPrefix(rel, "../") || item.Storage != "local" {
			return nil, errors.New("fixture path denied")
		}
		switch m {
		case plugins.StorageExistsCapability:
			_, e := os.Stat(item.Path)
			return json.Marshal(e == nil)
		case plugins.StorageListCapability:
			file, e := os.Open(item.Path)
			if e != nil {
				return nil, e
			}
			rows, e := file.Readdir(-1)
			file.Close()
			if e != nil {
				return nil, e
			}
			out := []map[string]any{}
			for _, x := range rows {
				kind := "file"
				if x.IsDir() {
					kind = "dir"
				}
				out = append(out, map[string]any{"storage": "local", "path": filepath.Join(item.Path, x.Name()), "type": kind, "name": x.Name(), "extension": strings.TrimPrefix(filepath.Ext(x.Name()), ".")})
			}
			return json.Marshal(out)
		case plugins.StorageDeleteCapability:
			if item.Path == f.declineDelete {
				f.trace = append(f.trace, map[string]any{"op": "delete_declined", "path": item.Path})
				return json.RawMessage(`false`), nil
			}
			e := os.RemoveAll(item.Path)
			if e != nil {
				return nil, e
			}
			f.trace = append(f.trace, map[string]any{"op": "delete", "path": item.Path})
			return json.RawMessage(`true`), nil
		}
	}
	if m == plugins.TransferHistoryReadCapability {
		var r plugins.TransferHistoryRequestV1
		_ = json.Unmarshal(raw, &r)
		f.historyReads = append(f.historyReads, r)
		path := r.Source
		if path == "" {
			path = r.Target
		}
		return json.Marshal(plugins.TransferHistoryResultV1{SchemaVersion: 1, Item: &plugins.TransferHistoryRowV1{ID: path}})
	}
	if m == plugins.TransferHistoryDeleteCapability {
		var r plugins.TransferHistoryDeleteV1
		_ = json.Unmarshal(raw, &r)
		f.trace = append(f.trace, map[string]any{"op": "history", "path": r.ID})
		return json.Marshal(plugins.HostMutationV1{SchemaVersion: 1, Changed: true})
	}
	if m == plugins.EventSendCapability {
		var r plugins.EventSendRequest
		_ = json.Unmarshal(raw, &r)
		var data map[string]any
		_ = json.Unmarshal(r.Data, &data)
		f.trace = append(f.trace, map[string]any{"op": "event", "type": r.Type, "path": data["src"]})
		return json.RawMessage(`null`), nil
	}
	if m == plugins.PostMessageCapability {
		var x map[string]any
		_ = json.Unmarshal(raw, &x)
		x["op"] = "notify"
		f.trace = append(f.trace, x)
		return json.RawMessage(`{"queued":0,"attempted":0,"failed":0,"errors":[]}`), nil
	}
	if m == plugins.SettingsReadCapability {
		return json.RawMessage(`{"schema_version":1,"key":"RMT_MEDIAEXT","value":[".mkv",".mp4"],"changed":null}`), nil
	}
	if m == plugins.SystemMessagePutCapability || m == plugins.LogWriteCapability {
		return json.RawMessage(`null`), nil
	}
	return nil, fmt.Errorf("unexpected fixture capability %s", m)
}
func (f *protocolFixture) call(method string, value any) plugins.RunResult {
	f.t.Helper()
	raw, _ := json.Marshal(value)
	out, e := f.client.CallWithOptions(f.ctx, method, raw, f.phase("owner:"+method), plugins.CallOptions{CallerDeadlineOnly: true})
	if e != nil {
		f.t.Fatal(method, e)
	}
	return out
}
func (f *protocolFixture) init(delayed bool) {
	f.call("init", map[string]any{"enabled": true, "monitor_dirs": filepath.Join(f.root, "m"), "delayed_deletion": delayed, "delay_seconds": 86400, "delete_history": true, "delete_torrents": true, "notify": true})
}
func (f *protocolFixture) links(n int) (string, []string) {
	f.t.Helper()
	dir := filepath.Join(f.root, "m")
	if e := os.Mkdir(dir, 0700); e != nil {
		f.t.Fatal(e)
	}
	a := filepath.Join(dir, "source.mkv")
	if e := os.WriteFile(a, []byte("owned synthetic media"), 0600); e != nil {
		f.t.Fatal(e)
	}
	links := []string{}
	for i := 0; i < n; i++ {
		p := filepath.Join(dir, fmt.Sprintf("linked-%03d.mkv", i))
		if e := os.Link(a, p); e != nil {
			f.t.Fatal(e)
		}
		links = append(links, p)
	}
	return a, links
}
func (f *protocolFixture) budget() {
	f.t.Helper()
	f.mu.Lock()
	defer f.mu.Unlock()
	max, total, children := 0, 0, 0
	for _, p := range f.phases {
		if p.Calls > max {
			max = p.Calls
		}
		total += p.Calls
		if p.Method == "cleanup_continue" {
			children++
		}
		if p.Calls > phaseHostCalls+1 {
			f.t.Fatalf("phase exceeded budget: %+v", p)
		}
	}
	f.t.Logf("actual SDK: phases=%d cleanup_phases=%d total_RPC=%d max_RPC_per_phase=%d hard_default=64", len(f.phases), children, total, max)
}
func TestActualWorkerMoreThan64LinksOwnerWaitsThroughLastEffect(t *testing.T) {
	f := startProtocol(t)
	a, links := f.links(100)
	f.init(false)
	if e := os.Remove(a); e != nil {
		t.Fatal(e)
	}
	f.call("test_event", map[string]any{"kind": "deleted", "path": a, "at": 1760000100})
	for _, path := range links {
		if _, e := os.Stat(path); !errors.Is(e, os.ErrNotExist) {
			t.Fatal("owner returned before linked delete", path, e)
		}
	}
	f.mu.Lock()
	deletes, events, histories, notices := 0, 0, 0, 0
	for _, x := range f.trace {
		switch x["op"] {
		case "delete":
			deletes++
		case "event":
			events++
		case "history":
			histories++
		case "notify":
			if x["mtype"] != "站点" {
				t.Fatal("source enum wire value changed", x["mtype"])
			}
			notices++
		}
	}
	f.mu.Unlock()
	if deletes != 100 || events != 101 || histories != 101 || notices != 1 {
		t.Fatal(deletes, events, histories, notices)
	}
	f.budget()
}
func TestActualWorkerLargeScrapeDirectoryAndFilteredCandidates(t *testing.T) {
	f := startProtocol(t)
	a, _ := f.links(0)
	for i := 0; i < 150; i++ {
		if e := os.WriteFile(filepath.Join(filepath.Dir(a), fmt.Sprintf("source-%03d.nfo", i)), []byte("owned metadata"), 0600); e != nil {
			t.Fatal(e)
		}
	}
	f.call("init", map[string]any{"enabled": true, "monitor_dirs": filepath.Dir(a), "delayed_deletion": false, "delete_scrap_infos": true, "exclude_keywords": "skip"})
	for i := 0; i < 80; i++ {
		f.call("test_event", map[string]any{"kind": "created", "path": filepath.Join(filepath.Dir(a), fmt.Sprintf("skip-%d.tmp", i)), "at": 1760000010})
	}
	if e := os.Remove(a); e != nil {
		t.Fatal(e)
	}
	f.call("test_event", map[string]any{"kind": "deleted", "path": a, "at": 1760000100})
	if _, e := os.Stat(filepath.Dir(a)); !errors.Is(e, os.ErrNotExist) {
		t.Fatal("large scrape-only directory remains", e)
	}
	f.budget()
}
func TestActualWorkerQueuedStopAndReloadFlushWithNewFlags(t *testing.T) {
	for _, reload := range []bool{false, true} {
		t.Run(fmt.Sprint(reload), func(t *testing.T) {
			f := startProtocol(t)
			a, links := f.links(90)
			f.init(true)
			if e := os.Remove(a); e != nil {
				t.Fatal(e)
			}
			f.call("test_event", map[string]any{"kind": "deleted", "path": a, "at": 1760000100})
			if reload {
				f.call("init", map[string]any{"enabled": false, "delete_history": false, "delete_torrents": false, "notify": false})
			} else {
				f.call("stop_service", nil)
			}
			for _, p := range links {
				if _, e := os.Stat(p); !errors.Is(e, os.ErrNotExist) {
					t.Fatal("not flushed before owner", p, e)
				}
			}
			if reload {
				f.mu.Lock()
				for _, x := range f.trace {
					if x["op"] == "history" || x["op"] == "event" || x["op"] == "notify" {
						t.Fatal("old flags used during reload flush", x)
					}
				}
				f.mu.Unlock()
			}
			f.budget()
		})
	}
}
func TestActualWorkerTransientAuthorityFailureStopsLaterEffects(t *testing.T) {
	f := startProtocol(t)
	a, links := f.links(100)
	f.init(false)
	_ = os.Remove(a)
	f.mu.Lock()
	f.reject = plugins.StorageDeleteCapability
	f.mu.Unlock()
	raw, _ := json.Marshal(map[string]any{"kind": "deleted", "path": a, "at": 1760000100})
	_, e := f.client.CallWithOptions(f.ctx, "test_event", raw, f.phase("owner:guard"), plugins.CallOptions{CallerDeadlineOnly: true})
	if e == nil {
		t.Fatal("guard refusal became success")
	}
	for _, p := range links {
		if _, e := os.Stat(p); e != nil {
			t.Fatal("later delete after restored guard", p, e)
		}
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	for _, x := range f.trace {
		if x["op"] == "delete" || x["op"] == "notify" {
			t.Fatal("later effect after guard failure", x)
		}
	}
}
func TestActualWorkerUnknownWriteCancellationRetainsFactNoReplay(t *testing.T) {
	f := startProtocol(t)
	a, links := f.links(100)
	f.init(false)
	_ = os.Remove(a)
	f.mu.Lock()
	f.block = plugins.StorageDeleteCapability
	f.blockAfter = true
	f.mu.Unlock()
	ctx, cancel := context.WithCancel(f.ctx)
	result := make(chan error, 1)
	raw, _ := json.Marshal(map[string]any{"kind": "deleted", "path": a, "at": 1760000100})
	go func() {
		_, e := f.client.CallWithOptions(ctx, "test_event", raw, f.phase("owner:unknown"), plugins.CallOptions{CallerDeadlineOnly: true})
		result <- e
	}()
	select {
	case <-f.entered:
	case <-f.ctx.Done():
		t.Fatal("write barrier not reached")
	}
	cancel()
	select {
	case <-f.canceled:
	case <-f.ctx.Done():
		t.Fatal("actual child host authority not canceled")
	}
	close(f.release)
	select {
	case e := <-result:
		if e == nil {
			t.Fatal("unknown write cancellation succeeded")
		}
	case <-f.ctx.Done():
		t.Fatal("cancel did not join")
	}
	// Snapshot is a separate actual invocation and waits for the source mutex.
	f.call("test_snapshot", nil)
	remaining := 0
	for _, p := range links {
		if _, e := os.Stat(p); e == nil {
			remaining++
		}
	}
	if remaining != 99 {
		t.Fatal("unknown write replayed or was rolled back", remaining)
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	writes := 0
	for _, x := range f.trace {
		if x["op"] == "delete" {
			writes++
		}
	}
	if writes != 1 {
		t.Fatal("selected write repeated", writes)
	}
}
func TestActualCleanupRootFlushesOver64LinksBeforeOwnerReturns(t *testing.T) {
	f := startProtocol(t)
	a, links := f.links(90)
	f.init(true)
	_ = os.Remove(a)
	f.call("test_event", map[string]any{"kind": "deleted", "path": a, "at": 1760000100})
	if e := f.client.BeginShutdown(f.ctx); e != nil {
		t.Fatal(e)
	}
	if _, e := f.client.CallCleanup(f.ctx, "stop_service", json.RawMessage(`{}`), f.phase("actual-cleanup-root")); e != nil {
		t.Fatal(e)
	}
	for _, p := range links {
		if _, e := os.Stat(p); !os.IsNotExist(e) {
			t.Fatal("root returned before delete", p, e)
		}
	}
	result, e := f.client.CallCleanup(f.ctx, "close", json.RawMessage(`{}`), f.phase("cleanup-snapshot"))
	if e != nil {
		t.Fatal(e)
	}
	var snapshot struct {
		Queue  []Task
		Passes int
	}
	_ = json.Unmarshal(result.Result, &snapshot)
	if len(snapshot.Queue) != 0 || snapshot.Passes != 0 {
		t.Fatal("cleanup source finally/queue not joined", string(result.Result))
	}
	f.budget()
	f.mu.Lock()
	defer f.mu.Unlock()
	counts := map[string]int{}
	max := 0
	total := 0
	for _, x := range f.trace {
		counts[fmt.Sprint(x["op"])]++
	}
	for _, phase := range f.phases {
		total += phase.Calls
		if phase.Calls > max {
			max = phase.Calls
		}
	}
	if counts["delete"] != 90 || counts["event"] != 91 || counts["history"] != 91 || counts["notify"] != 1 {
		t.Fatal("source side effects lost/replayed", counts)
	}
	t.Logf("actual cleanup root90links totalRPC=%d maxPhase=%d sourceEffects=%v", total, max, counts)
}

func TestActualCleanupEmptySourceStopNeedsNoBackgroundAdmission(t *testing.T) {
	f := startProtocol(t)
	_, _ = f.links(0)
	f.init(true)
	if e := f.client.BeginShutdown(f.ctx); e != nil {
		t.Fatal(e)
	}
	before := 0
	f.mu.Lock()
	before = len(f.phases)
	f.mu.Unlock()
	if _, e := f.client.CallCleanup(f.ctx, "stop_service", json.RawMessage(`{}`), f.phase("empty-cleanup-root")); e != nil {
		t.Fatal(e)
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	for _, phase := range f.phases[before:] {
		if phase.Method == "empty-cleanup-root" && phase.Calls > 3 {
			t.Fatal("empty source stop made more than its logger calls", phase.Calls)
		}
	}
}
