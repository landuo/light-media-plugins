import pathlib,json,hashlib,collections
p=pathlib.Path('/Users/accidia/projects/light-media-plugins');d=p/'work/sdk101-publication-20261106';w=p/'work/independent-sdk101-ledger-application-review-20261106';pub=p/'migration/evidence/sdk101-current-consumers-20261106';sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
before=json.loads((d/'ledger-before-current-dependency-apply.json').read_text());after=json.loads((p/'migration/ledger.json').read_text());proposal=json.loads((d/'current-dependency-reuse-proposal.json').read_text());applied=json.loads((d/'ledger-apply.json').read_text());targets=json.loads((d/'current-target-bindings.json').read_text());errors=[];checks={}
def ck(name,ok,detail=None):
 checks[name]=bool(ok)
 if not ok:errors.append({'check':name,'detail':detail})
bm={x['id']:x for x in before['evidence']};am={x['id']:x for x in after['evidence']};newids=['sdk101.current_consumers.20261106','sdk101.independent_dependency_closure.20261106'];rows={(r['evidence_id'],r['path']):r for r in proposal['rows']};ck('proposal127_unique',len(rows)==len(proposal['rows'])==127)
changed={};changedE=[]
for id,b in bm.items():
 a=am[id];bt=b['binding'].get('target_files',{});at=a['binding'].get('target_files',{});
 for path in set(bt)|set(at):
  if bt.get(path)!=at.get(path):changed[id,path]=(bt.get(path),at.get(path))
 if a!=b:changedE.append(id)
ck('actual_target_diff_equals_proposal',set(changed)==set(rows),list(set(changed)^set(rows)))
ck('actual_changed_evidence22',len(changedE)==22)
for k,r in rows.items():
 old,new=changed.get(k,(None,None));ck('row_previous_'+str(k),old==r['previous_bound_sha256']);ck('row_current_'+str(k),new==r['current_sha256']);f=p/r['path'];ck('actual_file_'+str(k),f.exists()and sha(f)==r['current_sha256'])
for id in bm:
 b,a=bm[id],am[id]
 if id not in changedE:ck('untouched_evidence_'+id,a==b);continue
 rest=lambda q:{k:v for k,v in q.items()if k not in ['binding','historical_bindings','dependency_evidence_ids']}
 ck('old_full_observations_commands_inputs_artifacts_'+id,rest(b)==rest(a))
 hb=b.get('historical_bindings',[]);ha=a.get('historical_bindings',[]);ck('history_prefix_'+id,ha[:-1]==hb and len(ha)==len(hb)+1)
 ck('full_binding_preserved_'+id,ha[-1].get('binding')==b['binding'])
 ck('historical_review_reference_'+id,ha[-1].get('independent_reuse_proposal_review_sha256')=='978f7579ad0de12fab09f413fac14d427997c94683dbc9afa35565e64f3def15')
 bb,ab=b['binding'],a['binding'];ignore={'target_files','current_dependency_evidence_ids','current_dependency_note'}
 ck('binding_environment_source_fixture_unchanged_'+id,{k:v for k,v in bb.items()if k not in ignore}=={k:v for k,v in ab.items()if k not in ignore})
 ck('dependency_ids_append_'+id,a.get('dependency_evidence_ids',[])==b.get('dependency_evidence_ids',[])+[x for x in newids if x not in b.get('dependency_evidence_ids',[])])
ck('new_evidence_exact_two',set(am)-set(bm)==set(newids))
for id in newids:ck('new_binding_exact617_'+id,am[id]['binding']['target_files']==targets)
ck('target_count617',len(targets)==617)
for path,h in targets.items():ck('617actual_'+path,(p/path).is_file()and sha(p/path)==h)
import copy
stage1=copy.deepcopy(after)
for e in stage1['evidence']:
 note=e.get('binding',{}).get('current_dependency_note','')
 if ' Five generic submitted_method_failed' in note:e['binding']['current_dependency_note']=note.split(' Five generic submitted_method_failed')[0]
 if e['id']==newids[0]:
  old=e.pop('historical_source_fact_evidence_ids');e.pop('historical_source_fact_note',None);e['dependency_evidence_ids']=old
