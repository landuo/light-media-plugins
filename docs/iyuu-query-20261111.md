# IYUU 查询：693 个 Transmission 种子的对照与修复

## 实机观察（2026-11-11，NAS）

- 只读获取同一批 693 个完成的 TR 种子，按同一顺序分为 200/200/200/93；完整输入摘要为 `8e9522f1aeb5535db2b36f35579d73755ae5c4b488c4aedfc7f5040d57e4389b`。凭据、info hash、私有种子和名称不写入本报告。
- 调用 NAS 当前安装的 MoviePilot IyuuHelper（不启动原插件调度），四批均返回业务 code=0，查询耗时 2.973/1.076/1.174/1.931 秒，匹配源种子数 103/109/101/40。
- 修复前 Go 对同一输入，容器环境代理和过滤后的 worker 直连均曾四批成功；当前没有重现夜间 20 秒中止，不能把一次网络畅通等同于夜间原因已经被现场证明。
- 实际常驻 IYUU worker 的 `/proc/.../environ` 仅含 GOMEMLIMIT、PATH、TZ、HOME，没有代理变量。宿主代理与 MoviePilot 环境代理均已配置；运行器有意过滤子进程环境。原插件 API 依赖 worker 的 ProxyFromEnvironment，因而实际没有获得宿主代理。
- 原 Go `http.Client.Timeout=20s` 是完整请求总时限；Python Requests 的 20s 是连接/套接字读取空闲超时。持续收到数据时，两者行为不同。夜间约 20 秒跳过的记录与该差异相符，但记录本身不足以证明全部失败都来自这一原因。
- 高频连续探针还观察到 HTTP 200 / 业务 code=400（访问频率过快）；这不是查询成功，也不是超时。后续业务验证应避免同时反复调用同一接口。

## 修复边界

- IYUU worker 通过 `network.proxy.read` 获取私有宿主代理环境快照，仅在内存使用；保留运行器环境过滤，不改全局代理/站点/下载器设置。
- 只用快照 Environment，不用宿主站点显式 Proxies；对应原 IyuuHelper 的 proxies=None。
- 每次逻辑请求使用共享 Requests-compatible proxy/timeout transport：lowercase、ALL_PROXY、NO_PROXY 合并语义、连接/TLS/空闲超时、context 取消；移除完整请求总时限。
- 构造时复制快照；nil 兼容 standalone CLI，非 nil 空表示明确直连；测试 loopback 始终直连。
- 固定 IYUU origin、TLS 证书/主机名校验、禁跨域重定向、16MiB bodylimit、双 guard、私密错误脱敏保持。
- 插件版本 1.0.3；不修改宿主其他功能，不更改原 MoviePilot 服务。

## 本地回归证据

- 新增 transport 测试：代理与空环境、不可变快照、固定生产 HTTPS origin 的 CONNECT/TLS、连续流总时间大于空闲阈值成功、header/body stall、header/body/CONNECT 取消、TLS/hostname、响应上限。
- 新增 SDK 接线测试：过滤的 worker 环境不能替代宿主快照；不使用显式站点 Proxies；快照读取失败不静默退回直连；manifest 声明能力。
- `go test ./plugins/iyuuautoseed`、transport 重复 5 次、`go test -race ./plugins/iyuuautoseed ./cmd/iyuu-auto-seed` 通过。
- 全仓第一次重复运行遇到现有 site-statistic queued-owner-cancel 时序测试失败；该测试独立重跑 5 次和 `go test -p 2 ./...` 均通过，未改动无关包。
- Linux amd64 / arm64 均交叉编译通过；这些是本地测试与构建证据，不代替 NAS 部署或实际添加 TR 辅种的证据。

## 实机添加阶段发现的独立 URL 拼接问题

- 1.0.3 经 NAS 安装 API 返回 success=true；数据库、落盘 manifest 和 worker SHA256 一致，原配置前后完整比较不变。构建期间临时提高光影容器内存，完成后恢复原 512MiB memory / 1GiB memory+swap；其他服务不变。
- 第一次安装客户端等待响应超时，不代表后台构建失败；后台使用独立 context，链接线程曾等待块 IO。容器内存与 IO pressure 偏高。最终以安装 API 回执、数据库、实际包元数据联合验收，不以进程退出或文件出现单独验收。
- 隔离分身只选取 1 个原 TR 种子和 1 个缺失候选：另外 692 个源种子、1995 个其他候选仅在分身缓存屏蔽，不改原实例。实际服务查询返回 `IYUU返回可辅种数：1`，但在获取种子文件阶段失败；服务返回 completed 不等于实际添加成功。
- 发现宿主 source-indexer 把站点管理的 `BaseURL` 原样作为 `url`（通常没有末尾 `/`）；原版解析器使用 `siteURL + download_page`，错误生成了站点域名后直接接 `download.php` 的新 host。详情页也有同样拼接问题，对应夜间多次 `source page target changed origin`。
- 1.0.4 在 worker 的 SDK 适配边界派生原版要求的目录型 base URL；不改宿主原始站点配置、凭据或 opaque Reference，不放松下载/页面的同源校验。

