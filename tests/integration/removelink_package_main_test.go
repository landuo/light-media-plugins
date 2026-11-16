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
	"runtime"
	"testing"
	"time"
)

// The canonical builder's ZIP is a separate actual Main observation; it does
// not relabel the complete lifecycle driver's independently constructed ZIP.
func TestRemoveLinkCanonicalPackageOrdinaryMain(t *testing.T) {
	zipPath := os.Getenv("REMOVELINK_PACKAGE_ZIP")
	if zipPath == "" {
		t.Skip("opt-in canonical ZIP/ordinary Main; not executed")
	}
	if runtime.GOOS != "linux" || os.Geteuid() == 0 {
		t.Fatal("canonical real watcher acceptance requires owned non-root Linux")
	}
	archive, err := os.ReadFile(zipPath)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(os.Getenv("REMOVELINK_PACKAGE_INDEX"))
	if err != nil {
		t.Fatal(err)
	}
	var catalog struct {
		Plugins []map[string]json.RawMessage `json:"plugins"`
	}
	if json.Unmarshal(raw, &catalog) != nil || len(catalog.Plugins) != 1 {
		t.Fatal("actual canonical single-plugin index")
	}
	index := catalog.Plugins[0]
	var releases []map[string]json.RawMessage
	var artifacts []map[string]json.RawMessage
	if json.Unmarshal(index["releases"], &releases) != nil || len(releases) != 1 || json.Unmarshal(releases[0]["artifacts"], &artifacts) != nil || len(artifacts) != 1 {
		t.Fatal("canonical release/artifact")
	}
	a := artifacts[0]
	var sum string
	var size int
	var files []struct {
		Path   string `json:"path"`
		SHA256 string `json:"sha256"`
		Size   int    `json:"size"`
	}
	if json.Unmarshal(a["sha256"], &sum) != nil || json.Unmarshal(a["size"], &size) != nil || json.Unmarshal(a["files"], &files) != nil || len(files) != 10 {
		t.Fatal("canonical worker + three frontend assets + six license/notice files required")
	}
	hash := sha256.Sum256(archive)
	if hex.EncodeToString(hash[:]) != sum || len(archive) != size {
		t.Fatal("canonical ZIP bytes differ from index")
	}
	repo := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
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
	// Preserve all canonical archive/manifest/file bytes. Only the unpublished
	// fixture download URL changes to this owned local HTTP repository.
	a["url"], _ = json.Marshal(repo.URL + "/canonical.zip")
	releases[0]["artifacts"], _ = json.Marshal(artifacts)
	index["releases"], _ = json.Marshal(releases)
	s := rmNewMain(t)
	s.ok("POST", "/api/plugins/install", map[string]any{"plugin_id": rmSource, "repo_url": repo.URL + "/index", "force": false})
	s.frontendRM(rmSource)
	var packageRoot string
	err = filepath.WalkDir(filepath.Join(s.dir, "plugin-packages", rmSource), func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.IsDir() && entry.Name() == "remove-link" {
			packageRoot = filepath.Dir(path)
		}
		return nil
	})
	if err != nil || packageRoot == "" {
		t.Fatal("actual canonical installed worker", err)
	}
	for _, file := range files {
		data, err := os.ReadFile(filepath.Join(packageRoot, filepath.FromSlash(file.Path)))
		h := sha256.Sum256(data)
		if err != nil || hex.EncodeToString(h[:]) != file.SHA256 || len(data) != file.Size {
			t.Fatal("actual installed canonical member", file.Path, err)
		}
	}
	s.ok("POST", "/api/plugins/"+rmSource+"/clone", map[string]any{"suffix": "Owned"})
	s.frontendRM(rmClone)
	baseSource, baseLinks := rmLinks(t, filepath.Join(s.files, "package-base"), "package-base", 2)
	cloneSource, cloneLinks := rmLinks(t, filepath.Join(s.files, "package-clone"), "package-clone", 2)
	s.configRM(rmSource, rmConfig(filepath.Dir(baseSource), false))
	cloneConfig := rmConfig(filepath.Dir(cloneSource), false)
	cloneConfig["enabled"] = false
	cloneConfig["owned_unknown"] = "canonical clone namespace"
	s.configRM(rmClone, cloneConfig)
	pids := s.workersRM()
	if len(pids) != 2 || pids[rmSource] == pids[rmClone] {
		t.Fatal("canonical base/clone independent workers absent", pids)
	}
	if err := os.Remove(baseSource); err != nil {
		t.Fatal(err)
	}
	rmWait(t, "canonical package real watcher cleanup", 10*time.Second, func() bool {
		for _, p := range baseLinks {
			if rmExists(p) {
				return false
			}
		}
		return true
	})
	for _, p := range append(cloneLinks, cloneSource) {
		if !rmExists(p) {
			t.Fatal("canonical base cleanup changed disabled clone", p)
		}
	}
	s.config(rmClone, cloneConfig)
	s.noInheritedModuleDiscovery("canonical-package-real-file-cleanup")
	s.mainHost.stop()
	for pid := range s.allPIDs {
		s.waitWorkerGone(pid)
	}
	s.noInheritedModuleDiscovery("canonical-package-after-worker-joins")
	s.record("rm_canonical_package_complete", map[string]any{"canonical_zip_sha256": sum, "verified_installed_members": len(files), "base_and_clone_source_relative_imports": true, "real_same_inode_alias_cleanup": true, "disabled_clone_unchanged": true, "all_workers_joined": len(s.allPIDs), "no_UI_claim": true})
}
