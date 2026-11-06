# Independent finite runtime review — Main R2 pass, global drain cause remains unverified

The exact R2 actual Go Main test passes25.33s on the reviewed old host8ea38cff / worker2b77bc3d / updatede38f1918 / CLI525e3440 / drivera2d0a15d tuple. The wrapper passes29.9246s, actual exit0, exception=None, unchanged BOM, exact container gone. This finite runtime evidence is accepted for the actual CLI, private-init/cold observations, ordinary Web command/history/broadcast, same-version executable update, reset isolation, public timer firing/outcome and native-ID site-delete/uninstall effects described below. It is not whole ASI/UI/live PT/private migration acceptance, and explicitly does not establish the global-drain cause.

Bound launch review7531464dca3d47cc0398394b1893b48c4da1e99ff2b0b9829bf05acc82ed00e8 and executed driver sourced87067940fc58353a3e86984bc6430502bafafd3a95df14208c3ae01c1f9c694 are preserved. Runner91f4/BOM032c and the five ELF hashes are not rebound to a later public-drain candidate. Recorded before/build/runtime7064 maps agree; the five binaries remain stable. Runtime raw contains98 observations, not98 accepted features. No Main/App/source rerun or true/NAS/ledger write occurred in this review.

## Source contract → actual observations

| Contract | Actual evidence | Finite conclusion |
| --- | --- | --- |
| Fixed native-source consumed subset; original source501 maps to existing Go local1 | Real offline Go stdin CLI states validated/ready/imported/already_imported, writes0/0/2/0, zero queued jobs/external calls; real form contains named numeric501 | Actual synthetic owned CLI→storage→getter/form path works; not original private data migration |
| Installed270 init_plugin private-onlyonce +3s and fixed965 config wait contract | onlyonce persisted false, physical TLS callback barrier, config request still pending after200ms, then successful page after release; source once not replayed over3500ms after first cold start | Observed private-init/cold result on this tuple; not a new private/global shutdown proof |
| Source get_page selected no-history semantics | Disabled selected clone is a full pending row, config remains enabled=false/selected501 | Prior wrong VAlert assertion is closed without changing product behavior |
| Ordinary message.web → command → PluginAction broadcast; enabled classes only; stored retry controls next round | Four actual Web requests; source user/channel/history and per-instance callback logs below | Source-derived bounded command/history/broadcast behavior passes |
| Fixed force install same2.9.15 replaces actual base code, cloned copy remains independent | Base122→136, clone115 remains; installed file and /proc/exe digest checks execute; config and successful pages retained | Actual hot executable replacement/isolation works; variant changes only owned manifest description |
| Reset affects only base; public interval0.001h | Base becomes exact empty/default page, clone still successful; real public callback arrives3640ms later and writes new base history, survives cold start | Actual interval firing and cooperative outcome pass; drain cause is separate |
| Original ordinary SiteDeleted removes last selected501 and disables | Before delete base enabled with501; after real managed-site DELETE config enabled=false/sign_sites=[] | Actual normal delete→source public-ID reverse mapping→ASI consumer effect passes for this case; not every raw event-payload contract |
| Source clone uninstall removes its code; ordinary base uninstall retains code | Actual clone code directory Lstat absent, later process snapshot has base only; actual base code Lstat present after uninstall, waitDead(base), final live-worker snapshot empty | Code/live-process policy is observed, beyond HTTP acknowledgements; this run does not independently read raw post-uninstall config/KV to certify data deletion/retention |

## Four commands and actual persisted replies

The independent original4f8 source oracle is unchanged. Base history is explicitly reset before first command; clone is disabled initially. Clone is then enabled. Both use empty retry first, then nonmatching nonempty retry: third round consumes prior stored [501], fourth dedups.

| Web command | Actual consumers in production logs | Cumulative attendance operations | Persisted records | Incoming/start/complete |
| --- | --- | ---: | ---: | --- |
|1 |base only |2 |3 |1/1/1 |
|2 |base+clone |4 |8 |2/3/3 |
|3 warmup |base+clone |6 |13 |3/5/5 |
|4 dedup |base+clone |6 |16 |4/7/5 |

