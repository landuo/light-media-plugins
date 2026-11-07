# Installed plugin migration, 2026-11-05

## Current resume (eight of 22 in scope accepted)

Read `migration/ledger.json` → `resume.current`. It is the only status
authority. The user deferred MergeMessageNotify. The installed inventory
still has 23 instances, of which 22 are in the current migration. The saved
Merge evidence and four local work-in-progress files are retained separately.

IYUUAutoSeed 2.22 is the active plugin. Its installed API helper is
byte-identical to the 2.19 original and the Go helper has a source replay in
this checkout. The paired host projection can opt in to qBittorrent's
native availability and completed-byte fields.
See `migration/evidence/iyuuautoseed-helper-qb-pack-fields-20261107.json`
for the paired revisions and observations.

The standalone IYUU 2.22 Go worker now binds the source lifecycle, public cron,
private one-shot and interval, downloader operations, site lookup and torrent
material handling. The paired host records a real isolated Linux install,
native form, config save, a single empty downloader pass with a renewed private
lease, and uninstall. Downloaders, site resolution and torrent handling have
separate controlled source replays. See
`migration/evidence/iyuuautoseed-worker-runtime-20261107.json`.

IYUU now renews reverse-call capacity within a large pass and persists all
three source-sized caches, including authenticated clone lineage after exact-ID
updates. An isolated Linux run reached the late seed after 24 existing
candidates and executed paused add, marker cleanup, recheck and start once.
It also verified the 429 cache and success history. The first Linux run exposed
an inherited HTTP/2 ALPN mismatch in the Requests-compatible transport, fixed
and verified with the same owned case. See
`migration/evidence/iyuuautoseed-seeded-capacity-20261107.json`.

IYUU reload, cold startup, clone instance/config/history/material isolation,
one-shot consumption and native Chrome form save/readback passed. The package
candidate uses the standard Go SDK contract and has a verified Linux amd64
ZIP manifest, entry and notice inventory. The extracted worker initialized
under the SDK with both arm64 and amd64 parents. A complete emulated amd64
App still reported an unexplained post-acquisition init failure, so the
package startup gate and build registry entry remain open. See
`migration/evidence/iyuuautoseed-lifecycle-browser-package-20261107.json`.

Close only the amd64 App startup gate. Reuse the passed seeded Linux,
lifecycle and Chrome evidence. Then resume the next installed plugin.

AutoSignIn 2.9.15 passed source, ordinary Linux host, real Chrome
and current package acceptance on SDK105. The local build registry includes
it. `migration/evidence/autosignin-acceptance-20261107.json` binds the executed
worker, notice-only package restaging, reused evidence and independent review.
Image comparisons are source-derived and finite. The prior browser deadline
and package observer failures retain their original records.

## Deferred MergeMessageNotify checkpoint

