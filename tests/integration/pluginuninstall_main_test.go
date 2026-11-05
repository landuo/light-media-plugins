package integration

// Coordinator-run ordinary Main acceptance. Local tests below validate response
// interpretation only. No in-process App import, direct SQL, production paths,
// native business delegation or alternate uninstall executor is used.
import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestPluginUninstallHTTPOutcomeContracts(t *testing.T) {
	cases := []struct {
		name           string
		status         int
		body           string
		mutation, want bool
	}{
		{"saved", 200, `{"data":{"success":true}}`, true, true},
		{"install-false-is-not-200-success", 200, `{"data":{"success":false,"message":"acquire failed"}}`, true, false},
		{"missing-explicit-ack", 200, `{"data":{}}`, true, false},
		{"self-public-config-empty-is-valid-read", 200, `{"data":{}}`, false, true},
		{"permission-partial", 500, `{"error":{"code":"INTERNAL_ERROR"}}`, true, false},
		{"api-unknown", 404, `{"error":{"code":"NOT_FOUND"}}`, false, false},
		{"outer-false", 200, `{"success":false,"data":{"success":true}}`, true, false},
		{"cold-observation", 200, `{"installed":[],"classes":[],"running":[],"installed_order":[],"pid":123}`, false, true},
		{"invalid-json", 200, `not json`, false, false},
		{"empty-body", 200, ``, true, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.Method != "GET" || r.URL.Path != "/contract" {
					http.Error(w, "wrong fixture route", 400)
					return
				}
				w.WriteHeader(c.status)
				_, _ = w.Write([]byte(c.body))
			}))
			defer server.Close()
			resp, e := server.Client().Get(server.URL + "/contract")
			if e != nil {
				t.Fatal(e)
			}
			var buf bytes.Buffer
			_, e = buf.ReadFrom(resp.Body)
			resp.Body.Close()
			if e != nil {
				t.Fatal(e)
			}
			_, e = puiResponse(resp.StatusCode, buf.Bytes(), c.mutation)
			if (e == nil) != c.want {
				t.Fatal("response classification", e)
			}
		})
	}
}
func TestPluginUninstallSourceFormControls(t *testing.T) {
	// Expected controls and source defaults are transcribed from installed raw
	// lines90–183, not obtained from the new Go worker.
	raw := json.RawMessage(`{"render_mode":"vuetify","conf":[{"component":"VForm","content":[{"component":"VSwitch","props":{"model":"clear_config"}},{"component":"VSwitch","props":{"model":"clear_data"}},{"component":"VSelect","props":{"model":"plugin_ids","multiple":true,"chips":true,"items":[{"title":"插件彻底卸载 v2.2","value":"PluginUnInstall"}]}}]}],"model":{"plugin_ids":[],"clear_config":false,"clear_data":false}}`)
	model, ids := puiForm(t, raw)
	puiAssert(t, ids, []string{puiID}, "source self option")
	puiAssert(t, model, map[string]any{"plugin_ids": []any{}, "clear_config": false, "clear_data": false}, "source defaults")
}

