# Third-party notices

## CategoryEditor business source

CategoryEditor 1.3 was written by jxxghp for MoviePilot. Its fixed source is
`plugins/categoryeditor/__init__.py` in
`https://github.com/jxxghp/MoviePilot-Plugins`, commit
`ce3357c0f2bb4e46f5ff9b72560505a33b26a362`.
The installed source SHA-256 is
`24a8109b5c15bb73b845e42653933d09eb83b608a53303fbab9ebff39b801c27`.

This repository contains a Go adaptation for the Light Media standard worker
protocol, not the original Python runtime. `LICENSE.upstream` preserves the
GNU General Public License version 3 text from that fixed upstream commit.
Author attribution is also retained in the worker manifest. The host performs
the actual category file write and cache refresh; its documented safety bounds
are intentional adaptation differences, not claims of identical behavior for
every input. No upstream icon image is redistributed by this package.

## Go and golang.org/x/text

The executable includes the Go runtime. Its copyright and license text are in
`third_party/Go-LICENSE`.

The only third-party Go module is `golang.org/x/text v0.43.0`; its copyright and
license text are in `third_party/x-text-LICENSE`, with its additional patent
grant in `third_party/x-text-PATENTS`. The module checksums are fixed in
`go.sum`.

## SDK provenance

`SDK_ORIGIN.json` identifies the exact complete-file SDK snapshot and permitted
import relocation. The CategoryEditor adaptation and this explicitly authorized minimum SDK
snapshot are distributed under GNU GPL version 3; see `LICENSE`. This grant
does not imply that the unrelated host application is public or GPL-licensed.
Go and x/text retain their original licenses as stated above. This repository
does not include the host application, private configuration, databases, or
original migration logs.
