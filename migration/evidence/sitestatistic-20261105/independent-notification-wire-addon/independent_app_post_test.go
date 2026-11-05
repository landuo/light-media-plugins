package app

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "os/exec"
 "reflect"
 "sync"
 "testing"
 "time"

 "light-media/internal/plugins"
)

// The actual Site business worker talks to real App Base/Post/SQLite. Only
// source-account resources and invocation authority are synthetic boundaries.
func TestIndependentActualSiteWorkerNativePostAndReceipt(t *testing.T) {
 binary:=os.Getenv("INDEPENDENT_SITE_WORKER_BINARY");if binary==""{t.Fatal("actual separately compiled business worker required")}
 raw,e:=exec.Command(binary,"--manifest").Output();if e!=nil{t.Fatal(e)};var m plugins.Manifest;if json.Unmarshal(raw,&m)!=nil||m.PluginID!="SiteStatistic"{t.Fatal("actual Site worker manifest")}
 enumRaw,e:=os.ReadFile("/Users/accidia/projects/light-media-plugins/work/sites-review-20261105/notification-wire-addon/source-enum-oracle.json");if e!=nil{t.Fatal(e)};var source struct{Value string};if json.Unmarshal(enumRaw,&source)!=nil||source.Value!="站点"{t.Fatal("actual source enum")}
 a:=newTestApp(t);setupTestAdmin(t,a);ctx,cancel:=context.WithTimeout(context.Background(),30*time.Second);defer cancel()
 identity:=plugins.Identity{PluginID:m.PluginID,InstanceID:"SiteStatisticWireSynthetic",Version:m.Version}
 client,e:=(plugins.Runner{Timeout:5*time.Second,ConcurrentCalls:true,RequireConcurrent:true}).Start(ctx,plugins.Command{Path:binary},m,plugins.SessionBinding{Identity:identity,Generation:1});if e!=nil{t.Fatal(e)}
 defer func(){c,x:=context.WithTimeout(context.Background(),3*time.Second);defer x();_ =client.Stop(c)}()
 in:=PluginInstallation{PluginID:m.PluginID,InstanceID:identity.InstanceID,Version:m.Version,Generation:1}
 object:=&originalPluginInstance{app:a,installation:in,manifest:m,session:client,external:true,hostContract:pluginResourcesSDKContract}
 scope:=originalBaseCallScope{object:object,installation:in,phase:"send_msg",validate:func(c context.Context)error{return c.Err()}}
 var host plugins.HostHandler;var children sync.WaitGroup;var mu sync.Mutex;posts:=[]json.RawMessage{};childErrors:=[]error{}
 host=func(c context.Context,id plugins.Identity,method string,payload json.RawMessage)(json.RawMessage,error){
  if id!=identity{return nil,errors.New("synthetic test identity mismatch")}
  switch method {
  case plugins.BackgroundSubmitCapability:
   var next struct{Method string;Payload json.RawMessage};if e:=json.Unmarshal(payload,&next);e!=nil{return nil,e};pending,e:=client.StartCallWithAdmission(c,ctx,next.Method,next.Payload,host,plugins.CallOptions{CallerDeadlineOnly:true});if e!=nil{return nil,e};children.Add(1);go func(){defer children.Done();_,e:=pending.Wait();if e!=nil{mu.Lock();childErrors=append(childErrors,e);mu.Unlock()}}();return json.RawMessage(`{"accepted":true}`),nil
  case plugins.SitesSourceAccountsCapability:
   var request plugins.SiteAccountHostRequestV1;if e:=json.Unmarshal(payload,&request);e!=nil{return nil,e};items:=[]plugins.SiteAccountHostRowV1{}
   if request.Latest{fields,_:=json.Marshal(map[string]any{"id":1,"domain":"owned.invalid","name":"Owned wire","updated_day":time.Now().Format("2006-01-02"),"upload":json.RawMessage(`8.589934592e+09`),"download":json.RawMessage(`2.147483648e+09`),"err_msg":""});items=append(items,plugins.SiteAccountHostRowV1{SiteID:"owned",Fields:fields})}
   return json.Marshal(plugins.SiteAccountHostResultV1{SchemaVersion:1,Items:items})
  case plugins.SitesReadCapability:return json.Marshal(plugins.SiteHostResultV1{SchemaVersion:1,Items:[]plugins.SiteHostRowV1{{ID:"owned",Domain:"owned.invalid",Name:"Owned wire",Enabled:true}}})
  case plugins.BaseGetData,plugins.BaseSaveData:return a.pluginOriginalBaseHost(c,scope,id,method,payload)
  case plugins.PostMessageCapability:
   var fields map[string]json.RawMessage;if e:=json.Unmarshal(payload,&fields);e!=nil{return nil,e};var actual string;if json.Unmarshal(fields["mtype"],&actual)!=nil{return nil,errors.New("invalid business notification type JSON")}
   mu.Lock();posts=append(posts,append(json.RawMessage(nil),payload...));mu.Unlock();result,e:=a.originalPostMessageResource(c,scope,payload);if e!=nil { var native *APIError; if errors.As(e,&native) {t.Logf("native_post_rejection_code=%s",native.Code)} };if actual!=source.Value && e==nil{return nil,errors.New("native accepted wire type differing from actual source enum")};return result,e
  case plugins.LogWriteCapability:return json.RawMessage(`null`),nil
  }
  return nil,errors.New("unexpected synthetic resource "+method)
 }
 call:=func(method string,input any)error{raw,e:=json.Marshal(input);if e!=nil{t.Fatal(e)};_,e=client.CallWithOptions(ctx,method,raw,host,plugins.CallOptions{CallerDeadlineOnly:true});return e}
 if e:=call("init",map[string]any{"enabled":true,"notify_type":"total","dashboard_type":"all","onlyonce":false});e!=nil{t.Fatal(e)}
 event:=map[string]any{"type":"site.refreshed","data":map[string]any{"site_id":"*"}}
 if e:=call("send_msg",event);e!=nil{t.Fatal("actual business worker→real App post failed",e)}
 children.Wait();mu.Lock();if len(childErrors)!=0||len(posts)!=1{t.Fatal("source cursor/post count",childErrors,len(posts))};post:=append(json.RawMessage(nil),posts[0]...);mu.Unlock()
 var notice map[string]any;if json.Unmarshal(post,&notice)!=nil{t.Fatal("wire notice")};sum:=sha256.Sum256([]byte(notice["text"].(string)))
 key:="last_notify";stored,e:=a.pluginStore.originalBaseGetData(ctx,identity.InstanceID,&key);if e!=nil{t.Fatal(e)};var receipt map[string]any;if json.Unmarshal(stored,&receipt)!=nil||receipt["fingerprint"]!=hex.EncodeToString(sum[:])||receipt["type"]!="total"{t.Fatalf("actual persistent receipt missing: %s %v",stored,e)}
 var before int;if e:=a.Store.DB.QueryRow(`SELECT count(*) FROM records WHERE kind='notification'`).Scan(&before);e!=nil||before!=1{t.Fatal("real native notice not saved once",before,e)}
 if e:=call("send_msg",event);e!=nil{t.Fatal(e)};children.Wait();var after int;if e:=a.Store.DB.QueryRow(`SELECT count(*) FROM records WHERE kind='notification'`).Scan(&after);e!=nil||after!=before{t.Fatal("same worker did not dedupe",after,e)}
 again,e:=a.pluginStore.originalBaseGetData(ctx,identity.InstanceID,&key);if e!=nil||!reflect.DeepEqual(stored,again){t.Fatal("dedupe receipt changed",string(again),e)}
}
