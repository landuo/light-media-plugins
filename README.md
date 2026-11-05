# Light Media Plugins

当前本地已验收 6/23 个实例：CategoryEditor（二级分类策略）1.3、TorrentTransfer（自动转移做种）1.10.3 及其音乐分身、SiteStatistic（站点数据统计）1.9.7、MPServerStatus（MoviePilot 服务监控）1.4、PluginUnInstall（插件彻底卸载）2.2。分身使用同一业务实现，由宿主管理独立身份、配置和数据。正在按原版逐个迁移实机安装的 23 个实例（22 个业务实现，含 1 个平台分身）。验收进度以 `migration/ledger.json` 为准；未验收插件不加入可发布索引。构建目标仅为 Linux amd64；本仓库不包含宿主应用、下载器、私人配置或数据库。

## CategoryEditor 安装与使用

1. 宿主必须具有 CategoryEditor 的标准资源接口。最低原配套提交为
   `2b795ebb62207861a5f4b5c54291b5ebd12b3bed`；本轮真实 Linux main 和浏览器验收使用
   `75e13686a0e3df05ac251e359303ef3fd5971cf6`。仅看到应用版本号不能证明包含这些接口。
2. 等本仓库的 **Linux amd64 plugins** 工作流成功，且根目录出现
   `go-plugins.v1.json` 后，在光影插件市场加入
   `https://github.com/landuo/light-media-plugins`，刷新并安装“二级分类策略”。
   源码目录或未完成的工作流不是可安装制品。
3. 打开插件设置，编辑 YAML，开启“启用插件（写入配置文件）”并保存。
   成功后写入宿主的全局 `category.yaml`、刷新分类缓存并自动关闭该开关。
   关闭开关时保存只保留插件配置，不应用全局策略。
4. 整理时还需为目标目录启用二级分类，并有匹配规则。修改策略不会自动搬动已经整理的文件。

CategoryEditor 原本通过 JSON `get_form` 使用宿主表单渲染器，没有独立 Vue
前端构建。它的表单 JSON 已嵌入 worker。其他包含独立 Vue 的插件必须同时打包
完整前端资源，不能仅分发 Go 可执行文件；见下文。

这不是 NAS 部署脚本，不会自动升级宿主或迁移私人配置/运行数据。

## 自动转移做种

本地已验收的 TorrentTransfer 需要宿主提交
`404daade9d5f321624e7b421dbf877a23fe5c2b9` 的 Source 下载器接口及其后续兼容实现。
这些宿主改动目前仅在本地分支，尚未合并、推送或部署；已发布宿主 `75e13686` 不具备这些接口。
本仓库新增代码也未推送，远端市场索引暂不包含此插件。

1. 配套宿主可用后安装“自动转移做种”1.10.3，选择源下载器、目标下载器，填写原版种子备份目录及所需标签、路径映射等选项。
2. 保存后可使用“一次运行”或原版定时服务。转移、校验、是否启动与任务删除顺序按原版；删除源任务保留下载文件。
3. 音乐实例通过宿主“分身”操作创建，后缀使用 `music`，按需填写名称和配置。它拥有独立配置、运行数据、进程和修复临时文件，不是第二套业务代码。

真实验收使用独占 qBittorrent5.1.2、Transmission3.00、合成文件和普通 Linux 主程序，覆盖四种转移组合、100 项真实批量、校验定时器、失败恢复、页面、分身、重启、更新、重置与卸载。
主插件卸载保留配置、数据和代码；已加载分身卸载清除其配置、数据和代码。历史失败测试与最终复合证据分别记录，详见
[`ACCEPTANCE.json`](migration/evidence/torrenttransfer-20261105/ACCEPTANCE.json) 和
[`ORIGIN.md`](plugins/torrenttransfer/ORIGIN.md)。测试中的 1.10.4 只是更新夹具。

## 站点数据统计

SiteStatistic1.9.7 需要本地宿主提交 `d715db2c3665b32670f3f60c519ad7220224a856` 的 SourceSites 资源与恢复修复；这些接口尚未合并、推送或部署，已发布宿主75e不具备。插件本轮也未推送，远端市场暂不可安装。