func TestPluginUninstallOrdinaryMain(t *testing.T) {
	if os.Getenv("PLUGINUNINSTALL_HOST_BINARY") == "" {
		t.Skip("opt-in ordinary Linux Main; not executed acceptance")
	}
	for _, name := range []string{"PLUGINUNINSTALL_WORKER_BINARY", "PLUGINUNINSTALL_UPDATE_BINARY", "PLUGINUNINSTALL_MPS_BINARY", "PLUGINUNINSTALL_FIXTURE_BINARY", "PLUGINUNINSTALL_EXPECT_HOST_SHA256", "PLUGINUNINSTALL_EXPECT_WORKER_SHA256", "PLUGINUNINSTALL_EXPECT_MPS_SHA256"} {
		if os.Getenv(name) == "" {
			t.Fatal("required owned input", name)
		}
	}
	first := puiLoad(t, os.Getenv("PLUGINUNINSTALL_WORKER_BINARY"), puiID, 98)
	updated := puiLoad(t, os.Getenv("PLUGINUNINSTALL_UPDATE_BINARY"), puiID, 98)
	mps := puiLoad(t, os.Getenv("PLUGINUNINSTALL_MPS_BINARY"), puiMPS, 99)
	probe := puiLoad(t, os.Getenv("PLUGINUNINSTALL_FIXTURE_BINARY"), puiProbe, 0)
	if first.version != "2.2" || updated.version != "2.2.1" {
		t.Fatal("manifest-only test update must use distinct real executable version")
	}
	if first.hash != os.Getenv("PLUGINUNINSTALL_EXPECT_WORKER_SHA256") || mps.hash != os.Getenv("PLUGINUNINSTALL_EXPECT_MPS_SHA256") {
		t.Fatal("actual worker inputs must match the explicitly expected PUI/MPS hashes")
	}
	actualHost := fileHash(t, os.Getenv("PLUGINUNINSTALL_HOST_BINARY"))
	if actualHost != os.Getenv("PLUGINUNINSTALL_EXPECT_HOST_SHA256") || actualHost == "7a08c6b60516a5ea9321916c25d587ceab9de2fd0c34a809a16222e48131eca8" {
		t.Fatal("exact reviewed PUI Main candidate required; superseded7a08 cannot be acceptance")
	}
	mainRepo, mpsRepo, probeRepo := puiRepo(t, first), puiRepo(t, mps), puiRepo(t, probe)
	s := puiNewMain(t)
	s.record("pui_inputs", map[string]any{"host": fileHash(t, s.binary), "worker": first.hash, "update_manifest_only_fixture": updated.hash, "MPS_original_order99": mps.hash, "owned_SDK_probe_order0": probe.hash, "UI_skipped": os.Getenv("PLUGINUNINSTALL_SKIP_UI") == "1", "no_SQL_fault_injection": "producer actualApp43 is separate evidence layer"})
	s.install(puiProbe, probeRepo, false)
	s.install(puiID, mainRepo, false)
	s.install(puiMPS, mpsRepo, false)
	noop := map[string]any{"plugin_ids": []string{}, "clear_config": false, "clear_data": false, "unknown": "keep-until-source-tail"}
	s.mutate("PUT", "/api/plugins/"+puiID, noop)
	s.config(puiID, noop)
	s.maps(puiID, true, true, true)
	for _, raw := range s.snapshot("").Local {
		var card struct {
			ID   string `json:"id"`
			Page bool   `json:"has_page"`
		}
		if json.Unmarshal(raw, &card) != nil {
			t.Fatal("local metadata object")
		}
		if card.ID == puiID && card.Page {
			t.Fatal("source pass get_page must not advertise a page")
		}
	}
	model, options := puiForm(t, s.read("/api/plugins/"+puiID+"/form"))
	puiAssert(t, model, noop, "stored raw model overlay")
	puiAssert(t, options, []string{puiProbe, puiID, puiMPS}, "actual manifest sort0/98/99; self included despite false state")
	// No API, service or page is invented for this source plugin.
	status, raw := s.http("GET", "/api/v1/plugin/"+puiID+"/not-declared", nil)
	if status != 404 || bytes.Contains(raw, []byte(`"success":true`)) {
		t.Fatal("undeclared PUI API was exposed", status, string(raw))
	}
	page := s.read("/api/plugins/" + puiID + "/page")
	puiAssert(t, puiJSON(t, page), map[string]any{"render_mode": "vuetify", "page": []any{}}, "source None page")
	puiAssert(t, puiJSON(t, s.read("/api/plugins/"+puiID+"/dashboard")), nil, "source None dashboard")
	services := s.read("/api/plugins/services")
	if bytes.Contains(services, []byte(`"instance_id":"PluginUnInstall"`)) {
		t.Fatal("source has no ordinary scheduler")
	}
	s.seed(puiID, nil, map[string]any{"namespace": "base"})
	clone := s.clone(puiID, "owned")
	cloneConfig := map[string]any{"plugin_ids": []string{}, "clear_config": false, "clear_data": false, "clone": "independent"}
	s.mutate("PUT", "/api/plugins/"+clone, cloneConfig)
	s.seed(clone, nil, map[string]any{"namespace": "clone"})
	s.stored(puiID, noop, map[string]any{"namespace": "base"})
	s.stored(clone, cloneConfig, map[string]any{"namespace": "clone"})
	s.record("pui_install_form_clone", map[string]any{"source_state": false, "page": []any{}, "dashboard": nil, "clone": clone, "actual_options": options})

	// Raw truthiness and source installed-list iteration. Selection order is
	// deliberately reversed; later log order must follow the installed list.
	a, b := s.clone(puiProbe, "a"), s.clone(puiProbe, "b")
	ca, cb := map[string]any{"synthetic": "a"}, map[string]any{"synthetic": "b"}
	da, db := map[string]any{"data": "a"}, map[string]any{"data": "b"}
	s.seed(a, ca, da)
	s.seed(b, cb, db)
	fileA := s.dataFile(a)
	fileB := s.dataFile(b)
	beforeOrder := s.snapshot("").Order
	wantOrder := []string{}
	for _, id := range beforeOrder {
		if id != a && id != b {
			wantOrder = append(wantOrder, id)
		}
	}
	s.order(beforeOrder)
	flags := map[string]any{"plugin_ids": []string{b, a}, "clear_config": "false", "clear_data": []any{0}, "unknown": "drop"}
	s.mutate("PUT", "/api/plugins/"+puiID, flags)
	rawReset := map[string]any{"plugin_ids": []string{}, "clear_config": "false", "clear_data": []any{0}}
	s.config(puiID, rawReset)
	puiAssert(t, s.snapshot("").Order, wantOrder, "source full remaining ordered list")
	for _, id := range []string{a, b} {
		s.maps(id, false, false, false)
		s.code(id, false)
		s.config(id, map[string]any{})
	}
	s.stored(a, ca, da)
	s.stored(b, cb, db)
	puiKeepFile(t, fileA)
	puiKeepFile(t, fileB)
	logs := s.read("/api/plugins/" + puiID + "/logs")
	var logBody struct {
		History struct {
			Entries []struct {
				Message string `json:"message"`
			} `json:"entries"`
		} `json:"history"`
	}
	if json.Unmarshal(logs, &logBody) != nil {
		t.Fatal("ordinary scoped log shape")
	}
	sequence := []string{}
	for _, row := range logBody.History.Entries {
		if strings.Contains(row.Message, a+" 已卸载") || strings.Contains(row.Message, b+" 已卸载") {
			sequence = append(sequence, row.Message)
		}
	}
	// Original endpoint returns newest-first. Source business emitted a then b.
	puiAssert(t, sequence, []string{"插件 " + b + " 已卸载", "插件 " + a + " 已卸载"}, "source per-installed-item INFO order (newest first)")
	s.record("pui_raw_flags_class_gate", map[string]any{"selection_order": []string{b, a}, "installed_iteration_order": []string{a, b}, "config_KV_retained": true, "data_files_retained": true, "code_removed": true, "tail_exact3_raw_flags": rawReset})

	// Unknown IDs still run the tail; noniterable selection instead raises after
	// reading installed IDs and leaves the already-saved raw configuration.
	unknown := map[string]any{"plugin_ids": []string{"OwnedPuiFixtureunknown"}, "unknown": "drop"}
	order := s.snapshot("").Order
	s.mutate("PUT", "/api/plugins/"+puiID, unknown)
	s.config(puiID, map[string]any{"plugin_ids": []string{}, "clear_config": nil, "clear_data": nil})
	puiAssert(t, s.snapshot("").Order, order, "unknown selection retains installed list")
	bad := map[string]any{"plugin_ids": true, "clear_config": true, "unknown": "saved-before-init-error"}
	oldPID := s.pids()[puiID]
	status, raw = s.http("PUT", "/api/plugins/"+puiID, bad)
	if status < 400 || !bytes.Contains(raw, []byte("error")) {
		t.Fatal("noniterable selection must report source init failure", status, string(raw))
	}
	s.config(puiID, bad)
	puiAssert(t, s.snapshot("").Order, order, "source error skips installed tail")
	if s.pids()[puiID] != oldPID {
		t.Fatal("source method error killed worker")
	}
	s.mutate("PUT", "/api/plugins/"+puiID, unknown)

	// Real UID1000 permission failure at Path.exists occurs after logical remove,
	// before installed-list/config tail. Restore only our package parent always.
	mpsConfig := map[string]any{"enable": false, "owned": "retain-mps"}
	mpsData := map[string]any{"namespace": "mps"}
	s.seed(puiMPS, mpsConfig, mpsData)
	mpsFile := s.dataFile(puiMPS)
	oldPID = s.pids()[puiMPS]
	partial := map[string]any{"plugin_ids": []string{puiMPS}, "clear_config": true, "clear_data": true, "unknown": "must-survive-error"}
	order = s.snapshot("").Order
	packageRoot := filepath.Join(s.dir, "plugin-packages")
	func() {
		if e := os.Chmod(packageRoot, 0000); e != nil {
			t.Fatal(e)
		}
		defer os.Chmod(packageRoot, 0700)
		status, raw = s.http("PUT", "/api/plugins/"+puiID, partial)
	}()
	if status < 400 || !bytes.Contains(raw, []byte("error")) {
		t.Fatal("real EACCES must escape source init", status, string(raw))
	}
	s.waitDead(oldPID)
	s.maps(puiMPS, true, false, false)
	s.code(puiMPS, true)
	s.config(puiID, partial)
	puiAssert(t, s.snapshot("").Order, order, "EACCES retains old installed list")
	s.stored(puiMPS, mpsConfig, mpsData)
	puiKeepFile(t, mpsFile)
	// Consume the old selected input with an unknown selection before reinstall,
	// so an unrelated operation can never accidentally replay an uninstall.
	s.mutate("PUT", "/api/plugins/"+puiID, unknown)
	s.install(puiMPS, mpsRepo, true)
	s.seed(puiMPS, mpsConfig, mpsData)
	pathMPS := filepath.Join(packageRoot, puiMPS)
	func() {
		if e := os.Chmod(pathMPS, 0000); e != nil {
			t.Fatal(e)
		}
		defer os.Chmod(pathMPS, 0700)
		s.mutate("PUT", "/api/plugins/"+puiID, partial)
	}()
	s.maps(puiMPS, false, false, false)
	s.code(puiMPS, true)
	s.config(puiID, map[string]any{"plugin_ids": []string{}, "clear_config": true, "clear_data": true})
	s.stored(puiMPS, mpsConfig, mpsData)
	s.record("pui_real_permissions", map[string]any{"uid": os.Geteuid(), "parent000": "exists EACCES after logical stop; old installed/config retained", "package000": "rmtree suppressed; installed removal and exact3 reset complete; code residue retained"})

	// UI is reached with no installed/running MPS, avoiding its unconditional
	// dashboard network probe. Only owned instrumentation and PUI remain.
	uiVictim := s.clone(puiProbe, "ui")
	uiConfig, uiData := map[string]any{"synthetic": "ui-retained"}, map[string]any{"data": "ui-retained"}
	s.seed(uiVictim, uiConfig, uiData)
	s.mutate("PUT", "/api/plugins/"+puiID, noop)
	_, options = puiForm(t, s.read("/api/plugins/"+puiID+"/form"))
	for _, id := range []string{puiID, clone, uiVictim} {
		if !puiContains(options, id) {
			t.Fatal("UI dynamic option missing", id)
		}
	}
	if puiContains(options, puiMPS) {
		t.Fatal("uninstalled MPS leaked into installed-only form")
	}
	s.barrier(uiVictim)
	if os.Getenv("PLUGINUNINSTALL_SKIP_UI") == "1" {
		s.mutate("PUT", "/api/plugins/"+puiID, map[string]any{"plugin_ids": []string{uiVictim}, "clear_config": true, "clear_data": true})
	}
	s.maps(uiVictim, false, false, false)
	s.code(uiVictim, false)
	s.stored(uiVictim, uiConfig, uiData)
	resetTrue := map[string]any{"plugin_ids": []string{}, "clear_config": true, "clear_data": true}
	s.config(puiID, resetTrue)
	s.stored(clone, cloneConfig, map[string]any{"namespace": "clone"})
	model, _ = puiForm(t, s.read("/api/plugins/"+puiID+"/form"))
	puiAssert(t, model, resetTrue, "UI exact3 reset and unknown drop")

	// Ordinary sync reload/update replaces the real process. The only modified
	// update fixture source is the version literal; it is not an upstream release.
	oldPID = s.pids()[puiID]
	s.mutate("POST", "/api/plugins/"+puiID+"/reload", nil)
	s.waitDead(oldPID)
	if s.pids()[puiID] == 0 {
		t.Fatal("reload missing actual worker")
	}
	s.config(puiID, resetTrue)
	mainRepo.change(updated)
	oldPID = s.pids()[puiID]
	s.install(puiID, mainRepo, true)
	s.waitDead(oldPID)
	s.config(puiID, resetTrue)
	s.stored(puiID, resetTrue, map[string]any{"namespace": "base"})
	s.stored(clone, cloneConfig, map[string]any{"namespace": "clone"})
	snap := s.snapshot("")
	for _, r := range snap.Running {
		if r.Instance == puiID && r.Version != "2.2.1" || r.Instance == clone && r.Version != "2.2" {
			t.Fatal("source update changed clone artifact", r)
		}
	}

	// Cold pre-import is a genuine process stop/start with raw config staged via
	// Base.UpdateConfig only. No alternative executor or lifecycle mock is used.
	s.install(puiMPS, mpsRepo, true)
	s.seed(puiMPS, mpsConfig, mpsData)
	coldFuture := map[string]any{"plugin_ids": []string{puiMPS}, "clear_config": true, "clear_data": true}
	s.seed(puiID, coldFuture, nil)
	s.cold()
	s.maps(puiMPS, false, true, true)
	s.code(puiMPS, false)
	s.config(puiMPS, mpsConfig)
	s.stored(puiMPS, mpsConfig, mpsData)
	s.config(puiID, resetTrue)
	_, options = puiForm(t, s.read("/api/plugins/"+puiID+"/form"))
	if puiContains(options, puiMPS) {
		t.Fatal("future preimport ghost must not be installed option")
	}
	s.record("pui_cold_future99", map[string]any{"installed": false, "class": true, "running": true, "code": false, "MPS_state": false, "raw_config_KV": "retained", "next_cold": "no resurrection"})
	s.cold()
	s.maps(puiMPS, false, false, false)
	s.code(puiMPS, false)

	// Loaded self removes both maps, but the active initializer must finish its
	// installed-list and own raw-config tail before actual worker retirement.
	oldPID = s.pids()[puiID]
	self := map[string]any{"plugin_ids": []string{puiID}, "clear_config": true, "clear_data": true, "unknown": "drop"}
	s.mutate("PUT", "/api/plugins/"+puiID, self)
	s.waitDead(oldPID)
	s.maps(puiID, false, false, false)
	s.code(puiID, false)
	s.config(puiID, map[string]any{})
	s.stored(puiID, resetTrue, map[string]any{"namespace": "base"})
	s.stored(clone, cloneConfig, map[string]any{"namespace": "clone"})
	// Stage self in the stored config before genuine cold construction. Source
	// startup unconditionally inserts the new object after its self-removing init.
	s.install(puiID, mainRepo, true)
	s.seed(puiID, self, nil)
	s.cold()
	s.maps(puiID, false, false, true)
	s.code(puiID, false)
	s.config(puiID, map[string]any{})
	s.stored(puiID, resetTrue, map[string]any{"namespace": "base"})
	model, options = puiForm(t, s.read("/api/plugins/"+puiID+"/form"))
	if puiContains(options, puiID) {
		t.Fatal("cold self runtime is not a class option")
	}
	puiAssert(t, model, map[string]any{"plugin_ids": []any{}, "clear_config": false, "clear_data": false}, "cold self class-gated public form defaults")
	s.record("pui_cold_self", map[string]any{"installed": false, "class": false, "running": true, "code": false, "public_config": map[string]any{}, "raw_config": resetTrue})
	s.cold()
	s.maps(puiID, false, false, false)
	// Clone owns its namespace and independent code, including self tail.
	oldPID = s.pids()[clone]
	s.mutate("PUT", "/api/plugins/"+clone, map[string]any{"plugin_ids": []string{clone}, "clear_config": true, "clear_data": true})
	s.waitDead(oldPID)
	s.maps(clone, false, false, false)
	s.code(clone, false)
	s.stored(clone, resetTrue, map[string]any{"namespace": "clone"})
	s.config(clone, map[string]any{})
	s.cold()
	s.maps(clone, false, false, false)

	// Ordinary platform reset/uninstall is deliberately tested separately from
	// PUI's remove-then-classgate behavior; neither is substituted for the other.
	s.install(puiID, mainRepo, true)
	coldClone := s.clone(puiID, "cold")
	s.seed(coldClone, map[string]any{"plugin_ids": []string{coldClone}, "clear_config": true, "clear_data": true}, map[string]any{"namespace": "cold-clone"})
	s.cold()
	s.maps(coldClone, false, false, true)
	s.code(coldClone, false)
	s.config(coldClone, map[string]any{})
	s.stored(coldClone, resetTrue, map[string]any{"namespace": "cold-clone"})
	s.maps(puiID, true, true, true)
	s.config(puiID, resetTrue)
	s.cold()
	s.maps(coldClone, false, false, false)
	s.seed(puiID, resetTrue, map[string]any{"namespace": "before-reset"})
	dataFile := s.dataFile(puiID)
	s.mutate("POST", "/api/plugins/"+puiID+"/reset", nil)
	s.config(puiID, map[string]any{})
	s.stored(puiID, nil, nil)
	puiKeepFile(t, dataFile)
	baseConfig := map[string]any{"plugin_ids": []string{}, "clear_config": false, "clear_data": false, "base": "ordinary-retained"}
	baseData := map[string]any{"namespace": "ordinary-base"}
	s.seed(puiID, baseConfig, baseData)
	platformClone := s.clone(puiID, "platform")
	s.seed(platformClone, cloneConfig, map[string]any{"namespace": "ordinary-clone"})
	cloneFile := s.dataFile(platformClone)
	result := s.mutate("DELETE", "/api/plugins/"+platformClone, nil)
	var uninstalled struct {
		Uninstalled bool  `json:"uninstalled"`
		Retained    *bool `json:"data_retained"`
	}
	if json.Unmarshal(result, &uninstalled) != nil || !uninstalled.Uninstalled || uninstalled.Retained == nil || *uninstalled.Retained {
		t.Fatal("ordinary clone uninstall must purge DB namespace", string(result))
	}
	s.code(platformClone, false)
	s.stored(platformClone, nil, nil)
	puiKeepFile(t, cloneFile)
	s.stored(puiID, baseConfig, baseData)
	result = s.mutate("DELETE", "/api/plugins/"+puiID, nil)
	uninstalled.Retained = nil
	if json.Unmarshal(result, &uninstalled) != nil || !uninstalled.Uninstalled || uninstalled.Retained == nil || !*uninstalled.Retained {
		t.Fatal("ordinary base uninstall must retain", string(result))
	}
	s.code(puiID, true)
	s.maps(puiID, false, false, false)
	s.config(puiID, map[string]any{})
	s.stored(puiID, baseConfig, baseData)
	s.install(puiID, mainRepo, false)
	s.config(puiID, baseConfig)
	s.stored(puiID, baseConfig, baseData)
	puiKeepFile(t, dataFile)
	all := s.pids()
	s.stop()
	for _, pid := range all {
		s.waitDead(pid)
	}
	for pid := range s.allPIDs {
		s.waitDead(pid)
	}
	s.record("pui_main_complete", map[string]any{"ordinary_main": "all asserted stages complete", "UI_executed": os.Getenv("PLUGINUNINSTALL_SKIP_UI") != "1", "instances": "base, platform clones, self/future cold source distinctions", "all_observed_workers_joined": len(s.allPIDs), "DB_fault_layer": "not injected in Main; producer realSQLite43 separate", "network": "owned loopback executable repositories only; MPS init/state only, no page/dashboard/network"})
}

