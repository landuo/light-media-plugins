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

## Go modules

The executable includes the Go runtime. Its copyright and license text are in
`third_party/Go-LICENSE`.

The shared SDK uses `golang.org/x/text v0.43.0`; its copyright and
license text are in `third_party/x-text-LICENSE`, with its additional patent
grant in `third_party/x-text-PATENTS`. The module checksums are fixed in
`go.sum`.

## SDK provenance

`SDK_ORIGIN.json` identifies the exact complete-file SDK snapshot and permitted
import relocation. The CategoryEditor adaptation and this required complete-file SDK
snapshot are distributed under GNU GPL version 3; see `LICENSE`. This grant
does not imply that the unrelated host application is public or GPL-licensed.
Go and the listed modules retain their original licenses as stated above. This repository
does not include the host application, private configuration, databases, or
private original migration logs. Controlled synthetic/source/main/browser evidence is
separately classified in migration/evidence; it contains no production
configuration or database.

## Installed plugin adaptations and MPServerStatus support

The installed TorrentTransfer1.10.3 and SiteStatistic1.9.7 business source was
written by jxxghp for MoviePilot. Their fixed installed content source, authors,
exact source SHA256, adaptations and evidence are retained in each plugin's
ORIGIN.md and migration/ledger.json. The content baseline is not represented
as a newly identified upstream commit.

The MPServerStatus1.4 Go candidate is adapted from jxxghp's installed source
SHA256 `63583e9706aeee31a181b2fefa4e80c793ae4f2b9a76c9efea5956f8b0043d90`.
Its fixed source/plugin behavior and pure codec/proxy helper reuse are described
in plugins/mpserverstatus/ORIGIN.md; this attribution does not claim acceptance.
It adds these exact runtime module dependencies:

- `github.com/andybalholm/brotli v1.2.6`: MIT text in
  third_party/brotli-LICENSE. A conservative complete-module copy of the
  unused flate subpackage's BSD notice is in third_party/brotli-flate-LICENSE.
- `golang.org/x/net v0.61.0`: BSD text in third_party/x-net-LICENSE
  and the additional Go IP grant in third_party/x-net-PATENTS. Only its
  proxy/internal-socks leaves are required here.

The pure encoding detector preserves CPython's PSF license/history, Unicode
LicenseV3 and chardet0BSD notice under plugins/mpserverstatus/encodingdetector/.
The finite requests proxy helper preserves the CPython, RequestsApache2.0
(including original NOTICE) and PySocksBSD texts under
plugins/mpserverstatus/requestsproxy/licenses/; REQUESTS-NOTICE identifies its
source and approved proxy-TLS adaptation. These tables/algorithms are Go source
and embedded assets; no Python interpreter or package is used at runtime.
The build allowlist must include all applicable notices in each corresponding
plugin ZIP and the selected release's third-party notice bundle.

## PluginUnInstall business source

PluginUnInstall 2.2 was written by thsrite for MoviePilot. The fixed installed
source SHA256 is `2210e9dea47eeccdc46208d515e45ce1222dcadf50dbfc63cbeb41f94e470487`
in the read-only installed content snapshot recorded by migration/ledger.json.
Its Go worker uses the existing GPLv3 SDK and x/text dependency, without a
Python runtime. Source algorithm, finite host adaptations and provenance are
recorded in plugins/pluginuninstall/ORIGIN.md. Author attribution is retained
in the actual worker manifest. No upstream icon is redistributed.

## AutoSignIn business source and image decoding

AutoSignIn2.9.15 identifies thsrite as its author in the fixed installed
MoviePilot source. The fixed installed
source inventory, source SHA256, runtime-free Go adaptation and original
attributions are retained in plugins/autosignin/ORIGIN.md and the single
migration ledger. The worker includes translated Pillow12.2 algorithms,
private Go/libjpeg and libwebp leaves, CPython Unicode/JSON/calendar helpers,
Requests behavior and the private MIT regular-expression engine; their
notices/licenses remain next to the implementations and in the ZIP allowlist.

Its image decoding uses golang.org/x/image v0.24.0 (BSD plus patent grant),
decoder-only private github.com/mububoki/jpeg2000 v1.0.0 (MIT) with
OpenJPEG2.5.4 arithmetic adaptation (BSD2), github.com/gen2brain/gav1d
v0.2.6 (BSD2 plus AV1 patent license), and decoder-only BSD source adapted
from github.com/hhrutter/tiff v1.0.7. The latter is a private source relocation,
not a shared module upgrade. plugins/autosignin/imagehash/ORIGIN.json and
NOTICE.txt identify exact versions, source inventories and license locations.
No Python, CGo or external codec process is used by the delivered worker.

The legacy image readers retain the selected Picsetgo MIT decoder leaves and
Pillow-derived format algorithms; legacycodec/PROVENANCE.json and
PICSETGO-LICENSE.txt identify the exact selection. The AVIF RGB conversion
translates libyuv fixed-point YUV constants and byte-plane interpolation;
imagehash/LIBYUV-LICENSE, LIBYUV-PATENTS and LIBYUV-AUTHORS retain its notices.
The BLP reader derives from the CC0 Pillow plugin; source attribution is retained
with the implementation. These are Go implementations, with no WASM or native
codec dependency. Root Go minimum1.26.4 is a build prerequisite, not a runtime
interpreter requirement.
