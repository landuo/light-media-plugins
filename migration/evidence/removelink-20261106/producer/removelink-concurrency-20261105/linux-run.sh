#!/bin/sh
set -eu
cd /home/admin/light-media-plugins-migration-removelink-concurrency-20261105
test "$(cat TASK)" = lm-plugin-removelink-concurrency-20261105
mkdir -m 700 tmp
chmod 700 removelink.test
export TMPDIR="$PWD/tmp"
id
date -u
sha256sum removelink.test
set +e
./removelink.test -test.v -test.timeout=150s -test.count=1 -test.run='^(TestActualWorker(IndependentTimerAndObserverCallers|ObserverLanesSerialPerRootAndIndependentAcrossRoots|ObserverStartsBeforeInitialBulkScanCompletes|StopWaitsForIndependentObserverAndTimerWork|TypedSourceAttributeStopsOnlyItsObserver|StopJoinsTimerBeforeQueueFlush|TenObserverRootsFairWhileSixCallbacksBlocked|ObserverToOwnedFilesystemCleanup|ObserverRenameAndStopBeforeDue|ObserverRealTimerDoesNotRunEarly|MoreThan64LinksOwnerWaitsThroughLastEffect|LargeScrapeDirectoryAndFilteredCandidates|QueuedStopAndReloadFlushWithNewFlags|TransientAuthorityFailureStopsLaterEffects|UnknownWriteCancellationRetainsFactNoReplay|FreshStopFlushesUnenteredTaskWithoutReplayingUnknownNotice)|TestActualCleanupRootFlushesOver64LinksBeforeOwnerReturns|TestLinuxSourceObserver(StartFailure|ActualNativeDelete))$'
rlk_test_exit=$?
printf '%s\n' "$rlk_test_exit" > run.exit
date -u
exit "$rlk_test_exit"
