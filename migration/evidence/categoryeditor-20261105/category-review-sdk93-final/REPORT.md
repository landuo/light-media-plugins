# CategoryEditor：最终 SDK93 依赖影响补证

结论：`passed_no_CategoryEditor_worker_dependency_impact`。新增下载器客户端没有进入 CategoryEditor 的可达业务代码；无需因这九个 SDK 文件单独重跑旧 Category main/UI。此结论仅适用于本证书绑定的 worker 依赖增量。旧75e实际 main/Linux/UI 验收保留原源码、宿主和二进制 SHA，不改称为当前404daade宿主的实机执行。

1. `current93-inputs.json` 固定 SDK_ORIGIN、全部93个文件和 Category 业务、表单、CLI、原测试、go.mod/go.sum及历史集成驱动。原84个 SDK 文件仍与封存 `source-target-proof.json` 一致。`sdk93-git-binding.json` 逐项读取本地宿主的75e／a3ae／404daade Git blob：93条均精确匹配，仅原先已声明的两个 import 路径重定位例外。当前顶层来源为404daade9d5f321624e7b421dbf877a23fe5c2b9；不声称推送、部署或远端确认。
2. 增量为四个生产文件、五个测试文件。四个生产文件分别提供 Source* outcome、Configurations、SourceConnection、SourceFindByTag 的 DTO及显式方法；完整 AST 检查无 init、包级变量或注册调用。测试文件不进入普通 worker。Linux/amd64、CGO=0下，参与和删除这些九文件时的 Go 导入图均128包，依赖边和嵌入资源相同，唯一编译文件差异是 SDK 中上述四文件。Category manifest也与旧记录完全相同。
3. 实际构建两份 Linux ELF：保留全部SDK93，以及 deletion overlay排除九个增量。两者4877个完整符号的名称、大小、类型相同；没有任何新增 Source*／Configurations 方法或 DTO 被链接。机器 `.text` 精确相同：1,376,177字节，SHA `cbdf8408b4ab822b4cd1f483df88b013233ddf16c2a1220b69a64531fc77e779`；类型索引、接口表、buildinfo、FIPS信息、运行数据等七个section原始字节相同。所有3210个函数逐字节PC→file/line映射相同，429个源文件集合相同。
4. **本次没有沿用旧87证书“完整nm和原始rodata相同”的结论。** 原始nm有三个元数据地址+16；原始rodata有68字节差异。`reflection-metadata-equivalence.json` 按当前Go1.26.2真实ABI解码所有差异：五条既有 Name／Kind／Type／Data／*plugins.HTTPAPI 名称及tag记录仅存放顺序不同，八个相关引用仍指向相同名称/tag/flag；其余rodata字节相同。`.gopclntab`增加16字节，moduledata仅cu表长度+4、后续元数据地址+16；实际函数源码映射完全相同。差异、失败断言和修正均保留，未改二进制或任意屏蔽差异。
5. 当前原生 Category 冷竞态测试73项通过，两包均通过。另一个只编译的单文件overlay故意在Category.New中调用SourceConnection，实际链接出该方法，证书检查能识别它，证明“无新客户端链接”检查有效。全部输入前后SHA保持一致；临时二进制、overlay和修改源码均已删除。旧Category证书及实际main/UI证据文件未改写，账本、SDK和产品未改。

证书入口：`impact-certificate.json`；全部文件摘要：`artifact-manifest.json`；当前完整输入：`current93-inputs.json`。`pc-file-line-maps.json`记录实际保留函数映射；`link-delta-diagnosis.json`记录所有ELF section、符号和差异范围；`linux-import-graph.json`记录同Linux环境下的两份依赖图。

复现顺序：运行 `diagnose_link_delta.py`、`normalize_reflection_metadata.py`、`bind_git_inputs.py`、`negative_reachable_client.py`；执行 `go test -count=1 -race -json ./plugins/categoryeditor ./cmd/category-editor`并保存至`current-category-race.jsonl`；最后运行`audit.py`。Go AST解析器及历史87方法保留在此目录供核对。旧方法两次严格断言失败如实保留；一次审查工具最初按空白分割而漏计120个含空格的泛型符号名，已改为只分前三列并保留完整名称，原始nm输出未改。

本补证不批准或替代 TorrentTransfer／Source*宿主业务验收，不证明当前宿主通用平台所有改动对Category的完整实机影响，也不声称重建出旧历史二进制的SHA。
