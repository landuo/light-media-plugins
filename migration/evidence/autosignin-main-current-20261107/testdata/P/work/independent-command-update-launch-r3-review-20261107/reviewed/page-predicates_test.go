package integration

import (
	"encoding/json"
	"os"
	"testing"
)

func TestASIPageDriverPredicatesAgainstOriginalGetter(t *testing.T) {
	raw, err := os.ReadFile("/Users/accidia/projects/light-media-plugins/work/independent-command-main-attempt4-review-20261107/source-oracle.json")
	if err != nil {
		t.Fatal(err)
	}
	var oracle struct {
		Rows []struct {
			Case string          `json:"case"`
			Page json.RawMessage `json:"page"`
		} `json:"rows"`
	}
	if json.Unmarshal(raw, &oracle) != nil || len(oracle.Rows) != 3 {
		t.Fatal("original getter oracle")
	}
	for _, row := range oracle.Rows {
		t.Run(row.Case, func(t *testing.T) {
			wrapped := append([]byte(`{"page":`), row.Page...)
			wrapped = append(wrapped, '}')
			pending, empty, success := asiOwnedPendingRow(t, wrapped), asiOwnedEmptyPage(t, wrapped), asiOwnedSuccessfulRow(t, wrapped)
			switch row.Case {
			case "disabled-selected-no-history":
				if !pending || empty || success {
					t.Fatal("selected pending source row", pending, empty, success)
				}
			case "disabled-unselected-no-history":
				if pending || !empty || success {
					t.Fatal("unselected empty source page", pending, empty, success)
				}
			case "disabled-selected-success-history":
				if pending || empty || !success {
					t.Fatal("successful source row", pending, empty, success)
				}
			default:
				t.Fatal("unrecognized original getter condition", row.Case)
			}
		})
	}
}