MergeMessageNotify was implementing from the pinned 23-file installed
1.20.3 snapshot. Its earlier Linux package run verified native form, save-only
trial and persisted reset, ordinary reload without replay, and a genuine
host notice reaching OneBot. The evidence retains that exact artifact.
Apprise hosted attachments, JSON/multipart, gateway, Bark, Gotify, ntfy and
PushDeer have source comparisons. The paired SDK106 Linux run observed an
authorized local-file upload and denied an outside-root path. Its observer
counted a duplicated log field, so the first driver exited with failure.
The unchanged artifact then passed the previously unreached symlink and
private-directory checks. See
`migration/evidence/mergemessagenotify-attachment-providers-20261107.json`.
Mako anonymous-block and page filters match the fixed source cases.
The next increment adds Pushbullet, PushSafer and ServerChan, with
source-derived checks for the upload handshake, batched images and one-line
destination lists. Mako call tags and caller namespaces have fixed-source
comparisons. See
`migration/evidence/mergemessagenotify-providers-mako-calls-20261107.json`.
Join, IFTTT, Pushjet, Discord and Pushover now have Go implementations and
targeted source replay. Pushover uses the pinned Goldmark Go renderer for
Markdown, with dialect differences tracked in the ledger. Mako decorated
definitions and the installed environment's lazy missing-Beaker behavior
have separate source evidence. See
`migration/evidence/mergemessagenotify-providers-mako-decorators-20261107.json`.
Mattermost, Google Chat, Slack, Telegram and Zulip now have native Go
delivery paths and targeted original-source comparisons. Mako's definition
defaults and callable names have separate evidence from its lexical and
namespace Context behavior. The Telegram timing observer correction and
Mako's initial failures retain separate logs. See
`migration/evidence/mergemessagenotify-chat-mako-defaults-20261107.json`.
Matrix, Rocket.Chat, Flock, Prowl and SimplePush have Go implementations
with fixed-source comparisons. An isolated Linux host loaded the candidate
ZIP and delivered an ordinary notice through Matrix login, room discovery,
join, send and logout. The first driver explicitly set an empty image and
was corrected to omit that field with the same worker and ZIP. Mako named
blocks have source evidence for page arguments and generated defaults. See
`migration/evidence/mergemessagenotify-matrix-named-blocks-20261107.json`.
PushPlus, Feishu, DingTalk, PagerDuty and Twist bring the Apprise count to
40 of 183 schemes with Go implementations. Mako named blocks now cover
reserved names, module bindings and the explicit `pageargs` collision.
The 59 new source cases and the Linux build are recorded in
`migration/evidence/mergemessagenotify-cn-pagerduty-twist-mako-edges-20261107.json`.
Chanify, PushMe and WxPusher bring the count to 43 of 183 schemes. The
shared timezone parser now handles the original aliases and suffixes.
WxPusher accepts UTF-16 and UTF-32 response JSON in both byte orders.
The targeted source replays and Linux build are recorded in
`migration/evidence/mergemessagenotify-chanify-pushme-wxpusher-timezone-20261107.json`.
WeCom Bot, Lark and Pushy bring the count to 46 of 183 schemes. Mako
uses the final page tag for the render signature, filters and caching while
retaining earlier declarations in the generated scopes. The source replay,
review follow-ups and exact Linux build are recorded in
`migration/evidence/mergemessagenotify-wecom-lark-pushy-multiple-pages-20261107.json`.
LINE, QQ and both Webex Teams schemes bring the count to 50 of 183.
Mako now binds variadic page signatures from the supplied keyword arguments
and keeps the root Context separate from generated render locals. The
source replays and Linux build are recorded in
`migration/evidence/mergemessagenotify-line-qq-webex-page-variadic-20261107.json`.
Custom Form, Custom XML and Home Assistant bring the count to 56 of 183.
The installed Mako entry creates templates without a file lookup. The Go
port preserves the observed include, inheritance and file namespace
behavior at that entry. The targeted replays and Linux build are recorded in
`migration/evidence/mergemessagenotify-form-xml-home-assistant-external-templates-20261107.json`.
The other 127 schemes, further Mako behavior, browser, clone and final
package acceptance remain open.
The original installed list has 23 instances. Private configuration/data import and production
deployment are separate. No changes to the original service,
remote main, or NAS production166/SDK101. Workflow, AI and official
grades/RSA are excluded. Reuse applicable evidence and rerun only when the
behavior being checked changes.

## Historical checkpoints (retain original bindings; not current state)

### Earlier continuation notes, superseded by current resume


最新恢复点：JSON5与全部产品normal/race已保存本地03f39c4；Main第五轮真实14.77秒/51观察、6worker+2Main完整阶段链经独审858b通过，公开189文件`migration/evidence/autosignin-owned-main-20261106/INTEGRATION.json`。普通卸载保留本fixture代码/配置/历史，重装恢复；分身卸载删自身代码，reset清数据。只签有限真实链，不签UI/PT/更新/全分身数据。五个自建NAS运行目录和九旧本机ELF已核hash/无进程后清理，仅留当前单套；旧失败与原绑定不动。native14候选24项normal/race已过，真实CLI/负控/独审继续；普通浏览器原程序验证继续。7/23，未推送或生产部署。

最新已验证有限进度：JSON5真实SDK/App75项（74条件/185HTTP）通过，公开274文件证据`migration/evidence/autosignin-ocr-json-20261106/INTEGRATION.json`；常规3源样本测试已固化。所有27产品包normal/race各7621项通过，40个实机opt-in跳过及10无测试包另列，4020输入稳定。证据与work模块边界修复仅隔离历史源码/负控，不修改旧证明。Main第四轮12.65秒真实通过一次签到/历史/分身空页/冷启/3.5秒无额外签到/reset；各阶段PID与普通卸载重装保留将另补新轮实测，不能从ack推断。总数仍7/23，不推送、不生产部署。

最新继续点：P11772d31已本地保存ASI真实实现与SDK102；JSON/OCR5已按独立审查实际集成，真63项normal/race通过，当前LinuxSDK/App闭口正在执行。Root真实Main第三轮确认一次attendance约3.02秒发出、凭据与成功历史正确，随后在测试helper误读已解包page处失败；连续三次夹具失败后停止重试，先独立复查剩余驱动，冷启/重置未执行。native14仍需原字段更新后保真与ID稳定，普通浏览器仍在work；7/23保持。生产NAS/远端main未变。下文历史检查点按原绑定保留。

