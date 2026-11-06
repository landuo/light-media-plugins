from pathlib import Path
import subprocess,json,hashlib,time
w=Path(__file__).resolve().parent;repo='/Users/accidia/projects/MoviePilot';fixed='8a83efeacd3e26b82be495e17d50146e31c96a60';http=subprocess.check_output(['git','show',fixed+':app/utils/http.py'],cwd=repo,text=True);ocr=subprocess.check_output(['git','show',fixed+':app/helper/ocr.py'],cwd=repo,text=True)
cases=[('null','null'),('false','false'),('zero','0'),('negative_zero_int','-0'),('zero_float','0.0'),('negative_zero_float','-0.0'),('empty_text','""'),('empty_list','[]'),('empty_dict','{}'),('text6','"ABC123"'),('bool_true','true'),('integer','123456'),('float','1.25'),('float_integral','1.0'),('float_underflow','1e-400'),('float_overflow','1e400'),('float_negative_overflow','-1e400'),('nan','NaN'),('positive_inf','Infinity'),('negative_inf','-Infinity'),('list6','["A","B","C","D","E","F"]'),('list_nan','[NaN,Infinity,-Infinity,null,true,1.0]'),('list_nested','[[1,2],null,{"z":1,"a":2},[],[null,"X"],[["A","B"]]]'),('dict_order','{"z":0,"b":2,"a":1,"c":3,"d":4,"e":5}'),('dict_duplicates','{"z":0,"a":1,"z":2,"b":3,"c":4,"d":5,"e":6}'),('dict_nested_nonfinite','{"z":[NaN,Infinity],"b":{},"a":false}'),('string_surrogate','"ABCDE\\ud800"'),('string_pair','"ABCD\\ud83d\\ude00Z"'),('list_surrogate','["ABCDE\\ud800","A","B","C","D","E"]'),('dict_surrogate','{"\\ud800":0,"A":1,"B":2,"C":3,"D":4,"E":5}'),('huge_int_4300','1'*4300),('huge_int_4301','1'*4301)]
for n in [100,9990,9993,9994,9995,9996,9997,9998]:cases.append(('array_depth_'+str(n),'['*n+'0'+']'*n))
for n in [9993,9995,9997]:cases.append(('dict_depth_'+str(n),'{"a":'*n+'0'+'}'*n))
cases += [('non_object_root_list','__ROOT__[]'),('non_object_root_null','__ROOT__null'),('non_object_root_true','__ROOT__true'),('bad_json','__ROOT__not-json')]
(w/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
payload='from __future__ import annotations\nHTTP='+repr(http)+'\nOCR='+repr(ocr)+'\nCASES='+repr(cases)+'\n'+r'''
import ast,sys,os,json,types,base64,hashlib,threading,signal,requests
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import quote,unquote
signal.alarm(90)
for k in list(os.environ):
 if k.lower()in('http_proxy','https_proxy','all_proxy','no_proxy'):os.environ.pop(k,None)
os.environ['NETRC']='/tmp/no-owned-netrc';wire=[];current={};logs=[]
class Logger:
 def __getattr__(self,name):return lambda *args,**kw:logs.append(name)
logger=Logger();get_caller=lambda:None;settings=types.SimpleNamespace(USER_AGENT='owned-UA',PROXY=None)
class Peer(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  body=self.rfile.read(int(self.headers.get('Content-Length','0')));wire.append({'path':self.path,'cookie':self.headers.get('Cookie'),'ua':self.headers.get('User-Agent'),'body':body.decode()});data=current['body'].encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
server=ThreadingHTTPServer(('127.0.0.1',0),Peer);server.daemon_threads=True;threading.Thread(target=server.serve_forever,daemon=True).start();endpoint='http://127.0.0.1:'+str(server.server_port);settings.OCR_HOST=endpoint
root=ast.parse(HTTP);nodes=[n for n in root.body if isinstance(n,ast.FunctionDef)and n.name in['_url_decode_if_latin','cookie_parse']];node=next(n for n in root.body if isinstance(n,ast.ClassDef)and n.name=='RequestUtils');node.body=[n for n in node.body if isinstance(n,ast.FunctionDef)and n.name in['__init__','request','get_res','post_res']];nodes.append(node);exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'fixed-http','exec'),globals());exec(compile(ast.Module(body=[next(n for n in ast.parse(OCR).body if isinstance(n,ast.ClassDef)and n.name=='OcrHelper')],type_ignores=[]),'fixed-ocr','exec'),globals())
rows=[]
def exception(e):return {'type':type(e).__name__,'message':str(e)}
for name,value in CASES:
 wire.clear();logs.clear();body=value[len('__ROOT__'):]if value.startswith('__ROOT__')else'{"result":'+value+'}';current={'body':body};row={'name':name,'body':body,'helper_error':None,'operations':{}}
 try:
  result=OcrHelper().get_captcha_text(image_b64='YWJj');row['helper_type']=type(result).__name__;row['truth']=bool(result)
  for op,callback in [('str',lambda:str(result)),('repr',lambda:repr(result)),('len',lambda:len(result)),('form',lambda:requests.Request('POST',endpoint+'/submit',data={'imagestring':result}).prepare().body)]:
   try:row['operations'][op]={'value':callback()}
   except Exception as e:row['operations'][op]={'error':exception(e)}
 except Exception as e:row['helper_error']=exception(e)
 row['wire']=wire[:];rows.append(row)
server.shutdown();server.server_close();print(json.dumps({'qualification':'actual complete fixed OcrHelper+RequestUtils+Requests HTTP POST; source operations str/repr/len/Requests form preparation recorded, synthetic-only immutable333 netnone; no source app import/config/DB/PT/browser','http_sha256':hashlib.sha256(HTTP.encode()).hexdigest(),'ocr_sha256':hashlib.sha256(OCR.encode()).hexdigest(),'python':sys.version,'recursion_limit':sys.getrecursionlimit(),'max_str_digits':sys.get_int_max_str_digits(),'rows':rows},ensure_ascii=True,indent=2))
''';(w/'source-payload.py').write_text(payload);cmd=['ssh','-o','BatchMode=yes','admin@192.168.8.129','docker','run','--rm','-i','--network','none','--read-only','--no-healthcheck','--tmpfs','/tmp','--tmpfs','/config','--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534','--label','task=lm-source-ocr-value-20261106','--entrypoint','python3','sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','-B','-'];start=time.monotonic();p=subprocess.run(cmd,input=payload.encode(),capture_output=True,timeout=100);(w/'source.stdout').write_bytes(p.stdout);(w/'source.stderr').write_bytes(p.stderr);(w/'source-command.json').write_text(json.dumps({'argv':cmd,'exit':p.returncode,'seconds':time.monotonic()-start,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest()},indent=2)+'\n');print({'exit':p.returncode,'bytes':len(p.stdout),'stderr':p.stderr.decode()[-1000:]});raise SystemExit(p.returncode)
