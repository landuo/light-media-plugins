package main
import("bytes";"encoding/json";"fmt";"go/ast";"go/format";"go/parser";"go/token";"os")
func body(path,name string)*ast.BlockStmt{f,e:=parser.ParseFile(token.NewFileSet(),path,nil,0);if e!=nil{panic(e)};for _,d:=range f.Decls{if x,ok:=d.(*ast.FuncDecl);ok&&x.Name.Name==name{return x.Body}};panic(name)}
func text(n ast.Node)string{var b bytes.Buffer;if e:=format.Node(&b,token.NewFileSet(),n);e!=nil{panic(e)};return b.String()}
func must(v bool,s string){if !v{panic(s)}}
func main(){a:=body(os.Args[1],"browserMutationAllowed");b:=body(os.Args[2],"browserMutationAllowedWithReferences");var stmts []ast.Stmt;var literal ast.Expr;changed:=0
for _,s:=range b.List{if q,ok:=s.(*ast.AssignStmt);ok&&len(q.Lhs)==1{if n,ok:=q.Lhs[0].(*ast.Ident);ok&&n.Name=="query"{must(len(q.Rhs)==1,"query rhs");literal=q.Rhs[0];changed++;continue}}
if q,ok:=s.(*ast.IfStmt);ok&&text(q.Cond)=="!protectReferences"{must(text(q.Body)=="{\n\tquery = `SELECT kind,payload FROM records WHERE kind='import_plan'`\n}","false query");changed++;continue}
if q,ok:=s.(*ast.AssignStmt);ok&&len(q.Lhs)==2{if n,ok:=q.Lhs[0].(*ast.Ident);ok&&n.Name=="rows"{call:=q.Rhs[0].(*ast.CallExpr);must(text(call.Args[1])=="query","rows query");call.Args[1]=literal}}
stmts=append(stmts,s)}
b.List=stmts;must(changed==2,"bounded additions");must(text(a)==text(b),"all other old interactive guard statements differ");wrapper:=body(os.Args[2],"browserMutationAllowed");must(text(wrapper)=="{\n\treturn a.browserMutationAllowedWithReferences(ctx, path, true)\n}","interactive must use true")
c:=text(body(os.Args[3],"originalHostLocalDelete"));d:=text(body(os.Args[4],"originalHostLocalDelete"));d=string(bytes.ReplaceAll([]byte(d),[]byte("browserMutationAllowedWithReferences(ctx, path, false)"),[]byte("browserMutationAllowed(ctx, path)")));must(c==d,"storage all other guards differ")
x,_:=json.Marshal(map[string]any{"old_interactive_body_byte_equivalent_after_only_new_query_selector_removed":true,"public_wrapper_always_true":true,"false_query_exact_import_plan_only":true,"storage_call_only_false_flag_changed_all_other_guards_same":true});fmt.Println(string(x))}
