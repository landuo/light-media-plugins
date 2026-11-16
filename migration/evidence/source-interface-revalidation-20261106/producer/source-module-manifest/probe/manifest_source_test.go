package sourceinterfaces

import (
	"encoding/json"
	"os"
	"slices"
	"testing"

	plugins "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/categoryeditor"
	"github.com/landuo/light-media-plugins/plugins/mpserverstatus"
	"github.com/landuo/light-media-plugins/plugins/pluginuninstall"
	"github.com/landuo/light-media-plugins/plugins/removelink"
	"github.com/landuo/light-media-plugins/plugins/sitestatistic"
	"github.com/landuo/light-media-plugins/plugins/torrenttransfer"
)

// The installed Python Class+Base+ObjectUtils AST was executed independently in
// fixed Python3.12. This checks only interfaces whose manager discovery first
// applies check_method. API/page/auth use other source ordering and are excluded.
func TestSourceCheckedManifestDeclarations(t *testing.T) {
	raw, e := os.ReadFile(os.Getenv("SOURCE_INTERFACE_ORACLE"))
	if e != nil {
		t.Fatal("executed source oracle required", e)
	}
	var source struct {
		Inventory []struct {
			Plugin     string
			Interfaces map[string]struct {
				CheckMethod bool `json:"check_method"`
			}
		}
	}
	if e = json.Unmarshal(raw, &source); e != nil || len(source.Inventory) != 7 {
		t.Fatal("source7 inventory", e)
	}
	manifests := map[string]plugins.Manifest{"categoryeditor": categoryeditor.Manifest(), "torrenttransfer": torrenttransfer.Manifest(), "torrenttransfermusic": torrenttransfer.Manifest(), "removelink": removelink.Manifest(), "sitestatistic": sitestatistic.Manifest(), "mpserverstatus": mpserverstatus.Manifest(), "pluginuninstall": pluginuninstall.Manifest()}
	for _, row := range source.Inventory {
		t.Run(row.Plugin, func(t *testing.T) {
			m, ok := manifests[row.Plugin]
			if !ok {
				t.Fatal("unmapped source instance")
			}
			for _, method := range []string{"get_module", "get_service", "get_command", "get_dashboard", "get_dashboard_meta"} {
				want, ok := row.Interfaces[method]
				if !ok {
					t.Fatal("source field absent", method)
				}
				if got := slices.Contains(m.Methods, method); got != want.CheckMethod {
					t.Errorf("%s advertised=%v, executed source check_method=%v", method, got, want.CheckMethod)
				}
			}
		})
	}
}
