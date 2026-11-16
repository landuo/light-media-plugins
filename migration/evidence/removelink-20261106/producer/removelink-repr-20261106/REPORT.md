# RemoveLink Python repr and partial-init order delta

Current producer is58 files, `current-files.json` SHA70658b192fdae91d55f3addabdf91592dee545e49776bb347cfb8a943291774f. Previous concurrency freeze375c425883ee41fb263300a003060966bd9cdda73ebcc27fe0c9e86dcc9fe699 and every old raw log are untouched. No SDK98, host, integration driver, frontend, module, registry or ledger change occurred.

## Source and repair

The independent source reviewer first executed the installed2.18 init AST in fixed image333544 and observed3 actual directory-list repr differences, plus3 partial initialization cases. Both independent source oracles and original Go reds are bound by `source-binding.json`. The custom extension parser is called by source before `int(delay)`; ±1e400 leaves the new parsed extension list (or clears it), old delay77, old observer/queue/timer, and earlier enabled assignment. `types.go` moves only the existing Extensions assignment before delay conversion. Its existing TypeError/ValueError fallback and uncaught overflow boundary are unchanged. The new real Plugin.Handle tests retain the single initialization INFO and assert no stop/admission/flush.

`pythonLogStrings` now follows CPython string repr: single quote normally, double quote only when a single quote is present and double quote absent; escape selected quote/backslash; use named tab/LF/CR escapes only; retain printable Unicode; use lowercase hexadecimal x/u/U escapes of2/4/8 digits for other scalar values. It no longer uses Go strconv.Quote, whose bell/backspace/formfeed and non-ASCII formatting differ. Python3.12 and the current Go toolchain both use Unicode15.0.0; the test asserts the table version and verifies actual behavior rather than relying only on that label.

A new isolated source run executed the fixed image's **builtin** repr for all1,112,064 Unicode scalar values in4 quote contexts:4,448,256 outputs, SHA256 d1c5a884cd44630b3d0c7a66e761142dc673c83618c15e8706ec916cecfac04c. It also captured18 mixed string examples and4 list cases, covering quotes/backslashes, every ASCII control, separators/format/private/unassigned/noncharacters, BMP/astral and printable combining/non-ASCII. This is actual CPython runtime evidence, not target-generated expected output; the existing3 AST log cases are independently reused. Scope is valid UTF8 strings within the existing host IPC contract, not a new surrogate/invalid-filename transport capability.

The source run imported only standard-library json/hashlib/unicodedata/sys; network-none, read-only, UID1000, cap-drop ALL, no-new-privileges, disposable tmpfs and exact task label are recorded in `source-command.json`. Python code was stdin only, with no production mounts/app/config. Exact label container count after exit is0; no remote staging files existed. It is test evidence only, not a Python product dependency.

## Executed results

- Producer before-red repr:3 AST log subtests plus whole-scalar digest failed; before-red assignment:3 cases failed. Raw failed runs are retained.
- Targeted race:17 tests/subtests passed, including old overflow cases. Current normal:226 passed/8 platform skips,11.556s; current race:226 passed/8 skips,56.880s. cmd/remove-link compiles and has no tests. Explicit vet exits0.
- Original independent new assertions on the repaired producer:8 passed under race. First replay mistakenly used the reviewer's complete frozen57 overlay and therefore selected the old producer; its8 reds are preserved and classified. The corrected r2 overlay adds only the independent assertion file and leaves actual current production inputs in place.
- Exact227 compile+runtime-fixture files were captured before the final full runs and remain byte-identical afterward. `verification.json`, `commands.json` and `compile-and-fixture-inputs-{before,after}.json` record that binding. The new fixture is the single58th file; existing2 test files were extended.

Earlier375c NAS UID1000/inotify/timer and concurrency mutation evidence remains historical source-bound evidence for its original inputs. This new delta did not rerun Linux kernel tests or ordinary cmd/server/main; it supplies fresh Linux executables for coordinator Main4. Do not relabel the old native runs as execution of these new binaries. The source/function change is covered by current normal/race and exhaustive actual-source differential tests; platform/main/UI acceptance is still coordinator-owned.

## Artifacts and cleanup

Both builds explicitly use GOOS=linux GOARCH=amd64 CGO_ENABLED=0 and `go build -trimpath -buildvcs=false`. Worker `remove-link-linux` SHA4d4ea1a6ba02b7ac065a570663fa2ca1abdf2976fd35cb0e6d6e87e854a85e15; version-only fixture `remove-link-2.18.1-linux` SHA9cf06b9069ce16cbe29a1c098f09b26f21345f3840230f228d5639379a01ea69. Each is5,400,895 bytes. Update build overlays one complete plugin.go with Manifest.Version2.18→2.18.1; production plugin.go remains unchanged. Both ELFs are retained solely for coordinator main/review, with exact input/overlay hashes in this evidence. Frontend3 assets are unchanged and remain in the whole58 manifest.

Source container is removed; no test process or remote test directory was created. No additional test ELF was built. Historical375c retained artifacts are not overwritten. Current SDK_ORIGIN remains40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875. Public-safe evidence consists only of synthetic source cases, run commands, hashes and raw tests; no credentials/live state are included. Root/reviewer owns final acceptance and artifact cleanup.
