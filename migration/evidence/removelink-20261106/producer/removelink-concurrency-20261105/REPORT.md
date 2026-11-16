# RemoveLink independent observer/timer repair

Producer is frozen for independent review, not ordinary-main acceptance. Fixed source RemoveLink2.18 `__init__.py` SHA22fb375e531378b3454607c7bca305b637abd60ee8ed69e14e32fbc2ddfc5485. SDK98/SDK_ORIGIN40e923 are unchanged; no host, PUI, registry, ledger, integration-driver or module file was edited. The coordinator owns Main4 and final platform/UI acceptance.

## Implementation and source chain

`operation.go` gives each source invocation its own Ops and notice failure barrier. It embeds the shared Machine but never assigns Machine.Ops, borrows a caller, retains a caller across yield, or selects authority from a goroutine. Direct Machine wrappers retain a default operation for existing source tests. The current continuation retains the existing24 actual RPC + one admission limit and fresh real Manager.Submit/SubmitCleanup lineage.

`machine.go`/`storage.go` use the source17 lock table: Created exists/stat/update under state; Moved separate pop/add/get/reinsert scopes; directory Deleted/keywords/STRM outside state; immediate hardlink handling under state. Delayed exists and initial scrap/event/history are outside state, recent inspection and link loop have separate state scopes, delayed notice is outside state. Queue mutex only selects, cleans/reschedules or snapshots/clears; source finally Processed has explicit queue synchronization in Go. Error recording has its own short mutex.

`watch.go` starts all configured native observers before the bulk state scan. Each observer has a serial event queue/one active callback; a separate timer callback can enter while an observer is blocked. A fresh invocation owns the actual callback/continuation caller. Typed source AttributeError (same text) closes only its observer; guard/cancel/opaque errors abort this runtime. Native close/pump join and all admitted callback bodies finish before stop/reload flushes tasks. Joining an active timer is the necessary Go authority/lifecycle adaptation; original Timer.cancel itself is not described as a join.

## Admission and fairness

Six is the maximum **active observer callbacks**, not the number of configured roots. Every native pump starts; an idle pump has no effect caller. A single coordinator can wait idle without executing effects. Admission rotates after the last admitted root; a continuously busy early root cannot keep taking a released slot ahead of later ready roots. A distinct timer reservation is independent of the six observer slots. With all slots blocked, other observer events queue until a slot is actually available, rather than creating unbounded effect-bearing owners.

Normal live work: six observer owners + six current continuations, one timer owner + one current continuation, and one current coordinator =15 entries; init/stop and each handoff have their own finite additional in-flight entries. This is not asserted to be a strict total entry bound: SDK worker removes its call only after handler/gate drain before publishing, while host removes only after receiving the reply and joining host callbacks. Publishing/drain tails are separately governed by the unchanged SDK32 hard admission. No scope, budget, or ordinary shutdown admission is enlarged. The producer does not claim a new ordinary-publication ACK guarantee in the frozen SDK.

Actual SDK ten-root causal test first blocks six independent Event callers. The timer completes its task while those slots remain occupied. It releases only the sixth slot; roots7–10 complete before that sixth root's next blocked event takes the slot. Idle roots never create observer/timer effect callers. Removing the round-robin update compiles but fails this exact assertion. On Linux the scenario observed193 RPC, maximum25 per phase. This is measured protocol behavior, not a source-config six-root cap.

## Executed gates

- Final normal:218 test/subtest passes,8 platform skips,10.543s. Final race:218 passes,8 skips,43.786s. `cmd/remove-link` has no tests (compiled by both commands), explicitly separate from the226 business test/subtest outcomes. Vet passes.
- Both independently sealed assertions were rerun against the frozen producer with race: delayed-exists permits Created/re-hardlink protection; actual independent native observer source failure leaves its sibling alive. Source expected results reuse the independently executed/sealed Python3.12 oracle; no new Python execution is claimed here.
- Synthetic unknown-notice finally and ten-root fairness ran race×10:20 test passes. Original unknown-notice, guard, no-replay, active reload, cleanup-root over64-links and continuation limits retain their original assertions.
- Four separate mutations actually compiled with race and were killed by source-causal assertions: no round-robin, source observer error aborts siblings, observer admission deferred past startup, and stop omits callback join. Build/run stdout and exact mutation source are preserved; all four mutant ELFs were removed.
- Actual NAS Linux/amd64 UID1000 test executable:19 roots/24 including subtests passed, with inotify, native start ENOSYS/limits,75-link observed deletion, rename, stop, ten-root fairness,100-link and large scrape work, real10.120151175s timer, unknown/guard, and cleanup-root over64-link flush. It used an owned task directory/TMPDIR and the current independently compiled SDK worker, no cmd/server/App. The marker-checked remote directory and test ELF are removed.

`commands.json`, `verification.json`, `source-binding.json`, `current-files.json`, `changed-files.json`, and `compile-inputs.json` bind exact contents. Complete210 nonstdlib worker/test inputs were captured after the runs and rechecked unchanged after Linux/overlay runs; this is not falsely labeled a captured complete pre-run hash graph. Initial `before-files.json` captures the old54-file plugin family, not cmd; cmd main was already present and unchanged by this repair.

## Preserved failures and fixture corrections

`delayed-before.jsonl` and `observer-before.jsonl` retain actual independently reproduced old Go reds. `causal-sdk-first.jsonl` preserves a missing fixture helper compile failure. `full-normal-first.jsonl` retains old `test_event` bypassing native runtime join. `full-race-first.jsonl` retains concurrent fixture trace append races: production source permits these concurrent effects, so only the test recorder now has a mutex. No whole-task production lock was restored.

`full-normal-final.jsonl` is deliberately a failed historical generation: host cancellation returned before worker finally and the old synthetic test_snapshot read an intermediate queue. `full-race-final.jsonl` happened to pass that generation but does not supersede it. The final `*-joined.jsonl` runs include the corrected **test-only** synchronous test_tick lifecycle count/done barrier. Snapshot waits only that synthetic helper's actual completion; it neither blocks independent real timer/observer inspection nor clears an unknown notice barrier. All original assertions remain.

Earlier TT five-file logging freeze282307 remains immutable historical evidence. No old failed main run is relabeled. No ordinary Main4, browser, clone install/update/reset/uninstall, or whole-family acceptance is claimed by this report.

## Handoff and cleanup

Linux worker `remove-link-linux` SHA761676900627c7d5f8e6088b59818373922ddba9f41e3f4bfb9fd3746bbf0c8a is retained for coordinator Main4. Linux test binary SHAa64e8cca434e9af72fb222e59c8c6fa1870654e88d62170a2be3c1fde16cd927 is temporarily retained for independent replay. Remote task data and four mutant binaries are removed; cleanup.json records exact paths and reasons. Root/reviewer can remove the remaining local test ELF after replay. Report and raw logs contain synthetic paths/events only; no credentials or live state are copied. Source oracles and external historical certificates remain at their immutable original paths.
