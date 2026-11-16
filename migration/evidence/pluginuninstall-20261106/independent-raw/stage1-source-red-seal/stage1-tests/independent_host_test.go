package app

import (
 "context"
 "encoding/json"
 "os"
 "path/filepath"
 "reflect"
 "testing"
 "time"
)

func TestIndependentSameOrderCloneStartupIgnoresInstalledArrayOrder(t *testing.T) {
 outcomes:=[][]bool{}
 for _,ids:=range [][]string{{"PluginUnInstall","PluginUnInstallowned","MPServerStatus"},{"PluginUnInstallowned","PluginUnInstall","MPServerStatus"}} {
  a,cookie:=sourceUninstallFixture(t);ctx:=context.Background()
  r:=callTest(t,a.Handler(),"POST","/api/plugins/PluginUnInstall/clone",`{"suffix":"owned","version":"9.4"}`,cookie,"");assertOriginalRegistrySuccess(t,r.Code,r.Body.Bytes());a.wg.Wait()
  sourceUninstallSave(t,a,"PluginUnInstall",json.RawMessage(`{"plugin_ids":[]}`))
  sourceUninstallSave(t,a,"PluginUnInstallowned",json.RawMessage(`{"plugin_ids":["PluginUnInstall"],"clear_config":true,"clear_data":true}`))
  raw,_:=json.Marshal(ids);if _,e:=a.pluginStore.sourceSetOriginalInstalled(ctx,raw);e!=nil{t.Fatal(e)}
  if e:=a.initializeOriginalPlugins(ctx);e!=nil{t.Fatal(e)};a.wg.Wait()
  _,class:=a.pluginOriginalClasses.Load("PluginUnInstall");_,running:=a.pluginRunningInstances.Load("PluginUnInstall");_,codeErr:=os.Stat(filepath.Join(a.pluginPackageRoot(),"PluginUnInstall"))
  got:=[]bool{class,running,codeErr==nil};outcomes=append(outcomes,got);t.Logf("installed order=%v parent class/running/code=%v",ids,got)
  if e:=a.Close();e!=nil{t.Fatal(e)}
 }
 if !reflect.DeepEqual(outcomes[0],outcomes[1]) {t.Fatal("original selective loader scans same physical package directories before stable equal-order sort; changing only installed membership array order must not change startup effects",outcomes)}
}

func TestIndependentLoadedSelfInitializerReapsOnlyAfterItsSourceTail(t *testing.T) {
 a,cookie:=sourceUninstallFixture(t);v,ok:=a.pluginRunningInstances.Load("PluginUnInstall");if !ok{t.Fatal("missing actual PUI object")};old:=v.(*originalPluginInstance)
 t.Cleanup(func(){ctx,cancel:=context.WithTimeout(context.Background(),3*time.Second);defer cancel();_ = old.closeOriginalSubmittedTransport(ctx)})
 sourceUninstallConfigure(t,a,cookie,"PluginUnInstall",[]string{"PluginUnInstall"},true)
 // Source local object still performs get_state at its init tail. Go then must
 // retire its physical transport, not leave an unregistered process alive.
 deadline:=time.Now().Add(2*time.Second)
 for {
  old.sessionMu.Lock();retired:=old.session==nil;old.sessionMu.Unlock()
  if retired {break}
  if time.Now().After(deadline){t.Fatal("loaded self removal finished source tail but leaked physical Go transport")};time.Sleep(time.Millisecond)
 }
 if !old.stopping.Load(){t.Fatal("retired object remains callable")}
 if _,exists:=a.pluginOriginalClasses.Load("PluginUnInstall");exists{t.Fatal("source class retained")}
 if _,exists:=a.pluginRunningInstances.Load("PluginUnInstall");exists{t.Fatal("loaded reinit incorrectly reinserted self")}
}

func TestIndependentFailedInstalledWriteLocalMetadataUsesSourceCache(t *testing.T) {
 a,_:=sourceUninstallFixture(t);ctx:=context.Background()
 sourceUninstallSave(t,a,"MPServerStatus",json.RawMessage(`{"enable":true,"retain":"source future"}`))
 sourceUninstallSave(t,a,"PluginUnInstall",json.RawMessage(`{"plugin_ids":["MPServerStatus"],"clear_config":true,"clear_data":true}`))
 if _,e:=a.pluginStore.sourceSetOriginalInstalled(ctx,json.RawMessage(`["PluginUnInstall","MPServerStatus"]`));e!=nil{t.Fatal(e)}
 if _,e:=a.Store.DB.Exec(`CREATE TRIGGER independent_uninstall_reject BEFORE UPDATE ON records WHEN NEW.kind='plugin-original-installed-order-v1' BEGIN SELECT RAISE(FAIL,'independent source cache fault'); END`);e!=nil{t.Fatal(e)}
 if e:=a.initializeOriginalPlugins(ctx);e!=nil{t.Fatal(e)};a.wg.Wait()
 ids,e:=a.originalInstalledPluginIDs(ctx);if e!=nil||len(ids)!=1||ids[0]!="PluginUnInstall"{t.Fatal("source failed write cache boundary not reached",ids,e)}
 if _,ok:=a.pluginRunningInstances.Load("MPServerStatus");!ok{t.Fatal("preimported future class did not reach running")}
 stored,e:=a.pluginStore.Installation(ctx,"MPServerStatus");if e!=nil||!stored.Installed{t.Fatal("source DB must remain old after failed write",stored,e)}
 cards,e:=a.originalLocalPluginCards(ctx,false);if e!=nil{t.Fatal(e)}
 found:=false;for _,card:=range cards {if card.InstanceID=="MPServerStatus"{found=true;if card.Installed{t.Error("source get_local_plugins uses copied process UserInstalledPlugins cache; target exposes stale SQL installed=true on preimported future ghost")};break}}
 if !found{t.Fatal("source imported future class metadata missing")}
 version,present,e:=a.originalLocalPluginVersion(ctx,"MPServerStatus");if e!=nil||present{t.Errorf("source get_local_plugin_version also gates on cache, expected absent; Go present=%v version=%s error=%v",present,version,e)}
}
