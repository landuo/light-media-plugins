# AutoSignIn Main 验收的独立原版合同（有限切片）

本合同来自固定 MoviePilot `8a83efeacd3e26b82be495e17d50146e31c96a60`、已安装 ASI 快照 `270ae0bcbf1d270b916ca9b14f8bffff9b1938d0`（插件主文件 SHA `1d8329afc00bc218710e302e0eda915351731d41101df08fcf378e90440b9220`），及 immutable333 中实际 APScheduler 3.11.3。未读取新 Main 测试或以 Go 实现生成预期；没有运行目标 Go App，没有修改目标生产文件、账本、旧服务或私人站点。

所有新运行均为原镜像 `33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881`，`--network none`、只读根文件系统、UID 65534、无挂载、独占 `/config`/`/tmp` tmpfs。测试只使用内存库、合成站点返回、受控安装内容和通知记录器。原函数通过 AST 取出原样执行，装饰器仅移除注册副作用、保留 static/classmethod；这些是**原函数重放和实际 APS 定时/线程证据**，不是完整原应用或真实 PT 访问。原 Python 源码仅作为参考/证据，不进入产品运行依赖。

## 1. 普通 `/site_signin` Web 命令

源码链：

- `app/api/endpoints/message.py:111–148 web_message`：JSON `text` 经普通 Web 入口进入 MessageChain，`channel=MessageChannel.Web`；`source/userid/username` 都取登录用户名。
- `app/chain/message.py:164–278 handle_message`、`1170–1198 _record_user_message`：普通文本先保存用户消息；消息历史 `action=0`，source 为用户名，userid 为 username or userid。
- `app/chain/message.py:349–362` 普通斜线命令分支：发送 `CommandExcute`，携带 cmd/user/channel/source/processing_status。AI 分支及工作流按用户要求排除。
- `app/core/event.py:367–373`：普通广播入队；`433–468` 为处理器逐个提交线程池。API 的 success 是接收入队成功，不能证明签到完成；command processing status 也不能替代业务完成状态。
- `app/command.py:269–289` 构造命令，`442–473 command_event` 拆出命令/余下参数；`392–432 execute` → `291–349 __run_command` 深拷贝命令数据，在 action data 内加入 channel/source/user；有参数时另加 arg_str；`435–440 send_plugin_event` 发送 PluginAction。
- ASI `159–169 get_command` 只带 `action=site_signin`；`1531–1555 sign_in` 先验证 action，再检验配置的允许小时范围，随后发“开始站点签到 ...”，先签到、再模拟登录。通知/执行的成功不受传入 arg_str 改变。
- ASI `1577–1774 __do`：原 ThreadPool 映射、月日明细、每日 do/retry/results 写入、可选详细通知，最后才发该种任务的完成回帖并保存配置。

实际证据 `source-actual.stdout/json`：Web 的 channel/source/user/arg_str 经原上述函数到达 PluginAction；首轮单一合成站点得到成功历史，回帖为“开始站点签到 ...”→“站点签到完成！”。第二次相同日期、非空且不匹配的 retry_keyword、已完成且 retry 空时，只有开始回帖，`__do` 早退，没有第二次站点调用或完成回帖。**不能强制断言每次命令都必有完成回帖。** 源码还表明：未选择任何站点时也只有开始；小时范围不满足或 action 不符时在开始回帖之前返回（这三个附加分支仅源码定位，未在本组运行）。

实际证据 `message-actual.stdout`：执行原 Notification Pydantic 模型、PluginBase.post_message、ChainBase.post_message 和原入站历史方法。notify=false：一条入站 action0、两条出站 action1；notify=true 再多一条 `【站点自动签到】` SiteMessage。出站原 ASI 没传 source/username，所以它们为 None；开始/完成的 channel=Web、userid=用户名。默认 save_history=True，默认 link 指向 `#/plugins?tab=installed&id=AutoSignIn`。每条出站均先历史存储，再 NoticeMessage，再发送队列。详细通知不带 Web/channel/user，交给原默认通知路由；本组路由开关为受控 None，**不证明外部收件人选择或实际发送**。

分身前提：命令登记字典虽含 pid，发送的 PluginAction 数据不含定向 pid。ASI sign_in 也不筛 pid；普通 PluginAction 广播会交给所有启用的 ASI/分身处理器。`EventManager.__dispatch_broadcast_event` 只有 MessageAction 的特定字段会定向，不适用于这里。因此 Main 场景要么只启用一个实例，要么验证多个启用实例各自响应，不把菜单项 pid 当成命令定向证据。这项为完整固定源码链推导，未在新运行中启动两实例事件消费者。

## 2. 私有 onlyonce、在途停止及随后初始化