最新本地保存准备：宿主56d02c7b已保存当前隐私与OCR有限实现；SDK102/Origin575d与该提交逐文件吻合。隐私真实App12项race/3612稳定、OCR真实Linux96项/2596稳定；当前ASI+SDK普通回归6188项/4包/849输入稳定，SDK17个独占夹具门未执行另列。JSON/OCR完整值域、普通浏览器引用、native14原字段私有导入仍在独占work开发，没有更新生产NAS或推送。详见同一ledger.resume；下文前一检查点与所有旧证明保留原绑定。


当前功能验收基线仍为7/23；AutoSignIn尚未验收，原私人配置/数据导入仍not_run。本轮不推送、不新增生产部署；NAS仍为上次166/09ab与SDK101配对的七个停用实例。恢复先读唯一ledger.resume，不把历史执行重新标成当前代码证明。

宿主已本地保存SourceSite7（9ae0b58a）、Cookie/初始URL3（fce9aed0）、RouSi3（b3d27057）。分别有535/248/182个精确公开证据文件，原失败和原绑定保留；当前RouSi真实Linux禁网29项通过。StandaloneSDK当前实际102文件，仍需更新旧SDK_ORIGIN和完成当前消费者影响闭口。

AutoSignIn已真正合入工作树：core/cache/regex/TEMP/notice/timeout/order/Cookie/RouSi/API，31个源oracle移到仓库测试目录，仅新增x/image外部依赖。真实源码无overlay无modfile的normal/race各6025项、3包通过，847输入稳定；无测试helper/CLI包单独记录。新LinuxMain882ea4+worker e6b6已真实跑空站点生命周期：安装、配置、默认表单/数据页、分身、36项源API、重载、重启恢复、重置和卸载，37项通过/8.32秒；尚无UI、更新、实际站点/定时/OCR验收。首次驱动误用settings/system的404已保存，修复严格使用现前端GET+PUT/settings流程。

日志F1分段漏洞的新4文件已通过作者和独立真实UTF8边界，但独审又发现F2：已知值先替换会破坏CSRF/token标签，使动态值漏出。最小顺序修复正在独立闭口；H7+P4尚未真正集成。OCR正在真实禁网验证，另有source-only请求首空白拒绝、结果JSON类型与浏览器引用要补；native rawURL/timeout以固定源码和实际DB/API可达性继续核实。Go标准HTTP对末尾OWS规整明确记为必要技术适配，原oracle和差异保留，禁止称逐字节等价。



### Earlier saved checkpoints


Latest saved code: pluginSDK publicGET c26a189f/Origin6b0053 and host96f4c776 (includesnumericfdd9/Unicode24d8) are local only;7/23 remains unchanged. GET hostactualSDK/App canonical99nodes passes; standalone163normalpass/17explicitfixture skips. Current-six unusedGET gate cbe7 proves allnon-noteELFbytes equal, NOTwholeELF identity/newMain/UI;47currentassociations independently39e93 proposed thenRootguarded exactappliedf3c35/6948targetchecks, alloldfullbindings/raw/commands/env/binaries/fixtures preserved. OriginalSDK101 saved824180f is historical, not overwritten.

Current work: cache908 sourceentry recursion independentlyRoot75dec/27 checks138authorfiles +80neworiginalcases→81race, pre-delta44leafreds; not trueintegrated. Interval75c independent68672/53 foundone rawsuffix diagnostic red; Rootf316 smallestrepair independently27495/15 passes6source/8actualApp race, no trueintegration. SharedTEMP117 independentcdc846/55 foundone walk iterationEIO domain red despite current5App/57pure greens; author nowrefines helper andTjupt2file TEMP_PATH/SettingsRead consumer from independentb420/13contract. TT sourceSite03ee/36 frozen66wire/CustomStatsSQLite/4compiledUA, source-site-request-owner6-file candidate nextactualApp. Root sourceNotice40 realORM/SQLite shows13UnicodeEncodeError beforehistory; work-only2prod raw-retention/helper, realApp old13leafreds. Initialcandidate public exacterror assertion failed because existingRPC sanitizes; repeatedrun/preparerTypeError retained, corrected test now separatesrealApp error/history prefix from exactprivate helper reason. Noallnotification/provider/Main/ASI claim. SourceDisc/SDK/TT workonly andAppwindows coordinated; originalMP/media untouched.

