// Package apprise incrementally ports the installed Apprise 1.9.9 dependency.
// The native library is not yet the complete provider set and has no implicit
// network transport. Valid unported providers are explicit dependencies.
package apprise

import (
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"reflect"
	"runtime"
	"strings"
	"sync"
)

var ErrUnsupported = errors.New("Apprise provider/dependency requires native implementation")

type Request struct {
	Method, URL             string
	Data                    []byte
	Headers, Params         map[string]string
	HeaderOrder, ParamOrder [][2]string
	RemoveHeaders           []string // Optional requests headers with None values; other clients retain defaults.
	Auth                    []any
	Verify                  bool
	Timeout                 [2]float64
}
type Response struct {
	Status  int
	Headers map[string]string
	Content []byte
}
type Transport func(context.Context, Request) (Response, error)

type notificationService interface {
	requests(title, body string) ([]Request, error)
	successful(status int) bool
}

type Client struct {
	transport Transport
	services  []notificationService
}

func New(transport Transport) *Client { return &Client{transport: transport} }

//go:embed testdata/catalog.json
var catalogJSON []byte
var knownSchemas = func() map[string]bool {
	var catalog []struct{ Schema string }
	if err := json.Unmarshal(catalogJSON, &catalog); err != nil {
		panic(err)
	}
	out := map[string]bool{}
	for _, p := range catalog {
		out[p.Schema] = true
	}
	return out
}()

func (c *Client) Add(raw string) (bool, error) {
	sep := strings.Index(raw, "://")
	if sep <= 0 {
		return false, nil
	}
	scheme := strings.ToLower(strings.TrimSpace(raw[:sep]))
	var service notificationService
	var valid bool
	var err error
	switch scheme {
	case "json", "jsons":
		service, valid, err = parseJSONService(raw)
	case "apprise", "apprises":
		service, valid = parseGatewayService(raw)
	case "http", "https":
		native, ok := gatewayNativeURL(raw)
		if !ok {
			return false, ErrUnsupported
		}
		service, valid = parseGatewayService(native)
	default:
		if knownSchemas[scheme] {
			return false, ErrUnsupported
		}
		return false, nil
	}
	if err != nil || !valid {
		return false, err
	}
	c.services = append(c.services, service)
	return true, nil
}
func (c *Client) Notify(ctx context.Context, title, body, attach any) (any, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if len(c.services) == 0 {
		return false, nil
	}
	wanted, validAttach := attachmentRequest(attach)
	if !validAttach {
		return false, nil
	}
	if wanted {
		return nil, ErrUnsupported
	}
	titleText, ok := sourceText(title)
	if !ok {
		return false, nil
	}
	bodyText, ok := sourceText(body)
	if !ok || bodyText == "" {
		return false, nil
	}
	type requestGroup struct {
		service notificationService
		calls   []Request
	}
	requests := make([]requestGroup, 0, len(c.services))
	hasCalls := false
	for _, service := range c.services {
		calls, err := service.requests(titleText, bodyText)
		if err != nil {
			return nil, err
		}
		hasCalls = hasCalls || len(calls) != 0
		requests = append(requests, requestGroup{service: service, calls: calls})
	}
	if !hasCalls {
		return false, nil
	}
	if c.transport == nil {
		return nil, ErrUnsupported
	}
	send := func(group requestGroup) bool {
		success := len(group.calls) != 0
		for _, request := range group.calls {
			reply, err := c.transport(ctx, request)
			success = (err == nil && group.service.successful(reply.Status)) && success
		}
		return success
	}
	if len(requests) == 1 {
		success := send(requests[0])
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		return success, nil
	}
	// The original default asset uses ThreadPoolExecutor's CPython 3.12 bound.
	// Reserve workers before sending; no unbounded waiting goroutine per URL.
	workers := runtime.NumCPU() + 4
	if workers > 32 {
		workers = 32
	}
	if workers > len(requests) {
		workers = len(requests)
	}
	jobs := make(chan requestGroup)
	results := make(chan bool, len(requests))
	var group sync.WaitGroup
	for i := 0; i < workers; i++ {
		group.Add(1)
		go func() {
			defer group.Done()
			for request := range jobs {
				results <- send(request)
			}
		}()
	}
	for _, request := range requests {
		jobs <- request
	}
	close(jobs)
	group.Wait()
	close(results)
	success := true
	for ok := range results {
		success = success && ok
	}
	if ctx.Err() != nil {
		return nil, ctx.Err()
	}
	return success, nil
}
func attachmentRequest(value any) (wanted, valid bool) {
	if value == nil {
		return false, true
	}
	validate := func(s string) bool { return s != "" }
	if s, ok := value.(string); ok {
		return true, validate(s)
	}
	r := reflect.ValueOf(value)
	if r.Kind() != reflect.Slice && r.Kind() != reflect.Array {
		return false, false
	}
	for i := 0; i < r.Len(); i++ {
		s, ok := r.Index(i).Interface().(string)
		if !ok || !validate(s) {
			return false, false
		}
	}
	// __init__ requires successful add(); an empty list is successful, while
	// invalid element types make the entire preparation fail before any IO.
	return r.Len() > 0, true
}
func sourceText(v any) (string, bool) {
	if v == nil {
		return "", true
	}
	if s, ok := v.(string); ok {
		return s, true
	}
	value := reflect.ValueOf(v)
	falseValue := false
	switch value.Kind() {
	case reflect.Bool:
		falseValue = !value.Bool()
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		falseValue = value.Int() == 0
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		falseValue = value.Uint() == 0
	case reflect.Float32, reflect.Float64:
		falseValue = value.Float() == 0
	case reflect.Array, reflect.Slice, reflect.Map:
		falseValue = value.Len() == 0
	}
	if falseValue {
		return "", true
	}
	return "", false
}
