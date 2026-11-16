# SDK95 → SDK98：四个已验收实例的依赖影响

范围内通过。CategoryEditor、TorrentTransfer、TorrentTransfermusic、SiteStatistic 的业务文件未改；本次验证当前 SDK98 与固定 f7 普通主程序的依赖兼容性，不重写历史实机验收的 SDK 版本。

| 证据层 | 实际结果与限制 |
| --- | --- |
| 完整旧/新依赖闭包 | 旧 SDK95 从 Git `16c572ecaf6994ddb38c135cdc76a3c05a9d40ab` 整文件恢复为一个共享 overlay；当前 SDK98 Origin SHA `40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875`。6 个旧文件改动、3 个新文件；77 个业务/测试/支持输入没有产品变更。183 个保守编译输入前后稳定。 |
| 本地消费者测试 | 两套 SDK 的 normal/race 各 477 tests/subtests 通过；Mac 上原 Category cmd Linux-only smoke 跳过，另有真实 worker 子进程矩阵及本次 Linux Main 覆盖。测试资源是合成 HostCaller，不能称作站点/下载器实机。 |
| 真实 worker / wire | Runner95/98 × Worker95/98 × 4 实例，normal/race 均通过。32 次实例执行的对应语义 trace（结果、错误码、callback 顺序）一致；非 consumer 的合法 hello/frame 不出现 cleanup 字段。并发取消后下一新调用、stop/join 均覆盖。 |
| HOME 与新 cleanup 分支 | 这三个 family 均不声明 `plugin.cleanup.submit`，业务不读 HOME/expanduser、不调用新 Local helper。HOME witness 确认旧 Runner 剥离，新 Runner 保留显式 set/empty，缺失仍缺失；无关 provider env 均剥离。新 generic session 方法仍在普通链可达，结论结合测试，而非把整个文件判为死代码。 |
| 当前普通 Linux Main | 固定 f7 host `7521f81d…`、当前 3 个 worker、平台生成 music 分身，Root run4 **exit 0 / 17.97s**。真实配置、Category YAML、source qB 查询、Nexus HTTPS→原生解析→SQLite→事件→通知、API/page/dashboard、4 实例 reload、cold 均通过。qB 是自有查询协议 peer，**没有实际 qB/TR daemon 完整转移**。 |

Main4 的独立原始事实：4 次 `POST torrents/info`，filter=completed、未发 hashes，0 mutation；两个公共 service owner 最终 `等待/can_run=true`。私有 one-shot 的原日志延时为 3.003s 和 3.000s。自有 Nexus 11 次 HTTPS 请求、4 次 CONNECT、0 非预期目标；真实 SQLite 单站事件3、全局事件1，当前19字段 API 与完整通知正文匹配源预期。4 个实例各自 reload 换 PID，cold 后再次出现4个新 PID；观察超过3.5秒，已清 once、配置/持久数据/Category 文件守恒。冷启动前后存储摘要和文件身份是冻结驱动中执行成功的断言，未为报告另行解密或打印 KV 值。

当前 SDK98 的原预算继续有效：120 torrents/1810 RPC/单 callback 最大15，400 filtered/809/最大8，70 ticks/421/最大6，大 recheck/11/最大6；normal/race 相同。pending/active stop 与 reinit 均有原始独立 SDK worker 观测。64 callback/256 phase、32 并发上界未调整。这些大样本资源仍为合成协议，不冒充 daemon 负载。

失败保留：Main1 的计数器误读 query 而源使用 POST form；Main2 将 admission 当完成；Main3 猜测 PUT-by-ID 路由而实际404。三次完整代际、原命令/退出/日志均保留。第三次之后审计了全部剩余10阶段与17个 f7 Gitblob，并补真实 HTTP 正负 fixture（normal/race 各15项）才运行 Main4。没有只改 URL 后继续盲跑。两个本地首次 normal 的输出目录缺失、封存文件数量误计及初次公共 manifest 名称碰撞也保留为测试/证据工具问题，没有覆盖或混入产品失败。

主证书为 `impact-certificate.json`，逐项源预期/实机观测比较为 `actual-main-comparison.json`。历史 `historical-local-freeze.json` 的“Main 未执行”文字保持原样；本证书是追加的实际结果。完整原始输入、wire、检查和已脱敏 Main 日志均由 `artifact-manifest.json` 绑定；未包含 ELF、数据库、key、Cookie 文件或生产配置。

建议协调者将这四实例的 **SDK95→98 范围内依赖回归**记为通过，保留各 family 原有独立验收与限制。不得据此宣布所有安装插件完成、当前真实 qB/TR 大批量重验或当前 UI 重验。75e 缺少 TT/Site 所需新 source capabilities，因此四实例使用 f7；独立 MPS 的 75e/current98 兼容证据不混入本项。Root 随后的 storage.delete hardlink 修复不在这枚 f7 ELF 中，三 family 不调用该资源，仍属另项影响审查。
