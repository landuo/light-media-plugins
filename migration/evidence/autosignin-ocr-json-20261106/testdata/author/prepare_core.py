from pathlib import Path
import json,hashlib,difflib
P=Path.cwd();w=Path(__file__).resolve().parent;rows=json.loads((w/'core-preimages.json').read_text())
for r in rows:assert hashlib.sha256(Path(r['before']).read_bytes()).hexdigest()==r['before_sha256']
p=w/'candidate/source_ocr_response.go';s=p.read_text();a=s.index('\traw, err := sourceHTTPJSONBytes(result)');s=s[:a]+'''\t// Keep the already-decoded source HTTP value. It may legally include
	// nonfinite floats, ordered maps, huge integers or lone codepoints.
	return &sourceOCRValue{value:result,fromHTTP:true},nil
}
''';p.write_text(s)
p=w/'candidate/ocr_value.go';s=p.read_text().replace('"encoding/json"','"encoding/json"\n "errors"\n "strings"');s=s.replace('\traw   json.RawMessage','\traw   json.RawMessage\n fromHTTP bool',1);needle='func ocrString(value *sourceOCRValue) string {\n';assert s.count(needle)==1;s=s.replace(needle,needle+' if value.fromHTTP { return pythonScalar(value.value) }\n',1)
s+='''
// This is Requests' existing two-stage doseq behavior, now over the already
// parsed source JSON values instead of forcing NaN/Inf back through strict IPC
// JSON. It preserves dictionary insertion order and drops only outer None.
func sourceOCRFormValues(value any)([]string,error){
 iterable:=func(value any)[]any{
  switch x:=value.(type){
  case []any:return x
  case sourceHTTPMap:
   out:=make([]any,0,len(x.keys));for _,key:=range x.keys{out=append(out,key)};return out
  }
  return []any{value}
 }
 out:=[]string{}
 for _,v:=range iterable(value){
  if v==nil{continue}
  for _,child:=range iterable(v){
   text:=pythonScalar(child)
   // Scalar strings are UTF8-encoded before urlencode. A nested container's
   // repr already escapes any lone codepoint, exactly as Python str does.
   if _,ok:=child.(string);ok{
    if e:=sourceWebSerializationFailure(text);e!=nil{
     var detail *ValueError
     if errors.As(e,&detail)&&detail.Kind=="PydanticSerializationError"{return nil,&ValueError{"UnicodeEncodeError",strings.TrimPrefix(detail.Message,"Error serializing to JSON: UnicodeEncodeError: ")}}
     return nil,e
    }
   }
   out=append(out,text)
  }
 }
 return out,nil
}
''';p.write_text(s)
p=w/'candidate/ocr_adapters.go';s=p.read_text();s=s.replace('return utf8.RuneCountInString(n), nil','return len(sourceCodepoints(n)), nil',1);needle='\tcase Object:\n\t\treturn len(n), nil';assert s.count(needle)==1;s=s.replace(needle,needle+'\n case sourceHTTPMap:\n  return len(n.values),nil',1);needle='\tvar rawForm map[string]json.RawMessage\n\tif text, ok := result.(string); ok {';assert s.count(needle)==1;s=s.replace(needle,'''\tvar rawForm map[string]json.RawMessage
	var formValues map[string][]string
	if source,ok:=result.(*sourceOCRValue);ok && source.fromHTTP {
	 values,err:=sourceOCRFormValues(source.value)
	 if err!=nil{return AdapterResult{},err}
	 formValues=map[string][]string{"imagestring":values}
	} else if text, ok := result.(string); ok {''',1);needle='PageRequest{Method: "POST", URL: address, Form: form, RawForm: rawForm, FormOrder: order, Referer: referer}';assert s.count(needle)==1;s=s.replace(needle,'PageRequest{Method: "POST", URL: address, Form: form, RawForm: rawForm, FormValues:formValues, FormOrder: order, Referer: referer}',1);p.write_text(s)
p=w/'candidate/visits.go';s=p.read_text();needle='\tRawForm              map[string]json.RawMessage';assert s.count(needle)==1;s=s.replace(needle,needle+'\n FormValues map[string][]string `json:"form_values,omitempty"`',1);p.write_text(s)
# Root explicitly supplied this fresh privacy-composed reference before writing.
base=P/'plugins/autosignin/source_site_binding.go';expected='4d1b5e2ff769a3788c042f4f378d6d165c7be4b300396dbd36dae4468a334ff7';assert hashlib.sha256(base.read_bytes()).hexdigest()==expected;s=base.read_text();needle='\tfor _, key := range keys {\n\t\tif raw, ok := request.RawForm[key]; ok {';assert s.count(needle)==1;s=s.replace(needle,'''\tfor _, key := range keys {
		if values,ok:=request.FormValues[key];ok{
		 for _,value:=range values{input.Form=append(input.Form,sdk.SiteHTTPPairV1{Name:key,Value:value})}
		 continue
		}
		if raw, ok := request.RawForm[key]; ok {''',1);out=w/'candidate/source_site_binding.go';out.write_text(s);rows.append({'target':'plugins/autosignin/source_site_binding.go','before':str(base),'before_sha256':expected,'candidate':str(out)})
# Compose exactly the independently frozen OCR6 backend hunks onto true privacy.
base=P/'plugins/autosignin/sdk_backend.go';expected='6a70e89bdc60e24ded5de557fe096be3d7209f17776f12b3b683df59d9f1a17b';assert hashlib.sha256(base.read_bytes()).hexdigest()==expected;s=base.read_text();needle='sdk.CaptchaOCRRequestV1{SiteID: transport.identity(), ImageURL: image}';assert s.count(needle)==1;s=s.replace(needle,'sdk.CaptchaOCRRequestV1{SourceReference: sourceReferencePointer(transport.reference(ctx)), ImageURL: image}',1);needle='''		b.fatal(err)
		var value any
		err = Decode(result.Result, &value)''';assert s.count(needle)==1;s=s.replace(needle,''' 		b.fatal(err)
		if result.SourceResponse != nil { return sourceOCRServiceResult(result.SourceResponse.Content, result.SourceResponse.ContentType) }
		var value any
		err = Decode(result.Result, &value)''',1);assert 'func sourceReferencePointer('not in s;s+='\nfunc sourceReferencePointer(value sdk.SiteSourceReferenceV1)*sdk.SiteSourceReferenceV1{return &value}\n';out=w/'candidate/sdk_backend.go';out.write_text(s);rows.append({'target':'plugins/autosignin/sdk_backend.go','before':str(base),'before_sha256':expected,'candidate':str(out),'qualification':'composition of unchanged frozen OCR6 backend two hunks onto true privacy; no new JSON logic here'})
(w/'production-preimages.json').write_text(json.dumps(rows,indent=2)+'\n')
