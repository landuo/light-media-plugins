# 启动观察失败：保留原失败，独立前提探针完成

没有重跑Main。仅只读本次exact root marker/BOM、exact owned container元数据、有限时间且exact task label的Docker events，及attempt3输出/owned-r2/runtime/evidence；没有读取DB/key/config或旧服务。

原attempt3的wrapper exit=-9是Docker客户端被其finally kill，不是已观测到业务assertion失败。exception是“owned container did not reach observable running state”；记录时owned_container_remaining=true。后来的exact ps为空、inspect/`container inspect`都为NoSuch，只能证明读回时已经清空，不能倒改原record为false。

原Docker events真实保留：create18:05:50.019731Z、attach50.024496、start50.677631、kill(signal15)54.819592、die(exit2)18:06:01.739015、destroy01.849478。四ELF仍与7428版本BOM匹配。由record文件mtime18:05:59.921406减其monotonic seconds13.969919，估算wrapper启动18:05:45.951487；create约+4.07s、start约+4.73s。结合代码40轮/50ms及两轮client wait各5秒、signal15事件，强支持“短观察与早期None清理早于真正创建，随后client终止中断了容器”的竞态推断。**原每次inspect exit/stdout/stderr没有记录，不能追签旧轮每一条错误为NoSuch**；新读回的NoSuch不是旧poll raw。

业务证据只到Main2启动：bootstrap、首次Main导入、四个offlineCLI阶段和第二代Main初始化；没有插件安装、签到成功或最终完成marker。因此不计本轮Native Main通过，也不把它误报为业务代码红。

按Root明确授权只执行了一次独占无bind sentinel：immutable333、networknone、read-only root、UID1000、capdrop/no-new-privileges、tmpfs，入口仅Python print+sleep8，不导入App/不启动Main/worker。执行前先本地compile/symtable，使用单一monotonic30s观察deadline；每次inspect保留实际exit/stdout/stderr及wall/monotonic耗时。

实际17.946秒exit0：17次NoSuchObject，最晚约+2.734秒；+2.915秒首次可见但为created/Pid0；+4.236秒首次观测Running，同一个fullCID `87f47666d7cd867b3b64ac2e9353839529b75bd333a194ee0a9f0745acd386c2`。sentinel正常打印/结束，auto-remove，exact task label最终0，无NAS绑定目录或自建ELF残留。源输入、完整inspect/events原输出在sentinel.*中；不是第四次Main或插件业务验收。probe的备用清理代码未在正常自动移除路径被触发，不把它当成Main异常清理验收。

已直接否定“Docker run发出后短固定循环内必须可inspect/Running”这一环境前提。候选修正应使用单一30s monotonic deadline，记录每条inspect，允许created尚未Running；不能仅增加循环次数。首次None不证明不会迟建；失败收尾须协调Docker client结束和exact task label/full ID，严格复核owner后停删，未知状态必须保留为failure/unknown。仅看到Docker客户端退出或一次ps空，不足以宣告全过程没有容器。

我此前只做语法/绑定/异常路径静态审查，没有验证2秒可见性的环境假设和迟建清理交错；此限制现已由实际证据暴露并明确补记，不把早期静态批准升级成运行成功。原v2/body2230与历史输出不修改。新的30s候选仅可另做静态审查，暂不运行Main。
