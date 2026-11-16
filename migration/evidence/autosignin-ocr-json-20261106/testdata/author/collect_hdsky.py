from pathlib import Path
import json,subprocess,hashlib,time
P=Path.cwd();w=Path(__file__).resolve().parent;repo='/Users/accidia/projects/MoviePilot';fixed='8a83efeacd3e26b82be495e17d50146e31c96a60';sources={k:subprocess.check_output(['git','show',fixed+':'+p],cwd=repo,text=True)for k,p in [('HTTP','app/utils/http.py'),('OCR','app/helper/ocr.py')]}
for k,p in [('BASE','sites/__init__.py'),('HDSKY','sites/hdsky.py'),('RESULT','result.py')]:sources[k]=(P/'work/migration-20261105/source-snapshot/autosignin'/p).read_text()
cases=json.loads((w/'cases.json').read_text());names=['text6','list_nan','dict_order','dict_duplicates','list_nested','bool_true','nan','float_overflow','huge_int_4300','string_surrogate','dict_surrogate','false','dict_nested_nonfinite','array_depth_9996'];cases=[r for r in cases if r[0]in names]
payload='from __future__ import annotations\n'+''.join(k+'='+repr(v)+'\n'for k,v in sources.items())+'CASES='+repr(cases)+'\n'+r'''
import ast,sys,os,json,types,base64,hashlib,threading,signal,requests,re,chardet,ssl,socket,socketserver,tempfile,pathlib,subprocess,select,time,warnings
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import quote,unquote
from lxml import etree
signal.alarm(100);warnings.filterwarnings('ignore',message='Unverified HTTPS request')
for k in list(os.environ):
 if k.lower()in('http_proxy','https_proxy','all_proxy','no_proxy'):os.environ.pop(k,None)
os.environ['NETRC']='/tmp/no-owned-netrc';wire=[];current={};logs=[];connects=[]
class Logger:
 def __getattr__(self,name):return lambda *a,**kw:logs.append({'level':name,'message':str(a[0])if a else''})
logger=Logger();get_caller=lambda:None;settings=types.SimpleNamespace(USER_AGENT='owned-UA',PROXY=None,PROXY_SERVER=None)
class Peer(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def call(self):
  body=self.rfile.read(int(self.headers.get('Content-Length','0')));wire.append({'method':self.command,'path':self.path,'host':self.headers.get('Host'),'cookie':self.headers.get('Cookie'),'ua':self.headers.get('User-Agent'),'referer':self.headers.get('Referer'),'body':body.decode()})
  data=b'<html><body>Owned authenticated lab</body></html>'
  if self.path=='/image_code_ajax.php':data=b'{"success":true,"code":"ownedhash"}'
  elif self.path.startswith('/image.php'):data=b'owned-image'
  elif self.path=='/captcha/base64':data=('{"result":'+current['value']+'}').encode()
  elif self.path=='/showup.php':data=b'{"success":true}'
  self.send_response(200);self.send_header('Content-Type','application/json'if self.command=='POST'else'text/html');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 do_GET=call;do_POST=call
class Proxy(socketserver.StreamRequestHandler):
 def handle(self):
  line=self.rfile.readline().decode().strip();method,target,_=line.split();connects.append(target);assert method=='CONNECT'and target=='hdsky.me:443'
  while self.rfile.readline()not in(b'\r\n',b'\n',b''):pass
  up=socket.create_connection(('127.0.0.1',tls.server_port),timeout=2);self.wfile.write(b'HTTP/1.1 200 Connection established\r\n\r\n');self.wfile.flush()
  try:
   while True:
    ready,_,_=select.select([self.connection,up],[],[],3)
    if not ready:break
    for sock in ready:
     data=sock.recv(65536)
     if not data:return
     (up if sock is self.connection else self.connection).sendall(data)
  finally:up.close()
class TCP(socketserver.ThreadingTCPServer):allow_reuse_address=True;daemon_threads=True
http=ast.parse(HTTP);nodes=[n for n in http.body if isinstance(n,ast.FunctionDef)and n.name in['_url_decode_if_latin','cookie_parse']];node=next(n for n in http.body if isinstance(n,ast.ClassDef)and n.name=='RequestUtils');node.body=[n for n in node.body if isinstance(n,ast.FunctionDef)and n.name in['__init__','request','get_res','post_res']];nodes.append(node);exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'fixed-http','exec'),globals());exec(compile(ast.Module(body=[next(n for n in ast.parse(RESULT).body if isinstance(n,ast.FunctionDef)and n.name=='visible_html')],type_ignores=[]),'installed-visible-html','exec'),globals());base=next(n for n in ast.parse(BASE).body if isinstance(n,ast.ClassDef));base.bases=[];base.keywords=[];base.body=[n for n in base.body if isinstance(n,ast.FunctionDef)and n.name in['get_page_source','sign_in_result']];exec(compile(ast.fix_missing_locations(ast.Module(body=[base],type_ignores=[])),'installed-site-base','exec'),globals());exec(compile(ast.Module(body=[next(n for n in ast.parse(HDSKY).body if isinstance(n,ast.ClassDef)and n.name=='HDSky')],type_ignores=[]),'installed-hdsky','exec'),globals())
rows=[]
with tempfile.TemporaryDirectory(prefix='owned-ocr-hdsky-')as td:
 cert=pathlib.Path(td)/'cert.pem';key=pathlib.Path(td)/'key.pem';subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=hdsky.me'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);tls=ThreadingHTTPServer(('127.0.0.1',0),Peer);tls.daemon_threads=True;ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cert,key);tls.socket=ctx.wrap_socket(tls.socket,server_side=True);threading.Thread(target=tls.serve_forever,daemon=True).start();plain=ThreadingHTTPServer(('127.0.0.1',0),Peer);plain.daemon_threads=True;threading.Thread(target=plain.serve_forever,daemon=True).start();proxy=TCP(('127.0.0.1',0),Proxy);threading.Thread(target=proxy.serve_forever,daemon=True).start();settings.OCR_HOST='http://127.0.0.1:'+str(plain.server_port);os.environ['HTTPS_PROXY']='http://127.0.0.1:'+str(proxy.server_address[1]);os.environ['NO_PROXY']='127.0.0.1';exec(compile(ast.Module(body=[next(n for n in ast.parse(OCR).body if isinstance(n,ast.ClassDef)and n.name=='OcrHelper')],type_ignores=[]),'fixed-ocr','exec'),globals())
 for name,value in CASES:
  current={'value':value};wire.clear();logs.clear();connects.clear();site={'id':7,'name':'Owned','url':'https://hdsky.me/','ua':None,'cookie':None,'proxy':False,'render':False,'timeout':1.25};started=time.monotonic()
  try:result=HDSky().signin(site);error=None
  except Exception as e:result=None;error={'type':type(e).__name__,'message':str(e)}
  rows.append({'name':name,'site':site,'value_json':value,'result':result,'error':error,'wire':wire[:],'connect_targets':connects[:],'logs':logs[:],'seconds':time.monotonic()-started})
 proxy.shutdown();proxy.server_close();tls.shutdown();tls.server_close();plain.shutdown();plain.server_close()
print(json.dumps({'qualification':'actual full original HDSky.signin+site base visible HTML+fixed OcrHelper/RequestUtils and Requests; real owned HTTPS CONNECT/image/code/submit+HTTP OCR; actual source sleep retained; synthetic-only immutable333 netnone; logger recorded as boundary, not original UTF8 sink','hashes':{k:hashlib.sha256(globals()[k].encode()).hexdigest()for k in['HTTP','OCR','BASE','HDSKY','RESULT']},'rows':rows},ensure_ascii=True,indent=2))
''';(w/'hdsky-source-payload.py').write_text(payload);cmd=['ssh','-o','BatchMode=yes','admin@192.168.8.129','docker','run','--rm','-i','--network','none','--read-only','--no-healthcheck','--tmpfs','/tmp','--tmpfs','/config','--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534','--label','task=lm-source-ocr-hdsky-values-20261106','--entrypoint','python3','sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','-B','-'];start=time.monotonic();p=subprocess.run(cmd,input=payload.encode(),capture_output=True,timeout=110);(w/'hdsky-source.stdout').write_bytes(p.stdout);(w/'hdsky-source.stderr').write_bytes(p.stderr);(w/'hdsky-source-command.json').write_text(json.dumps({'argv':cmd,'exit':p.returncode,'seconds':time.monotonic()-start,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest()},indent=2)+'\n');print({'exit':p.returncode,'bytes':len(p.stdout),'stderr':p.stderr.decode()[-1000:]});raise SystemExit(p.returncode)
