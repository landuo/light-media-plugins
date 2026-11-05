package main
import (
 "crypto/sha256"
 "debug/elf"
 "debug/gosym"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "sort"
)
func main(){
 out:=[]map[string]any{}
 for _,p:=range os.Args[1:]{ if p=="--"{continue}; f,e:=elf.Open(p);if e!=nil{panic(e)}
  raw,e:=f.Section(".gopclntab").Data();if e!=nil{panic(e)}
  line:=gosym.NewLineTable(raw,f.Section(".text").Addr);tab,e:=gosym.NewTable(nil,line);if e!=nil{panic(e)}
  files:=[]string{};for file:=range tab.Files{files=append(files,file)};sort.Strings(files)
  funcs:=[]map[string]any{}
  for _,fn:=range tab.Funcs{
   h:=sha256.New();lastFile:="";lastLine:=-1;segments:=0
   for pc:=fn.Entry;pc<fn.End;pc++{file,n,_:=tab.PCToLine(pc);if file!=lastFile||n!=lastLine{fmt.Fprintf(h,"%d:%s:%d\n",pc-fn.Entry,file,n);lastFile,lastLine=file,n;segments++}}
   funcs=append(funcs,map[string]any{"name":fn.Name,"entry":fn.Entry,"end":fn.End,"pc_file_line_sha256":hex.EncodeToString(h.Sum(nil)),"line_segments":segments})
  }
  out=append(out,map[string]any{"binary":p,"files":files,"functions":funcs});f.Close()
 }
 if e:=json.NewEncoder(os.Stdout).Encode(out);e!=nil{panic(e)}
}
