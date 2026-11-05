package app
import("context";"database/sql";"encoding/json";"errors";"net/http";"os";"path/filepath";"testing";"time")
func TestIndependentRemoveLinkActualHistoryManagedAliasSourceContract(t *testing.T){
 a,item:=historyRemovalFixture(t);t.Cleanup(a.closeOriginalSessions);cookie:=setupTestAdmin(t,a)
 authActualInstall(t,a,cookie,os.Getenv("AUTH_RLK_BINARY"))
 cfg,_:=json.Marshal(map[string]any{"enabled":true,"monitor_dirs":filepath.Dir(item.Source)+"\n"+filepath.Dir(item.Target),"delayed_deletion":false,"delete_history":true,"delete_scrap_infos":false,"delete_torrents":false,"notify":false})
 r:=callTest(t,a.Handler(),http.MethodPut,"/api/plugins/RemoveLink",string(cfg),cookie,"");assertOriginalRegistrySuccess(t,r.Code,r.Body.Bytes());
 srcInfo,err:=os.Stat(item.Source);if err!=nil{t.Fatal(err)};dstInfo,err:=os.Stat(item.Target);if err!=nil{t.Fatal(err)};if !os.SameFile(srcInfo,dstInfo){t.Fatal("real import fixture must be an actual same-inode hardlink")};t.Logf("actual import source and target share inode; history=%s",item.ID)
 if err:=os.Remove(item.Source);err!=nil{t.Fatal(err)}
 deadline:=time.Now().Add(8*time.Second);for time.Now().Before(deadline){_,err:=a.transferHistoryItem(context.Background(),item.ID);if errors.Is(err,sql.ErrNoRows){break};time.Sleep(20*time.Millisecond)}
 _,e:=a.transferHistoryItem(context.Background(),item.ID);if !errors.Is(e,sql.ErrNoRows){t.Fatal("real src history delete not reached",e)}
 // Wait for this callback's guard result, rather than claiming callback
 // completion from successful history deletion alone.
 deadline=time.Now().Add(2*time.Second);for time.Now().Before(deadline){if _,e=os.Stat(item.Target);errors.Is(e,os.ErrNotExist){break};time.Sleep(20*time.Millisecond)}
 if _,e=os.Stat(item.Target);!errors.Is(e,os.ErrNotExist){t.Fatalf("SOURCE MISMATCH: real imported history source was removed but managed same-inode target remains: %s (%v); source RemoveLink1246-1274 unlinks this alias",item.Target,e)}
}
