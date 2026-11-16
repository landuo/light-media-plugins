#!/bin/sh
set -eu
cd /home/admin/light-media-plugins-migration-removelink-home-error-20261106
test "$(cat TASK)" = lm-plugin-removelink-home-error-20261106
mkdir -m 700 tmp
chmod 700 removelink.test
export TMPDIR="$PWD/tmp"
id
sha256sum removelink.test
./removelink.test -test.v -test.timeout=45s -test.run='^(TestSource312UnknownNamedHomeStopsBeforeUnlink|TestEmptyExcludeDoesNotNormalizeUnknownHome|TestSource312PathExpansionOrder|TestActualWorkerUnknownHomeKeepsSourceCatchAndObserverBoundary)$'
