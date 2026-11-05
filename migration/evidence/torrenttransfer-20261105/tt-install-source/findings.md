# Forced clone install against a parent-only index

The source rejects this request by exact requested plugin ID. No product change is indicated by the coordinator's negative force-install observation.

Actual source files were read from the original running container without importing the application or touching configuration/data: helper/plugin.py SHA a7455fbb0f0e09267476b2628459dcfd1af26a94e9fc4eea04b51e5f08dfdcba and api/endpoints/plugin.py SHA16e96285764587b266c07af21b6df140836c00f916d6626b87584a492a4031ce. Image/start are unchanged in manifest.json.

1. API install lines591–603 skips acquisition only for already-installed/nonforce; force passes the exact requested clone ID to `PluginHelper.async_install`. False result returns immediately at605–606, without statistics, reload or installed-list update.
2. Helper async package resolution2135–2143 checks the exact PID in the versioned index, then `.get(pid)` in default index. It has no clone-parent fallback. Sync resolution592–603 has the same exact-key rule.
3. Async install2728–2735 returns `(False,"TorrentTransfermusic 没有找到适用于当前版本的插件")` when package resolution is None; this precedes its destructive installation flow. Metadata lookup2793–2800 also uses `.get(pid)` exactly. The clone creation path is separate: actual core/plugin.py1905+ copies the source directory to the new clone identity; later installing/updating the source ID does not make that copied clone directory a parent-pointer implementation.
4. `install-identity-source-oracle.json` records five executed source-AST guard cases, including an actual API function call with synthetic parent-only index, installed clone identity and inert statistics/reload/DB receivers. Force fails without touching those receivers. Nonforce existing-clone succeeds by skipping installation, a distinct source branch. The harness never imports app, performs real install, writes plugin files, runs pip or contacts GitHub. Its local Python3.14 runtime is explicit; ordinary dictionary/API branch semantics are not presented as an actual original application install.

The coordinator's main6 completed transfer/timer/EACCES/clone/UI observations and its exit1 UI-wait timeout must remain classified separately from the later ordinary-main lifecycle continuation. This source guard proof does not convert that failed combined run into a passing exit status.
