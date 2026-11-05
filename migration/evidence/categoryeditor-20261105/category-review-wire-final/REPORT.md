# CategoryEditor：SourceAdd wire 增量无影响复核

**结论：passed_no_CategoryEditor_dependency_impact。原 CategoryEditor 验收继续有效，无需重跑整套 main/UI。**

本次仅写 `work/migration-20261105/category-review-wire-final/`；没有改旧证明、产品、SDK 或账本。此证书判断 CategoryEditor 的依赖影响，不替 Source* 下载器接口或 TorrentTransfer 签业务验收。

1. 原84个 SDK 文件逐项与封存 `source-target-proof.json` 相同；CategoryEditor 的业务、表单、main、原测试、go.mod/go.sum 均与前次最终独审相同。实际当前 `--manifest` 与旧 manifest 完全一致，仍为1.3及原四项分类/消息/配置 capability。
2. 新增三文件已完整阅读并经 Go AST 检查：无 init、包级变量、注册调用；两份 `_test.go` 只有测试函数，普通 worker 构建不编入。生产新增 `SourceAddRequestV1`／Validate 及 Source* 方法都由显式调用触发。三个文件还与本地 host commit `a3ae854abecfe85eab283a9ef42f6b31eb23b645` 的 Git blob 精确相同；不声称已合并、推送或部署。
3. 实际分别构建 current CategoryEditor，以及通过 deletion-overlay 排除这三文件的基线。两者 Go 导入图均为126包，依赖边相同，唯一编译文件差异为 SDK 的 `downloader_source.go`。**4877个完整链接符号列表逐字节一致**；新 SourceTasks/Completed/Add/Control、辅助方法及 SourceAddRequest/Validate 均无链接符号。
4. 八个关键 ELF section 全部相同：`.text`、`.rodata`、`.typelink`、`.itablink`、`.go.buildinfo`、`.go.fipsinfo`、`.noptrdata`、`.data`。`.text`为1,376,177字节／SHA `cbdf8408b4ab822b4cd1f483df88b013233ddf16c2a1220b69a64531fc77e779`；`.rodata`为397,985字节／SHA `58cc096e8a7e9d75bdc3594a384d46aaf216d1e38cbc89d0cf4fd1fd97a69165`。构建 ID、源码和调试表不同，整二进制 SHA 不同；没有伪称二进制相同，也没有用本次交叉编译替换旧 Linux/main/UI 的实际 SHA。
5. 已审补录的 `category-worker-driver-build-binding.json`：五个历史制品 SHA/size 均吻合原 runtime inputs；原 worker 命令没有被补成宿主的 `-trimpath/-buildvcs=false`。Linux worker/driver 显式 linux/amd64/CGO=0；Mac 命令未逐次捕获环境的字段保留 null，未从另一次 SDK 的 go env 倒推。Mac driver 为原 `go test` 的临时测试二进制，run1缺独立源码快照的限定保留。此补录是历史元数据核对，不是新运行或逐字节历史重建。

当前生产增量 SHA：

| 文件 | SHA256 |
| --- | --- |
| `internal/sdk/downloader_source.go` | `8144622951198e648c76365c368f257de1fde503c372702494ff48cd1dadd8ca` |
| `internal/sdk/downloader_source_test.go` | `a784d4c14d6e53d36d7ad2903baabbc0513f673474fe821e61faee2f30f87077` |
| `internal/sdk/downloader_source_wire_test.go` | `8762ed49a1fa4f8cac02866290d15574fb20b10c6cddc172dc97950437e2529d` |

本次 SDK_ORIGIN 快照为87条目、SHA `a7ee9679da337a3b24cae97c2f92b5f4e7ff08a8c95f11b8fdbe60fd5dfd0ca1`；顶层已绑定上述本地 commit。三个增量条目的 `source_state` 仍带提交前的 pending 字样，已通知协调者校正来源说明；该文字不参与 worker 编译，也不改变本证书的代码 SHA。若仅校正元数据，追加新元数据摘要即可，不必重跑链接证明。

历史构建命令补录 SHA：`da853a7870ccb8e74c4d898a1d58d9aa8279dc952845a0e9a689e6fa89a79653`。

复现：从目标仓库运行 `python3 work/migration-20261105/category-review-wire-final/audit.py`。实际命令、环境、全部 ELF section 摘要、逐文件绑定和 manifest 见 `impact-certificate.json`；AST 见 `new-file-ast.json`，新本地 Git 来源核对见 `new-sdk-git-binding.json`。第一次 AST 工具调用因 Go 将末尾 `_test.go` 参数当源文件而退出，修正的是审查工具的参数分隔，原失败如实保留。

本次临时二进制和 overlay 已自动删除。旧 main/UI 验收仍沿用原始确切源码、制品及日志绑定；没有重跑、改写或扩张其范围。
