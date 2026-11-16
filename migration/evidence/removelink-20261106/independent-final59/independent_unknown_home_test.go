package removelink

import (
	"encoding/json"
	"os"
	"testing"
)

func TestIndependentUnknownNamedHomeStopsUnlinkLikePathlib(t *testing.T) {
	raw, err := os.ReadFile("/Users/accidia/projects/light-media-plugins/work/sites-review-20261105/removelink-family-review/current58/unknown-home-source-oracle.json")
	if err != nil {
		t.Fatal(err)
	}
	var suite struct {
		Cases []struct {
			Input    oracleCase
			Expected struct {
				Files        []string `json:"files"`
				State        []string `json:"state"`
				LoggedErrors int      `json:"logged_errors"`
			}
		} `json:"cases"`
	}
	if err = json.Unmarshal(raw, &suite); err != nil {
		t.Fatal(err)
	}
	for _, row := range suite.Cases {
		t.Run(row.Input.Name, func(t *testing.T) {
			got := runOracle(t, row.Input).(map[string]any)
			files, _ := json.Marshal(got["files"])
			want, _ := json.Marshal(row.Expected.Files)
			if string(files) != string(want) || got["logged_errors"] != float64(row.Expected.LoggedErrors) {
				t.Fatalf("source Path.expanduser unknown user raises before unlink; source files=%s errors=%d; Go files=%s errors=%v", want, row.Expected.LoggedErrors, files, got["logged_errors"])
			}
		})
	}
}
