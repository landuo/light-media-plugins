# Light Media Plugins

光影的 Go 插件仓库。构建清单包含 21 个插件包，目标平台为 Linux amd64。分身由光影创建和管理，共用插件包，配置与数据分别保存。

## 在光影安装

1. 在「插件市场」添加仓库地址 `https://github.com/landuo/light-media-plugins`。
2. 刷新市场，选择插件并安装。市场读取根目录的 `go-plugins.v1.json`，其中的索引指向带完整校验信息的 Release 安装包。
3. 在「已安装」打开插件配置。使用前按需配置站点、下载器和本地目录。CustomHosts 需要为光影容器单独挂载可写的 Hosts 文件。

配套宿主必须提供对应插件声明的资源接口。完整清单使用光影宿主提交
`7de1d57e6685beaa387480fd803bbe6c717b8799` 开发验收。较早的宿主可能能读取市场卡片，但无法安装全部插件。市场发布、宿主升级和导入原 MoviePilot 配置是独立操作。

## 自动构建与发布

- Go 1.26.4。推送 `main` 后，GitHub Actions 先运行 Go 检查和打包测试。
- 检查通过后，工作流创建 `build-<源码提交 SHA>` Release，发布 Linux amd64 ZIP、插件索引及第三方许可包。
- 公开下载校验通过后，工作流更新仓库根索引。已有安装包不覆盖，索引更新不触发重复构建。

## 本地构建

在 Linux amd64 环境执行。输出目录须尚不存在。

```sh
go test ./...
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/build_plugins.py --output dist \
  --release-base-url https://github.com/landuo/light-media-plugins/releases/download/build-REPLACE_WITH_SOURCE_SHA/
```

构建器运行各 worker 的 `--manifest`，并完整打包已声明的 Vue 前端资源。构建输入见 [build-plugins.json](build-plugins.json)。项目许可见 [LICENSE](LICENSE)，第三方许可和原始来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和各插件目录。
