from pathlib import Path
import ast,hashlib,json
w=Path(__file__).resolve().parent;p=Path('/Users/accidia/projects/light-media-plugins');f=p/'work/migration-20261105/source-snapshot/autosignin/__init__.py';raw=f.read_text();assert hashlib.sha256(raw.encode()).hexdigest()=='1d8329afc00bc218710e302e0eda915351731d41101df08fcf378e90440b9220';tree=ast.parse(raw);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='AutoSignIn');funcs={n.name:n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};names={'get_page'};todo=['get_page']
while todo:
 fn=funcs[todo.pop()]
 for node in ast.walk(fn):
  if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and isinstance(node.func.value,ast.Name)and node.func.value.id in ['self','cls']and node.func.attr in funcs and node.func.attr not in names:names.add(node.func.attr);todo.append(node.func.attr)
body=[]
for node in cls.body:
 if isinstance(node,(ast.Assign,ast.AnnAssign))or isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))and node.name in names:
  import copy
  node=copy.deepcopy(node)
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):node.decorator_list=[d for d in node.decorator_list if isinstance(d,ast.Name)and d.id in ['staticmethod','classmethod']]
  body.append(node)
selected=ast.ClassDef(name='AutoSignIn',bases=[],keywords=[],body=body,decorator_list=[]);selected=ast.unparse(ast.fix_missing_locations(selected))+'\n';(w/'selected-original-getter.py').write_text(selected)
(w/'source-binding.json').write_text(json.dumps({'path':str(f),'sha256':hashlib.sha256(raw.encode()).hexdigest(),'snapshot':'installed270ae0bcbf1d270b916ca9b14f8bffff9b1938d0','functions':{n:[funcs[n].lineno,funcs[n].end_lineno]for n in sorted(names)},'selection':'AST unchanged body/decorator wiring removed; no target/originalapp imported','source_operation':'get_page with only memory reads and synthetic indexer/ORM records'},indent=2)+'\n')
