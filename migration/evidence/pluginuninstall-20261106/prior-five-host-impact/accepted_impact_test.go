package app

// Bounded actual App/SQLite + real accepted Go worker coverage. Only synthetic
// disabled configs, owned namespaces and loopback artifact repositories. No
// cmd/server or browser/NAS/daemon acceptance is claimed by this overlay.
import (
	"context"
	"encoding/json"
	"fmt"
	"light-media/internal/plugins"
	"light-media/internal/plugins/artifacts"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"slices"
	"sort"
	"testing"
	"time"
)

var impactIDs = []string{"CategoryEditor", "TorrentTransfer", "TorrentTransfermusic", "SiteStatistic", "MPServerStatus"}
var impactPage = map[string]bool{"CategoryEditor": false, "TorrentTransfer": false, "TorrentTransfermusic": false, "SiteStatistic": true, "MPServerStatus": true}
var impactOrder = map[string]int{"CategoryEditor": 5, "TorrentTransfer": 18, "TorrentTransfermusic": 18, "SiteStatistic": 1, "MPServerStatus": 99}
var impactVersion = map[string]string{"CategoryEditor": "1.3", "TorrentTransfer": "1.10.3", "TorrentTransfermusic": "owned-music", "SiteStatistic": "1.9.7", "MPServerStatus": "1.4"}