Attendance includes the earlier one private callback. Actual host logs independently tie the1/2/2/2 callback deliveries to AutoSignIn/AutoSignIncmd, rather than trusting a summary boolean. Complete physical peer raw has exactly7 GET /attendance.php, all expected owned Cookie/UA and verified TLS: private1+Web5+timer1. All proxy requests are exact owned repository GETs or the owned hhanclub.net TLS CONNECT target. No foreign request succeeds.

All incoming Web rows have source/userid category-owned, text /site_signin and action0; outgoing rows have source=None, same user/channel and action1 start/completion titles. notify=false produces no detailed SiteMessage or timer Web replies. The raw host log also contains12 notification_failed events corresponding to the Web outputs. Therefore this review signs persisted local Web replies and consumer behavior, not external notification-provider delivery. No original raw error is hidden or reclassified as successful delivery.

## Update, cold, reset and process limits

Observed actual live executable PID snapshots are82 →100 for private cold recovery; before hot update base122/clone115; after hot update136/115; after base reset/timer configuration143/115; after stop none; after cold start161/167; after clone uninstall/source delete base161 only; after base uninstall none. The executed driver reads both installed binaries and /proc/PID/exe and compares base against e38f1918, clone against old2b77bc3d, hot and cold. These are actual executed file/proc assertions tied to the passed ELF/source, not newly invented standalone raw hash records.

Base/clone successful pages after hot update and the populated clone page after base reset are directly in raw. Base's new timer history is directly queried after cold start; no extra attendance occurs on cold restart before it is disabled, and messages remain16. Both cold executable hashes are checked. This run does not query clone page/config again after that final cold restart, so clone cold-history/config persistence is not separately accepted by this packet. The original source/other historical proofs retain their own tuples.

Uninstall response data_retained=false/true is retained as an acknowledgement; the accepted physical assertions are clone code removed/base code retained and live worker disappearance. Clone has no separate waitDead call immediately at its DELETE; its subsequent /proc executable snapshot lacks it and the entire container exits cleanly. Base has an explicit waitDead after its final uninstall. Do not inflate this into every intermediate PID/retention property having a distinct observation.

## Global stop: outcome only, not cause

Raw public_timer_global_shutdown_complete and callback_completed_before_exit=true are preserved unchanged. The actual factual result is: a real timer callback is in flight, the test calls h.stop, observes non-return for200ms from that call, releases the owned HTTP gate, later sees successful new history after cold start, and all observed workers/Main exit cooperatively.

The test has no observation that the real scheduler has entered stopping/draining before the200ms or the gate release. Existing code backup and HTTP shutdown can occupy that interval. The callback may complete naturally before cancellation/revocation, so this passing trace cannot distinguish correct active-job draining from the known public-drain defect. It does not overturn the separately identified old-host/App failures or settle private global-close risks. Global drain remains unverified by this Main. No record fields or test results are rewritten to conceal that limitation.

For a subsequent fixed-host Main, observe an actual production scheduler-stopping entry after irrelevant backup/HTTP phases, ensure the callback is still active at that boundary, then require the additional wait/release/history/process ordering. A real ordinary stopping log analogous to the original Scheduler.stop logger is a valid observation point; a sleep after SIGTERM alone is not. The new public-drain candidate requires its own independent review and current Main evidence, not a retrospective relabel of this25.33s run.

## Isolation and preserved evidence

Live inspect verifies UID1000, netnone, read-only root and exact owned/bundle mounts. Network readback has onlylo and no IPv4 routes; final full immutable ID, name and task-label queries are absent. Outer uploaded only the changed driver; all four product binaries are unchanged. Exact raw stdout/stderr, wrapper/inspect/network data, all4 host logs/98 observations and the recorded build/runtime bindings are copied into this independent packet. Python is only an owned metadata/source verification helper; server/worker/importer are Go. No old DB, production service, real PT or external recipient was used.
