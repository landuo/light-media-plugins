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