ASI `82–142 init_plugin` 第一件事是 `stop_service()`，之后才读取新配置、过滤站点、保存配置。onlyonce 时创建独立 BackgroundScheduler，登记 now(settings.TZ)+3 秒 date job；在启动 scheduler **之前**清 onlyonce 并保存配置。`2007–2018 stop_service` 先 remove_all_jobs，再在 running 时 `.shutdown()`，最后 scheduler=None；没有 wait=False 参数。

实际库默认：`BaseScheduler.shutdown(self, wait=True)` → executor.shutdown(wait) → `BasePoolExecutor._pool.shutdown(wait)`；BackgroundScheduler 还 join 自己的调度线程。源码/签名和各文件 SHA 在 `source-actual.json.library`。

`source-actual` 的原 init/date/完整 sign_in/__do 使用实际 APS 和 ThreadPool：第一次站点调用在登记后 **3.013 秒**进入；onlyonce 在触发前已为 false。在此回调阻塞于合成站点的受控屏障时，另一线程调用原 init，新 init 不能返回，插件内存 cron 仍为旧值 1；屏障释放后旧任务完成、历史写入，随后新配置 cron2 生效且 scheduler=None。第二条经原 PluginManager.__stop_plugin 的实际调用也证明：close→stop_service，stop 返回在回调完成之后。`_PluginBase.close:342–343` 本身只是 pass，不能按注释猜成关闭 DB。

固定 `app/api/endpoints/plugin.py:976–989 set_plugin_config` 比直接 init 多一步：**先持久保存新 conf，再 init，再 register_plugin**。因此等待时数据库不保证是旧配置；旧回调末尾 __update_config 可临时写旧配置，新 init 随后保存新配置。这里应验最终生效和副作用顺序，不能把本组“内存旧 cron”观察扩张为“持久存储始终旧值”。API 保存期间的完整并发 DB 序列本组只核源码，未执行真实数据库。

## 3. 公共 interval：实际触发、移除与整机关闭是不同合同

ASI `192–267 get_service` → `Scheduler.update_plugin_job:1338–1390` → APS 实际回调 `Scheduler.start:975–1041` → `sign_in`。公共服务没有 command event，因此不发 Web 开始/完成回帖；仍保留成功历史和开启 notify 后的详细通知。

`source-actual` 使用原上述完整函数、实际 APS：120ms interval 在登记后 **122ms**实际进入合成站点，逻辑任务 running=true。执行中调用插件 stop_service 时私有 scheduler 本来就是 None；随后原 `remove_plugin_job:1251–1301` 约 **51µs**返回，旧回调尚未完成。释放屏障后原 callback 完成并保存历史。remove_job 删除未来触发，不中断/等待已经运行的 callback。不能把该 API 的返回当在途 drain 完成。

相反，`supplement-actual.stdout` 执行原整个 `Scheduler.stop:1459–1474`：callback_enter→stop_enter→callback_finished→stop_return；默认 shutdown 确实等待公共回调，scheduler=None。记录字段 `event_cleared=false` 是对 `not event.is_set()` 的原始观察；原 stop 实际调用 `_event.set()`，并非清除该事件。该字段名不用于改变原预期。

固定 `app/startup/lifecycle.py:64–70 run_shutdown_step` 直接同步调用非协程 callback，无 wait_for；普通关机 `125–126` **先 stop_scheduler，再 stop_plugins**，之后才 worker client/module/message transport/log 关闭。工作流/AI 阶段按用户要求不迁移。原服务关机不预设“立即返回”。

重要的重试前提：ASI `1731–1733` 在 retry_keyword 为空时把 retry 设为全部本轮 selected_site_ids，即使本轮成功，下次 interval 也会重试。`source-actual` 实跑空关键词两次调用确实得到两次执行/两条月日记录。非空且不匹配关键词、已成功且 retry 空才会同日去重。Main 若要证明没有重复访问，必须明确这项配置；不能改源码预期以迁就新实现。

## 4. force 同版本更新

`app/api/endpoints/plugin.py:577–623 install`：force=false 且已加载 ID 时只兼容检查/安装统计，不下载，最后仍 reload；force=true 走 async_install，成功再统计和 reload。repo 空失败；准备失败直接失败，不调用 reload。`reload_plugin:563–573` → manager.stop→manager.start→普通 PluginReload → register_plugin（服务、命令、API）。新对象使用已保存配置初始化。

`PluginHelper.async_install:2689–2790` 不因插件 version 相等拒绝内容更新；元数据决定 release/filelist。`__install_flow_async:2805–2840`：非 force 先备份，均先 remove 旧目录，再 prepare，再依赖安装，最后持久备份刷新。失败时非 force 恢复备份；force 无备份时再次删除准备目录，不伪造成功。

