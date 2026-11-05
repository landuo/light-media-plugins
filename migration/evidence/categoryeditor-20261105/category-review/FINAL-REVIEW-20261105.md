# CategoryEditor 1.3 最终独立审查 — 2026-11-05

**结论：passed。按用户已选定的目标 SDK 与已批准安全适配验收；未发现新的 CategoryEditor 阻断遗漏，不称无差异复刻。**

审查者：`/root/category_review`。本轮仅新增本目录审查产物，未修改产品、SDK、账本或构建注册表，未部署、提交、推送或操作旧 MoviePilot。真实 main/浏览器执行由协调者与运行验证工作者完成；审查者独立读原始记录、驱动、源代码和五张截图，没有冒称亲自重演浏览器。

## 已核对的完整切片

1. 固定已安装原源码 SHA256 `24a8109b5c15bb73b845e42653933d09eb83b608a53303fbab9ebff39b801c27`；原版全文件仅一个 CategoryEditor 类。原元数据、get_form 完整 AST、一次性 init、get_state、空命令/API/页面及 stop_service 均已映射。原版没有插件私有 KV/业务文件、事件、计划任务或后台服务，因此不虚构这些验收项。当前 live helper 与历史 oracle helper 精确同字节，当前 live builtin `/app/config/category.yaml` 与宿主嵌入默认策略精确同字节；已核 core/config.py 的 INNER_CONFIG_PATH 与活动 CONFIG_PATH 区别。
2. 本审查独立执行原源码与 Go Handle：57 案、138 步、1,242 项字段比较零差异；包含 JSON 真值、原始状态值、默认值反复读取、完整表单、文件字节、回调顺序、部分失败、忽略 False/None 更新返回、停止不重放及 Unicode。移除自动关闭的负控产生 70 处差异。原始 oracle、旧失败和旧测试输出没有被改写。YAML helper 的实际业务行为与安全限制沿用精确固定宿主的已批准合同，不把合成 helper 记录器冒称真实 parser。
3. 真实 Linux main 的 78 条原始事件／42 次驱动 HTTP，以及 Mac 第二轮的 76 条事件／41 次 HTTP 已逐条解析核对；确认安装真实独立可执行制品、原版表单与默认字节、关闭开关只存草稿、写入准确 Unicode/CRLF/末尾换行、分类缓存更新、站内 SSE 消息、自动关闭和全量配置替换。普通坏 YAML 已写入而暖缓存保留，符合原 helper 行为。实际非 root 0400 写失败返回 500，保留草稿配置、原文件/缓存和相同 worker PID；恢复 0600 后成功。
4. 已实际打开五组浏览器 PNG 并读取对应 AX/observation：source 保存 UI来源电影/剧集后为关闭；clone 仍保留独立原配置；clone 0400 保存失败显示同一请求错误并保留文本和开启状态；同表单恢复后保存成功且再次打开为关闭；整页刷新后 source 仍是自己的 UI来源文本。独立最终 HTTP/文件观察确认两配置不同且均 disabled，真实全局文件与缓存为 UI分身策略。配置隔离与全局分类共享同时成立。
5. 已核实际 source/clone 独立 worker PID、代码目录／文件 inode 和制品 SHA；source-only reload 不替换 clone，同版本 force 真正重新取制品。完整 main 冷重启更换 main 及两 worker PID；驱动的 inode/mtime/字节断言和后续 cleanup 记录一致，SSE 新队列为空。clone reset 返回空配置、source 配置保留；clone 卸载后代码目录删除/API404；source 卸载保留配置，凭真实索引重新安装后配置仍在。四次索引与可执行制品取回均有记录。所有 main 正常退出，测试进程、NAS 独占根及本任务二进制已清理。

## 实际源码、制品与版本绑定

