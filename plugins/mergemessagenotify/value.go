package mergemessagenotify

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"reflect"
	"strconv"
	"strings"
)

// JSON configuration and event values retain json.Number; nil is Python None.
func Decode(raw []byte) (any, error) {
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	var v any
	err := d.Decode(&v)
	if err == nil && d.Decode(new(any)) != io.EOF {
		return nil, errors.New("invalid trailing JSON")
	}
	return v, err
}

func clone(v any) any {
	switch x := v.(type) {
	case map[string]any:
		r := map[string]any{}
		for k, v := range x {
			r[k] = clone(v)
		}
		return r
	case []any:
		r := make([]any, len(x))
		for i, v := range x {
			r[i] = clone(v)
		}
		return r
	case []byte:
		return bytes.Clone(x)
	case []string:
		return append([]string(nil), x...)
	default:
		return x
	}
}
func cloneMap(v map[string]any) map[string]any {
	if v == nil {
		return nil
	}
	return clone(v).(map[string]any)
}
func truth(v any) bool {
	if v == nil {
		return false
	}
	switch x := v.(type) {
	case bool:
		return x
	case string:
		return x != ""
	case json.Number:
		n, e := strconv.ParseFloat(string(x), 64)
		return e != nil || n != 0
	case float64:
		return x != 0
	case int:
		return x != 0
	}
	r := reflect.ValueOf(v)
	switch r.Kind() {
	case reflect.Map, reflect.Slice, reflect.Array:
		return r.Len() > 0
	}
	return true
}
func str(v any) string {
	if v == nil {
		return "None"
	}
	switch x := v.(type) {
	case string:
		return x
	case bool:
		if x {
			return "True"
		}
		return "False"
	case json.Number:
		return pythonNumber(x)
	case float64:
		return pythonFloat(x)
	}
	return fmt.Sprint(v)
}
func pythonNumber(n json.Number) string {
	if strings.ContainsAny(string(n), ".eE") {
		if v, e := strconv.ParseFloat(string(n), 64); e == nil {
			return pythonFloat(v)
		}
	}
	return string(n)
}
func pythonFloat(v float64) string {
	s := strconv.FormatFloat(v, 'e', -1, 64)
	pos := strings.IndexByte(s, 'e')
	if pos < 0 {
		return s
	}
	exp, _ := strconv.Atoi(s[pos+1:])
	if exp >= -4 && exp < 16 {
		s = strconv.FormatFloat(v, 'f', -1, 64)
		if !strings.Contains(s, ".") {
			s += ".0"
		}
		return s
	}
	return s
}
func or(v, other any) any {
	if truth(v) {
		return v
	}
	return other
}
func numberEq(v any, want int) bool {
	switch x := v.(type) {
	case bool:
		return (x && want == 1) || (!x && want == 0)
	case int:
		return x == want
	case float64:
		return x == float64(want)
	case json.Number:
		n, e := strconv.ParseFloat(string(x), 64)
		return e == nil && n == float64(want)
	}
	return false
}
func contains(v any, want string) (bool, error) {
	switch x := v.(type) {
	case string:
		return strings.Contains(x, want), nil
	case []any:
		for _, i := range x {
			if i == want {
				return true, nil
			}
		}
		return false, nil
	case []string:
		for _, i := range x {
			if i == want {
				return true, nil
			}
		}
		return false, nil
	case map[string]any:
		_, ok := x[want]
		return ok, nil
	default:
		return false, errors.New("TypeError")
	}
}
func iterable(v any) ([]any, error) {
	switch x := v.(type) {
	case []any:
		return x, nil
	case []string:
		r := make([]any, len(x))
		for i, v := range x {
			r[i] = v
		}
		return r, nil
	case string:
		r := []any{}
		for _, c := range x {
			r = append(r, string(c))
		}
		return r, nil
	case map[string]any:
		return nil, errors.New("unordered Python mapping iteration requires ordered input")
	}
	return nil, errors.New("TypeError")
}
