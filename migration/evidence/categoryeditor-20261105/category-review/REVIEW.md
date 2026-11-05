# CategoryEditor independent source/target audit — 2026-11-05

Status: **worker behavior review passed; target-repository real-host acceptance pending coordinator evidence; final SDK binding independently checked**. No product source edits, production imports, NAS writes, deployment, commit or push were performed by this reviewer.

## Fixed inputs

- Installed plugin source: `work/migration-20261105/source-snapshot/categoryeditor/__init__.py`, local content-baseline commit `270ae0bcbf1d270b916ca9b14f8bffff9b1938d0`, SHA256 `24a8109b5c15bb73b845e42653933d09eb83b608a53303fbab9ebff39b801c27`. This directory contains one behavior file; no extra CategoryEditor frontend/support files were found.
- Target: `/Users/accidia/projects/light-media-plugins`, branch `codex/installed-plugins-20261105`, starting HEAD `4453f821ba32d5d4cc949e68d08d970e6ee7c975`. Main is the fixed delivery branch; no new release/publication authorization is inferred.
- Read-only host: `/Users/accidia/projects/light-media`, clean published commit `75e13686a0e3df05ac251e359303ef3fd5971cf6`.
- Current live helper, collected read-only by the coordinator: `work/migration-20261105/host-reference/app/modules/themoviedb/category.py`, SHA256 `1c0ec53b78caa3a4949dd970931f38430c67c9d46ea2e16c3cc00950fb24c2b2`. This reviewer verified exact byte equality with the 2026-10-20 archived helper used by prior oracles. The prior test outputs remain unchanged.
- Current live builtin default `/app/config/category.yaml` is 5,298 bytes, SHA256 `1095b3aeb315569f541fded31bc77f43fa625cb9ac4844e3a28ba7d7868b2303`, and compares byte-for-byte equal to the pinned host embedded default. Live core/config.py AST confirms ROOT_PATH=/app and INNER_CONFIG_PATH=/app/config, distinct from Docker active user CONFIG_PATH=/config (or configured override). This audit never substitutes the active user policy for the builtin default.
- Frozen SDK origin SHA256 `00961b4882382db60785200b8ee14c04310939c7a376fc8a00f66025a77a54e1`; production-set digest `46bce3cfb0e8b8f42fbc4fa3f53e90e1fe5e8d421cc229be724a6063c1e162f0`. This reviewer independently checked all 84 listed files against pinned host Git objects after allowed import relocation, validated SDK evidence hashes, and reran CategoryEditor unit tests with the SDK unchanged before/after. See `live-dependency-binding.json`.

## Independent discovery and mapping

| Original source branch | Target and finding |
| --- | --- |
| Class metadata lines 9–29 | Actual `go run ./cmd/category-editor --manifest` metadata matches name, description, icon, version 1.3, author, author URL and order. `auth_level` omission follows the task exclusion. The original config prefix is replaced by the chosen host's per-instance binding. |
| `init_plugin` lines 31–50 | `Plugin.init` accepts raw config, preserves existing members on falsey config, uses Python JSON truthiness, and retains raw enabled/content spellings. Truthy non-object config fails before assignments. |
| Enabled branch lines 37–50 | Exact order: write user YAML → helper init → local systemmessage → member enabled=false → full update_config. Failure stops following operations without undoing prior writes/messages. False/None update returns do not count as errors; exceptions do. Explicit repeat init repeats effects. |
| `get_state` lines 52–53 | Returns raw member, including null/non-bool values after assignment or failure; no forced bool conversion. |
| `get_form` lines 63–117 | Source AST and embedded `form.json` compare equal. Original VSwitch, VAceEditor modelvalue/lang/theme/30rem properties and tuple shape are retained. Reads the host default resource on every call, never member/user YAML. |
| `get_command`, `get_api`, `get_page`, `stop_service` | Explicit source `pass` returns null; target does the same. Stop does not reset state or change files/config. |
| Data, schedules, events and lifecycle | Source defines no KV/file-data API, cron/service, event decorator, command, API endpoint, dashboard or background job. No ordinary event has been removed. Inherited base behavior is the explicitly selected current host SDK contract, not an omitted business feature. |
| Clones | One business implementation; config/update callbacks resolve the bound calling instance. Global category.yaml/helper are intentionally shared resources in the source; independent clone config does not imply a private classification policy. Real clone lifecycle is a host obligation still pending the coordinator's new evidence. |

The target's CategoryEditor `.go`, `form.json` and executable main are byte-for-byte equal to the pinned current host equivalents after only module-import relocation. `static-audit.json` preserves the initial product/test/build/host snapshot; the later `live-dependency-binding.json` independently binds the final frozen SDK and newly collected live helper/default. Code/source identity does not grant automatic target-repository real-host acceptance.

## Executed evidence