1. 安装后选择启用、仪表板统计范围和通知范围，保存配置。站点刷新事件触发原版汇总与正文去重；“运行一次”在三秒后由宿主刷新站点并自动清除此开关。
2. 通过插件数据页查看统计和站点账户数据；仪表板可选择此插件。移动端应用布局下可由下拉快捷入口打开数据页。原版没有此插件的独立侧栏项。
3. 分身由宿主创建和管理，配置、数据、进程、重载和更新相互隔离。主插件卸载保留存储，公开配置返回空对象，重装恢复；已加载分身卸载清除其命名空间和代码。

真实普通Linux主程序、独占TLS/Nexus样本、SQLite、API、事件、通知持久化以及桌面/触摸页面均已验收；无实际外部通知接收方。失败历史和最后通过的复合证据见 [`ACCEPTANCE.json`](migration/evidence/sitestatistic-20261105/ACCEPTANCE.json)，必要适配见 [`ORIGIN.md`](plugins/sitestatistic/ORIGIN.md)。1.9.8仅为更新夹具，没有迁移私人配置或操作原系统。

## MoviePilot 服务监控

MPServerStatus1.4 已在普通 Linux 主程序和真实桌面、移动触摸页面验收。开启后可查看服务状态、延迟和最近记录；支持数据页、仪表板及平台分身的独立开关。原版没有命令、定时服务或插件 API，页面请求时获取原版指定状态源。

验收使用受控 HTTPS/DNS/TLS/代理样本，证明响应处理和页面交互；不表示公网状态源始终可用。更新测试中的1.4.1仅为版本夹具。完整证据与必要适配见 [`ACCEPTANCE.json`](migration/evidence/mpserverstatus-20261105/ACCEPTANCE.json) 和 [`ORIGIN.md`](plugins/mpserverstatus/ORIGIN.md)。当前源码和配套改动仍仅本地保存，尚未推送或部署。

## 插件彻底卸载

PluginUnInstall2.2 已通过普通 Linux 主程序、真实配置页面及正式 ZIP 安装验收。配套宿主的新增管理接口目前仅本地分支，已发布75e宿主尚不包含本功能；本插件和宿主改动均未推送或部署。

1. 在设置中选择目标插件及两个清除开关，保存后立即按原版已安装顺序停止对象、移除代码并更新安装记录。没有额外启用开关、运行一次、定时任务或数据页。
2. 原版移除类后再以默认强制参数清除配置与数据，这些调用通常保留命名空间。迁移保持该行为；两个开关的原始值仍保留，选中列表执行后清空。普通平台卸载、重置与这里的逻辑分别验收。
3. 分身身份、代码和数据由平台管理。自身卸载及冷启动期间移除后续插件的原版状态差异也保留；后续真正重启不重新加载已移除记录。

来源、必要 Go 适配和完整证据见 [`ORIGIN.md`](plugins/pluginuninstall/ORIGIN.md) 与 [`ACCEPTANCE.json`](migration/evidence/pluginuninstall-20261106/ACCEPTANCE.json)。测试2.2.1仅为更新夹具，未导入私人配置或操作原系统。

## 自动构建与发布

- `main` 的代码提交先执行 Go vet、race/真实 worker 协议测试及打包/发布受控测试；
  PR 只测试，不发布。仅支持 Linux amd64。
- 测试通过后，以源码提交的完整 SHA 创建独立 `build-<SHA>` Release，上传完整
  插件 ZIP、索引和第三方许可包。已有不同字节的资产不会删除或覆盖。
- 匿名下载校验通过后，以非 force 的整分支并发保护更新根索引；如果源码期间已变化，
  旧任务不得覆盖新索引。索引自动提交不会再次触发构建。
- 工作流只用该仓库临时 `GITHUB_TOKEN`：测试只读、发布 job 的 contents 写权限。
  不需要 PAT、SSH key 或访问光影私有主仓。

