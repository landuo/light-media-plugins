from pathlib import Path
import json,hashlib,subprocess,shutil
P=Path('/Users/accidia/projects/light-media-plugins');H=Path('/Users/accidia/projects/light-media');W=P/'work/sites-review-20261106/current-consumer-main-review/managed-history-guard-review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,x):(W/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
inputs=json.loads((W/'current-inputs-after.json').read_text());assert all(sha(H/n)==s for n,s in inputs.items());assert json.loads((W/'current-race.command.json').read_text())['exit']==0;assert json.loads((W/'strict651-race-red.command.json').read_text())['exit']==1
src=W.parent/'source-storage-readonly/capture-manifest.json';source=json.loads(src.read_text());assert all(r['identical_to_fixed_8a83'] for r in source['files'])
R=P/'work/migration-20261106/managed-storage-main-impact/raw';mf=R/'harvest-manifest.json';assert sha(mf)=='ed97f205327b1ce771cb1709b516861dbd13bab822dad6c1ff20da4727d6e21f';m=json.loads(mf.read_text())
for row in m['files']:
 f=R/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes']
for name in ['managed-storage-main-four-1','managed-storage-pui-main-1','main-run-9']:assert m['runs'][name]['exit_code']==0
assert m['runs']['main-run-8']['exit_code']==-15
capabilities={}
for family,path in [('CategoryEditor','categoryeditor/categoryeditor.go'),('TorrentTransfer','torrenttransfer/plugin.go'),('SiteStatistic','sitestatistic/plugin.go'),('MPServerStatus','mpserverstatus/plugin.go'),('PluginUnInstall','pluginuninstall/plugin.go')]:
 s=(P/'plugins'/path).read_text();assert 'StorageDeleteCapability' not in s;capabilities[family]={'source_sha256':sha(P/'plugins'/path),'StorageDelete_advertisement':False}