- 宿主为 `75e13686a0e3df05ac251e359303ef3fd5971cf6` 的普通 `cmd/server`。审查者通过 `git cat-file` 独立核对保存的 **1818 个**编译输入，全部与该不可变提交的 Git blob 相同；宿主 Mac/Linux 二进制分别为 `b4743ec9a2be669068ded6544dca960d710a0a7c81ee9be138b6afc9ed542842`、`0162d7edd2c22af31b2adf6348c224304d020c5800551605d9e172b9c525cce5`，当前保留的二进制本体 SHA 与实际日志一致。不是靠 `-buildvcs=false` buildinfo 猜来源。
- 实际 Linux CategoryEditor 1.3 worker 为 `091493585e9a33b68ddc1ea3e11e5b2fccacb16289b7284771c7862bc5e33cd3`；测试更新制品为 `f46fef8bbcc8c18ed8c5b3fb7c28196e793842bb81628d502bec3005646b02df`。版本 **1.3.1 只是同一业务的 manifest overlay 测试制品**；已逐文本核对只有 `manifest.Version = "1.3.1"` 这一行增加，不宣称存在已迁移的 upstream 1.3.1。
- 目标业务 `.go`／表单／main 与上述固定宿主对应文件在仅导入路径调整后相同。SDK_ORIGIN SHA `00961b4882382db60785200b8ee14c04310939c7a376fc8a00f66025a77a54e1`，原 production56 集合摘要 `46bce3cfb0e8b8f42fbc4fa3f53e90e1fe5e8d421cc229be724a6063c1e162f0`；84 个完整 SDK／测试／fixture 文件均独立核源且最终仍未变化。SDK 工作者的 normal/race 82 根测试、独立 worker、vet 与预期失败负控日志已校验 SHA；不冒称它们是本审查重新执行。
- 当前 SDK_ORIGIN 已作为 v3 元数据扩展至86文件（SHA `63b48f5dcc28dcdc80fdcff34362c9dfdfcba6dd7f9eda1816d2aa95df019acc`），明确记录75e基线加未提交 host 增量；原84个文件内容仍逐一与封存证据相同。00961b...属于原真实运行时已核的历史元数据，不被改写为当前摘要。新增 source client/test 的 host commit 尚未固定，不归为75e既有接口，也不由本报告替它们签发布。见 `current-origin-metadata-binding.json`。
- 当前源代码、测试输入、所有原始运行记录、浏览器与清理材料的完整文件 SHA 见同名 JSON 以及 `final-evidence-audit.json`。初次驱动编译错误和 Mac 第一轮空 repo 重装假设错误仍保留；修复的是驱动，无产品修补。真实成功不只依据 HTTP200，已检查 success、具体配置、文件字节、类别、消息、worker 和 lifecycle 后果。

## 新增下载器 SDK 文件的影响结论

TorrentTransfer 新增 `internal/sdk/downloader_source.go`，本审查固定 SHA `a4d631a0e99f998402698c39447aa4336b0fb02b3555ad03bee82736562b4275`。它只有四个 capability 常量、两个 DTO 类型和 Downloaders 方法，无 init、包级变量、注册或新依赖模块；CategoryEditor manifest 仍只声明原四项分类/消息/配置能力，业务不调用 Downloaders。

独立构建当前 CategoryEditor 与通过 Go deletion-overlay 排除新文件的冻结基线后：**4,877 个完整链接符号列表逐字节一致，`.text` 与 `.rodata` 完全一致；新 SourceTasks/Completed/Add/Control 没有链接符号**。`.typelink`、`.itablink`、`.noptrdata` 和 `.data` 也相同。构建 ID、源码/调试表等不同，因此没有声称二进制 SHA 相同；新的交叉编译 SHA 没有替换旧真实 main 运行的 SHA。当前 manifest、业务单测和 vet 另已执行。

据此，新增文件**不失效 CategoryEditor 的可达业务与原真实 main/UI 证据，无需为它重演整套 main/浏览器**。这是基于实际依赖与链接内容的判断，未默认共享 SDK 任意变化都无影响。新文件后续若增加 init/全局注册、改动原冻结可达文件或改变 CategoryEditor 链接内容，须重新评估。当前宿主工作树的 TorrentTransfer 适配尚在进行，本签审只认证已运行的 75e 宿主；不认证尚未验收的新宿主构建。

## 保留的边界

- 已批准的目录名、普通文件/no-symlink、字节/数量、YAML 复杂度及特殊结构防线继续有效；默认模板为不可变嵌入资源。不是原 Python 所有危险输入与外部可变默认文件 IO 的逐字等价。
- 当前 live helper/default 字节身份已核，历史 oracle 不因此变成当前 NAS Python/ruamel/WeakSingleton/数据库运行实测；历史人工保留失败构造对象的适配差异仍保持原记录。
- 本轮真实安装通过宿主支持的 executable-format HTTP 制品索引，不是新发布的远端 ZIP/Release；没有生产部署、私密配置/数据迁移、真实媒体改写、下载器操作或外部通知。本签审仅闭合 CategoryEditor 业务切片，不称全部已安装插件迁移完成。
- 原 worker/driver 的完整构建 flags 未在最初 runtime manifest 单列。实际输入、Go 环境、manifest 和制品 SHA 已绑定；本审查不声称逐字节重建旧 worker。保留了一次不匹配的候选构建探针，明确不作为产品失败或新运行证据。

后续交付和权威账本由协调者处理。本报告没有改变任何中央状态或扩展操作授权。