1. `source_replay.py` parses/executes the complete fixed plugin module with synthetic `app.*` imports and real owned temporary files. No production module is imported. `CategoryHelper` is explicitly a recorder with fault injection, so these results do not purport to prove YAML parsing/cache behavior. Raw source observations are in `source-observations.json`.
2. `_replay/target_replay.go` runs the real target `Plugin.Handle` with synthetic scoped resources and real owned temporary files. It consumes the same independent inputs. Source and target compare **57 cases / 138 steps / 1,242 field comparisons, zero differences**. Fields include result/error, state, exact file bytes, ordered callbacks, messages, complete config update arguments and helper-call count. `comparison.json` is the machine result.
3. Covered cases include fresh defaults/noops; changed/empty/injected-read-failure/invalid-UTF8 defaults; disabled draft vs applied content; falsey and truthy config shapes; missing fields; raw enabled values; falsey and non-string content; large integers, Unicode/CRLF and unpaired surrogates; repeated enabled init; write/helper/message/update failures; and ignored False/None update return values. Error strings/types are recorded for source but are not claimed identical across languages.
4. The overlay mutation in `mutation_control.py` changes successful initialization to leave enabled=true. The same comparator rejects it with exit 1 and **70 differences**. Original observations are restored; the mutation is never applied to product files. Raw negative evidence is `mutation-comparison.json` and `mutation.log`.
5. Existing target package tests were executed before and after the shared SDK freeze with `go test ./plugins/categoryeditor ./cmd/category-editor -count=1 -v`; they pass (`unit-tests.log` and `unit-tests-sdk-frozen.log`). `TestWorkerProtocolSmoke` explicitly skips on this darwin/arm64 machine because its supported target is Linux/amd64. This is **not** counted as a passed worker-stdio or Linux packaging test.

Reproduce from the target repository root:

```sh
python3 work/migration-20261105/category-review/source_replay.py
go run ./work/migration-20261105/category-review/_replay/target_replay.go
python3 work/migration-20261105/category-review/compare.py
python3 work/migration-20261105/category-review/static_audit.py
python3 work/migration-20261105/category-review/mutation_control.py
```

The Go harness is under `_replay`, so `go test ./...` does not gain a test-only business package from this audit. Mutation source is stored as `.go.txt`, not compiled by ordinary package discovery. All temporary file directories are removed at process exit.

## YAML/error/cache and existing host adaptations

The source plugin itself never parses or validates YAML. It writes exactly supplied text (after `or ""`) and delegates to `CategoryHelper.init`. Source/helper and current host resource code were read independently:

- Normal nonempty root mappings replace cached movie/tv maps. Empty/falsey roots and ordinary parse failures preserve warm maps; cold maps begin empty. A truthy scalar/list root raises at `.get` after the write, retains previous maps for getters, and suppresses the notice/auto-disable/config update.
- Helper IO errors are caught in the original; an earlier truthy-root error remains observable on a later failed read. Getters do not reload externally changed files. Missing user YAML copies the bundled default. Current `media_category_runtime.go` explicitly models these states, including retained rootError and cache-only getters.
- Section/rule/condition shape errors can be deferred to category listing/matching rather than init. Current host preserves recorded deferred failures; matching uses ordered rules, all-condition intersection, exclusions and ranges. The target worker does not introduce an early YAML validator or second implementation of this logic.
- The selected host retains already approved safety adaptations: bounded bytes/counts/complexity, safe category directory names, regular-file/no-symlink handling and supported YAML structure/tag limits. Immutable embedded default-template packaging also differs from Python's externally mutable default file. The pinned host's final independent report and ledger record these as accepted/documented boundaries. This audit does not enlarge them or present them as strict Python equivalence.
- The newly collected current live helper/default are now byte-bound to the historical helper/default inputs. Historical helper oracle outputs remain historical executions; this provenance improvement does not establish current ruamel/WeakSingleton/message/config DB runtime behavior. Prior host acceptance is not relabeled as execution of this target checkout or as user configuration migration.

## Build and runtime

`build-plugins.json` selects `./cmd/category-editor` and `light-media.sdk-resources/v1`. The real manifest has no standalone frontend, because the exact form JSON is embedded in the worker. Existing Linux/amd64 builder runs the actual release worker's `--manifest`, then packages that Go executable and legal notices; no Python runtime is shipped. Python scripts are build/test tools only. The CI runs Go vet/race, real-worker transport tests and controlled packaging tests before release. Static review of these paths is complete; **this reviewer did not execute a Linux release build or publish an archive**.

## Remaining gate and recommendation

No genuine CategoryEditor worker omission was found in this audit, so no product implementation change is recommended. Keep this slice at `implementing`/acceptance-pending until the coordinator supplies real-host evidence from this checkout after the now independently checked shared SDK freeze: actual Linux package/manifest and install, browser form/save/apply/failure recovery, exact host policy bytes/category consumption/local message/config auto-disable, cold restart without replay, and clone identity/config/data/update/reset/uninstall isolation. Hash-bind those runs to the final SDK/product dependency closure. Do not use these unit/oracle results or the old host's acceptance as substitutes.
