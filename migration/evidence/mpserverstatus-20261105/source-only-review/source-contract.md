# MPServerStatus independent source contract (source before target)

Fixed source: source-snapshot270ae0bcbf1d270b916ca9b14f8bffff9b1938d0/mpserverstatus/__init__.py; SHA25663583e9706aeee31a181b2fefa4e80c793ae4f2b9a76c9efea5956f8b0043d90;1017lines. All1017lines read independently before inspecting target or author oracle/contract. Single source file, version1.4; no plugin resource files. Metadata includes nameMoviePilot服务监控/order99/configprefixMPServer_; original official authlevel excluded by user scope.

## Entrypoints/state

-45–53 init(config or {}) stores Python bool(config.get('enable')); clears all three instance caches. Form68–101 is one enable VSwitch, default current enable. Commands56–60 and API62–66 empty, get_state154 true/false, stop160 literally pass. No scheduler/service/event/data/DB/file write at all.
-103–130 page: disabled returns one div 插件未启用, no network. Enabled loads detailed snapshot then metrics false/error→unavailable tree, else full tree.
-132–152 dashboard: no enable gate, always status request; cols12/md8, refresh10; deliberately noDNS/TLS. Successful/unavailable compact6cards. Dashboard and page share last_sample.
- Class/default state35–43: fixedpublic https://movie-pilot.org/status, status timeout20, independentnet timeout5, DNSTTL60, TLSTTL3600, cachesNone. All cache state in memory only. Stop does not clear; init clears; no locks/whole-call serialization. Concurrent init may be followed by in-flight cache/sample refill.

## Request/order/errors

-166–187 exact order HTTP request→probe→DNS(ifdetail)→TLS(ifdetail)→request_error/not response gate→try parse+buildmetrics. Probe/DNS/TLS exceptions outside final parse catch can escape. DNS/TLS normally convert exceptions only inside their narrow try blocks. RequestUtils Response truth is requests.Response truth(status<400), independent probe.ok(200<=status<400). Thus e.g100 validparse can render success with probe.okFalse;399success;400false rendersunavailable evenvalidstub. Failedstatus/parse retain prior sample.
-189–210 timer starts/log before RequestUtils(timeout20).get_res. Any TypeError in constructor OR get_res retries once RequestUtils().get_res; any exception from either finalpath returnsNone/elapsed/str(err), logswarn. NormalNone→'网络错误'; nonNone error status is not classified here. No plugin-level retry of HTTPexception/None/errorstatus.
- Actual installed RequestUtils: independent actualstaticcapture cooldown-source/app/utils/http.py SHAf8d90a731717de14a822d8035a14486caba2e25d52018c87d6ec0d9fcd3b2b27; constructor330–374 timeout or20, sessionNone, proxiesNone, noUA/cookie/accept/referrer exceptContent-Type application/x-www-form-urlencoded; request397–464 usesrequests.request, verifyFalse, streamFalse, defaultheaders, timeout; get_res511–545 GET allow_redirectsTrue. SessionNone means no customsessionkeepalive retry. Requests/environmentproxy/decoding/redirect policy is runtime vendor dependent, separate required dependency, not an invented pluginconfig. HTTP verifyFalse and independentTLS verified handshake must not be conflated.
-315–338 probe uses headers/content/text falsey defaults, contentlength ifnonempty else UTF8textlength, raw.version10/11/20mapping, Server/Date/Content-Type defaults. HTTPDateparsedate_to_datetime formatting `%Y-%m-%d %H:%M:%S %Z`; errors return originalheader. Probe uses fixedURL and parsedhostname.

## Parsing/sample