Current numeric3-file work7cc47/44 is source25-first: old29failedAppnodes→new76normal/140combinedUnicode race,3compiledpuremutants/vet green; SDKagent independentreview next, no actual targetchange. Cache908f/138 is new17prod/11testsource-entry recursionwork,124realAPI/ThreadPoolsourcecases and3465normal/race eachold98/new101 plus5mutants; not independentlyaccepted/integrated. GET r307277/66 now has independent32a299/45 sourceURI/NoReplay/finiteDTO+actualSDKAppclosure, awaiting exactintegration+current-six unusedcodegate/newSDKsourcebinding. SourceIntervaldeadline75c30d/100 has35Appnodes per mode/977pure/2realphysicalmutants, sourceAPSthreads andsame-loopwake; fullownerindependentreview/Main stillpending. SourceDisc sharedTEMP3-file candidate hasactualApp/race/UID1000Linux4roots, not yet frozen/independentreviewed/consumerwired. Its sourceENV validator fallback3 and normalgraceful-shutdown phase are measured, neverstartup/plugin.Init. TT collects the remaining sourceSite realwire contract only.

Current local code checkpoint: `824180f` saves standaloneSDK101 and159public evidence files after finite independent71ed, Originmetadata-onlydcb1,127current-dependencyproposal978f, exactapplicationb727/1508checks. Current seven-instance count remains7/23; old business/UI/package executions retain original bindings. Full old bindings/history and all raw commands/env/binary/fixture/artifact hashes are preserved; the current5SDK/Origin associations are explicit source-supported dependency metadata. Originf976 changes3explanatory fields only from testedb417, all101 bytes unchanged. No push/deploy/private original-data import/ASI completion is claimed. Older “SDK101dirty/pending” paragraphs below are chronological checkpoints.

HostUnicode3 is now actually applied after independentevidencea3f (Root8b104+c8dbaddendum): original21sourcecase64normal/77race, independent34source68App endpoints/103actions,4compiledmutants and actual realf10 worker/SQLite/Linux6rawhistory rows. Source ordinary method errors remain{}200; finalbadUnicode is500 after override; keys/rawdata remain intact. Nativeerror-envelope adaptation is explicit. This does not claim fullPydantic: independent floatInf→null/page truth is the next separate numeric slice. Shared Go edits are coordinated with TT; physical input hashes, not timing guesses, determine test stability.

Cachewriterf10 newindependent9bd9 found late dump RecursionError versus GoWRITE1 at deep validcache. Newauthor sourcefullAPI/ThreadPool frames show path-specific thresholds, so do not impose one995/1000 limit or confuse Cloads9997 with Pythonindentdump recursion. TEMP cleanup is confirmed graceful shutdown, not startup; source generic setting validator can fallback3 on bad environment input, still being captured before host-only implementation. PublicGETr3 actual99normal/race plus183+30URI/chains is sealed07277 with trueUnicode3 in its stable2141 closure. SourceInterval single-loop deadline/wakeup work adds physical shortinterval/earlyregistration/stops/fuse cases; no finalMain yet.

Latest continuation: accepted baseline remains c260/SDK98 seven instances. Host metadata193 is now actually integrated/saved1661b1c6 (independent417f), current Linux09ab. Eight SDK101 workers were rebuilt and actually ran against it: four Main17.868s/74 observations, PUI22.556s/291, Rlk35.136s/177, all exit0; 22 safe raw files1041288bytes are under work/sdk101-current-consumers-20261106. UI is explicitly skipped, MPS remains a disabled witness, old98 drivers/OwnedPUI helper are declared. SDK101 independent finite copy/build/Main closure and plugin save remain pending; earlier paragraphs below describe historical checkpoints, not current ownership.

ASI immutable e19 now has independent2b06 changes_required: 13/24 cache writer reds remain; source successful get_page followed by actual Pydantic500 differs from throwing inside the worker (which native catches to{}200). New work-only cache/page f10 has source314+24 writer bytes and old98/current101 normal/race3340 each; not independently accepted or integrated. Root works on actual App final response serialization after method catch and form overrides, preserving raw keys/mode; its source21-case real ASGI/Manager AST baseline precedes candidate tests. Notifications/typedregex/realRawKV/Main remain distinct gaps. Source Tjupt TEMP_PATH/signin is global, not code-local; target baseDataPath lifecycle is still to verify. The full source call chain corrects an earlier Root assumption: modules_initializer.stop_modules:154 invokes clear_temp at shutdown, not startup; init_modules has no such call. Do not clean on plugin.Init/startup.

PublicGET first121b refinement failed five new base-aware urljoin cases. New TT r2 bd38 has86 normal/race nodes, real extra source URI cases and two compiled controls; independent source-first review underway, true host/SDK unchanged. Interval owner first20 actualApp normal and977 pure race are work-only; complete mixed-job source float timestamp/full-id order and final owner race remain. Root additionally removed219 explicit old completed-platform Go executables2013984096bytes after SHA/buildinfo/no-open checks, keeping source/raw/sharedcache; existing ENOSPC failures remain setup failures. Current task owners and exact work paths are in ledger.resume.

