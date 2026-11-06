from pathlib import Path
import hashlib,json,os,shutil,subprocess,time,sys

P=Path('/Users/accidia/projects/light-media-plugins');H=P.parent/'light-media';W=Path(__file__).resolve().parent
ENV=dict(os.environ,GOOS='linux',GOARCH='amd64',CGO_ENABLED='0',GOFLAGS='',GOPROXY='off')
PLANS=[
    ('host',H,'./cmd/server',None,False),
    ('worker',P,'./cmd/auto-sign-in',None,False),
    ('worker-updated',P,'./cmd/auto-sign-in',W/'updated-worker-overlay.json',False),
    ('cli',H,'./cmd/source-sites-migrate-owned',None,False),
    ('driver',P,'./tests/integration',W/'driver-overlay.json',True),
]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def capture(label):
    paths={Path(__file__),W/'prepare.py',W/'extra-stages.go.txt',W/'remote-body.py'}
    source=P/'work/independent-source-main-contract-20261107'
    paths.update(source/n for n in ('CONTRACT.md','contract-index.json','message-actual.json','freeze.json'))
    embeds=set();commands=[]
    for name,root,pkg,overlay,test in PLANS:
        mapping=json.loads(overlay.read_text())['Replace']if overlay else{}
        if overlay:paths.add(overlay)
        args=['go','list','-deps','-compiled']+(['-test']if test else[])+(['-overlay='+str(overlay)]if overlay else[])+['-json',pkg]
        r=subprocess.run(args,cwd=root,env=ENV,capture_output=True,timeout=90)
        (W/(label+'-'+name+'-list.stderr')).write_bytes(r.stderr)
        assert r.returncode==0,r.stderr.decode()
        commands.append({'argv':args,'cwd':str(root)})
        data=r.stdout.decode();decoder=json.JSONDecoder();at=0
        while at<len(data):
            while at<len(data)and data[at].isspace():at+=1
            if at==len(data):break
            obj,at=decoder.raw_decode(data,at);directory=Path(obj.get('Dir',root))
            for key in ('GoFiles','CompiledGoFiles','TestGoFiles','XTestGoFiles','CgoFiles','CFiles','CXXFiles','MFiles','HFiles','FFiles','SFiles','SwigFiles','SwigCXXFiles','SysoFiles','EmbedFiles','TestEmbedFiles','XTestEmbedFiles'):
                for value in obj.get(key,[]):
                    logical=Path(value);logical=logical if logical.is_absolute()else directory/logical
                    physical=Path(mapping.get(str(logical),str(logical)))
                    assert physical.is_file(),str(physical);paths.add(physical)
                    if 'Embed'in key:embeds.add(physical)
            module=obj.get('Module')or{}
            for module in (module,module.get('Replace')or{}):
                if module.get('GoMod'):paths.add(Path(module['GoMod']))
        paths.update((root/'go.mod',root/'go.sum'))
    tools=Path(subprocess.check_output(['go','env','GOTOOLDIR'],cwd=P,env=ENV,text=True).strip())
    paths.update(tools/name for name in ('compile','link','asm'))
    paths.add(Path(shutil.which('go')).resolve())
    values={str(p):sha(p)for p in sorted(paths)}
    (W/(label+'-inputs.json')).write_text(json.dumps(values,indent=2)+'\n')
    (W/(label+'-list-commands.json')).write_text(json.dumps(commands,indent=2)+'\n')
    (W/(label+'-embeds.json')).write_text(json.dumps({str(p):sha(p)for p in sorted(embeds)},indent=2)+'\n')
    return values,embeds

def build():
    before,embeds=capture('before-build');rows=[]
    for name,root,pkg,overlay,test in PLANS:
        args=['go']+(['test','-p=1','-c']if test else['build','-p=1','-trimpath','-buildvcs=false'])+(['-overlay='+str(overlay)]if overlay else[])+['-ldflags=-s -w','-o',str(W/name),pkg]
        started=time.monotonic();r=subprocess.run(args,cwd=root,env=ENV,capture_output=True,timeout=120)
        (W/(name+'-build.stdout')).write_bytes(r.stdout);(W/(name+'-build.stderr')).write_bytes(r.stderr)
        row={'name':name,'argv':args,'cwd':str(root),'exit':r.returncode,'seconds':time.monotonic()-started,'sha256':sha(W/name)if r.returncode==0 else None,'bytes':(W/name).stat().st_size if r.returncode==0 else None}
        rows.append(row);assert r.returncode==0,r.stderr.decode()
        (W/(name+'.buildinfo.txt')).write_bytes(subprocess.check_output(['go','version','-m',str(W/name)]))
    after,_=capture('after-build');assert before==after
    result={'env':{k:ENV[k]for k in ('GOOS','GOARCH','CGO_ENABLED','GOFLAGS','GOPROXY')},'inputs':len(before),'embeds':len(embeds),'stable':True,'builds':rows,'scope':'real Go Main/worker/CLI; test-only description-marked same-version worker and driver; compilation is not runtime acceptance'}
    (W/'builds-current.json').write_text(json.dumps(result,indent=2)+'\n')
    bom={f"bin/{row['name']}":{'sha256':row['sha256'],'bytes':row['bytes']}for row in rows}
    (W/'bundle-bom.json').write_text(json.dumps(bom,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':
    if sys.argv[1:]==['--capture-runtime']:
        after,_=capture('after-runtime');before=json.loads((W/'before-build-inputs.json').read_text())
        assert before==after
        for row in json.loads((W/'builds-current.json').read_text())['builds']:assert sha(W/row['name'])==row['sha256']
        print(json.dumps({'stable':True,'inputs':len(after),'binaries_stable':True}))
    else:
        assert not sys.argv[1:]
        build()
