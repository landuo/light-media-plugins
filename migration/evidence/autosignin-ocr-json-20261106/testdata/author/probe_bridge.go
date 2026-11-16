package autosignin

import (
	"context"
	"encoding/json"
	sdk "github.com/landuo/light-media-plugins/internal/sdk"
	"github.com/landuo/light-media-plugins/plugins/autosignin/pyvalue"
)

func OwnedOCRValueDomain(ctx context.Context, host sdk.HostCaller, raw json.RawMessage) (out json.RawMessage, callErr error) {
	defer func() {
		if v := recover(); v != nil {
			if boundary, ok := v.(*boundaryFailure); ok {
				out = nil
				callErr = boundary.cause
				return
			}
			if source, ok := v.(*sourceException); ok {
				out, _ = json.Marshal(map[string]any{"helper_error": source.cause.Error(), "error": source.cause.Error(), "probe_error": source.cause.Error()})
				callErr = nil
				return
			}

			panic(v)
		}
	}()
	var input struct{ Mode string }
	if e := json.Unmarshal(raw, &input); e != nil {
		return nil, e
	}
	resources := sdk.Sites{Host: host}
	cfg, e := resources.SourceCustomConfig(ctx)
	if e != nil {
		return nil, e
	}
	ordinal := 0
	private, e := resources.SourceCredentials(ctx, sdk.SiteSourceReferenceV1{CustomOrdinal: &ordinal, Snapshot: cfg.Snapshot})
	if e != nil {
		return nil, e
	}
	decoded, e := sourceRestoreSavedJSON(private.Fields)
	if e != nil {
		return nil, e
	}
	site := decoded.(Object)
	site["_host_source_reference"] = private.Reference
	backend := sdkBackend{ctx: ctx, host: host}
	hooks := backend.visitor(site).Hooks
	if input.Mode == "hdsky" {
		result, e := OCRSignin(AdapterHDSky, ctx, site, hooks)
		if e != nil {
			return json.Marshal(map[string]any{"error": e.Error()})
		}
		return json.Marshal(map[string]any{"state": result.State, "message": result.Message})
	}
	result, e := hooks.OCR(ctx, "data:image/png;base64,YWJj")
	if e != nil {
		return json.Marshal(map[string]any{"helper_error": e.Error()})
	}
	value := result
	wrapped, wrappedOK := result.(*sourceOCRValue)
	if wrappedOK {
		value = wrapped.value
	}
	reprValue := value
	if wrappedOK && !wrapped.fromHTTP && len(wrapped.raw) > 0 {
		if v, e := parseSiteJSON(string(wrapped.raw)); e == nil {
			reprValue = v
		}
	}
	points := []int{}
	for _, r := range sourceCodepoints(pythonScalar(result)) {
		points = append(points, int(r))
	}
	observation := map[string]any{"type": typeName(value), "truth": Truth(result), "str_codepoints": points, "repr": sourceContainerRepr(reprValue)}
	if length, e := sourceLength(result); e != nil {
		observation["len_error"] = e.Error()
	} else {
		observation["len"] = length
	}
	var values []string
	if wrappedOK && !wrapped.fromHTTP {
		values, e = pyvalue.RequestFormValues(wrapped.raw)
	} else {
		values, e = sourceOCRFormValues(value)
	}
	if e != nil {
		observation["form_error"] = e.Error()
		return json.Marshal(observation)
	}
	transport := sdkSiteTransport{backend: backend, site: site}
	response, e := transport.Do(ctx, PageRequest{Method: "POST", URL: "https://hdsky.me/submit", FormValues: map[string][]string{"imagestring": values}, FormOrder: []string{"imagestring"}})
	if e != nil {
		return nil, e
	}
	if response == nil {
		observation["form_transport_none"] = true
	} else {
		observation["form_status"] = response.Status
	}
	return json.Marshal(observation)
}