Current continuation: host opt-in parallelSDK6/Appguard2 is saved locally in code `b69663ab349de0547c34680a68b66c8486bacd51`, proof metadata HEAD21494c26. Independent integration3e443 verifies exact8 production bytes, cold Linuxc8e8bf,804normal/race+16explicitfixture gates per mode,App72race and oldSDK98 current7 native76/291/177 observations. No UI/MPS public-page or ASI proof is inferred. The original217copy manifest is unchanged; an additional20manifest-items+2sealwrapper files have a supplemental map. An initial publication count assertion was wrong; code and all22review files saved inb696, corrected metadata saved separately21494c26, no history rewrite. Five generic background failure logs have no exact method/cause and only finite lifecycle/time association; no fabricated cancellation explanation.

True standaloneSDK is now101 files, Originb417c613, synchronized exactly from hostb69663. This is5old productionfiles changed plus1newbudget helper+2newtests (not6oldfiles changed). Old98Origin40e/5preimages are saved, with an explicit old98overlay; TT also froze a complete98 copy for old-source replay. New101 ordinary/race each163pass plus16separatelycompiled fixture gates eachpass; allsix currentfamily source/CLI regressions each1316pass with10explicitskips. NewSDK consumer recompiled Linux/nativeimpact, independentbinding and localplugin save remain pending. Do not rewrite historical98 source/UI/runtime proof or present the dirty101delta as part of saved c260 seven-instance baseline.

AutoSignIn source-edge independent27196 has five remaining real groups despite old2851green: HTTPinteger/depthlimits,rawsurrogates/nonfinitecontainerYema,nestedhistory.get shortcircuit,publicsaved.times overflow. Author now works only in a new refinement overlay. Oldtypedregex7a466 remains immutable; codepoint/serialization/warning boundaries are not certified. Root metadata2filework9c73 actually captures193source lookup keys/178identities/7public vs old165 categorysubset;196normal/race stable2135inputs include SDK/SQLite/cache, independent review underway. Rawprovenance/effectiveUA/customreferences/aliases/OCR/render/stats remain separate gaps. Scheduler author1b5bf source27hours/53triggers+299normal/race/6mutants is work-only, needs source-owner integration. TT source-publicGET profile work has actual source20idle/21progress/envproxy wire and is in final regression. No candidate is ASI/Main/browser acceptance.

Disk pressure caused actual linker setup failures. Root removed only12 explicitly identified superseded task binaries (475022842bytes), retaining source/raw evidence/current13inputs/current6ce/newc8/NASf7 and shared Go cache. Initial no-space negatives are not compiled controls. Serialize large App links until enough free space is confirmed. Current ledger ownership supersedes the older chronological paragraphs.
The live original `moviepilot` container was inspected through SQLite `mode=ro`, `query_only`, static AST and file hashes only. It has 23 instances, including `TorrentTransfermusic`. Every installed source file matches the earlier read-only handoff archive; the exact local content-baseline SHA and inventory are recorded in the single `migration/ledger.json`. This content SHA is not represented as an upstream commit.

Keep all original behavior within the existing Go/Linux/local-storage/single-user contract. Workflow and AI functionality and official authentication levels/RSA remain excluded. Split mixed branches rather than deleting ordinary plugin behavior. Clones are managed by the platform, with one business implementation per plugin family. Original configuration/data compatibility must be reviewed without publishing secrets or applying private state to production.

Worktree: `/Users/accidia/projects/light-media-plugins`; initial remote/main `4453f821ba32d5d4cc949e68d08d970e6ee7c975`; working branch `codex/installed-plugins-20261105`; fixed delivery branch `main`. Local development/acceptance is authorized, with no new remote push or production deployment assumed. Existing CategoryEditor and shared SDK/build/release code must be inspected and reused when correct.

Execution order follows the live installed list. First revalidate the existing CategoryEditor against current source and the current host SDK. Then implement TorrentTransfer 1.10.3, including its music clone through platform identity. Continue the remaining installed plugins as complete slices, each with fixed source, full UI/API/event/service paths, real host tests, source-derived failure/restart/data cases and independent review. Discovery of later plugins may run independently, while business implementation acceptance proceeds individually.

The coordinator maintains `migration/ledger.json`; it is the only feature-state authority. Statuses are discovered/implementing/blocked/needs_decision/verified/excluded. Previously copied code or historical host-repository acceptance is not automatically current target-repository acceptance. Keep exact source/target/test/environment bindings. No final whole-migration claim until every in-scope slice has valid executed evidence and independent review.

Private source baseline, live inventory, temporary binaries and isolated runtime data are under `work/migration-20261105/`. Confirmed public-safe contracts and evidence belong under `migration/` and `docs/`. Do not change old MoviePilot, activate live subscriptions/downloaders or send notifications to real recipients during development.

