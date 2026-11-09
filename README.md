# Light Media Plugins

光影的 Go 插件源码仓库，支持 Linux amd64 和 arm64。分身由光影创建和管理，共用插件包，配置与数据分别保存。

## 在光影安装

1. 在「插件市场」添加仓库地址 `https://github.com/landuo/light-media-plugins`。
2. 刷新市场，选择插件并安装。支持源码安装的光影读取 [go-plugins.v2.json](go-plugins.v2.json)，按清单中的 Git 提交获取源码，用当前机器的 Go 工具链编译所选插件。安装和更新使用同一方式。
3. 在「已安装」打开插件配置。使用前按需配置站点、下载器和本地目录。CustomHosts 需要为光影容器单独挂载可写的 Hosts 文件。

源码安装需要光影宿主支持 v2 清单、可用的 Go 1.26.4 或更新工具链，以及下载 Go 模块的网络。市场卡片读取清单时无需编译。仓库中声明的前端目录包含随插件安装的静态页面资源。

历史 [v1 清单](go-plugins.v1.json) 和 Linux amd64 Release 继续供较早的宿主使用，保持最后一次二进制发布的版本。

### 聚合消息通知

在插件设置中选择「爱语飞飞」或「QQ Bot（腾讯官方）」。爱语飞飞填写 IYUU 令牌。QQ Bot 填写开放平台的 AppID、AppSecret，并选择私聊或群聊，填写该机器人的收件人 OpenID。腾讯平台需要允许机器人向这个对象主动发消息，配额及收件人设置也会影响投递。[腾讯官方 SDK 的主动发送说明](https://github.com/tencent-connect/qqbot-nodejs/blob/429a0f1b798f3b0fcef3679e207dbc0469a1df2d/USAGE.md#94-主动-push无-msgid)

两个渠道可以独立筛选通知类型。打开「测试一下」并保存会发送一条测试消息，发送结果可在插件日志查看。

## 更新源码清单

推送源码到 `main` 后，GitHub Actions 检查代码和两种架构的构建。工作流从临时编译的 worker 读取 `--manifest`，校验许可和前端资源，再提交源码清单。源码清单记录完整提交号和各插件入口，临时 worker 随 CI 作业清理。需要让已安装实例看到新版时，请更新插件的版本字段。

在 Linux amd64 或 arm64 上也可从干净的已提交检出生成清单：

```sh
python3 scripts/build_source_catalog.py --source-sha "$(git rev-parse HEAD)"
```

构建输入见 [build-plugins.json](build-plugins.json)。项目许可见 [LICENSE](LICENSE)，第三方许可和原始来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和各插件目录。
