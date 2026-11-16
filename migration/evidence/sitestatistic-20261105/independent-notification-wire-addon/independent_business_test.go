package sitestatistic
import (
 "bytes"
 "context"
 "encoding/json"
 "math/big"
 "os"
 "reflect"
 "sync"
 "testing"
 "time"
)
func independentBusinessSemantic(raw []byte)any{d:=json.NewDecoder(bytes.NewReader(raw));d.UseNumber();var v any;if e:=d.Decode(&v);e!=nil{panic(e)};var conv func(any)any;conv=func(v any)any{switch x:=v.(type){case json.Number:n,ok:=new(big.Rat).SetString(string(x));if !ok{panic(x)};return struct{Exact string}{n.RatString()};case []any:for i:=range x{x[i]=conv(x[i])};case map[string]any:for k:=range x{x[k]=conv(x[k])}};return v};return conv(v)}
type independentSelectionHost struct{Host;latest,history []Data;active []string;trace []map[string]any}
func(h *independentSelectionHost)Latest(context.Context)([]Data,error){h.trace=append(h.trace,map[string]any{"op":"latest"});return h.latest,nil}
func(h *independentSelectionHost)ActiveDomains(context.Context)([]string,error){h.trace=append(h.trace,map[string]any{"op":"active"});return h.active,nil}
func(h *independentSelectionHost)ByDate(_ context.Context,day string)([]Data,error){h.trace=append(h.trace,map[string]any{"op":"date","date":day});rows:=[]Data{};for _,d:=range h.history{if d["updated_day"]==day{rows=append(rows,d)}};return rows,nil}
func TestIndependentSourceSelectionCallOrder(t *testing.T){
 raw,e:=os.ReadFile("/Users/accidia/projects/light-media-plugins/work/migration-20261105/sitestatistic-preparation/execution/python312-source-oracle.json");if e!=nil{t.Fatal(e)}
 var source struct{Historical,Additional []struct{Name string;Latest,History []Data;Active []string `json:"active_domains"`;Day any;Current,Previous json.RawMessage;Trace []map[string]any}}
 d:=json.NewDecoder(bytes.NewReader(raw));d.UseNumber();if d.Decode(&source)!=nil{t.Fatal("source312 fixture")}
 for _,c:=range append(source.Historical,source.Additional...){t.Run(c.Name,func(t *testing.T){h:=&independentSelectionHost{latest:c.Latest,history:c.History,active:c.Active};s,e:=GetData(context.Background(),h);if e!=nil{t.Fatal(e)}
 for _,pair:=range []struct{got any;want json.RawMessage}{{s.Current,c.Current},{s.Previous,c.Previous}}{a,_:=json.Marshal(pair.got);if !reflect.DeepEqual(independentBusinessSemantic(a),independentBusinessSemantic(pair.want)){t.Fatal("source selected rows changed")}}
 var expected []map[string]any;for _,x:=range c.Trace{if x["op"]=="latest"&&len(expected)>0{break};if x["op"]=="latest"||x["op"]=="active"||x["op"]=="date"{expected=append(expected,x)}}
 a,_:=json.Marshal(h.trace);b,_:=json.Marshal(expected);if !reflect.DeepEqual(independentBusinessSemantic(a),independentBusinessSemantic(b)){t.Fatalf("source read order differs got %s want %s",a,b)}
 })}
}
type independentModeHost struct{Host;receipt any;notices []Notification;trace []string}
func(h *independentModeHost)GetData(context.Context,string)(any,error){h.trace=append(h.trace,"get");return nil,nil}
func(h *independentModeHost)SaveData(_ context.Context,_ string,v any)error{h.trace=append(h.trace,"save");h.receipt=v;return nil}
func(h *independentModeHost)Post(_ context.Context,v Notification)error{h.trace=append(h.trace,"post");h.notices=append(h.notices,v);return nil}
func(h *independentModeHost)Log(context.Context,string,string)error{h.trace=append(h.trace,"log");return nil}
func TestIndependentSourceRealtimeNotificationMode(t *testing.T){
 raw,e:=os.ReadFile("/Users/accidia/projects/light-media-plugins/work/sites-review-20261105/notification-wire-addon/oracle.json");if e!=nil{t.Fatal(e)}
 var source struct{Cases []struct{Name string `json:"case"`;Day string;Current,Previous []Data;Reads []struct{Value any} `json:"mode_reads"`;Notices []struct{Title,Text string};Receipt json.RawMessage `json:"last_notify"`}}
 if json.Unmarshal(raw,&source)!=nil||len(source.Cases)!=2{t.Fatal("actual source mode2")}
 for _,c:=range source.Cases{t.Run(c.Name,func(t *testing.T){index:=2;mode:=func()any{if index>=len(c.Reads){t.Fatal("extra source mode read")};value:=c.Reads[index].Value;index++;return value};h:=&independentModeHost{};now:=func()time.Time{return time.Date(2026,10,16,12,34,56,0,time.UTC)}
 if e:=sendSelected(context.Background(),h,Selected{Day:c.Day,Current:c.Current,Previous:c.Previous},mode,now,new(sync.Mutex));e!=nil{t.Fatal(e)}
 if index!=len(c.Reads)||len(h.notices)!=1||h.notices[0].Title!=c.Notices[0].Title||h.notices[0].Text!=c.Notices[0].Text{t.Fatal("source realtime mode reads/body changed",index,h.notices)}
 got,_:=json.Marshal(h.receipt);if !reflect.DeepEqual(independentBusinessSemantic(got),independentBusinessSemantic(c.Receipt)){t.Fatalf("source receipt changed got %s source %s",got,c.Receipt)}
 if !reflect.DeepEqual(h.trace,[]string{"get","post","save","log"}){t.Fatal("source critical-section effect order",h.trace)}
 })}
}