Local accepted slices: CategoryEditor, TorrentTransfer and its platform music clone, SiteStatistic, MPServerStatus and PluginUnInstall are accepted (6/23); see the ledger and TT `ACCEPTANCE.json`. Every actual TT failed driver exit is retained separately from passed business observations and the successful source-derived retention tail. Owned TT daemons/image/runtime and generated binaries are cleaned. Remote main remains the initial repository baseline; no new push or deployment occurred.

Resume the current in-flight slices from `ledger.resume`. The accepted4-instance baseline is local16c572e/SDK95; the current SDK98 snapshot40e923 comes from local hostf7b34c33 and its four accepted-consumer impact25bc2bf5 has passed actual Main4 and independent local/process evidence. Cleanup/HOME and Local helper deltas have actual bounded tests and separate independent evidence; they must not relabel historical Main observations. The exact two MPS modules and licenses were added with three byte-identical unused-consumer builds in16c572e.

MPS current98 source/standalone72f9cde8, ordinary Main4/desktop02c22b2c and final Main5/touch composite48f6ecbe are sealed. Main4 exits0/369.50s and Main5 exits0/1048.87s with full cold/reset/purge/retention/reinstall tails. Actual Chrome touch pull-down, list, enabled-base data, recent and disabled-clone page are passed; the extension-control interruption was resolved by the user's synthetic login. Existing packaging functions produced a byte-identical66300 Linux release with19 notices; native NAS --manifest and ZIP inventories passed, independent packaging866d2b3b is passed. The ledger now accepts MPS as the fifth installed instance (fourth family). The owned MPS NAS root/network are removed; the single current worker is retained in the SDK98 shared input directory for PluginUnInstall. Preserve actual failures1–3 and corrected driver/metadata generations.

SDK95-to98 four-instance ordinary f7 Main4 has actually passed17.97s after the full10-stage/17Gitblob source-tail audit, with4 native source-qB POST queries/zero mutations, real owned Nexus HTML/HTTPS, SQLite/events/API/notice, four reloads and cold/no-replay. Public raw closure/independent impact25bc2bf5 and Root exact253-file/183-input review are passed. This is a query-protocol peer, not new real-daemon full-transfer evidence. RemoveLink Main1 failed the host hardlink guard (fixed local162798), Main2 had a driver keyword expectation error, Main3 passed initial link/permission/timer/recreation then failed an incorrect STRM NFO-stem expectation. The third-failure stop led to a full remaining-driver and family review; do not launch Main4 until that review and any source defect are resolved. The newer Linux parent0300 adaptation is frozen separately and has actual UID1000 red/green SDK tests plus nine guard/storage/clone/cold roots; independent review remains pending.

PluginUnInstall independent source-only50-case/7-filesystem/DB discovery and21-case startup/reinit add-on79792c47 precede the finite host/worker implementation. Cold self removal and removal of a future pre-imported class differ from loaded reinitialization; class, running, installed and configuration gates must remain separate. The implementation worker owns its installed-order loop, raw flags and final reset. The host supplies ordinary finite resources and physical Go process adaptation; it must not delegate to the ordinary uninstall endpoint, which would incorrectly purge clone data. Root owns the single ledger and NAS/browser acceptance; assigned workers own their listed code paths. These paragraphs are resume pointers, not a second status authority.

The complete RemoveLink review additionally found actual source-confirmed defects: ±1e400 must raise before stop/flush (Root minimal correction and actual8-case fixture added); timer callbacks must interleave observer-created same-inode protection outside the source state lock (current serial code has an independent race red); Linux Path.unlink must not require parent listing, and an inotify start ENOSYS is not a silent PollingObserver fallback. The99 source logger calls and11 actual source log sequences guide the separate logging slice. These are open implementation/verification gates; no Main4 until resolved.

Accepted five-instance source/SDK/MPS evidence is now saved locally in371625843ff40fc881d56699a24e10e64c62fd4a, branch codex/installed-plugins-20261105. The commit deliberately preserves byte-exact raw evidence whitespace (AX/buildinfo/copied diffs); product-source whitespace is checked separately. Current RemoveLink/PluginUnInstall implementations are not in that checkpoint. No push occurred.

Current continuation (2026-11-06): plugin local checkpoint3716258 and host0719a22 are saved; remote plugin main still4453f82. SDK98 remains40e/f7 exactly. Root host parent0300 narrow2188 is passed and temporary regression bins/runtime are cleaned. PUI producer15/target18/aeee was followed by source-confirmed startup tie order, failed-class stop clearing, cached local/version membership and source page-stub metadata corrections. Currenthost19 is f9e4, independent source/standalone/App f38f (private103 per mode, actualApp52 per mode); Root48 normal/race and accepted-five finite App impact6f97 also pass. Source52 is not ordinary Main. Superseded7a08 is compile-only and explicitly rejected by driver0052. Root is building a new immutable candidate from0719+f9e4 for current4-instance Main and complete PUI Main/UI; MPS is only a disabled state witness, never call its public page/dashboard in this native test. The optional UI-ready fixture file stays0600/private outside evidence. Keep all original53/4354/source reds and first missing-Counter-fixture run.

