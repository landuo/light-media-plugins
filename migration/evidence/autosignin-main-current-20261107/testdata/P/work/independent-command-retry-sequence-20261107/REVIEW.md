# Independent source addendum: ordinary Web commands and stored retry

This adds actual source-only evidence to frozen contract965068464af1bf76e955e73f747f8f66d9df6fd187fc88733c777090e72479b9. It does not change that packet or any original source/raw. Fixed MoviePilot commit is 8a83efeacd3e26b82be495e17d50146e31c96a60; installed ASI snapshot270 source SHA is 1d8329afc00bc218710e302e0eda915351731d41101df08fcf378e90440b9220. All18 inputs are exact verified fixed blobs or the preserved installed snapshot.

The immutable333 actual Python execution used netnone, read-only root, UID65534, cap-drop, no-new-privileges, owned tmpfs, and no bind mounts. Exit0 in14.259108 seconds. Exact owned label readback is empty. No original service/DB, target Go Main/App, private config, real PT, or external recipient was used.

The original selected source bodies executed are the Web endpoint, incoming message history, ordinary slash-command branch349–362, Command command_event/execute/__run_command/send_plugin_event, EventManager enabled gate, PluginBase/ChainBase outgoing messages, and installed ASI init_plugin/sign_in/full__do/history cleanup/config update. AST strips wiring decorators only. Queue, synchronous event delivery/module lookup, registry, memory stores, identity template, and successful synthetic SiteResult are controlled boundaries. The explicit reset boundary clears only the owned memory history; this does not verify a target reset API. The clone uses a distinct owned Python subclass with the installed ASI methods. Fixed class enable gating is executed; registry enable/disable state is supplied from original get_state according to the fixed manager contract.

## Actual sequence

Base first completes one private synthetic sign-in with a nonmatching nonempty keyword; its history has retry=[]. The actual negative control then changes only the keyword to empty: sign_in emits its start message but makes no second site call. init_plugin does not reset history.

For the four-command scenario the base history is explicitly reset, then base is enabled with empty retry; clone starts disabled with empty history. First command delivers only to base. Clone is enabled before the second. Before the third both are reinitialized with keyword `错误|失败`; their complete histories are asserted unchanged by init.

| Command | Enabled delivery | Actual cumulative attendance | Actual cumulative message records | Completion records added | Stored retry after |
| --- | --- | ---: | ---: | ---: | --- |
|1 empty keyword after explicit reset |base |2 |3 |1 |base[501], clone absent |
|2 empty keyword |base+clone |4 |8 |2 |both[501] |
|3 nonempty keyword warmup |base+clone |6 |13 |2 |both[] |
|4 nonempty keyword dedup |base+clone |6 |16 |0 |both[] |

Attendance includes the one earlier private base call; messages begin at the first Web command. Every command records one incoming action0 record. Each delivered enabled plugin records a start action1 record; completion action1 is absent on the dedup round. notify=False produces no detailed SiteMessage. Incoming source/user is owned-user/Web; outgoing source and username are the original default None while userid/channel are retained. Full records, order, per-instance history, events and timeline are in actual.stdout.

## Why the draft must keep a warmup

Installed __do1577–1642 reads previous `retry`, `do`, and successful results before executing. Its current keyword policy is written only after actual execution, especially1731–1733. Therefore changing empty→nonempty alone does not clear the stored [501]; one further actual round must consume that retry and persist []. The next command dedups and posts only starts. Testing a third command as immediately deduplicated would contradict the original implementation.

This is a finite source oracle for the corrected target Main preconditions, not target acceptance or whole ASI equivalence. The original command event is a broadcast action; the command dictionary's pid does not turn it into a per-plugin target. Thread/event interleaving is deliberately controlled and is not a source scheduler/concurrency acceptance claim.
