import pathlib,json,hashlib,subprocess,tarfile
R=pathlib.Path('/Users/accidia/projects/light-media-plugins');H=pathlib.Path('/Users/accidia/projects/light-media');O=R/'work/sites-review-20261105/site-final-composite';T=R/'work/migration-20261105/sitestatistic-runtime'
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
f=load(R/'SDK_ORIGIN.json');items=f['files'];refs=[f['source_commit']+':'+x['source_path'] for x in items];raw=subprocess.run(['git','-C',str(H),'cat-file','--batch'],input=('\n'.join(refs)+'\n').encode(),stdout=subprocess.PIPE,check=True).stdout;off=0;rows=[]
for row in items:
 end=raw.index(b'\n',off);a=raw[off:end].decode().split();assert a[1]=='blob';size=int(a[2]);b=raw[end+1:end+1+size];off=end+2+size;source=b
 for c in f['allowed_changes']:b=b.replace(c['from'].encode(),c['to'].encode())
 p=R/row['path'];actual=p.read_bytes();rows.append({'path':row['path'],'source_path':row['source_path'],'actual_sha256':sh(p),'declared_sha256':row['sha256'],'matches_declared':sh(p)==row['sha256'],'source_blob_sha256':hashlib.sha256(source).hexdigest(),'declared_source_sha256':row['source_sha256'],'matches_declared_source':hashlib.sha256(source).hexdigest()==row['source_sha256'],'whole_bytes_equal_after_only_declared_relocations':b==actual})
assert off==len(raw)
# Binary BOM + all linked external module versions/sums against captured build dependency list.
binding=load(T/'host-build-source-binding.json');deps={x['Path']:x for x in binding['module_dependencies']};boms=[]
prior=load(O/'input-verification.json')
observed_worker={'classification':'reviewer actual go version -m base worker invocation before cleanup; structured transcription of tool result, not a claimed newly captured raw stdout','path':'github.com/landuo/light-media-plugins/cmd/site-statistic','version':'go1.26.2','dep':{'path':'golang.org/x/text','version':'v0.43.0','sum':'h1:1QivrlhwAsnMOcqgOdl9my7s9OyZl8O5/UGUTJVXoWc='},'flags':['-buildmode=exe','-compiler=gc','-trimpath=true','CGO_ENABLED=0','GOARCH=amd64','GOOS=linux','GOAMD64=v1']}
(O/'worker-buildinfo-observation.json').write_text(json.dumps(observed_worker,indent=2)+'\n')
s=(T/'host-buildinfo.txt').read_text();(O/'host-buildinfo-reused.txt').write_text(s);linked=[]
for line in s.splitlines():
 fields=line.split('\t')
 if len(fields)>=4 and fields[1]=='dep':
  mod,ver=fields[2:4];checksum=fields[4] if len(fields)>4 else'';dep=deps.get(mod);ok=dep is not None and dep.get('Version')==ver
  if checksum:ok=ok and dep.get('Sum')==checksum
  linked.append({'path':mod,'version':ver,'sum':checksum,'in_host_frozen_module_graph':ok,'local_replacement':dep.get('Replace') if dep else None})
boms.append({'binary':'light-media-site-host-linux','sha256':prior['host_binary'][0]['actual'],'classification':'Root retained raw buildinfo, body independently observed via actual go version -m before cleanup','buildinfo_sha256':sh(O/'host-buildinfo-reused.txt'),'linked_external_modules':linked,'pure_go_linux_amd64':all(x in s for x in ['CGO_ENABLED=0','GOOS=linux','GOARCH=amd64'])})
x=observed_worker['dep'];x['in_host_frozen_module_graph']=deps[x['path']]['Version']==x['version'] and deps[x['path']]['Sum']==x['sum']
boms.append({'binary':'site-statistic-enum-fixed-linux','sha256':prior['binaries'][0]['actual'],'classification':observed_worker['classification'],'linked_external_modules':[x],'pure_go_linux_amd64':True})
boms.append({'binary':'site-statistic-update-enum-fixed-linux','sha256':prior['binaries'][1]['actual'],'classification':'binary hash independently verified; closure reused identical62SDK/module/40source except manifest-version-only overlay, not a separate executed update BOM command','linked_external_modules':[x],'pure_go_linux_amd64':True})
m=load(T/'main-harvest-manifest.json');harvest=[{'path':p,'sha256':sh(T/'harvest'/p),'matches':sh(T/'harvest'/p)==h} for p,h in m['files'].items()];archive=T/'main-all-raw.tar.gz';assert sh(archive)==m['archive_sha256']
with tarfile.open(archive,'r:gz') as tar:
 ar={x.name:hashlib.sha256(tar.extractfile(x).read()).hexdigest() for x in tar.getmembers() if x.isfile()}
# Archive paths include its harvest root (do not extract).
archive_matches={p:any(k.endswith('/'+p) or k==p for k,v in ar.items() if v==h) for p,h in m['files'].items()}
result={'classification':'independent95SDK bytes/declared-only-relocations, ELF buildinfo module BOM,25raw/archived body integrity; no binary execution','sdk_origin_sha256':sh(R/'SDK_ORIGIN.json'),'sdk_source_commit':f['source_commit'],'sdk_files':rows,'boms':boms,'host_local_replacement_covered_by_repository_inputs':any(p.startswith('third_party/go-dateparser/') for p in binding['repository_inputs']),'host_repository_input_count':len(binding['repository_inputs']),'harvest25':harvest,'archive_sha256':sh(archive),'archive_all25_raw_hashes_match':all(archive_matches.values()),'archive_file_count':len(ar)}
(O/'closure-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert len(rows)==95 and all(x['matches_declared'] and x['matches_declared_source'] and x['whole_bytes_equal_after_only_declared_relocations'] for x in rows)
assert all(x['matches'] for x in harvest) and all(archive_matches.values())
assert all(x['in_host_frozen_module_graph'] for bom in boms for x in bom['linked_external_modules'])
print(json.dumps({'sdk_files':len(rows),'harvest_files':len(harvest),'archive_files':len(ar),'linked_external_modules':[len(x['linked_external_modules']) for x in boms],'allchecks':True}))
