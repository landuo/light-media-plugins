package autosignin

// Decode only original OCR HTTP bytes. Invalid JSON and a non-object .get are
// ordinary source exceptions; they must not become a host capability failure.
func sourceOCRServiceResult(content []byte, contentType string) (any, error) {
	text, err := responseText(content, contentType)
	if err != nil {
		return nil, err
	}
	value, err := parseSiteJSON(text)
	if err != nil {
		return nil, err
	}
	object, err := jsonObject(value)
	if err != nil {
		return nil, err
	}
	result := object["result"]
	if !Truth(result) {
		return "", nil
	}
	raw, err := sourceHTTPJSONBytes(result)
	if err != nil {
		return nil, err
	}
	result, err = sourceRestoreSavedJSON(raw)
	if err != nil {
		return nil, err
	}
	return &sourceOCRValue{value: result, raw: raw}, nil
}
