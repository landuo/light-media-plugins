package removelink
import("os";"os/user";"testing")
func TestIndependentUnmappedCurrentUIDHomeDoesNotBecomeRoot(t *testing.T){
 if _,present:=os.LookupEnv("HOME");present{t.Fatal("requires genuinely absent HOME")}
 if _,err:=user.Current();err==nil{t.Fatal("requires unresolved current UID")}else{t.Logf("current UID resolution error: %v",err)}
 p:=NewPlugin();var recovered any;var value string
 func(){defer func(){recovered=recover()}();value=normalized("~",p.machine.Home)}()
 t.Logf("NewPlugin Home=%q normalized(~)=%q panic=%v",p.machine.Home,value,recovered)
 if recovered==nil{t.Fatal("actual3.12 Path.expanduser requires RuntimeError when HOME absent and passwd UID missing")}
}