发布之前必须具有已获批准的根 `LICENSE`。`--local-probe` 仅供本地诊断，
缺少该根许可的探针包会被发布脚本拒绝。

## 本地验证

需要 Go 1.26.0 或更新版本。

```sh
go test ./...
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -buildvcs=false -o category-editor ./cmd/category-editor
./category-editor --manifest
```

CI 固定 Go 1.26.2。完整包本地构建示例（输出目录必须尚不存在）：

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/build_plugins.py --output dist \
  --release-base-url https://github.com/landuo/light-media-plugins/releases/download/build-REPLACE_WITH_SOURCE_SHA/
```

构建脚本运行真实 worker 的 `--manifest`，而非另写一份漂移的声明；生成 ZIP
的总 size/SHA、可执行文件 SHA 和每个文件的 size/SHA。`build-plugins.json`
是构建输入，**不是**宿主市场索引。

### 独立 Vue 资源

包含 `manifest.frontend` 的 worker 必须在构建配置中声明真实前端构建命令与
独占输出目录。打包器收集输出目录里的全部 JS、动态 chunk、CSS、字体及图片，
保持相对路径；缺入口、可识别的缺失依赖或符号链接都会失败。它遵守宿主现有
`light-media.vue-federation/v1` / `light-media.plugin-api/v1` 协议，不生成新 schema。
前端构建及静态引用检查不能替代安装后的真实浏览器验收。

入口名称保持 `category-editor`。进程通过标准输入/输出的 SDK 协议与宿主通信，不是独立图形界面或原生 invoke 适配器。

## 来源和差异

- CategoryEditor 的固定上游业务源为已安装 1.3 版本，源文件 SHA-256 为 `24a8109b5c15bb73b845e42653933d09eb83b608a53303fbab9ebff39b801c27`，已核验与 `jxxghp/MoviePilot-Plugins` 提交 `ce3357c0f2bb4e46f5ff9b72560505a33b26a362` 的 CategoryEditor 源文件逐字节相同。该提交的 GPL3 许可证原文保留于 `LICENSE.upstream`。本轮只读核对了用户设备现用 helper 和内置默认模板，指纹与固定参考一致；未在原服务执行插件。
- CategoryEditor 的 Go 业务来源保留原提交 `2b795ebb62207861a5f4b5c54291b5ebd12b3bed`；共享 SDK 基线已核对至 `75e13686a0e3df05ac251e359303ef3fd5971cf6`。`SDK_ORIGIN.json` 列出完整文件、逐文件指纹、历史快照和仅有的模块导入调整。后续插件所需的新宿主接口单独记录，尚未发布的接口不冒称已包含在该宿主提交。
- `plugins/categoryeditor` 保留业务实现、嵌入表单及纯合成单元测试。协议 smoke test 启动真实 worker 进程并提供合成宿主回调，不等同于真实宿主的端到端验收。
- `migration/evidence/` 保存经检查的受控测试、源码差分、真实 Linux main/浏览器记录和独立审查；合成、协议回放和实机证据分别标明。私人迁移材料仍在被忽略的 `work/`。本仓库插件实现及所需完整文件 SDK 快照按现有 GNU GPLv3 授权提供，条款见 `LICENSE`；第三方材料保留各自许可。
- 第三方 Go 模块固定为 `golang.org/x/text v0.43.0`、服务监控候选所需的 `github.com/andybalholm/brotli v1.2.6` 和 `golang.org/x/net v0.61.0`。许可证、专利文本和适用的纯算法来源说明见 `third_party/`、`THIRD_PARTY_NOTICES.md` 及对应插件来源文档；候选依赖存在不代表插件已验收。

本轮迁移约束与恢复入口：[`docs/migration-task.md`](docs/migration-task.md)。CategoryEditor 的保存、全局策略与分身配置关系，以及失败恢复、重启和卸载证据见 [`migration/evidence/categoryeditor-20261105/`](migration/evidence/categoryeditor-20261105/)。测试中的 1.3.1 仅为 manifest 更新夹具，不代表上游新版本或已发布制品。