stage1_sha=hashlib.sha256((json.dumps(stage1,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
ck('initial127_stage_reconstructs_exact_apply_hash',stage1_sha==applied['after_sha256'])
ck('final_note_and_acyclic_stage_hash',sha(p/'migration/ledger.json')=='b6d43dd87f1f67364146e8cbd7b03d03dd256d9d468f90df5a4ddda2303fad68')
ck('before_hash_matches_apply',sha(d/'ledger-before-current-dependency-apply.json')==applied['before_sha256'])
ck('top_only_features_resume_evidence_changed',all(before[k]==after[k]for k in before if k not in ['evidence','features','resume']))
featureallowed={'evidence_ids','review','current_dependency_status','current_sdk_origin_sha256','current_host_dependency_status','current_review_gate'};fchanges=[]
for b,a in zip(before['features'],after['features']):
 ck('feature_identity_'+b['id'],a['id']==b['id'])
 if b==a:continue
 fchanges.append(a['id']);ck('feature_unchanged_business_fields_'+b['id'],{k:v for k,v in a.items()if k not in featureallowed}=={k:v for k,v in b.items()if k not in featureallowed})
 ck('feature_status_unchanged_'+b['id'],a.get('status')==b.get('status'))
 ck('feature_evidence_append_'+b['id'],a['evidence_ids']==b['evidence_ids']+[x for x in newids if x not in b['evidence_ids']])
 ck('feature_original_review_kept_'+b['id'],{k:v for k,v in a['review'].items()if k!='evidence_ids'}=={k:v for k,v in b['review'].items()if k!='evidence_ids'})
 ck('feature_review_evidence_append_'+b['id'],a['review']['evidence_ids']==b['review']['evidence_ids']+[newids[1]])
ck('seven_features_only',len(fchanges)==7)
ck('count_remains7of23',after['resume']['current']['functional_verified_instances']==before['resume']['current']['functional_verified_instances']==7 and after['resume']['current']['total_installed_instances']==before['resume']['current']['total_installed_instances']==23)
copyrows=[]
for name in ['copy-manifest.json','additional-copy-manifest.json','dependency-copy-manifest.json']:
 m=json.loads((pub/name).read_text());
 for row in m['files']:
  s=pathlib.Path(row['source']);dest=pub/row['path'];expected=row['sha256'];ok1=s.is_file()and sha(s)==expected;ok2=dest.is_file()and sha(dest)==expected;ck('copy_source_'+row['path'],ok1);ck('copy_destination_'+row['path'],ok2);copyrows.append({'map':name,'path':row['path'],'sha256':expected,'source_matches':ok1,'destination_matches':ok2})
ck('copy138_unique',len(copyrows)==len({r['path']for r in copyrows})==138,len(copyrows))
physical={str(f.relative_to(pub)) for f in pub.rglob('*') if f.is_file()}; mapped={r['path']for r in copyrows};ck('physical143_exact_closure',len(physical)==143 and physical-mapped=={'copy-manifest.json','additional-copy-manifest.json','dependency-copy-manifest.json','README.md','ACCEPTANCE.json'})
reuse_review=json.loads((p/'work/independent-sdk101-current-dependency-reuse-review-20261106/review.json').read_text());ck('approved_proposal_exact',reuse_review['proposal_sha256']==sha(d/'current-dependency-reuse-proposal.json') and reuse_review['ledger_before_sha256']==sha(d/'ledger-before-current-dependency-apply.json'))
for id in changedE:
 note=am[id]['binding'].get('current_dependency_note','');ck('explicit_unattributed_limits_'+id,('five' in note.lower() or '5' in note) and 'INVALID_PATH' in note and ('unattributed' in note.lower() or 'no exact' in note.lower() or 'without exact' in note.lower()))
ck('new_consumer_no_cycle',not am[newids[0]].get('dependency_evidence_ids') and bool(am[newids[0]].get('historical_source_fact_evidence_ids')))
accept=json.loads((pub/'ACCEPTANCE.json').read_text());ck('acceptance_current617_exact',accept['current_target_files']==targets);ck('publicationOriginMatches',accept['publication_origin_sha256']==sha(p/'SDK_ORIGIN.json')==targets['SDK_ORIGIN.json']);ck('testedOriginStillOld',sha(pub/'SDK_ORIGIN-tested101.json')==accept['tested_origin_sha256']=='b417c613195590062759633af4142f8a433c8d2fc8279fb36fa00e33e4d112a0');ck('proposal_public_exact',sha(pub/'current-dependency-reuse-proposal.json')==sha(d/'current-dependency-reuse-proposal.json'))
(w/'audit-result.json').write_text(json.dumps({'checks':len(checks),'passed':sum(checks.values()),'errors':errors,'actual_target_changes':len(changed),'changed_evidence':changedE,'changed_features':fchanges,'target_count':len(targets),'public_copy_count':len(copyrows),'public_copies':copyrows,'input_hashes':{str(f):sha(f)for f in [d/'ledger-before-current-dependency-apply.json',d/'current-dependency-reuse-proposal.json',d/'ledger-apply.json',d/'current-target-bindings.json',p/'migration/ledger.json',pub/'copy-manifest.json',pub/'additional-copy-manifest.json',pub/'dependency-copy-manifest.json',pub/'ACCEPTANCE.json']}},indent=2)+'\n');print('checks',len(checks),'passed',sum(checks.values()),'errors',len(errors));print(json.dumps(errors[:10],indent=2))
