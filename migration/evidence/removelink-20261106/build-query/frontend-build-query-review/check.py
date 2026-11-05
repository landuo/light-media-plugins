from pathlib import Path
import importlib.util,subprocess,json,hashlib,tempfile,sys,zipfile,time
r=Path('/Users/accidia/projects/light-media-plugins');w=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();current=r/'scripts/build_plugins.py';test=r/'scripts/test_build_plugins.py';assert sha(current.read_bytes())=='917a1166bd4ecbb155f5cda684213816a194c98bdfd97eea5ede3afa6cfd953e';assert sha(test.read_bytes())=='079791b9ae6afaab6680d969ff9b4683e8e9d6b4408a2605fd0d3493140f5ed6'
old=subprocess.check_output(['git','show','fbddc379789af40528fedac75b0cb193379b7401:scripts/build_plugins.py'],cwd=r);(w/'before.py').write_bytes(old)
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
before=load('builder_before_review',w/'before.py');now=load('builder_current_review',current);front={'entry':'remoteEntry.js','shared':['vue']};source=json.loads((r/'work/sites-review-20261105/frontend-query-addon/source-oracle.json').read_text());queries=[x['query']for x in source['cases']if x['route']=='/static/view.js'];assert len(queries)==12
rows=[]
for q in queries:
 with tempfile.TemporaryDirectory(dir=w,prefix='owned-query-')as name:
  root=Path(name);values={'remoteEntry.js':('export const get=()=>import(new URL('+json.dumps('./view.js'+q)+',import.meta.url).href);const css=new URL('+json.dumps('./style.css'+q)+',import.meta.url);').encode(),'view.js':b'export default {};','style.css':('@import '+json.dumps('./other.css'+q)+';').encode(),'other.css':b'.owned{color:purple}'}
  for n,b in values.items():(root/n).write_bytes(b)
  olderror=None
  try:oldfiles=before.collect_frontend(root,front)
  except before.BuildError as e:olderror=str(e)
  if q:assert olderror is not None
  else:assert oldfiles==values
  actual=now.collect_frontend(root,front);assert actual==values
  output=root/'owned-fixture.zip';now.archive_plugin(output,actual)
  with zipfile.ZipFile(output)as z:
   assert set(z.namelist())==set(values)and len(z.namelist())==len(values)
   assert all(z.read(n)==b for n,b in values.items())
  output.unlink();(root/'view.js').unlink()
  try:now.collect_frontend(root,front);raise AssertionError('missing member accepted')
  except now.BuildError as e:assert 'missing asset: view.js'in str(e)
  rows.append({'query':q,'old_error':olderror,'current_exact_bytes':True,'archive_exact_members_and_bytes':True,'missing_member_rejected':True})
with tempfile.TemporaryDirectory(dir=w,prefix='owned-real-source-')as name:
 root=Path(name);sourcebytes={n:(r/'work/migration-20261105/source-snapshot/removelink/dist/assets'/n).read_bytes()for n in ['remoteEntry.js','view.js','style.css']}
 for n,b in sourcebytes.items():(root/n).write_bytes(b)
 assert now.collect_frontend(root,front)==sourcebytes
 original_source_case={n:sha(b)for n,b in sourcebytes.items()}
negative=[]
for ref in ['https://example.invalid/view.js?v=2.18','//example.invalid/view.js?v=2.18','/view.js?v=2.18','../../outside.js?v=2.18','./view.js#fragment','..\\outside.js?v=2.18']:
 with tempfile.TemporaryDirectory(dir=w,prefix='owned-unsafe-')as name:
  root=Path(name);(root/'remoteEntry.js').write_text('export const get=()=>import('+json.dumps(ref)+');');(root/'view.js').write_text('export default{};')
  try:now.collect_frontend(root,front);raise AssertionError('external/escape accepted '+ref)
  except now.BuildError as e:negative.append({'reference':ref,'rejected':str(e)})
args=['python3','-m','unittest','discover','-s','scripts','-p','test_*.py','-v'];start=time.monotonic();p=subprocess.run(args,cwd=r,capture_output=True);(w/'tool-tests.stdout').write_bytes(p.stdout);(w/'tool-tests.stderr').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode();assert sha(current.read_bytes())=='917a1166bd4ecbb155f5cda684213816a194c98bdfd97eea5ede3afa6cfd953e'
res={'classification':'independent canonical tooling query graph review and synthetic archive tests; original Rlk source JS/CSS bytes consumed, not production ZIP/main/browser acceptance','passed':True,'builder_sha256':sha(current.read_bytes()),'test_sha256':sha(test.read_bytes()),'before_sha256':sha(old),'actual_source_oracle_sha256':sha((r/'work/sites-review-20261105/frontend-query-addon/source-oracle.json').read_bytes()),'query_cases':rows,'original_Rlk_remoteEntry_and_siblings_collect_exactly':original_source_case,'unsafe_references_rejected':negative,'legacy_tool_tests':{'command':args,'exit_code':p.returncode,'seconds':time.monotonic()-start,'stderr_sha256':sha(p.stderr)},'no_product_modules_registry_modified':True,'temporary_owned_asset_trees_and_ZIPs_removed':True};(w/'review-evidence.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'passed':True,'source_query_cases':len(rows),'old_query_rejections':sum(x['old_error']is not None for x in rows),'unsafe_cases':len(negative),'certificate_sha256':sha((w/'review-evidence.json').read_bytes())}))
