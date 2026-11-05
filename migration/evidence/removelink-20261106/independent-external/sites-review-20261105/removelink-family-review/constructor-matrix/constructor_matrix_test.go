package removelink

import (
	"encoding/json"
	"os"
	"testing"
)

const independentCtorOracle = "{\n  \"classification\": \"independent actual333/Python3.12 Path constructor dependency chain; each UID/env branch is a new read-only network-none disposable process; no app/config/DB imports\",\n  \"source_sha256\": \"22fb375e531378b3454607c7bca305b637abd60ee8ed69e14e32fbc2ddfc5485\",\n  \"cases\": [\n    {\n      \"mode\": \"present-empty\",\n      \"uid\": 65533,\n      \"HOME_present\": true,\n      \"HOME\": \"\",\n      \"passwd\": null,\n      \"values\": [\n        {\n          \"path\": \"~\",\n          \"value\": \"/\",\n          \"error\": null\n        },\n        {\n          \"path\": \"~/child\",\n          \"value\": \"/child\",\n          \"error\": null\n        },\n        {\n          \"path\": \"/absolute/no-home\",\n          \"value\": \"/absolute/no-home\",\n          \"error\": null\n        }\n      ],\n      \"empty_exclude\": false,\n      \"runtime\": \"3.12.13 (main, Aug  5 2026, 01:11:46) [GCC 12.2.0]\"\n    },\n    {\n      \"mode\": \"present-value\",\n      \"uid\": 65533,\n      \"HOME_present\": true,\n      \"HOME\": \"/owned/home\",\n      \"passwd\": null,\n      \"values\": [\n        {\n          \"path\": \"~\",\n          \"value\": \"/owned/home\",\n          \"error\": null\n        },\n        {\n          \"path\": \"~/child\",\n          \"value\": \"/owned/home/child\",\n          \"error\": null\n        },\n        {\n          \"path\": \"/absolute/no-home\",\n          \"value\": \"/absolute/no-home\",\n          \"error\": null\n        }\n      ],\n      \"empty_exclude\": false,\n      \"runtime\": \"3.12.13 (main, Aug  5 2026, 01:11:46) [GCC 12.2.0]\"\n    },\n    {\n      \"mode\": \"absent-found\",\n      \"uid\": 65534,\n      \"HOME_present\": false,\n      \"HOME\": null,\n      \"passwd\": {\n        \"name\": \"nobody\",\n        \"home\": \"/nonexistent\"\n      },\n      \"values\": [\n        {\n          \"path\": \"~\",\n          \"value\": \"/nonexistent\",\n          \"error\": null\n        },\n        {\n          \"path\": \"~/child\",\n          \"value\": \"/nonexistent/child\",\n          \"error\": null\n        },\n        {\n          \"path\": \"/absolute/no-home\",\n          \"value\": \"/absolute/no-home\",\n          \"error\": null\n        }\n      ],\n      \"empty_exclude\": false,\n      \"runtime\": \"3.12.13 (main, Aug  5 2026, 01:11:46) [GCC 12.2.0]\"\n    },\n    {\n      \"mode\": \"absent-unmapped\",\n      \"uid\": 65533,\n      \"HOME_present\": false,\n      \"HOME\": null,\n      \"passwd\": null,\n      \"values\": [\n        {\n          \"path\": \"~\",\n          \"value\": null,\n          \"error\": {\n            \"class\": \"RuntimeError\",\n            \"message\": \"Could not determine home directory.\"\n          }\n        },\n        {\n          \"path\": \"~/child\",\n          \"value\": null,\n          \"error\": {\n            \"class\": \"RuntimeError\",\n            \"message\": \"Could not determine home directory.\"\n          }\n        },\n        {\n          \"path\": \"/absolute/no-home\",\n          \"value\": \"/absolute/no-home\",\n          \"error\": null\n        }\n      ],\n      \"empty_exclude\": false,\n      \"runtime\": \"3.12.13 (main, Aug  5 2026, 01:11:46) [GCC 12.2.0]\"\n    }\n  ]\n}\n"

func TestIndependentHOMEConstructorAllBranches(t *testing.T) {
	var source struct {
		Cases []struct {
			Mode   string
			Uid    int
			Values []struct {
				Path  string
				Value *string
				Error *struct{ Class, Message string }
			}
			EmptyExclude bool `json:"empty_exclude"`
		}
	}
	if err := json.Unmarshal([]byte(independentCtorOracle), &source); err != nil {
		t.Fatal(err)
	}
	mode := os.Getenv("LM_REVIEW_CTOR_CASE")
	var index = -1
	for i, c := range source.Cases {
		if c.Mode == mode {
			index = i
		}
	}
	if index < 0 {
		t.Skip("explicit isolated UID/env constructor case required")
	}
	c := source.Cases[index]
	if os.Getuid() != c.Uid {
		t.Fatal("wrong uid", os.Getuid(), c.Uid)
	}
	p := NewPlugin()
	for _, r := range c.Values {
		t.Run(r.Path, func(t *testing.T) {
			var got string
			var recovered any
			func() { defer func() { recovered = recover() }(); got = normalized(r.Path, p.machine.Home) }()
			if r.Error == nil {
				if recovered != nil || r.Value == nil || got != *r.Value {
					t.Fatalf("source normalization value=%v Go=%q panic=%v", r.Value, got, recovered)
				}
			} else {
				failure, ok := recovered.(effectFailure)
				if !ok || failure.err.Error() != r.Error.Class+":"+r.Error.Message {
					t.Fatalf("source error=%+v Go=%q panic=%v", r.Error, got, recovered)
				}
			}
		})
	}
	t.Run("empty-exclude-no-premature-normalize", func(t *testing.T) {
		cfg := NewConfig()
		if got := cfg.Excluded("~__lm_review_absent__", p.machine.Home); got != c.EmptyExclude {
			t.Fatal("source empty excludes", got, c.EmptyExclude)
		}
	})
}
