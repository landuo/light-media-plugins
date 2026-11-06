from pathlib import Path
import json,hashlib,subprocess,re
P=Path.cwd();H=Path('/Users/accidia/projects/light-media');w=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=P/'work/autosignin-source-timeout-refinement-20261106';o=json.loads((base/'overlay.json').read_text())['Replace']
cookie=P/'work/autosignin-source-cookie-override-refinement-20261106';rousi=P/'work/source-rousi-credentials-20261106'
binding=w/'source_site_binding.go';m=subprocess.run(['git','merge-file','-p',str(cookie/'candidate/source_site_binding.go'),str(base/'candidate/source_site_binding.go'),str(rousi/'candidate/source_site_binding.go')],capture_output=True);assert m.returncode==0,m.stdout.decode();binding.write_bytes(m.stdout)
o[str(P/'plugins/autosignin/source_site_binding.go')]=str(binding)
for source in [cookie/'worker-test-overlay.json',rousi/'worker-overlay.json']:
    for k,v in json.loads(source.read_text())['Replace'].items():
        if k.endswith('_test.go') and '/plugins/autosignin/'in k and k not in o:o[k]=v
o={k:v for k,v in o.items()if '/internal/sdk/'not in k}
# Synchronize the already-owned SDK snapshot, plus only the new source-site DTO.
origin=json.loads((P/'SDK_ORIGIN.json').read_text());source_rows=origin['files']+[{'source_path':'internal/plugins/site_source_request.go','path':'internal/sdk/site_source_request.go'}]
reloc=[(b'light-media/internal/plugins',b'github.com/landuo/light-media-plugins/internal/sdk'),(b'light-media/internal/sourcejson',b'github.com/landuo/light-media-plugins/internal/sdk/sourcejson')]
outputs={};provenance=[]
for r in source_rows:
    src=H/r['source_path'];out=src.read_bytes()
    for a,b in reloc:out=out.replace(a,b)
    target=P/r['path']
    if not target.exists()or target.read_bytes()!=out:outputs[target]=out;provenance.append({'target':str(target),'source':str(src),'source_sha256':sha(src),'kind':'SDK two declared import relocations only'})
for k,v in o.items():
    target=Path(k)
    assert target.is_relative_to(P/'plugins/autosignin'),target
    outputs[target]=Path(v).read_bytes()if v else None
    provenance.append({'target':k,'source':v,'source_sha256':sha(Path(v))if v else None,'kind':'independently reviewed composed core/timeout/order/Cookie/RouSi/API; deletion is old replaced typed regex frontend'})
# Retain source-derived test inputs in the repository; tests must not depend on
# a developer's ignored work directory or absolute home path.
tests={p:b for p,b in outputs.items()if p.name.endswith('_test.go')and b is not None};all_strings=[]
for b in tests.values():all_strings+=re.findall(rb'"([^"\n]*)"',b)
roots={};fixture_rows=[]
for target,b in list(tests.items()):
    for raw in re.findall(rb'"(/Users/accidia/[^"\n]*)"',b):
        text=raw.decode();src=Path(text)
        if src.is_dir():root=src
        else:assert src.is_file(),src;root=src.parent
        roots[str(root)]=root
for root in roots.values():
    candidates=set()
    for raw in all_strings:
        text=raw.decode(errors='ignore');p=Path(text)
        if text.startswith(str(root))and p.is_file():candidates.add(p)
        elif '/'not in text and text.endswith(('.json','.stdout'))and(root/text).is_file():candidates.add(root/text)
    for src in candidates:
        dest=P/'plugins/autosignin/testdata/source-oracles'/root.name/src.name
        assert dest not in outputs or outputs[dest]==src.read_bytes(),dest
        outputs[dest]=src.read_bytes();fixture_rows.append({'source':str(src),'target':str(dest.relative_to(P)),'sha256':sha(src),'classification':'original source observation copied byte-exact; assertion values unchanged'})
for target,b in list(tests.items()):
    prefix='../testdata/source-oracles/'if target.parent.name=='pyregex'else'testdata/source-oracles/'
    for raw,root in roots.items():b=b.replace((raw+'/').encode(),(prefix+root.name+'/').encode())
    assert b'/Users/accidia/'not in b,target
    outputs[target]=b
# Only the image codecs are a new external Go requirement. The regexp engine is
# already vendored privately with its original MIT/ATTRIB notices.
mod=(P/'go.mod').read_text();assert 'golang.org/x/image'not in mod;outputs[P/'go.mod']=mod.replace('\tgolang.org/x/net','\tgolang.org/x/image v0.24.0\n\tgolang.org/x/net').encode()
sm=(P/'go.sum').read_text();extra=[l for l in(base.parent/'migration-20261105/autosignin-implementation-20261106/autosignin.sum').read_text().splitlines()if l.startswith('golang.org/x/image v0.24.0')]
assert len(extra)==2;outputs[P/'go.sum']=('\n'.join(sorted(set(sm.splitlines()+extra)))+'\n').encode()
plan=[]
for target,out in sorted(outputs.items()):
    previous=target.read_bytes()if target.exists()else None
    if previous==out:continue
    rel=target.relative_to(P);backup=w/'preimage'/rel
    if previous is not None:backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(previous)
    plan.append({'target':str(rel),'preimage_sha256':hashlib.sha256(previous).hexdigest()if previous is not None else None,'new_sha256':hashlib.sha256(out).hexdigest()if out is not None else None,'delete_old_frontend':out is None})
(w/'application-plan.json').write_text(json.dumps({'status':'apply composed implementation; fullApp/Main/UI unaccepted','scope':'No registry publication or private import. Root2 timeout/order+Cookie3+RouSi4+API2 composed atop already independently reviewed908/7716/TEMP/notice','files':plan,'provenance':provenance,'fixture_copies':fixture_rows,'SDK_origin_metadata':'pending exact host saved code commit and standalone validation; oldSDK_ORIGIN retained until updated'},indent=2)+'\n')
for row in plan:
    target=P/row['target'];assert (sha(target)if target.exists()else None)==row['preimage_sha256'];out=outputs[target]
    if out is None:target.unlink()
    else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(out)
print(json.dumps({'applied_files':len(plan),'deleted_old_replaced_frontend':sum(r['delete_old_frontend']for r in plan),'source_oracles':len(fixture_rows),'binding_sha256':sha(binding),'plan_sha256':sha(w/'application-plan.json')}))
