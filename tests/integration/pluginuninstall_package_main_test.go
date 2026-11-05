package integration

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io/fs"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

// This separately verifies the canonical seven-file published-package shape.
// The full Main1 source lifecycle used an executable artifact and remains its
// own immutable observation; this test does not relabel that original run.
func TestPluginUninstallCanonicalPackageOrdinaryMain(t *testing.T) {
	zipPath := os.Getenv("PLUGINUNINSTALL_PACKAGE_ZIP")
	if zipPath == "" {
		t.Skip("opt-in canonical ZIP/native Main; not executed")
	}
	archive, err := os.ReadFile(zipPath)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(os.Getenv("PLUGINUNINSTALL_PACKAGE_INDEX"))
	if err != nil {
		t.Fatal(err)
	}
	var catalog struct {
		Plugins []map[string]json.RawMessage `json:"plugins"`
	}
	if err := json.Unmarshal(raw, &catalog); err != nil || len(catalog.Plugins) != 1 {
		t.Fatal("actual canonical single-plugin index", err)
	}
	index := catalog.Plugins[0]
	var releases []map[string]json.RawMessage
	if json.Unmarshal(index["releases"], &releases) != nil || len(releases) != 1 {
		t.Fatal("actual canonical release")
	}
	var artifacts []map[string]json.RawMessage
	if json.Unmarshal(releases[0]["artifacts"], &artifacts) != nil || len(artifacts) != 1 {
		t.Fatal("actual canonical artifact")
	}
	a := artifacts[0]
	var sum string
	var size int
	var files []struct {
		Path   string `json:"path"`
		SHA256 string `json:"sha256"`
		Size   int    `json:"size"`
	}
	if json.Unmarshal(a["sha256"], &sum) != nil || json.Unmarshal(a["size"], &size) != nil || json.Unmarshal(a["files"], &files) != nil || len(files) != 7 {
		t.Fatal("canonical file inventory")
	}
	h := sha256.Sum256(archive)
	if hex.EncodeToString(h[:]) != sum || len(archive) != size {
		t.Fatal("canonical ZIP bytes differ from index")
	}
	var repo *httptest.Server
	repo = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			http.Error(w, "method", 405)
			return
		}
		switch r.URL.Path {
		case "/index":
			_ = json.NewEncoder(w).Encode(index)
		case "/canonical.zip":
			_, _ = w.Write(archive)
		default:
			http.NotFound(w, r)
		}
	}))
	defer repo.Close()
	// Keep exact archive/manifest/files; change only the nonpublished fixture
	// download URL to the owned local HTTP repository, as in the full Main test.
	a["url"], _ = json.Marshal(repo.URL + "/canonical.zip")
	releases[0]["artifacts"], _ = json.Marshal(artifacts)
	index["releases"], _ = json.Marshal(releases)
	s := puiNewMain(t)
	if want := os.Getenv("PLUGINUNINSTALL_EXPECT_HOST_SHA256"); want == "" || fileHash(t, s.binary) != want {
		t.Fatal("exact reviewed host ELF required")
	}
	probe := puiLoad(t, os.Getenv("PLUGINUNINSTALL_FIXTURE_BINARY"), puiProbe, 0)
	s.install(puiProbe, puiRepo(t, probe), false)
	s.mutate("POST", "/api/plugins/install", map[string]any{"plugin_id": puiID, "repo_url": repo.URL + "/index", "force": false})
	s.maps(puiID, true, true, true)
	var packageRoot string
	err = filepath.WalkDir(filepath.Join(s.dir, "plugin-packages", puiID), func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.IsDir() && entry.Name() == "plugin-uninstall" {
			packageRoot = filepath.Dir(path)
		}
		return nil
	})
	if err != nil || packageRoot == "" {
		t.Fatal("actual canonical installed worker", err)
	}
	for _, f := range files {
		b, err := os.ReadFile(filepath.Join(packageRoot, filepath.FromSlash(f.Path)))
		h := sha256.Sum256(b)
		if err != nil || hex.EncodeToString(h[:]) != f.SHA256 || len(b) != f.Size {
			t.Fatal("actual installed package member", f.Path, err)
		}
	}
	_, options := puiForm(t, s.read("/api/plugins/"+puiID+"/form"))
	if !puiContains(options, puiID) {
		t.Fatal("canonical worker source form lacks self")
	}
	clone := s.clone(puiID, "package")
	config := map[string]any{"plugin_ids": []string{}, "clear_config": false, "clear_data": false, "owned": "canonical-clone"}
	data := map[string]any{"owned": "canonical-clone-data"}
	s.mutate("PUT", "/api/plugins/"+clone, config)
	s.seed(clone, nil, data)
	pid := s.pids()[clone]
	s.mutate("PUT", "/api/plugins/"+puiID, map[string]any{"plugin_ids": []string{clone}, "clear_config": true, "clear_data": true})
	s.maps(clone, false, false, false)
	s.code(clone, false)
	s.stored(clone, config, data)
	s.waitDead(pid)
	s.maps(puiID, true, true, true)
	s.config(puiID, map[string]any{"plugin_ids": []string{}, "clear_config": true, "clear_data": true})
	s.pids()
	s.mainHost.stop()
	for pid := range s.allPIDs {
		s.waitDead(pid)
	}
	s.record("pui_canonical_package_complete", map[string]any{"canonical_zip_sha256": sum, "verified_installed_members": len(files), "source_form": true, "canonical_platform_clone_source_removed": true, "clone_config_KV_retained": true, "base_independent": true, "all_workers_joined": len(s.allPIDs), "no_UI_or_MPS": true})
}
