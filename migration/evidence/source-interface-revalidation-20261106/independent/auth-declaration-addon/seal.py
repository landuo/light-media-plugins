from pathlib import Path
import os,json,hashlib,subprocess,shutil
P=Path('/Users/accidia/projects/light-media-plugins');H=Path('/Users/accidia/projects/light-media');W=P/'work/sites-review-20261106/auth-declaration-addon';A=P/'work/migration-20261106/source-auth-declaration-addon'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,x):(W/name).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
source=P/'work/sites-review-20261105/module-method-declarations-20261106/registry-source-oracle.json';expected='d3b241a8b783c825cc5b11f28010d95fee8fe280ce7f51e3b3f1e001ca1246c1';assert sha(source)==expected
shutil.copyfile(source,W/'registry-source-oracle.json')
rows=json.loads((A/'source613-auth-epoch.json').read_text());old=json.loads((P/'work/migration-20261106/source-module-manifest/all-current-inputs.json').read_text());oldmap={r['path']:r['sha256'] for r in old};changes=[r['path'] for r in rows if oldmap.get(r['path'])!=r['sha256']];assert len(rows)==613 and len(changes)==4,changes;assert all(sha(P/r['path'])==r['sha256'] for r in rows)
assert sha(H/'internal/app/plugin_original_session.go')==json.loads((W/'host-session-input.json').read_text())['sha256']
dump('final-inputs.json',{'source613':{'count':613,'sha256':sha(A/'source613-auth-epoch.json'),'all_match_after_tests':True,'exact_changed_files_from_4693':changes},'producer_freeze_sha256':sha(A/'freeze.json'),'host_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=H,text=True).strip(),'unchanged_production_session_sha256':sha(H/'internal/app/plugin_original_session.go'),'module_or_sdk_changes':False})
for phase,code in [('old20',1),('current23',0)]:
 r=json.loads((W/(phase+'-actual-race.command.json')).read_text());assert r['exit_code']==code
 t=json.loads((W/(phase+'-actual-trace.json')).read_text());assert t['enabled_objects']==4 and not t['errors'];wanted=['get_state','get_auth_providers','get_render_mode'] if phase=='old20' else ['get_state'];assert all(v==wanted for v in t['methods'].values())
# Clean exact owned binaries only, after confirming no process refers to them.
bins=list((W/'bins').iterdir())+list((W/'independent-linux').iterdir());paths=[str(p) for p in bins];ps=subprocess.check_output(['ps','-axo','pid=,command='],text=True);live=[s for s in ps.splitlines() if any(p in s for p in paths)];assert not live,live
removed=[{'path':str(p.relative_to(W)),'sha256':sha(p),'bytes':p.stat().st_size} for p in bins]
for p in bins:p.unlink()
(W/'bins').rmdir();(W/'independent-linux').rmdir();shutil.rmtree(W/'tmp')
dump('cleanup.json',{'removed_owned_binaries':removed,'count':len(removed),'own_worker_processes_remaining':0,'only_own_binary_and_TMP_directories_removed':True,'producer_Root_artifacts_untouched':True})
(W/'FINDINGS.md').write_text('''本补证纠正独立审查中的遗漏：旧1901/b24把继承pass的Auth当作可继续广告的nullable兼容入口，未保持原认证发现实际调用序列。原始source oracle本来已区分1/0/0与1/1/1；这里修正审查结论，不修改旧证书/源码预期/历史Main记录。

原版get_plugin_auth_providers先调用get_state，随后check_method false便continue。CategoryEditor、TorrentTransfer（含music）、RemoveLink继承Base pass，无普通直接Auth HTTP调用者。删去三Manifest广告恰好保留state-first，不改HostAuth、Handle、SDK、算法或其它接口。累计为23个family声明/28个实例声明修正，历史20/24保持原代际计数。API/page直接nullable入口及direct-dashboard有限Base兼容不受影响。

本次实际App+独立SDK生产进程对照：旧20四启用实例均state/auth/render=1/1/1（编译真实负控，exit1）；当前23四启用实例均1/0/0（race exit0）。测试直接GET公开/api/auth/providers，只对具有测试context的host成功/失败forward call做完成记录；真实worker Manifest、Handle、消息、权限与调用选项不变。Cat通过真实content=1 partial-init错误保enabled；TT使用空的owned种子目录、无私有job；Rlk空监控目录；真实music分身创建后显式启用。首次fixture忘记分身默认disabled，尚未进入Auth断言即失败，已完整保留。

独立核613当前输入全部SHA、只有三Manifest+source assertion四文件变化，三完整生产Go严格等于单次Auth声明删除加gofmt；Handle及六ORIGIN、SDK98/modules无变。独立Linux/amd64 CGO0七次重编均逐字吻合：Cat/TT/Rlk/版本fixture四新，Site/MPS/PUI三不变。最低有限Host依赖本地651dd2c3（未推送）；Host4已封独审9669维持有效，不需要新host字段或SDK。

本补证签有限源码→声明→真实Auth发现与二进制闭包。旧Main6/UI、current4、PUI3、canonical包Main均为其真实旧20输入，保留成功/失败事实，不改标签为新23。新普通Main/ZIP/浏览器影响由Root另行归档；本次未访问生产站点/下载器/外部认证或通知接收端，不声明用户体验或全部家族完成。完整host session记录器副本为本地私有审查输入，不纳入公开插件证据；测试与hash/命令/trace可公开。
''')
private={'session-recorder.private.go'}
files=[]
for p in sorted(W.rglob('*')):
 if p.is_file() and p.name not in ['artifact-manifest.json','review-evidence.json']:
  files.append({'path':str(p.relative_to(W)),'sha256':sha(p),'bytes':p.stat().st_size,'public_copy':p.name not in private})
dump('artifact-manifest.json',files)
dump('review-evidence.json',{'status':'passed_bounded_auth_declaration_correction','classification':'source-derived exact-order actual App/real production workers race plus seven byte-identical Linux reproductions; no new ordinary Main/UI claim','supersedes_only':'overbroad inherited Auth nullable-advertisement conclusion in immutable1901/b24, not their raw observations or unrelated host4 gates','producer_freeze_sha256':sha(A/'freeze.json'),'source_registry_oracle_sha256':expected,'source613_sha256':sha(A/'source613-auth-epoch.json'),'host_minimum_local_commit':'651dd2c3f75f4be74951d0a552f93a9079046e1d','actual_old_red_exit':1,'actual_new_race_exit':0,'old_state_auth_render':[1,1,1],'new_state_auth_render':[1,0,0],'real_enabled_instances':['CategoryEditor','TorrentTransfer','TorrentTransfermusic','RemoveLink'],'independent_ELFs':7,'cleanup_binary_count':len(removed),'artifact_manifest_sha256':sha(W/'artifact-manifest.json'),'historical_evidence_immutable':True,'ordinary_main_ui_package_current23':'separate Root impact scope; not claimed here'})
print('certificate',sha(W/'review-evidence.json'));print('manifest',sha(W/'artifact-manifest.json'))
