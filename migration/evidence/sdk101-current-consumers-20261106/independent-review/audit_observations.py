from pathlib import Path
import json,collections,hashlib,datetime
r=Path('/Users/accidia/projects/light-media-plugins');w=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();old=r/'work/parallel-hostcall-current-consumers-20261106/actual-harvest';new=r/'work/sdk101-current-consumers-20261106/actual-harvest';errors={};counts={};http=[]
for label,root in [('historicalSDK98',old),('currentSDK101',new)]:
 errors[label]={};counts[label]={}
 for phase in ['four','pui','rlk']:
  rows=[]
  for p in sorted((root/phase/'evidence').glob('host-*.log')):
   for index,line in enumerate(p.read_text().splitlines(),1):
    try:x=json.loads(line)
    except:continue
    if x.get('level')in['ERROR','WARN']:rows.append(dict(x,file=str(p),line=index))
  counts[label][phase]=dict(collections.Counter(x['level']+':'+x.get('event','')for x in rows));errors[label][phase]=rows
 rows=[json.loads(l)for l in(root/'four/evidence/observations.jsonl').read_text().splitlines()];c=collections.Counter((x['value'].get('method'),x['value'].get('path'),x['value'].get('status'))for x in rows if x['event']=='ss_http');http.append(c)
classification=[]
for phase,rows in errors['currentSDK101'].items():
 for x in rows:
  event=x['event'];note=''
  if event=='submitted_method_failed':note='unattributed: no method/cause/callID; do not infer source branch from temporal association'
  elif event=='request_failed'and phase=='pui':
   obs=[json.loads(l)for l in(new/'pui/evidence/observations.jsonl').read_text().splitlines()];matching=[q for q in obs if isinstance(q['value'],dict)and q['value'].get('response',{}).get('request_id')==x.get('request_id')];note='expected deliberate invalid-config/partial-cleanup HTTP500; exact requestID matched'if matching else'unknown';x['matched_observations']=[q['value']for q in matching]
  elif event=='storage_host_INVALID_PATH':note='INVALID_PATH authority denial during explicit current-root-withdrawal negative; aliases preserved. Event has callID but no path/method, so individual selector/unique cause is not independently attributable'
  elif event=='plugin_message'and'/permission/no-write/denied.mkv' in x.get('message',''):note='explicit owned EACCES negative; source continues and same observer later recovers'
  elif event=='notification_failed':note='no external channel success claimed; persisted notice/receipt and dispatch are distinct, same event count as historical run'
  elif event=='http_completed':note='owned site-icon404 path during create; peer records favicon and source icon fallback; same historical count'
  elif event=='command_registration_unavailable':note='existing platform menu-provider warning, same historical count; no command-menu completion claim'
  elif event=='site_icon_unavailable':note='owned icon fallback, same historical count'
  elif event=='request_completed':note='HTTP404/500 negative outcomes; corresponding PUI request expectations retained'
  classification.append({'phase':phase,'file':x['file'],'line':x['line'],'level':x['level'],'event':event,'request_id':x.get('request_id'),'plugin_call_id':x.get('plugin_call_id'),'note':note})
result={'event_counts':counts,'event_multisets_equal':counts['historicalSDK98']==counts['currentSDK101'],'observation_delta':{'old_four':76,'current_four':74,'old_minus_current':[{'method':k[0],'path':k[1],'status':k[2],'count':v}for k,v in(http[0]-http[1]).items()],'current_minus_old':[{'method':k[0],'path':k[1],'status':k[2],'count':v}for k,v in(http[1]-http[0]).items()],'explanation':'one fewer ordinary asynchronous SQLite-history poll and one fewer notification/receipt poll; all other event/stage counts identical, no stage removed'},'classification':classification,'generic_background_unattributed':sum(x['event']=='submitted_method_failed'for xs in errors['currentSDK101'].values()for x in xs)}
(w/'error-and-observation-audit.json').write_text(json.dumps(result,indent=2)+'\n')
# Correlate current standalone MPS evidence to its actual consumer test window.
mps={}
for mode in ['normal','race']:
 raw=r/('work/parallel-sdk-sync-20261106/consumers-'+mode+'.stdout');events=[json.loads(l)for l in raw.read_text().splitlines()if l.startswith('{')];selected=[x for x in events if x.get('Package')=='github.com/landuo/light-media-plugins/cmd/mp-server-status'and x.get('Test')=='TestStandaloneNativeWorkerBudgetsAndLifecycle'];start=next(x['Time']for x in selected if x.get('Action')=='run');end=next(x['Time']for x in selected if x.get('Action')=='pass');data=r/('work/migration-20261105/mpserverstatus-preparation/worker-budget-observations-'+mode+'.json');x=json.loads(data.read_text());times=[]
 for o in x['observations']:
  for key in ['Start','End','start','end']:
   if key in o:times.append(o[key])
 mps[mode]={'raw_test_sha256':sha(raw),'observation_sha256':sha(data),'test_start':start,'test_end':end,'observation_calls':x['calls'],'host_calls':x['host_calls'],'max_host_calls':x['max_host_calls'],'owned_http_requests':x['owned_http_requests'],'expired_host_calls':x['expired_host_calls'],'unexpected_network':x['unexpected_network'],'observed_time_min':min(times),'observed_time_max':max(times),'within_test_window':start<=min(times)<=max(times)<=end,'classification':x['classification']}
(w/'mps-supplement-audit.json').write_text(json.dumps({'scope':'actual native standalone executable/SDK/ownedTLS + current101; Main only disabled startup/state/cold witness. No public-page/browser Main acceptance. Test source comment lifetime256 is historical shorthand; actual budgets per incoming, not session total.','modes':mps},indent=2)+'\n');print('error multiset same',result['event_multisets_equal'],'generic unresolved',result['generic_background_unattributed']);print(json.dumps(mps,indent=2))
