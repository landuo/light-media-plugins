import pathlib,subprocess,json,hashlib,os,sys
r=pathlib.Path('/Users/accidia/projects/light-media-plugins');p=r/'work/migration-20261106/source-module-manifest';env=os.environ.copy();env.update(GOOS='linux',GOARCH='amd64',CGO_ENABLED='0');fmt='{{if .Module}}{{if .Module.Main}}{{.Dir}}|{{join .GoFiles ","}}|{{join .EmbedFiles ","}}{{end}}{{end}}';out={}
for cmd in ['category-editor','torrent-transfer','site-statistic','mp-server-status','plugin-uninstall','remove-link']:
 raw=subprocess.check_output(['go','list','-deps','-f',fmt,'./cmd/'+cmd],cwd=r,env=env,text=True);files={}
 for line in raw.splitlines():
  if not line:continue
  d,*groups=line.split('|')
  for group in groups:
   for name in group.split(','):
    if name:
     f=pathlib.Path(d)/name;files[str(f.relative_to(r))]=hashlib.sha256(f.read_bytes()).hexdigest()
 for name in ['go.mod','go.sum','SDK_ORIGIN.json']:files[name]=hashlib.sha256((r/name).read_bytes()).hexdigest()
 out[cmd]={'linux_compile_files':files,'count':len(files)}
(p/'inputs'/sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n')
