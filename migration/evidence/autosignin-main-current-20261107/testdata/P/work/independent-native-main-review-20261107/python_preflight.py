"""Read-only syntax/global-name check. Does not execute the inspected file."""
from pathlib import Path
import ast,builtins,symtable,json,sys
RUNTIME={'__name__','__file__','__package__','__loader__','__spec__','__cached__','__builtins__','__doc__'}
def inspect_source(text,name):
 try:
  compile(text,name,'exec');tree=ast.parse(text,filename=name);table=symtable.symtable(text,name,'exec')
 except SyntaxError as e:return dict(path=name,syntax_ok=False,error=dict(type=type(e).__name__,line=e.lineno,offset=e.offset,message=e.msg),unbound=[])
 module_bound={s.get_name()for s in table.get_symbols()if s.is_assigned()or s.is_imported()or s.is_parameter()or s.is_namespace()}
 allowed=module_bound|set(vars(builtins))|RUNTIME;rows=[]
 def walk(t,path):
  for s in t.get_symbols():
   if s.is_referenced()and s.is_global()and s.get_name()not in allowed:
    rows.append(dict(symbol=s.get_name(),scope=path,scope_line=t.get_lineno(),load_lines=sorted({n.lineno for n in ast.walk(tree)if isinstance(n,ast.Name)and isinstance(n.ctx,ast.Load)and n.id==s.get_name()})))
  for child in t.get_children():walk(child,path+'/'+child.get_name())
 walk(table,table.get_name())
 return dict(path=name,syntax_ok=True,unbound=rows,limits='static module globals only; conditional assignments, exec/eval/embedded scripts and external subprocess behavior require separate review')
if __name__=='__main__':
 print(json.dumps([inspect_source(Path(p).read_text(),p)for p in sys.argv[1:]],indent=2))
