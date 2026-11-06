# Independent R5 bounded acceptance

Actual R5 passes14.74seconds (command wall14.77s), no skipped root. Host b0a9a175 and worker a4524236 match R4 byte-for-byte; only driver4114b0d7 changes. All three build before/after snapshots are equal (P worker/driver4015, H host16707 recorded inputs). This review reads the actual raw, exact test/helper source, compiled binary hashes/buildinfo and one post-run marked owned-root metadata query; no Main rerun, compilation, source/SDK/ledger edit or deployment is performed. Current local commit03f39c4 does not replace those actual binary/input bindings.

## Observed lifecycle

| Stage | Base worker | Clone worker | Actual checked effect |
| --- | --- | --- | --- |
| Clone then once config save |2680611|2680669|Two workers/code directories; save retains both PIDs.|
| Cold stop/start |2680707|2680715|Both old workers joined; no workers while stopped; Main2680553 cleanly exits and2680696 starts.|
| Ordinary base uninstall |absent|2680715|Old base joined; both code directories retained; clone remains.|
| Same-repo reinstall |2680727|2680715|New base; exact saved false-once config and successful same-day source page restored; clone remains.|
| Base reset |2680765|2680715|Old base joined; new base default config{}/exact empty page; clone worker unchanged.|
| Clone uninstall |2680765|absent|Clone joined and its code directory removed; base/code remain.|
| Final ordinary uninstall |absent|absent|Base joined; ordinary code directory remains. Both Main/worker final joins complete.|

The pui_worker_pids records are reuse of a generic /proc/readlink observer, not PluginUnInstall business execution. Six distinct worker PIDs are all included in final waitDead checks, followed by actual Main clean exit before the final physical peer record. code() reads actual Lstat paths; these effects are supported by bound test assertions plus a post-run read-only metadata check, not uninstall HTTP acknowledgement alone.

Source linkage remains installed ASI270ae0 init82-134, generic1856-1916, __do histories1648-1738, page759-771/1441-1529; fixed MP8a83efe endpoint install576-624, reset739-761, uninstall992-1030 and manager stop156-190/reload641-651. Target H plugin_original_config/reset/lifecycle/install/uninstall and P autosignin/plugin/config/page implement the corresponding actions. Original object replacement becomes Go SDK worker replacement; this OS process adaptation is explicit.

## Functional evidence and limits

There is exactly one physical GET /attendance.php at3.036474844seconds, with the exact synthetic Cookie and Owned-ASI/1 UA. Host site.updated's three homepage/favicon observations remain separate. The named base success chip and11月6日 success dot appear before cold, after cold and after ordinary reinstall; clone retains source-exact empty state. Same false-once config survives cold and ordinary uninstall/reinstall. Reset then produces config{} and exact empty page. Ordinary retained=true and clone retained=false flags agree with fixed source policy.

Post-cold no additional attendance is observed for3500ms. Reinstall has only 0.701seconds of remaining observed tail before reset/final shutdown, so it is not another independent3-second no-replay test; original successful-day dedup also prevents using no HTTP as proof sign_in never ran. The retained history evidence concerns this fixture's config and rendered successful-day record, not every unseeded plugin KV or file. Reset proves base replacement and unchanged clone PID; an empty clone provides no separate seeded clone-data retention test. Lstat verifies code presence/removal, not every code file's byte identity. Whole AutoSignIn, realPT, browser/OCR/UI, updates or23-instance completion remain outside this acceptance.

## Final readback and cleanup

A read-only query of the exact marked own R5 root finds installed flags0/0, no plugin_values in either synthetic namespace, ordinary code present, clone code absent, no own executable process and all eight recorded Main/worker PIDs absent. No DB/private payload/key is exported. Binary SHA/buildinfo are preserved; local lsof finds no open handles. This review needs no ELF or runtime retained. Root may release redundant r5 driver and synthetic runtime after preserving raw/recipes/hashes; keep one current H/P pair only if the next gate will reuse it. cleanup-plan.json lists exact own root, marker and guards. No cleanup is executed here and no production NAS artifact is included.