func TestPluginUninstallAuditedRouteBodies(t *testing.T) {
	// All remaining ordinary Main routes are audited before the first costly NAS
	// execution. This fixture validates the driver's HTTP serialization/auth only,
	// and is explicitly not evidence that Main implements these responses.
	type route struct {
		method, path string
		body         any
		response     string
		mutation     bool
	}
	rows := []route{
		{"POST", "/api/plugins/install", map[string]any{"plugin_id": puiID, "repo_url": "http://127.0.0.1:1/index", "force": true}, `{"data":{"success":true}}`, true},
		{"POST", "/api/plugins/PluginUnInstall/clone", map[string]any{"suffix": "owned", "name": "Owned PluginUnInstallowned", "version": "owned"}, `{"data":{"success":true,"created":true,"instance_id":"PluginUnInstallowned","source_instance_id":"PluginUnInstall"}}`, true},
		{"PUT", "/api/plugins/PluginUnInstall", map[string]any{"plugin_ids": []string{}, "clear_config": "false", "clear_data": []any{0}, "unknown": "preserve"}, `{"data":{"success":true}}`, true},
		{"POST", "/api/plugins/PluginUnInstall/reload", nil, `{"data":{"success":true}}`, true},
		{"POST", "/api/plugins/PluginUnInstall/reset", nil, `{"data":{"success":true}}`, true},
		{"DELETE", "/api/plugins/PluginUnInstallplatform", nil, `{"data":{"success":true,"uninstalled":true,"data_retained":false}}`, true},
		{"DELETE", "/api/plugins/PluginUnInstall", nil, `{"data":{"success":true,"uninstalled":true,"data_retained":true}}`, true},
		{"GET", "/api/plugins/PluginUnInstall", nil, `{"data":{}}`, false},
		{"GET", "/api/plugins/PluginUnInstall/form", nil, `{"data":{"render_mode":"vuetify","conf":[],"model":{}}}`, false},
		{"GET", "/api/plugins/PluginUnInstall/page", nil, `{"data":{"render_mode":"vuetify","page":[]}}`, false},
		{"GET", "/api/plugins/PluginUnInstall/dashboard", nil, `{"data":null}`, false},
		{"GET", "/api/plugins/services", nil, `{"data":[]}`, false},
		{"GET", "/api/plugins/PluginUnInstall/logs", nil, `{"data":{"history":{"entries":[]}}}`, false},
		{"PUT", "/api/plugins/OwnedPuiFixture", map[string]any{"seeds": []any{map[string]any{"id": puiID, "config": map[string]any{"plugin_ids": []string{puiID}}, "data": map[string]any{"namespace": "owned"}}}}, `{"data":{"success":true}}`, true},
		{"PUT", "/api/plugins/OwnedPuiFixture", map[string]any{"installed": []string{puiProbe, puiID, puiMPS}}, `{"data":{"success":true}}`, true},
		{"GET", "/api/v1/plugin/OwnedPuiFixture/inspect?target=PluginUnInstall", nil, `{"installed":[],"classes":[],"running":[],"installed_order":[],"pid":1,"raw_config":null,"raw_data":null}`, false},
	}
	for _, row := range rows {
		t.Run(row.method+" "+row.path, func(t *testing.T) {
			hit := false
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				hit = true
				if r.Method != row.method || r.URL.RequestURI() != row.path || r.Header.Get("Content-Type") != "application/json" {
					t.Error("route/method/content-type mismatch")
				}
				if strings.HasPrefix(row.path, "/api/v1/plugin/") {
					if r.Header.Get("X-API-KEY") != "owned-synthetic-test-only" {
						t.Error("API auth header missing")
					}
				} else if r.Header.Get("X-API-KEY") != "" {
					t.Error("API key unnecessarily sent")
				}
				if row.body != nil {
					var body any
					d := json.NewDecoder(r.Body)
					d.UseNumber()
					if d.Decode(&body) != nil || !puiEqual(body, row.body) {
						t.Error("raw body type/shape changed")
					}
				}
				_, _ = w.Write([]byte(row.response))
			}))
			defer server.Close()
			f, e := os.CreateTemp(t.TempDir(), "observations")
			if e != nil {
				t.Fatal(e)
			}
			defer f.Close()
			s := &puiMain{mainHost: &mainHost{t: t, base: server.URL, client: server.Client(), events: f}, token: "owned-synthetic-test-only"}
			status, raw := s.http(row.method, row.path, row.body)
			if _, e = puiResponse(status, raw, row.mutation); e != nil || !hit {
				t.Fatal("audited HTTP serialization", e)
			}
			bytes, e := os.ReadFile(f.Name())
			if e != nil {
				t.Fatal(e)
			}
			if strings.Contains(string(bytes), s.token) || strings.Contains(string(bytes), "?target=") {
				t.Fatal("evidence must omit API key and raw query")
			}
		})
	}
}
