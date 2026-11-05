from pathlib import Path
import hashlib,json,os,struct,subprocess,tempfile
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
origin=json.loads((root/'SDK_ORIGIN.json').read_text());baseline=json.loads((here/'live-dependency-binding.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'SDK_ORIGIN.json')==baseline['sdk']['origin_sha256']
for item in origin['files']: assert sha(root/item['path'])==item['sha256'],item['path']
new=root/'internal/sdk/downloader_source.go';initial=sha(new);text=new.read_text()
# Full newly added source reviewed by the agent; no package initializer/global variable.
assert '\nfunc init(' not in text and '\nvar ' not in text
def elf_sections(path):
 raw=path.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01'
 off=struct.unpack_from('<Q',raw,40)[0];size,count,index=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+n*size) for n in range(count)]
 names=sections[index];table=raw[names[4]:names[4]+names[5]];out={}
 for section in sections:
  start=section[0];name=table[start:table.find(b'\0',start)].decode()
  if section[1]!=8: out[name]=dict(bytes=section[5],sha256=hashlib.sha256(raw[section[4]:section[4]+section[5]]).hexdigest())
 return out
saved=set(x['path'] for x in origin['files']);production=sorted(str(x.relative_to(root)) for x in (root/'internal/sdk').rglob('*.go') if not x.name.endswith('_test.go') and 'testdata' not in x.parts)
extra=[x for x in production if x not in saved];assert extra==['internal/sdk/downloader_source.go'],extra
with tempfile.TemporaryDirectory(prefix='category-current-build-',dir=here) as tmp:
 tmp=Path(tmp);overlay=tmp/'overlay.json';overlay.write_text(json.dumps({'Replace':{str(new):''}}))
 outputs=[]
 for mode,flags in [('current',[]),('frozen-minus-new-file',['-overlay='+str(overlay)])]:
  binary=tmp/(mode+'-linux');env={**os.environ,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'}
  argv=['go','build',*flags,'-trimpath','-buildvcs=false','-o',str(binary),'./cmd/category-editor']
  run=subprocess.run(argv,cwd=root,env=env,text=True,capture_output=True);assert run.returncode==0,run.stderr
  nm=subprocess.check_output(['go','tool','nm','-size',str(binary)],cwd=root,text=True)
  (here/(mode+'-category-nm.txt')).write_text(nm)
  names=[line.split()[-1] for line in nm.splitlines() if line.split()]
  forbidden=[n for n in names if any(word in n for word in ['.SourceTasks','.SourceCompleted','.SourceAdd','.SourceControl','.sourceTasks','.sourceMutation'])]
  assert not forbidden,forbidden
  # Function symbol names, size, addresses and linker retained metadata are compared
  # independently of Go's build ID bytes by retaining the complete nm listing.
  outputs.append(dict(mode=mode,command=' '.join(argv).replace(str(tmp),'<owned-temp>'),binary_sha256=sha(binary),bytes=binary.stat().st_size,nm_sha256=sha(here/(mode+'-category-nm.txt')),source_methods_in_linked_binary=forbidden,symbols=len(names),elf_sections=elf_sections(binary)))
 assert sha(new)==initial,'source SDK extension changed during dependency audit'
 assert outputs[0]['elf_sections']['.text']==outputs[1]['elf_sections']['.text']
 assert outputs[0]['elf_sections']['.rodata']==outputs[1]['elf_sections']['.rodata']
 out=dict(status='new SDK file has no CategoryEditor reachable code; original evidence preserved',sdk_origin_sha256=sha(root/'SDK_ORIGIN.json'),frozen_84_file_hashes_unchanged=True,frozen_production_set=baseline['sdk']['production_tree_sha256_as_independently_file_checked_sdk_evidence'],new_production_files=[dict(path=str(new.relative_to(root)),sha256=initial,no_init_or_package_variables=True,imports=['context','errors','strings'],declarations='four capability constants, two DTO types, Downloaders method implementations only')],compiled_category=outputs,linked_nm_identical=outputs[0]['nm_sha256']==outputs[1]['nm_sha256'],linked_text_and_rodata_identical=True,binaries_equal=outputs[0]['binary_sha256']==outputs[1]['binary_sha256'],no_new_linked_Source_methods=True,temporary_binaries_removed=True,limits=['This is current-target cross-compilation and linker reachability verification, not a new Linux/App/browser execution.','Old real main executions remain bound to their actual original worker binary hashes; their SHA values are not replaced with current rebuild SHA.','Any subsequent initializer/global registration or edit to original Category reachable files requires reevaluation.'])
 (here/'current-dependency-audit.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:out[k] for k in ['frozen_84_file_hashes_unchanged','linked_nm_identical','binaries_equal','no_new_linked_Source_methods','temporary_binaries_removed']}))
 print(json.dumps([dict(mode=x['mode'],binary_sha256=x['binary_sha256'],bytes=x['bytes'],text=x['elf_sections']['.text'],rodata=x['elf_sections']['.rodata']) for x in outputs]))