dump('current6-nonconsumer-impact.json',{'families':capabilities,'music_uses_TorrentTransfer_manifest_same_caps':True,'SDK98_modules_and_product_business_changed':False,'current_host_actual_four_Main_exit':0,'current_host_actual_PUI_Main_exit':0,'classification':'new generic storage.delete branch is not granted to five accepted families/six instances; interactive browser defaulttrue unchanged; actual current6 Main limits preserved'})
prod=[{'path':n,'sha256':s}for n,s in inputs.items()];dump('final-frozen-inputs.json',prod)
(W/'REVIEW.md').write_text('''有限宿主修复独立通过。原版RemoveLink硬链1246–1274直接Path.unlink；STRM经StorageChain88–92→FileManager314–325→Local.delete178–195，只查storage/path和文件系统，不读媒体登记。actual已安装两helper静态SHA同fixed8a83；首次metadata inspect命令引号问题未影响source静态读取，修正后实际image333/StartedAt11-05记录如实，不沿用10-28旧启动声明。

缺陷由真实导入数据复现：实际App的historyRemovalFixture经过preview/execute/runImport产生SQLitehistory、有效asset/managed_file和同inode文件；安装真实生产Rlk/真实观察器删除源。原651两完整生产文件overlay的严格sameinode门race确实失败：history已删除但alias被FILE_IN_USE阻断。当前相同测试实际转绿。不是只造history行或手动把asset改removed。host测试进程带race，外部真实Rlk/HostServices正常native编译；不冒称这些子worker也是race构建或普通Main。

两生产变更范围：交互browserMutationAllowed恒委托protectReferences=true；仅plugin原生StorageDelete调用false。false查询只选import_plan，仍检查queued/running；旧true整个guard在去掉唯一query选择器后AST规范化逐字相等。Storage函数除这一false参数全部旧guard/锁/调用相同。Scope、当前allowedroot、静态系统路径、symlink、双snapshot、import锁、downloader检查及O_PATH最终写入验证保持。没有worker可控制的新flag、SDK、Rlk专属入口或HostCaller伪写。

独立当前8root race全过：上述真实Rlk+两新managed/activeimport+原SourceStorage actualSDK clone/cold+selectedhardlink+交互stale/symlink/protectedroot/activeimport/owneddownloader协议peer保护。current3文件pre/post一致。独立生产1838输入除明确两SHA全部精确Git651；无overlay/SDK变化，Linux CGO0冷重编逐字同Root6ce69c24...。Root实际Linux普通Main当前四实例、PUI尾链、RlkMain9原完整driver无UI均成功，45raw逐SHA核验；Main8 UI_WAIT字符串0误开gate、未执行UI和tail、graceful主进程/worker关闭后driver-15事实保留。Main7 IAB22件仍旧3c05，不重标新6ce UI；Rlk业务P1/P2真实history/customscrap/成功通知仍另待ordinaryMain证据。

物理Storage与内部登记/审计是不同操作。保留asset/managed/auditplan并如实读回，正是SourceLocalStorage无登记修改的有限Go表示适配；不能宣称原版SQL物理擦除或清索引。Rlk后续Storage.Exists/List读FS，Delete false不再查询asset/managed，故其父空目录和sidecar清理不被残留登记再次阻断；History投影hidden影响后续exact查询。无需为本迁移顺带markremoved或扩大资产/订阅系统，普通文件管理仍保护登记。新driver要同时观察此保留事实和实际物理效果。

原六实例均无StorageDelete能力，产品/SDK98未动，当前host的四实例+PUI真实Main再次通过；历史fullUI/realdaemon/SourceStatus证据仍按旧ELF/宿主标签保存。此证书不代替Rlk整体验收，也不声明外部通知接收、真实种子删除、生产数据迁移或部署。
''')
# Only our generated binaries/temp are removed. Private historical host source
# is retained locally and expressly excluded from public copying.
bins=[W/n for n in ['remove-link-native','host-services-native','guard-ast','independent-host-linux']];ps=subprocess.check_output(['ps','-axo','pid=,command='],text=True);needles=[str(x)for x in bins]+[str(W/'tmp')+'/'];live=[x for x in ps.splitlines()if any(n in x for n in needles)];assert not live,live
removed=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in bins]
for p in bins:p.unlink()
shutil.rmtree(W/'tmp');dump('cleanup.json',{'removed_own_binaries':removed,'own_worker_processes_remaining':0,'Root_and_producer_binaries_untouched':True})
files=[]
for p in sorted(W.rglob('*')):
 if p.is_file()and p.name not in ['artifact-manifest.json','review-evidence.json']:files.append({'path':str(p.relative_to(W)),'sha256':sha(p),'bytes':p.stat().st_size,'public_copy':'before651-private'not in p.parts})
dump('artifact-manifest.json',files);dump('review-evidence.json',{'status':'passed_bounded_host_plugin_storage_registration_delta','production_test_files':prod,'source_actual_static_manifest_sha256':sha(src),'independent_AST_all_other_guards_unchanged':True,'independent_source_actual_Rlk_before651_race':{'exit':1,'same_inode':True,'history_deletion_reached':True,'failure':'managed alias FILE_IN_USE remains'},'independent_current_race':{'exit':0,'roots':8,'seconds':14.688,'exact_inputs_pre_post_same':True,'real_App_SDK_workers':'production Rlk + resource fixture; subprocesses native normal, host test race','downloader_guard':'owned httptest protocol peer, not realqB daemon'},'independent_host_cold_reproduction':json.loads((W/'host-independent-reproduction.json').read_text()),'Root_native_actual_raw_manifest_sha256':sha(mf),'Root_native_actual_raw_files_verified':45,'Root_Main8_harness_failure_retained':True,'current6_nonconsumer_impact_sha256':sha(W/'current6-nonconsumer-impact.json'),'internal_index_bookkeeping':'preserved records, not erased; no claim SQL physical equivalence, no addedmarkremoved','Rlk_whole_family_acceptance':'pending separate actual two business chain closure; no UI generation relabeling','private_host_source_public_copy':False,'artifact_manifest_sha256':sha(W/'artifact-manifest.json'),'cleanup_own_binaries':4})
print('certificate',sha(W/'review-evidence.json'));print('manifest',sha(W/'artifact-manifest.json'))
