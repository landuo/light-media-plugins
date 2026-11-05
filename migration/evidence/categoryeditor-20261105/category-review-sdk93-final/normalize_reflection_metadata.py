"""Finite ABI name-pool/reference proof, no binary/production modifications."""
from pathlib import Path
import json,hashlib,subprocess
R=Path(__file__).resolve().parent
v=json.loads((R/'link-delta-diagnosis.json').read_text());a=v['builds']['current'];b=v['builds']['exclude-new-sdk']
# The diagnostic stores every differing byte and12 bytes of context; all five
# records in the90-byte permutation are fully recoverable from these contexts.
d=v['section_delta']['.rodata'];assert d['changed_bytes']==68
roaddr=a['sections']['.rodata']['address'];pool_start=24747;pool_end=24837
contents={mode:{} for mode in ['current','exclude']}
for diff in d['ranges']:
 offset=diff['offset'];lo=max(0,offset-12)
 for mode in contents:
  data=bytes.fromhex(diff[mode+'_surrounding_hex'])
  for index,value in enumerate(data):
   at=lo+index
   if at in contents[mode]:assert contents[mode][at]==value
   contents[mode][at]=value

def read(mode,at,n):return bytes(contents[mode][at+i] for i in range(n))
def varint(mode,at):
 value=0;shift=0;start=at
 while True:
  ch=read(mode,at,1)[0];at+=1;value|=(ch&127)<<shift
  if ch<128:return value,at
  shift+=7;assert at-start<10

def name(mode,at):
 start=at;flags=read(mode,at,1)[0];at+=1;n,at=varint(mode,at);text=read(mode,at,n).decode();at+=n;tag=None
 if flags&2:n,at=varint(mode,at);tag=read(mode,at,n).decode();at+=n
 assert not flags&4
 return {'flags':flags,'name':text,'tag':tag},at-start
records={};offset_to_name={}
for mode in contents:
 cursor=pool_start;records[mode]=[];offset_to_name[mode]={}
 while cursor<pool_end:
  item,size=name(mode,cursor);records[mode].append({'offset':cursor,**item,'bytes':size});offset_to_name[mode][cursor]=item;cursor+=size
 assert cursor==pool_end and len(records[mode])==5
assert sorted(json.dumps({k:v for k,v in item.items() if k not in ['offset']},sort_keys=True) for item in records['current'])==sorted(json.dumps({k:v for k,v in item.items() if k not in ['offset']},sort_keys=True) for item in records['exclude'])
# Two Type.Str nameOff32 values and six abi.Name absolute64 references are the
# only non-pool bytes that differ. Decode rather than normalize arbitrary bytes.
ref_widths={130056:4,182752:8,182776:8,182992:8,229232:8,236656:8,240520:4,267312:8};references=[]
for offset,width in ref_widths.items():
 values={}
 for mode in contents:
  value=int.from_bytes(read(mode,offset,width),'little');target=value if width==4 else value-roaddr
  values[mode]={'encoded':value,'target_offset':target,'resolved':offset_to_name[mode][target]}
 assert values['current']['resolved']==values['exclude']['resolved']
 references.append({'offset':offset,'abi':'Type.Str/nameOff32' if width==4 else 'abi.Name absolute64','width':width,**values})
positions=[]
for diff in d['ranges']:positions.extend(range(diff['offset'],diff['offset']+diff['changed_byte_count']))
assert all(pool_start<=x<pool_end or any(o<=x<o+w for o,w in ref_widths.items()) for x in positions)
# Pointers/lengths in runtime.firstmoduledata move only as required by the cutab.
module=v['section_delta']['.go.module'];assert module['changed_bytes']==9
assert {x['offset'] for x in module['ranges']}=={40,48,56,80,104,128,152,320,328}
module_rows=[]
for diff in module['ranges']:
 off=diff['offset'];lo=max(0,off-12);values={m:int.from_bytes(bytes.fromhex(diff[m+'_surrounding_hex'])[off-lo:off-lo+8],'little') for m in ['current','exclude']}
 assert values['current']-values['exclude']==(4 if off in [40,48] else 16)
 module_rows.append({'offset':off,'current':values['current'],'exclude':values['exclude'],'delta':values['current']-values['exclude']})
# All actual retained text and externally used runtime tables/data are exact.
critical=['.text','.typelink','.itablink','.go.buildinfo','.go.fipsinfo','.noptrdata','.data']
for sec in critical:assert a['sections'][sec]['sha256']==b['sections'][sec]['sha256']
assert v['pc_function_map_difference_count']==0 and v['pc_file_table_difference']=={'only_current':[],'only_exclude':[]}
goroot=Path(subprocess.check_output(['go','env','GOROOT'],text=True).strip());sources=[goroot/'src/internal/abi/type.go',goroot/'src/runtime/symtab.go',goroot/'src/cmd/link/internal/ld/pcln.go']
out={'kind':'finite exact Go1.26.2 ABI interpretation of all68 changed rodata bytes; no arbitrary output normalization','original_rodata_changed_bytes':68,'name_pool_range':[pool_start,pool_end],'name_pool_records':records,'same_encoded_names_tags_and_flags':True,'all8_name_references_resolve_to_identical_semantics':references,'all_changed_rodata_bytes_explained':True,'moduledata_changed_bytes':module['changed_bytes'],'all_moduledata_deltas_are_cutab_size4_or_subsequent_metadata_address16':module_rows,'raw_identical_sections':critical,'pc_functions_checked':v['pc_function_count'],'pc_file_line_maps_identical':True,'file_sets_identical':True,'abi_source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'old_full_nm_and_raw_rodata_equality_not_claimed':True,'code_or_business_inputs_modified':False}
(R/'reflection-metadata-equivalence.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'all68rodata_bytes_explained':True,'names':len(records['current']),'references':len(references),'pc_functions':v['pc_function_count'],'identical_sections':critical}))
