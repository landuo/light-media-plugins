package iyuuautoseed

import (
	"context"
	"encoding/json"
	"io"
	"os"
	"reflect"
	"strings"
	"testing"
)

type historyReplayNotice struct {
	Type  string `json:"mtype"`
	Title string `json:"title"`
	Text  string `json:"text"`
}

type historyReplayHost struct {
	*coreReplayHost
	originals, candidates []string
	legacy                any
	adds, reads           []string
	histories             map[string]any
	successCaches         [][]any
	notices               []historyReplayNotice
}

func (h *historyReplayHost) Indexer(context.Context, string) (*Site, error) {
	return &Site{Fields: map[string]any{"id": 1, "url": "https://owned.example/", "name": "owned"}}, nil
}

func (h *historyReplayHost) CheckSite(context.Context, string) (bool, error) { return false, nil }

func (h *historyReplayHost) DownloadURL(_ context.Context, seed map[string]any, _ Site, _ string) (string, error) {
	return "https://owned.example/" + seed["info_hash"].(string), nil
}

func (h *historyReplayHost) Torrent(_ context.Context, _ Site, address string) (TorrentContent, error) {
	hash := strings.TrimSuffix(strings.TrimPrefix(address, "https://owned.example/"), "?https=1")
	return TorrentContent{Bytes: []byte(hash)}, nil
}

func (h *historyReplayHost) AddPaused(_ context.Context, _ Service, spec AddSpec) (AddReceipt, error) {
	hash := string(spec.Content)
	h.adds = append(h.adds, hash)
	return AddReceipt{SourceTruthy: true, Accepted: true, Outcome: "confirmed", Hash: hash}, nil
}

func (h *historyReplayHost) LoadHistory(_ context.Context, hash string) (any, error) {
	h.reads = append(h.reads, hash)
	if hash == h.originals[0] {
		return h.legacy, nil
	}
	return nil, nil
}

func (h *historyReplayHost) SaveHistory(_ context.Context, hash string, history any) error {
	h.histories[hash] = history
	return nil
}

func (h *historyReplayHost) SaveConfig(_ context.Context, config map[string]any) error {
	h.successCaches = append(h.successCaches, config["success_caches"].([]any))
	return nil
}

func (h *historyReplayHost) Notify(_ context.Context, title, message string) error {
	h.notices = append(h.notices, historyReplayNotice{Type: "站点", Title: title, Text: message})
	return nil
}

func (h *historyReplayHost) SeedInfo(_ context.Context, hashes []string) (APIResult, error) {
	rows := map[string]any{}
	for i, key := range hashes {
		rows[key] = map[string]any{"torrent": map[string]any{"sid": json.Number("1"), "info_hash": h.candidates[i]}}
	}
	return APIResult{Data: rows, ObjectKeys: hashes}, nil
}

func (h *historyReplayHost) TorrentURL(context.Context, any) (any, any, error) {
	return "https://owned.example/", "/download", nil
}

func TestSourceIYUUHistoryShapeKeepsSuccessfulPass222(t *testing.T) {
	var oracle struct {
		Originals, Candidates []string
		Legacy                any            `json:"legacy_history"`
		Adds                  []string       `json:"successful_adds"`
		Reads                 []string       `json:"history_reads"`
		Writes                map[string]any `json:"history_writes"`
		Caches                [][]any        `json:"persisted_success_caches"`
		Notifications         []historyReplayNotice
		Diagnostic            string
		FinalLog              string `json:"final_log"`
	}
	raw, err := os.ReadFile("reference/history-shape-oracle.json")
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(raw, &oracle); err != nil {
		t.Fatal(err)
	}
	legacy, err := cloneJSON(oracle.Legacy)
	if err != nil {
		t.Fatal(err)
	}
	service := Service{Ref: "owned", Name: "owned", Kind: "transmission"}
	completed := []NativeTorrent{}
	for _, hash := range oracle.Originals {
		completed = append(completed, NativeTorrent{Fields: map[string]any{"hashString": hash, "download_dir": "/owned", "total_size": json.Number("100")}})
	}
	host := &historyReplayHost{
		coreReplayHost: &coreReplayHost{services: []Service{service}, completed: map[string][]NativeTorrent{service.Name: completed}},
		originals:      oracle.Originals, candidates: oracle.Candidates, legacy: legacy, histories: map[string]any{},
	}
	cfg := NewConfig()
	cfg.values["downloaders"] = []any{service.Name}
	cfg.values["notify"] = true
	core, err := NewCore(cfg, host, host)
	if err != nil {
		t.Fatal(err)
	}
	var finalLog string
	ctx := WithSourceLogSink(t.Context(), func(_ context.Context, entry SourceLog) { finalLog = entry.Message })
	diagnostic, runErr := captureHistoryDiagnostic(t, func() error { return core.AutoSeed(ctx) })
	if runErr != nil {
		t.Fatal(runErr)
	}
	if !reflect.DeepEqual(host.adds, oracle.Adds) || !reflect.DeepEqual(host.reads, oracle.Reads) ||
		!reflect.DeepEqual(host.histories, oracle.Writes) || !reflect.DeepEqual(host.successCaches, oracle.Caches) ||
		!reflect.DeepEqual(host.notices, oracle.Notifications) || !reflect.DeepEqual(host.legacy, oracle.Legacy) ||
		diagnostic != oracle.Diagnostic || finalLog != oracle.FinalLog {
		t.Fatalf("source history behavior diverged: adds %v, reads %v, writes %v, cache %v, notices %v, legacy %v, diagnostic %q, final log %q",
			host.adds, host.reads, host.histories, host.successCaches, host.notices, host.legacy, diagnostic, finalLog)
	}
}

func captureHistoryDiagnostic(t *testing.T, run func() error) (string, error) {
	t.Helper()
	read, write, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer read.Close()
	previous := os.Stderr
	os.Stderr = write
	defer func() {
		os.Stderr = previous
		_ = write.Close()
	}()
	runErr := run()
	if err := write.Close(); err != nil {
		t.Fatal(err)
	}
	raw, err := io.ReadAll(read)
	if err != nil {
		t.Fatal(err)
	}
	return strings.TrimSpace(string(raw)), runErr
}