-213–253 text(or'').strip().splitlines, eachstrip/nonempty; active/RWW regex case-insensitive, Unicode `\d` (decimaldigits,intconvert). Find first 'server accepts' case-insensitive with nextline>=3 numbers; take first3. Else first line with exactly3 numbers and case-sensitive exclusions 'Reading'/'Writing'. Missingvalidation orderactive→counters→RWW, originalChineseerrors. Extra/unrelatednumbers may legally qualify under exact sourcealgorithm.
-255–313 busy=read+write, dropped=max(accepts-handled,0), percentNone onfalseydenominator, raw divisionotherwise; no100%clamp. requests/handled ratio. now=time.time separatefromrequestelapsed. Existingtruthylast sample andpositive(now-prevtime) produces3rates; counterdecrease→thatfieldNone, equal0. Invalid/zero/negativewindow leavesallratesandwindowNone. Successful sample ALWAYS replaces timestamp/3counters even if window invalid. Python arbitraryintegers/floatconversionoverflow are sourceeffects, not fixedint64 assumptions.

## DNS/TLS

-340–376 DNS now capture beforework; ifcache and now-cachetime<60, returns exactcachedobject including cachedfailure. getaddrinfo(host,port,typeSOCK_STREAM), port parsed orhttps443/other80. dedupIP infirstresultorder (IPv4+IPv6), errorscachedwithips[]/elapsed/str. Parsedhostname/port occurs outsidecatch. Cache timestamp start, notend, nohostkey.
-378–427 TLS nonhttps immediately {enabled:false,error:''}, beforecachecheck. https ifcacheage<3600 returns sameobject. DefaultverifiedSSLcontext, socket.create_connection((host,port),timeout5), wrapSNIhost, nestedcontextmanagerclose. certnotAfter `%b %d %H:%M:%S %Y %Z`, replaceUTC, floor(total_seconds//86400) evennegativefraction; version or'-', issuer/subject helper. Any exception insidecontext→fullfailure record withNone days; cachedfailure andsuccess timestampstart. Parsedhostname/port outsidetry.
-430–444 certificate names: firstcommonName (includingemptystring) wins; otherwisefirsttruthyvalue, else'-'. NoSANfallback.

## Rendering/formatting

-446–536 compactrender alwayssummary+VRow6cards; responseDelay/active/waiting/busy/requestRate/acceptRate. Normal full538–613 summary+VRow12cards+2tables; unavailable615–655 summary+4cards+1table. NestedVuetifycomponent/props/order/text exactsource; no newtitle or controls. HTTPfullcard is color success even probe.okFalse ifparsevalid.
-658–818 summary uses truthy HTTPstatus and host defaults; statcardcols6/md3/smonlyiftruthy, subtitleor'-'; fullnestedVCol/VCard/VCardText/span/div/VIcon. Tablesrowsinputorder, noescape/sort/rewrite.
-821–845 safepersent/ratio falsytotalNone; delta<=0/decreaseNone.848–1017 sourcePythonformatrounding/sign/nonfinite/errorsemantics; seconds<1 inms .0f else .2fseconds, rateNone'待刷新', sampleNone'等待下一次采样', sizeB/KB/MBonly, IPSerrorwins/first3join+' ...', TLSdaysdisabled/error/None/value priority. Severitythreshold direction depends error>=warning; latencynotok→error evenNone, exact1→warning/3→error; TLS<7error/<30warning.

## Verification limits

This is original-source discovery, not target approval, not realHTTP/DNS/TLS execution. Original request helper is verified installed static input; Python vendor/runtime networking should be bound separately. No sourceplugin production import, no app import, no live configuration, no externalrequest. All later source execution will use ASTclass and synthetic dependencies, explicitly labelled runtime.

## Verified host invocation boundary

Actual captured host core/plugin.py1191–1221 dashboard metadata filters get_stateFalse and exposes only overridden dashboard hooks; direct dashboard1223–1274 looks up loaded instance and calls hook by signature count without state gate. MPS bound hook has0params so called with noarguments. It wraps3tuple as PluginDashboard render_modevuetify; exception→HTTP500. ActualAPI plugin.py703–745 exposes bothkeyed/unkeyed requests; disabled direct endpoint semantics therefore matter even when metadata omitted. SourceBase141–164 documents refreshseconds and optionalborder/title; MPS overrides onlyrefresh10. No independent MPServerStatus-specific serverroute is registered.