RemoveLink log2823 is frozen; the shared SDK did not change. Its exact source17 lock ranges, independent timer/serial per-observer lanes and invocation-local effects are being implemented by plugin_sdk. The source timer-created and observer failure-domain reds have turned green in targeted actual SDK tests; final normal/race, Linux native and negative controls still gate Main4. Root owns only its integration driver, which now has matched NFO/short NFO/keep.txt assertions and actual0300 adapter coverage. Source reviewer resumes cold final review at the new family freeze; do not reuse old0ebb as current worker proof. AutoSignIn26-source/22-adapter/55-source observations are fixed; torrent_transfer now owns its complete Go slice only. Absolute provider/API alias/custom-site/timeout capability gaps are unverified until Root provides approved finite host adaptations; do not bypass credentials or mutate SDK98 during current acceptance.

2026-11-06 executed continuation: reviewed8305 host four-instance SDK Main5 actually passed17.82s. PUI Main1 actually passed830.29s including IAB real form select/save/reset/clone isolation and all following reload/update/cold self/future/clone/reset/uninstall/worker-join tail. Raw marker-bound sanitized23 files are harvested under work/migration-20261105/pluginuninstall-main-runtime-20261106/actual-harvest (da452273); private UI-ready remains excluded. Packaging and independent composite review are still gates; accepted remains5/23. Existing front end uses #plugins; an initial /plugins FileServer404 was a navigation mistake, not a product modification or claimed success.

RemoveLink independent final57 review passed normal/race222 each and actual Linux29 nodes, plus four compiled mutations, but found two new exact source differences: Python directory-list repr escapes for BEL/C1/NBSP, and custom extensions assigned before delay int OverflowError. Producer owns only these targeted corrections; preserve375c/ba149 and source reds. Do not start Main4 with the previous761 worker.

PUI Main1/real form and canonical package API crossbuild/native NAS manifest are now executed; public output351 files maps the sanitized observations. The current-four Main5 driver has a historical hardcoded "ordinary f7 Main" classification string: preserve raw, identify actual8305 from both start hashes/command/build binding. Its qB evidence remains query-protocol only. Seven PNGs are real screenshots; AX files include incremental/no-change captures. Independent full composite/packaging is pending.

Root finite getState increment (state.go3a1383a9) fixes legal JSON exponent overflow, arbitrary-size integer and nonempty-container state rejected by float64 decoding. Original8+15 source fixtures drive actual App install/PUT/state/card/event tests:24nodes normal/race and native UID1000 Linux24nodes pass; old compiled production is red7 cases. A deterministic cold2746repo+1generated-Go-input rebuild matches the actual NAS ELF5d1d62. This does not relabel earlier0719/f9/8305 Main. Independent review and current Rlk Main with source8 scalar probes remain gates. Source/SDK98/global truth helpers are unchanged. Preserve original failed harness generations and exact oracle files.

Rlk58/7065 closes repr+partial custom assignment, but independent actual source discovered unknown ~user Path.expanduser raises RuntimeError while current Go incorrectly treats it as unmatched and deletes links. Producer owns this final finite exception/catch repair; source current58 unknown-home reds retained. No Main4 until newfreeze/review. AutoSignIn source ThreadPool concurrency cannot be claimed from SDK98 serial reverse calls; author continues22 algorithms/ordinary surfaces, minimal explicitly-negotiated SDK concurrency design is prepared without changing current frozen shared inputs.

Current accepted count is6/23 (five families): independent complete PUI composite1c17 passes current18/19f9/98, actual8305 Main1+IAB, actual canonicalZIP Main3.46, package byte replay and scoped old-consumer effect. Public copy370/a99 plus source/App/private-input accounting is exact. Later Root state3a is independently closed by3e696b77 and must remain a separate host increment; none of its executions is relabeled8305. Root will save PUI/host19 locally and clean owned scratch; no remote push/deploy authorized.

Rlk final59/d9/da98 still needed a constructor correction: absent HOME and unmapped current UID must defer the original RuntimeError via unexpanded home, while explicit empty HOME resolves/. Four actual333/CGO0 process branches are now producer red/green; final binding/review gates precede Main4. All earlier source red and final-looking intermediate generations remain historical. AutoSignIn work-only regexp2 candidate rebuilt five old/current consumer ELFs byte-identically; shared root modules are still unchanged pending final Rlk and independent unused-module/license gate.