## 最终发布与真实 TR 添加验收

- 查询修复提交：`0e70558226dc5f84bde6f02414efc0299644c035`；URL 适配修复提交：`e1cbc962762a383b281edf22029c18e0da0d56b3`。两次源码发布 CI 的 Linux amd64 / arm64 构建及清单发布均成功。
- NAS 安装 API 返回 success=true，实际包 manifest=1.0.4，数据库 version=1.0.4 / generation=7；worker SHA256=`befb9f3469b8d2e97fd7224fd12a8d5c1959fbda03f14488e717d879d0219c54`。宿主主程序未替换，无其他服务重启。
- 为缩短磁盘校验时间，第二轮隔离分身选取 1 个 2.02GiB 的 CARPT 缺失候选，屏蔽其他源与候选，保留 skipverify=false；不是批量添加，也不是探针模拟 Add。
- 实际通过安装后的 worker / 宿主 SDK 完成种子文件获取、TR 添加、完整校验及开始做种。日志记录 `共 1 个任务校验完成，开始辅种 ...`；TR 原生 RPC 回读的 hash 与选定候选精确相等。
- 最终 TR 从 693 增至 694，新增恰好 1 个；status=6（做种）、percentDone=1、error=0、totalSize=haveValid=2165609907、leftUntilDone=0，保存目录与原源种子相同。
- 原有 693 个任务无缺失，status/downloadDir/percentDone/labels 前后比较变化数=0；IYUU 原实例完整配置前后相等。
- 验证分身已卸载，新增 TR 种子仍处于做种状态；光影容器恢复原 memory=536870912、memory+swap=1073741824，health=healthy。未修改 MoviePilot 调度、站点/下载器全局设置或既有媒体。

## 后续受控网络对照与证据限制

同首批 200 个种子、相同有效凭据、每个 HTTP 前间隔 1.1 秒，非构建期间采样：

| 调用 | reseed 业务结果 | reseed 耗时 | CLI |
| --- | --- | --- | --- |
| 原 MP helper / MP 环境代理 | code=0，103 个源种子匹配 | 8.164s | 0 |
| 修复版 Go / 光影宿主环境代理 | HTTP200 / code=0，123287B | 3.588s | 0 |
| 修复版 Go / MP 环境代理入口 | HTTP200 / code=0，123287B | 12.740s | 0 |
| 修复版 Go / 显式直连 | HTTP200 / code=400 | 非传输超时 | 1 |

- 直连 code=400 未读取正文追加重放，具体业务原因未归因；不是 HTTP200 即成功。
- 另一次修复版完整四批复测仍实际出现 no_response，reseed 耗时约 21.8/43.5/40.2/39.2 秒；持续进展后的空闲超时可以使总时间超过 20 秒。失败日志保留，不用后续单批成功抹掉先前失败。
- 本次已验证明确的光影代理传递、总时限语义和 URL 适配缺陷被修复，且真实添加 TR 辅种成功。没有据此承诺上游网络或全部批次已长期稳定，也没有证明全部夜间失败只有一个原因。
- 当前两端凭据去除光影多出的前导空白后相同。对照输入使用原 MP 的有效值；未把 Python 对原样前导空白的立即失败算成网络超时；原实例凭据配置未改。

## 清理与留存

- [结构化 TR 验收收据](<iyuu-tr-verification-20261111.json>) 保存实际计数、状态、文件有效字节、配置及既有任务比较结果，来源/目标仅使用 SHA256 摘要。
- 测试分身已卸载，其临时数据目录、NAS 和本地本次生成的探针/构建二进制已清理；维护会话已登出，本地含凭据和原始私密种子信息的临时快照已删除。
- 保留部署前的单份插件回滚包和脱敏对照/构建/验收证据。未停止或重启原 MoviePilot、其他下载服务，未删除新增成功的 TR 辅种。
