# 首次 Native Main 实际尝试：有限诊断，不是通过

仅只读核NAS exact root `/home/admin/light-media-plugins-root-asi-native-20261107` 的两处marker和四ELF BOM；只取actual.stdout/stderr及owned/runtime/evidence六个文件。未取runtime数据库、key、配置、CA或真实旧服务数据。容器名称精确查询为空；本审查没有启动、停止或重跑Main。

原driver实际FAIL14.09秒，报foreign proxy origin 127.0.0.1:41037。该authority与evidence内安装请求 `repo_url=http://127.0.0.1:41037/index` 精确相同，是本测试自建可执行仓库，不能当成未经授权外域的证据。

原TLS peer的 `connects` 在验证method之前记录所有代理请求的Host，原raw命名 `CONNECT` 因此不证明这些请求真实为CONNECT。根据宿主源码：originalPluginInstall→acquireOriginalImplementation→originalPluginHTTPClient(repositoryFallback=true)→artifact GET index/worker，显式代理遇403会fallback普通环境路由。两次owned repo authority与这两次正常获取尝试一致，但原raw没有method/URI，不能据此独立确定具体path，亦不能说已经证明是图标/后台调用。新夹具应记录method/host/RequestURI，只允许自己的exact repo authority/URI；只有hhanclub.net:443的CONNECT路由到自建TLS peer，不能开放任意loopback。

原失败证据还直接支持：四次实际Go CLI返回validated/ready/imported/already_imported及counter；三代Main启动/正常exit；实际form选项501；onlyonce已false；真实自建TLS attendance仅一次、Cookie/UA精确；200ms private_init_waited记录；两次配置/成功页（本审查独立重新核named签到成功chip、首日success dot、1/1）；worker PID71→88、冷启后3.5秒未再次attendance。它们是此次失败前的有限观察，不是整条链完成。源三秒和private等待的具体旧assert执行顺序只引用SHA绑定的历史driver；不把当前改过的driver倒签。

Root曾在执行后修改夹具源，现 `attempt2-native-run/source-reconstruction.json` 用已知后续fixture编辑的逆向恢复，两个SHA均精确命中原after-build-inputs：driver428f74f4、ownedTLS fc5120e2，旧ELF97e544e5保留。已独立验证恢复字节。自己的old-inputs目录最初保存的是当时可见输入，部分已是未运行新版本；historical-source-binding.json已明确区别，实际旧源以historical-source下这两份精确SHA为准。

未执行尾部：site delete事件、配置选择清空、uninstall/PID/code和native_source_Main_complete。旧driver还在disabled状态期望SiteDeleted被消费，这是第二个未执行的夹具前提问题。固定manager按get_state禁用整class，事件safe invoke跳过禁用handler；应在删除前显式enable，确保事件准入。**删空后enabled=false仍正确**：ASI.__remove_site_id2045–2051会在原非空列表被清空时设置_enabled=False。我最初只看site_deleted主体、建议删后保持true，漏读这个helper尾部；该建议已撤回并更正在runtime-diagnosis.json，不修改原source/raw。

wrapper两次错误：attempt1广义ROOT替换破坏OWNED_ASI_ROOT键，整个Python脚本parse即失败，没有Docker/Main执行；attempt2修sentinel后仍遗留NAME两处未绑定，Popen之后在inspect处NameError。原Go driver继续执行并最终失败，旧wrapper无finally、没有自己的live-inspect/network/command收尾记录。语法compile不能发现NameError；自己的只读symtable检查已对原两脚本准确检出syntax错误及NAME未绑定。

新runner最初5fb1的finally仍存在final ps/BOM读异常跳过command，以及stop失败未force回收的问题，已向Root指出。最后c3ad8098版本已独立核常量前缀、compile/递归symtable、嵌入python -c及完整try/finally：inspect/ps有timeout；stop失败后重验image/label/mount/immutable ID才rm-f；客户端join、最终query/BOM异常各自记录，检查后写command。其body SHA2230f84168ab57e0b5ccccb30c2555def091e53352e72c24fbd564f81b0ecf8f。新driver d06eabb5/helper56887601仅静态复核；新owned-r2/runtime和attempt3不覆盖原数据。当前CONFIG还指旧97e ELF，是BOM预览，不能据此执行或宣称新driver验证。Root重编后须只更新CONFIG前缀BOM，并重新核新ELF；外层必须只harvest存在的允许观察文件。新runner/driver均无实际执行证据，不把静态通过升格Main通过。
