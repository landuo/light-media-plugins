from pathlib import Path
import os,subprocess,json,sys
r=Path.cwd();p=r/'work/migration-20261105/sdk98-impact-20261105';phase=sys.argv[1];files=['tests/integration/testhost_main_test.go','tests/integration/sitestatistic_helpers_test.go','tests/integration/sitestatistic_main_test.go','tests/integration/sdk98_impact_test.go','tests/integration/sdk98_impact_helpers_test.go'];env=dict(os.environ);env['GOFLAGS']='';over={'GOFLAGS':'','SDK98_IMPACT_HTTP_OBSERVATIONS':str(p/('main4-http-'+phase))};env.update(over)
if phase=='vet':cmd=['go','vet']+files
elif phase=='linux':cmd=['go','test','-c','-o',str(p/'sdk98-impact-main-tests-linux-amd64')]+files;over.update({'CGO_ENABLED':'0','GOOS':'linux','GOARCH':'amd64'});env.update(over)
else:cmd=['go','test','-count=1','-json']+(['-race']if phase=='race'else[])+files+['-run','^TestSDK98Impact(QBPeerSourcePostSelector|RemainingHTTPContract|AsyncHTTPCompletion|DelayedNotificationHTTP|ReloadAndConfigHTTP)$']
log=p/('main4-'+phase+'.log');err=p/('main4-'+phase+'.stderr')
with log.open('wb')as out,err.open('wb')as ef:x=subprocess.run(cmd,cwd=r,env=env,stdout=out,stderr=ef)
result={'command':cmd,'env':over,'exit_code':x.returncode,'stdout':str(log),'stderr':str(err)};(p/('main4-'+phase+'-result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(x.returncode)