func impactConfigs() map[string]json.RawMessage {
	return map[string]json.RawMessage{
		"CategoryEditor":       json.RawMessage(`{"enabled":false,"owned_marker":"category"}`),
		"TorrentTransfer":      json.RawMessage(`{"enabled":false,"onlyonce":false,"owned_marker":"transfer"}`),
		"TorrentTransfermusic": json.RawMessage(`{"enabled":false,"onlyonce":false,"owned_marker":"music"}`),
		"SiteStatistic":        json.RawMessage(`{"enabled":false,"onlyonce":false,"dashboard_type":"today","notify_type":"","owned_marker":"site"}`),
		"MPServerStatus":       json.RawMessage(`{"enable":false,"owned_marker":"monitor"}`),
	}
}
func impactOpen(t *testing.T, dir string) *App {
	t.Helper()
	none := []string{}
	a, e := New(Options{DataDir: dir, PluginMarketsOverride: &none})
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { _ = a.Close() })
	settings := a.Settings()
	no, noURL := false, ""
	settings.PluginStatisticShare = &no
	settings.PluginServerURL = &noURL
	settings.PluginMarkets = []string{}
	if e = a.saveSettings(context.Background(), settings); e != nil {
		t.Fatal(e)
	}
	return a
}
func impactObserve(t *testing.T, a *App, label string) {
	t.Helper()
	ctx := context.Background()
	cards, e := a.originalLocalPluginCards(ctx, false)
	if e != nil {
		t.Fatal(e)
	}
	class, running := []string{}, []string{}
	a.pluginOriginalRunningMu.Lock()
	class = slices.Clone(a.pluginOriginalClassOrder)
	running = slices.Clone(a.pluginOriginalRunningOrder)
	a.pluginOriginalRunningMu.Unlock()
	ids, e := a.originalInstalledPluginIDs(ctx)
	if e != nil {
		t.Fatal(e)
	}
	raw, _ := json.Marshal(map[string]any{"phase": label, "classes": class, "running": running, "source_installed": ids, "cards": cards})
	t.Logf("IMPACT %s", raw)
}
func impactClients(a *App) []*plugins.Client {
	out := []*plugins.Client{}
	for _, p := range a.originalLoadedPluginSnapshot() {
		p.sessionMu.Lock()
		if p.session != nil {
			out = append(out, p.session)
		}
		p.sessionMu.Unlock()
	}
	return out
}
func impactJoined(t *testing.T, clients []*plugins.Client) {
	t.Helper()
	for _, c := range clients {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		e := c.Stop(ctx)
		cancel()
		if e != nil {
			t.Fatal("actual SDK process exit/join", e)
		}
	}
}
func impactSave(t *testing.T, a *App, id string, cfg json.RawMessage) {
	t.Helper()
	in, e := a.pluginStore.Installation(context.Background(), id)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = a.pluginStore.saveOriginalPluginConfiguration(context.Background(), in, cfg); e != nil {
		t.Fatal(e)
	}
	a.invalidateOriginalBaseConfig(id)
}
func impactConfigKV(t *testing.T, a *App) {
	t.Helper()
	for id, want := range impactConfigs() {
		cfg, e := a.originalManagerConfiguration(context.Background(), id)
		if e != nil || !originalBaseJSONEqual(cfg, want) {
			t.Fatal("disabled configuration changed", id, string(cfg), string(want), e)
		}
		key := "owned-impact"
		data, e := a.pluginStore.originalBaseGetData(context.Background(), id, &key)
		if e != nil || string(data) != fmt.Sprintf(`{"instance":%q}`, id) {
			t.Fatal("namespace KV changed", id, string(data), e)
		}
	}
}
func impactStateAndPage(t *testing.T, a *App) {
	t.Helper()
	ctx := context.Background()
	cards, e := a.originalLocalPluginCards(ctx, false)
	if e != nil || len(cards) != 5 {
		t.Fatal("five imported classes", len(cards), e)
	}
	var sources []artifacts.Discovery
	for _, c := range cards {
		if c.HasPage != impactPage[c.InstanceID] || c.State || c.PluginOrder != impactOrder[c.InstanceID] || !c.Installed {
			t.Fatal("source metadata projection", c.InstanceID, c.HasPage, c.State, c.PluginOrder, c.Installed)
		}
		version, present, e := a.originalLocalPluginVersion(ctx, c.InstanceID)
		if e != nil || !present || version != impactVersion[c.InstanceID] {
			t.Fatal("class version", c.InstanceID, version, present, e)
		}
		p, ok := a.pluginRunningInstances.Load(c.InstanceID)
		if !ok {
			t.Fatal("missing actual running object", c.InstanceID)
		}
		object := p.(*originalPluginInstance)
		if slices.Contains(object.manifest.Capabilities, plugins.PluginManagerControlCapability) {
			t.Fatal("accepted family unexpectedly enables pre-import control gate", c.InstanceID)
		}
		state, e := object.getState(ctx)
		if e != nil || state {
			t.Fatal("disabled source state", c.InstanceID, state, e)
		}
		// No MPS dashboard: it probes even when disabled. Its disabled page is pure.
		page, e := a.originalExternalViewHTTP(ctx, object, "page", "", nil)
		raw, _ := json.Marshal(page)
		if e != nil {
			t.Fatal("actual worker page", c.InstanceID, e)
		}
		switch c.InstanceID {
		case "CategoryEditor", "TorrentTransfer", "TorrentTransfermusic":
			var v struct {
				Page []json.RawMessage `json:"page"`
			}
			if json.Unmarshal(raw, &v) != nil || len(v.Page) != 0 {
				t.Fatal("source pass page changed", c.InstanceID, string(raw))
			}
		case "SiteStatistic":
			if !containsImpact(raw, "暂无数据") {
				t.Fatal("actual source empty Site page missing", string(raw))
			}
		case "MPServerStatus":
			if !containsImpact(raw, "插件未启用") {
				t.Fatal("disabled MPS page must not probe upstream", string(raw))
			}
		}
		if _, e := a.originalExternalViewHTTP(ctx, object, "form", "", nil); e != nil {
			t.Fatal("ordinary actual form", c.InstanceID, e)
		}
		sources = append(sources, artifacts.Discovery{PluginID: c.InstanceID, CurrentVersion: "999", RepositoryURL: "https://example.invalid/owned-metadata-no-network", Current: artifacts.Compatibility{Manifest: c.Manifest}})
	}
	markets := a.originalMarketCards(cards, sources, map[string]bool{})
	if len(markets) != 5 {
		t.Fatal("five synthetic market declarations", len(markets))
	}
	for _, c := range markets {
		if c.HasPage != impactPage[c.InstanceID] {
			t.Fatal("source market page projection", c.InstanceID, c.HasPage)
		}
	}
	impactConfigKV(t, a)
}
func containsImpact(raw []byte, s string) bool {
	var x any
	if json.Unmarshal(raw, &x) != nil {
		return false
	}
	var walk func(any) bool
	walk = func(v any) bool {
		switch y := v.(type) {
		case string:
			return y == s
		case []any:
			for _, c := range y {
				if walk(c) {
					return true
				}
			}
		case map[string]any:
			for _, c := range y {
				if walk(c) {
					return true
				}
			}
		}
		return false
	}
	return walk(x)
}
func impactPhysicalOrder(t *testing.T, a *App, wanted []string) []string {
	t.Helper()
	d, e := os.Open(a.pluginPackageRoot())
	if e != nil {
		t.Fatal(e)
	}
	entries, e := d.ReadDir(-1)
	d.Close()
	if e != nil {
		t.Fatal(e)
	}
	out := []string{}
	for _, e := range entries {
		if e.IsDir() && slices.Contains(wanted, e.Name()) {
			out = append(out, e.Name())
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return impactOrder[out[i]] < impactOrder[out[j]] })
	return out
}
func TestIndependentPUIHost19AcceptedConsumers(t *testing.T) {
	a := impactOpen(t, t.TempDir())
	cookie := setupTestAdmin(t, a)
	ctx := context.Background()
	for _, variable := range []string{"IMPACT_CATEGORY_BINARY", "IMPACT_TT_BINARY", "IMPACT_SITE_BINARY", "IMPACT_MPS_BINARY"} {
		p := os.Getenv(variable)
		if p == "" {
			t.Fatal("required actual worker", variable)
		}
		m := installOwnedResourceProcessWorker(t, a, cookie, p)
		if m.PluginID == "PluginUnInstall" || slices.Contains(m.Capabilities, plugins.PluginManagerControlCapability) {
			t.Fatal("test contains a manager-control consumer")
		}
	}
	clone := callTest(t, a.Handler(), http.MethodPost, "/api/plugins/TorrentTransfer/clone", `{"suffix":"music","name":"Owned music","version":"owned-music"}`, cookie, "")
	assertOriginalRegistrySuccess(t, clone.Code, clone.Body.Bytes())
	a.wg.Wait()
	for id, cfg := range impactConfigs() {
		r := callTest(t, a.Handler(), http.MethodPut, "/api/plugins/"+id, string(cfg), cookie, "")
		assertOriginalRegistrySuccess(t, r.Code, r.Body.Bytes())
		if e := a.pluginStore.originalBaseSaveData(ctx, id, "owned-impact", json.RawMessage(fmt.Sprintf(`{"instance":%q}`, id))); e != nil {
			t.Fatal(e)
		}
	}
	t.Run("actual-five-source-pages-forms-version-disabled", func(t *testing.T) {
		impactStateAndPage(t, a)
		response := callTest(t, a.Handler(), "GET", "/api/plugins/releases/TorrentTransfermusic?repo_url="+url.QueryEscape("local://TorrentTransfermusic?path=/unused"), "", cookie, "")
		var release struct {
			Data struct {
				Version string `json:"current_version"`
			} `json:"data"`
		}
		if response.Code != 200 || json.Unmarshal(response.Body.Bytes(), &release) != nil || release.Data.Version != "owned-music" {
			t.Fatal("ordinary local-release imported clone version", response.Code, response.Body.String())
		}
		impactObserve(t, a, "initial-five")
	})
	t.Run("physical-tie-order-and-installed-order-independent", func(t *testing.T) {
		want := impactPhysicalOrder(t, a, impactIDs)
		var traces [][]string
		for _, ids := range [][]string{slices.Clone(impactIDs), {"MPServerStatus", "TorrentTransfermusic", "TorrentTransfer", "CategoryEditor", "SiteStatistic"}} {
			raw, _ := json.Marshal(ids)
			if _, e := a.pluginStore.sourceSetOriginalInstalled(ctx, raw); e != nil {
				t.Fatal(e)
			}
			clients := impactClients(a)
			if e := a.initializeOriginalPlugins(ctx); e != nil {
				t.Fatal(e)
			}
			a.wg.Wait()
			impactJoined(t, clients)
			a.pluginOriginalRunningMu.Lock()
			got := slices.Clone(a.pluginOriginalRunningOrder)
			classes := slices.Clone(a.pluginOriginalClassOrder)
			a.pluginOriginalRunningMu.Unlock()
			if !reflect.DeepEqual(got, want) || !reflect.DeepEqual(classes, want) {
				t.Fatal("source physical directory then stable class order", want, got, classes)
			}
			traces = append(traces, got)
			impactConfigKV(t, a)
		}
		if !reflect.DeepEqual(traces[0], traces[1]) {
			t.Fatal("membership reorders equal18 TT/music", traces)
		}
		impactObserve(t, a, "physical-tie-order")
	})
	t.Run("source-cache-before-SQL-fault-metadata-and-version", func(t *testing.T) {
		// Actual owned SQLite fault. Source SystemConfigOper updates its cache first;
		// SQL installation flags stay old while source local/version sees the cache.
		if _, e := a.Store.DB.ExecContext(ctx, `CREATE TRIGGER owned_impact_fail BEFORE UPDATE ON records WHEN NEW.kind='plugin-original-installed-order-v1' BEGIN SELECT RAISE(FAIL,'owned impact installed write failure'); END`); e != nil {
			t.Fatal(e)
		}
		ids := []string{"CategoryEditor", "TorrentTransfer", "SiteStatistic", "MPServerStatus"}
		raw, _ := json.Marshal(ids)
		if _, e := a.pluginStore.sourceSetOriginalInstalled(ctx, raw); e == nil {
			t.Fatal("actual SQLite failure not reached")
		}
		if _, e := a.Store.DB.ExecContext(ctx, `DROP TRIGGER owned_impact_fail`); e != nil {
			t.Fatal(e)
		}
		in, e := a.pluginStore.Installation(ctx, "TorrentTransfermusic")
		if e != nil || !in.Installed {
			t.Fatal("SQL projection unexpectedly changed", e, in.Installed)
		}
		cards, e := a.originalLocalPluginCards(ctx, false)
		if e != nil {
			t.Fatal(e)
		}
		seen := false
		for _, c := range cards {
			if c.InstanceID == "TorrentTransfermusic" {
				seen = true
				if c.Installed {
					t.Fatal("local card used old SQL flag instead of source cache")
				}
			}
		}
		if !seen {
			t.Fatal("uninstalled imported music class disappeared")
		}
		if _, present, e := a.originalLocalPluginVersion(ctx, "TorrentTransfermusic"); e != nil || present {
			t.Fatal("source version ignored cached membership", present, e)
		}
		response := callTest(t, a.Handler(), "GET", "/api/plugins/history/TorrentTransfermusic", "", cookie, "")
		if response.Code != 404 {
			t.Fatal("cached uninstalled history must reject before any repository call", response.Code, response.Body.String())
		}
		clients := impactClients(a)
		if e := a.initializeOriginalPlugins(ctx); e != nil {
			t.Fatal(e)
		}
		a.wg.Wait()
		impactJoined(t, clients)
		if _, ok := a.pluginRunningInstances.Load("TorrentTransfermusic"); ok {
			t.Fatal("source cached unselected music started")
		}
		if _, ok := a.pluginOriginalClasses.Load("TorrentTransfermusic"); ok {
			t.Fatal("source cached unselected music class survived stop-all")
		}
		impactObserve(t, a, "cache-ahead-SQL-four-running")
	})
	dir := a.Dir
	clients := impactClients(a)
	if e := a.Close(); e != nil {
		t.Fatal(e)
	}
	impactJoined(t, clients)
	cold := impactOpen(t, dir)
	t.Run("true-cold-reloads-real-SQL-five-no-replay", func(t *testing.T) {
		if e := cold.initializeOriginalPlugins(ctx); e != nil {
			t.Fatal(e)
		}
		cold.wg.Wait()
		impactStateAndPage(t, cold)
		impactObserve(t, cold, "true-cold-five-from-unchanged-SQL")
	})
	t.Run("failed-disabled-music-class-cleared-on-next-init", func(t *testing.T) {
		impactSave(t, cold, "TorrentTransfermusic", json.RawMessage(`{"enabled":false,"onlyonce":false,"add_torrent_tags":1,"owned_marker":"source-strip-type-error"}`))
		clients := impactClients(cold)
		if e := cold.initializeOriginalPlugins(ctx); e != nil {
			t.Fatal(e)
		}
		cold.wg.Wait()
		impactJoined(t, clients)
		if _, ok := cold.pluginOriginalClasses.Load("TorrentTransfermusic"); !ok {
			t.Fatal("source failed init must retain imported music class")
		}
		if _, ok := cold.pluginRunningInstances.Load("TorrentTransfermusic"); ok {
			t.Fatal("disabled tags1 failed init unexpectedly published runtime")
		}
		impactObserve(t, cold, "disabled-source-strip-failure-class-without-runtime")
		if _, e := cold.pluginStore.sourceSetOriginalInstalled(ctx, json.RawMessage(`["CategoryEditor","TorrentTransfer","SiteStatistic","MPServerStatus"]`)); e != nil {
			t.Fatal(e)
		}
		clients = impactClients(cold)
		if e := cold.initializeOriginalPlugins(ctx); e != nil {
			t.Fatal(e)
		}
		cold.wg.Wait()
		impactJoined(t, clients)
		if _, ok := cold.pluginOriginalClasses.Load("TorrentTransfermusic"); ok {
			t.Fatal("stop-all retained failed now-unselected music class")
		}
		impactObserve(t, cold, "failed-music-class-cleared-by-stop-all")
	})
	t.Run("empty-membership-stops-without-reading-code-dir", func(t *testing.T) {
		if _, e := cold.pluginStore.sourceSetOriginalInstalled(ctx, json.RawMessage(`[]`)); e != nil {
			t.Fatal(e)
		}
		clients := impactClients(cold)
		path := cold.pluginPackageRoot()
		if e := os.Chmod(path, 0000); e != nil {
			t.Fatal(e)
		}
		e := cold.initializeOriginalPlugins(ctx)
		if restore := os.Chmod(path, 0700); restore != nil {
			t.Fatal(restore)
		}
		if e != nil {
			t.Fatal("empty membership scanned code directory", e)
		}
		cold.wg.Wait()
		impactJoined(t, clients)
		if len(cold.originalLoadedPluginSnapshot()) != 0 {
			t.Fatal("empty membership retained runtime")
		}
		cold.pluginOriginalRunningMu.Lock()
		n := len(cold.pluginOriginalClassOrder)
		cold.pluginOriginalRunningMu.Unlock()
		if n != 0 {
			t.Fatal("empty membership retained classes")
		}
		for id := range impactConfigs() {
			key := "owned-impact"
			v, e := cold.pluginStore.originalBaseGetData(ctx, id, &key)
			if e != nil || string(v) != fmt.Sprintf(`{"instance":%q}`, id) {
				t.Fatal("stop-only empty membership purged KV", id, string(v), e)
			}
			if _, e = os.Stat(filepath.Join(path, id)); e != nil {
				t.Fatal("empty membership purged code", id, e)
			}
		}
		impactObserve(t, cold, "empty-no-code-scan")
	})
	if e := cold.Close(); e != nil {
		t.Fatal(e)
	}
}
