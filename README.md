# Light Media Plugins

当前包含 CategoryEditor（二级分类策略）1.3 的标准 Go worker。构建目标仅为 Linux amd64；宿主功能由光影提供，本仓库不包含宿主应用、下载器或私人迁移证据。

## 安装与使用

1. 宿主必须具有 CategoryEditor 的标准资源接口。已验证的配套光影提交为
   `2b795ebb62207861a5f4b5c54291b5ebd12b3bed`；仅看到应用版本号不能证明包含这些接口。
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

- CategoryEditor 的固定上游业务源为已安装 1.3 版本，源文件 SHA-256 为 `24a8109b5c15bb73b845e42653933d09eb83b608a53303fbab9ebff39b801c27`，已核验与 `jxxghp/MoviePilot-Plugins` 提交 `ce3357c0f2bb4e46f5ff9b72560505a33b26a362` 的 CategoryEditor 源文件逐字节相同。该提交的 GPL3 许可证原文保留于 `LICENSE.upstream`。辅助 helper 的迁移依据为归档版本，不据此宣称证明用户设备现用 helper 版本。
- Go 业务实现与最小 SDK 文件固定于光影提交 `2b795ebb62207861a5f4b5c54291b5ebd12b3bed`。`SDK_ORIGIN.json` 列出相对源路径、逐文件 SHA-256 与唯一允许的模块导入路径调整；SDK 20 个完整文件未裁剪或改写。
- `plugins/categoryeditor` 保留业务实现、嵌入表单及纯合成单元测试。协议 smoke test 启动真实 worker 进程并提供合成宿主回调，不等同于真实宿主的端到端验收。
- 原始内部迁移材料、源代码 oracle、完整 SDK 测试、其他业务插件和宿主系统没有复制。本仓库插件实现及所含最小 SDK 快照经权利人明确授权按 GNU GPLv3 发布，完整条款见 `LICENSE`；第三方材料保留各自许可。
- 唯一第三方 Go 模块为 `golang.org/x/text v0.43.0`。Go 与 x/text 的许可证及 x/text 专利授权文本保留于 `third_party/`。
