package autosignin

import (
	"encoding/json"
	"github.com/landuo/light-media-plugins/plugins/autosignin/pyvalue"
)

// OCR is annotated str in Python but its JSON result has no type enforcement.
// Retain raw order/precision for the eventual Requests form and logger repr.
type sourceOCRValue struct {
	value any
	raw   json.RawMessage
}

func rawOCRValue(value any) (json.RawMessage, error) {
	if v, ok := value.(*sourceOCRValue); ok {
		return append(json.RawMessage(nil), v.raw...), nil
	}
	return json.Marshal(value)
}
func ocrString(value *sourceOCRValue) string {
	text, err := pyvalue.JSONString(value.raw)
	if err != nil {
		panic(&sourceException{err})
	}
	return text
}
