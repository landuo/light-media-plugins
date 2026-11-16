package main
import("bytes";"crypto/sha256";"debug/elf";"encoding/json";"fmt";"os";"path/filepath";"reflect";"strings")
func must(ok bool,msg string){if !ok{panic(msg)}}
func digest(b []byte)string{return fmt.Sprintf("%x",sha256.Sum256(b))}
func main(){
 root:="/Users/accidia/projects/light-media-plugins";var rows []struct{ID string `json:"id"`;Artifact string `json:"artifact"`;SHA string `json:"sha256"`};b,e:=os.ReadFile(filepath.Join(root,"work/parallel-sdk-sync-20261106/linux-consumer-builds.json"));if e!=nil{panic(e)};if e=json.Unmarshal(b,&rows);e!=nil{panic(e)}
 observations:=[]map[string]any{}
 for _,r:=range rows{if strings.HasSuffix(r.ID,"-update"){continue};next:=filepath.Join(root,"work/source-public-get-unused-consumers-20261106",r.ID+"-linux");before,e:=os.ReadFile(r.Artifact);if e!=nil{panic(e)};after,e:=os.ReadFile(next);if e!=nil{panic(e)};must(digest(before)==r.SHA,"old hash");must(len(before)==len(after),"file size")
  a,e:=elf.Open(r.Artifact);if e!=nil{panic(e)};z,e:=elf.Open(next);if e!=nil{panic(e)};must(reflect.DeepEqual(a.FileHeader,z.FileHeader),"ELF header");must(len(a.Sections)==len(z.Sections),"section count");must(len(a.Progs)==len(z.Progs),"program count");for i,p:=range a.Progs{must(p.ProgHeader==z.Progs[i].ProgHeader,"program header")}
  maskA:=append([]byte(nil),before...);maskB:=append([]byte(nil),after...);changed:=[]string{};noteRows:=[]map[string]any{}
  for i,sa:=range a.Sections{sb:=z.Sections[i];must(sa.SectionHeader==sb.SectionHeader,"section metadata");x,e:=sa.Data();if e!=nil&&sa.Type!=elf.SHT_NOBITS{panic(e)};y,e:=sb.Data();if e!=nil&&sb.Type!=elf.SHT_NOBITS{panic(e)};if !bytes.Equal(x,y){changed=append(changed,sa.Name)}
   if sa.Name!=".note.go.buildid"&&sa.Name!=".note.gnu.build-id"{must(bytes.Equal(x,y),"nonprovenance section differs: "+sa.Name);continue}
   must(sa.Type==elf.SHT_NOTE,"not NOTE");must(sa.Flags&(elf.SHF_EXECINSTR|elf.SHF_WRITE)==0,"note executable or writable");must(sa.Offset+sa.FileSize<=uint64(len(before)),"note range")
   for j:=sa.Offset;j<sa.Offset+sa.FileSize;j++{maskA[j]=0;maskB[j]=0}
   noteRows=append(noteRows,map[string]any{"name":sa.Name,"flags":sa.Flags.String(),"offset":sa.Offset,"file_size":sa.FileSize,"before_sha256":digest(x),"after_sha256":digest(y)})
  }
  must(bytes.Equal(maskA,maskB),"outside note bytes differ");must(len(changed)==2,"exact2sections");count:=0;for i:=range before{if before[i]!=after[i]{count++}}
  oldInfo,e:=a.DWARF();must(e==nil&&oldInfo!=nil,"old debug info readable");newInfo,e:=z.DWARF();must(e==nil&&newInfo!=nil,"new debug info readable");a.Close();z.Close();observations=append(observations,map[string]any{"id":r.ID,"before_path":r.Artifact,"after_path":next,"before_sha256":digest(before),"after_sha256":digest(after),"bytes":len(before),"full_ELF_equal":bytes.Equal(before,after),"different_sections":changed,"different_bytes":count,"all_bytes_outside_two_notes_equal":true,"program_headers_equal":true,"all_section_headers_equal":true,"dwarf_readable_both":true,"notes":noteRows})
 }
 out,_:=json.MarshalIndent(observations,"","  ");fmt.Println(string(out))
}