Saved accepted six-instance checkpoint: plugin repo fbddc379789af40528fedac75b0cb193379b7401, branch codex/installed-plugins-20261105. The exact PUI19 host source is saved separatelyafb1ebf224a224ab98a733960ab3aa319be5e212; finite state3a is not mixed into that commit. Owned PUI root and completedSDKMain5 directory removed after independent read-only sample; seven local generated artifacts removed, single86cfLinux/66dNative inputs moved to shared-acceptance-inputs. Public470-file closure topmanifest23df8ae2 and cleanup9611121a are saved. No push/deploy.

Current Rlk producer59/d52/96ef includes only the final source constructor fallback after completeHOME parse/expanduser/rstrip and four separate UID/env process controls; fullnormal/race254 each pass,9platform skips. Independent final59 full cold review is running. Root immutable candidate1ddd264a is0719+PUI19+state4 (source23manifest5356ebc7), compile-only so far. New RlkMain4 driver adds exact source8 raw numeric truth at existing typed card boundary, precise hostSHA gate, previously source-correct NFO assertions and actualparent0300 adapter chain. Later public non-bool original Python Plugin-model wire is not claimed identical to existing native boolean DTO.

2026-11-06 actual RlkMain4 ran with1ddd host/final59 e219 worker/866a update/c41 driver. 135 pre-UI observations passed, including raw8 typed state probes, real100 links/timer/parent0300/clone/update. Actual IAB configuration failed: exact source remoteEntry imports view.js and style.css with?v=2.18, but native frontend route rejected anyRawQuery. Preserve browser-run4 failed AX/PNG and actual-harvest; coordinator gracefully stopped Main/all ownedworkers then SIGTERM driver, actual -15/708.89s. No ui-complete was written, no cold/reset/uninstall tail ran. Count remains6/23. Root finite host-only query adaptation now ignores query for resource identity exactly like fixed source endpoint; cookie authentication, normalized path/package graph/ETag guards remain independent. Source24-case oracle is actual333 standalone endpoint/StaticFiles with synthetic verifier, not production JWT. Root realApp query red33 retained; currentquery+oldHTTP guard race passes. Independent review and freshMain5 are gates. No target Rlk59/SDK98 source changes.

Main5 actual1eeb/c41/e219/866a/frozen frontend completes exit0/283.97s,170 observations and7workerPIDjoins. Actual IAB Config relative imports,save enable,reopen,clone disabled ownpath,STRM/cleanup tabs and log filter are verified; owned base source unlink removes2aliases in0.052s while keep.txt and clone3sameinode links remain. A source-relevant manifest issue was then discovered from retained module_declaration_failed logs: Cat,TT(includingmusic),Rlk advertise inherited pass get_module, whereas original ObjectUtils.check_method skips it without state/module/name calls. Existing host Methods gate is correct. Current verified count is therefore3/23 (Site,MPS,PUI); prior6 checkpoint and all their observations remain historical, not deleted or relabeled. Producer owns only3Manifest minimum corrections and new source-negative/private/ELF freezes; reviewer owns actual source counts/other-interface gate audit and independent closure. Root owns Main6/current-consumer impact/canonicalpackage after these gates; no remote push/deploy. Finite host state is locally saved21e5c54f and query3a3f9e54; new Main5 exacthost1eeb contains both, no SDK99/parallel candidate.

The adjacent source audit extends finite revalidation to all6 historical instances. Commands/services check_method precedes state; native lacked that gate and incorrectly required both optional declarations at artifact preflight. Dashboard metadata gates exist but false declarations must be removed, while direct Base dashboard pass remainsnull after render_mode without state. Auth state-first order and nullable directAPI/page compatibility remain. Current verified count0/23 pending finite current-consumer revalidation; all6 original business/UI/network dossiers retained. Root4hostfiles/counter actualApp11race pass; producer6Manifest20omissions and reviewer actualsource13+fullgetter matrix still gate current artifacts/Main6/package. SDK98 unchanged.

2026-11-07 continuation: ordinary source notice dispatch and published-private scheduler lifetime corrections have been guarded into the true H/P worktrees, with source/target/independent/current-package evidence tracked only by migration/ledger.json resume.AutoSignIn_current.latest_20261107. AutoSignIn remains implementing: a new actual source/target pair proves individual public service stop must return without canceling its already accepted callback, whereas current Go cancels and loses history. The source-public-service-retention work candidate is in progress; do not promote the family or reuse private/global green as its acceptance. Current local checkpoint/SDK104 association is being saved; no new push, merge, private import or production deployment.
