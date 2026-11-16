from pathlib import Path
import json,hashlib,os,subprocess,tempfile,struct
R=Path(__file__).resolve().parent;root=R.parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
origin=json.loads((root/'SDK_ORIGIN.json').read_text());old=json.loads((root/'work/migration-20261105/sdk/source-target-proof.json').read_text());base={x['path'] for x in old['files']};new=[x['path'] for x in origin['files'] if x['path'] not in base]
def sections(raw):
 offset=struct.unpack_from('<Q',raw,40)[0];size,count,index=struct.unpack_from('<HHH',raw,58);rows=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+n*size) for n in range(count)];names=rows[index];table=raw[names[4]:names[4]+names[5]]
 return {table[x[0]:table.find(b'\0',x[0])].decode():{'address':x[3],'offset':x[4],'bytes':x[5],'sha256':sha(raw[x[4]:x[4]+x[5]]),'data':raw[x[4]:x[4]+x[5]]} for x in rows if x[1]!=8}
def symbols(text):return {parts[3]:{'address':int(parts[0],16),'bytes':int(parts[1]),'kind':parts[2]} for x in text.splitlines() for parts in [x.split(maxsplit=3)] if len(parts)==4}
with tempfile.TemporaryDirectory(prefix='owned-sdk93-diagnosis-',dir=R) as temp:
 temp=Path(temp);overlay=temp/'excluded.json';overlay.write_text(json.dumps({'Replace':{str(root/p):'' for p in new}}));env={**os.environ,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'};builds={};paths=[]
 for mode,flags in [('current',[]),('exclude-new-sdk',['-overlay='+str(overlay)])]:
  binary=temp/(mode+'-linux');cmd=['go','build',*flags,'-trimpath','-buildvcs=false','-o',str(binary),'./cmd/category-editor'];r=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr
  raw=binary.read_bytes();nm=subprocess.check_output(['go','tool','nm','-size',str(binary)],cwd=root,text=True);paths.append(str(binary));builds[mode]={'binary_sha256':sha(raw),'bytes':len(raw),'sections':sections(raw),'symbols':symbols(nm),'nm_sha256':sha(nm.encode())}
  (R/(mode+'-nm.txt')).write_text(nm)
 semantic=json.loads(subprocess.check_output(['go','run',str(R/'_tools/elfinspect.go'),'--',*paths],cwd=root,text=True));a,b=builds['current'],builds['exclude-new-sdk'];differences={}
 for n,s in a['sections'].items():
  other=b['sections'][n]
  if s['data']==other['data']:continue
  if len(s['data'])==len(other['data']):
   positions=[i for i,(x,y) in enumerate(zip(s['data'],other['data'])) if x!=y];groups=[]
   for i in positions:
    if groups and i<=groups[-1][-1]+1:groups[-1].append(i)
    else:groups.append([i])
   if len(positions)<=200:
    ranges=[]
    for group in groups:
     lo=max(0,group[0]-12);hi=min(len(s['data']),group[-1]+13);addr=s['address']+group[0]
     hits=[{'name':name,**value} for name,value in a['symbols'].items() if value['address']<=addr<value['address']+max(value['bytes'],1)]
     ranges.append({'offset':group[0],'address':addr,'changed_byte_count':len(group),'current_surrounding_hex':s['data'][lo:hi].hex(),'exclude_surrounding_hex':other['data'][lo:hi].hex(),'containing_symbols':hits})
   else:ranges=None
   differences[n]={'current_sha256':s['sha256'],'exclude_sha256':other['sha256'],'bytes':len(s['data']),'changed_bytes':len(positions),'ranges':ranges}
  else:differences[n]={'current_bytes':len(s['data']),'exclude_bytes':len(other['data'])}
 funcs0={x['name']:x for x in semantic[0]['functions']};funcs1={x['name']:x for x in semantic[1]['functions']}
 semantic_diff={name:{'current':funcs0.get(name),'exclude':funcs1.get(name)} for name in funcs0.keys()|funcs1.keys() if funcs0.get(name)!=funcs1.get(name)}
 file_delta={'only_current':sorted(set(semantic[0]['files'])-set(semantic[1]['files'])),'only_exclude':sorted(set(semantic[1]['files'])-set(semantic[0]['files']))}
 out={'kind':'LinuxELF raw section + debug/gosym actual PC→file/line semantics, current SDK93 vs deletion overlay of9 new SDK files','environment':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'},'builds':{n:{**v,'sections':{k:{x:y for x,y in item.items() if x!='data'} for k,item in v['sections'].items()}} for n,v in builds.items()},'section_delta':differences,'pc_function_count':len(funcs0),'pc_function_map_difference_count':len(semantic_diff),'pc_function_map_difference':semantic_diff,'pc_file_table_difference':file_delta,'pc_file_table_counts':[len(x['files']) for x in semantic],'temporary_binaries_removed':True}
 (R/'link-delta-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n');(R/'pc-file-line-maps.json').write_text(json.dumps(semantic,indent=2)+'\n');print(json.dumps({'text_equal':a['sections']['.text']['data']==b['sections']['.text']['data'],'section_differences':{k:{x:y for x,y in v.items() if x!='ranges'} for k,v in differences.items()},'pc_map_differences':len(semantic_diff),'file_delta':file_delta},indent=2))