`source-actual` 实际原 endpoint 四条件证明非 force 已加载、force 成功/准备失败/无 repo 的分支和 reload 顺序；网络安装助手为记录器。`supplement-actual` 进一步执行原 async_install+install_flow，使用 **真实 owned tmpfs 文件**和受控 metadata/download/dependency 回调，六条件证明：同为2.9.15的 old 字节换成 new 字节；force 失败内容删除，非force失败旧字节恢复。不是外网 downloader/GitHub/release 全链实测。

原 Python 同进程加载新 class/module，没有 Go ELF/PID 概念。Main 中同版本新 ELF 的不同 hash/实际新进程、旧进程退休、配置与历史延续，是 Go 独立插件进程架构下应观察的必要适配；仅 HTTP success、版本字符串或文件存在不足以证明更新实际生效。也不能把原 force 失败语义未经记录改写成已严格相同的 Go 回滚语义。

## 5. interval producer 接入已有 source_interval 的合同

`get_service` 的原行为不是毫秒/正数验证器：

- enabled 且 cron truthy、非五空格 Cron 分支，使用 Python `float(str(...).strip())`。普通 hours 分支 descriptor 只给 `trigger='interval'`、原 float hours、func；没有显式 start/end/timezone/jitter/next_run_time。`cron='0'` 返回 interval，APS 把零 timedelta 归为1秒；数值0/False/空串/None 是 falsy，走随机 Cron 分支。字符串 underscore 和 Unicode数字以真实 Python float 为准。
- 原 `get_service` 的转换错误由该方法捕获并只日志后返回 []。NaN/±Infinity/过大有限数已转为 float，会先返回 descriptor；宿主先移除旧定时、写入 logical _jobs，再在 APS.add_job 构造触发器时失败并记录系统消息。禁止提前以 MissingCapability 或正数范围校验改变阶段。
- `producer-actual.stdout` 给出20个原输入的类型/repr、float64 bits、原 descriptor、原日志和真实 APS pending constructor结果；随机时间内容在该探针内只作受控分支标记，不当随机算法证据。
- 复用独立 `owner-phase-oracle.json` 8条件：NaN/±Inf/±1e16 logical 已存在而 native0；360µs/0/-1h 创建 pending job。复用 source precision r3 的27 timedelta转换和53 trigger序列、负周期有界子进程的0 callback停滞；均按原分类引用，未把旧 target 通过升格为新 ASI consumer 通过。
- 实际 `_create_trigger` 对字符串trigger注入 scheduler.timezone；ASI 公共 scheduler 的 timezone=settings.TZ。隐式 start 是该 zone 的 datetime.now 加原 timedelta（civil 加法）后归一化，First 注册时的 now 仍用同一 timezone 对象。Python ZoneInfo 缓存对象身份、DST fold/gap 与 explicit fixed offset 不可混为 Go Location 指针。原普通 descriptor 不自行传 start。
- NaN/Inf 要用明确的有限 JSON 表示传原 float/位模式，不能输出非法标准JSON。保留 Python timedelta 精度及超 Go duration范围；不能先转 int64 毫秒。负周期原 Job._get_run_times 先完整收集 due-list，可能不进展；不得先派一个callback或伪造原验证异常。已有 Go owner 的有界取消/资源中止（零部分派发）必须保留为明确必要适配。

本组 image 进程 `TZ=Asia/Shanghai`（metadata-actual），而 private/public探针 scheduler被显式设UTC；ASI today/monthday 使用进程本地 datetime.today/now，不是都读 scheduler时区。验收日期必须使用对应原时钟来源，不能统一换成UTC。

## 验收用途和剩余边界

本包提供五个有限 source合同，不签 ASI整体或23插件完成。Main后续必须真实经过宿主入口，观察站点实际到达/完成、业务历史、通知、实际 ELF/PID、clone隔离和停止生命周期；不能以合成返回或200代替。宽 Cookie/UA/FSresponse、私有凭据迁移、外部通知投递、完整命令事件消费者、普通API并发真实DB、异常关机强杀不在本组新增实测。源码静态可达但未运行的分支已逐处标明，未作为新运行验收。

初始两次主探针分别因夹具漏传 SCHEDULER_PROGRESS_PREFIX、Command.pluginmanager 而失败；补充探针首次因夹具漏全局 lock 失败。原始 payload/stdout/stderr/命令都保存在 attempt1/、attempt2/、supplement-attempt1/，属于夹具错误，不冒称原产品红或覆盖原 raw。最终每个运行的确切输入字节、镜像、退出码和时长见 `*-command.json`。
