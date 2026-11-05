from pathlib import Path
p=Path('plugins/removelink/machine.go');s=p.read_text()
keep={'StateValue','currentConfig','applyConfig','put','pop','find'}
import re
s=re.sub(r'func \(m \*Machine\) (\w+)',lambda x:x.group(0) if x[1] in keep else 'func (m *operation) '+x[1],s)
s=s.replace('mu                 sync.Mutex','mu                 sync.Mutex\n queueMu sync.Mutex\n errorsMu sync.Mutex\n metaMu sync.Mutex\n defaultOp *operation\n timerWake func()')
s=s.replace('\n\tnoticeFatal        error','')
s=s.replace('return &Machine{Config: NewConfig(), State: []Tracked{}, Queue: []*Task{}, Watches: []Watch{}, Ops: ops, Now: sourceNow}','m:=&Machine{Config: NewConfig(), State: []Tracked{}, Queue: []*Task{}, Watches: []Watch{}, Ops: ops, Now: sourceNow}\n m.defaultOp=&operation{Machine:m,Ops:ops}\n return m',1)
# Shared diagnostic slices have their own short mutex, never an effect lock.
s=re.sub(r'm\.(Errors|SourceErrors) = append\(m\.\1, ([^\n]+)\)',lambda x:'m.recordError('+x[2]+', '+str(x[1]=='SourceErrors').lower()+')',s)
p.write_text(s)
p=Path('plugins/removelink/storage.go');s=p.read_text().replace('(m *Machine)','(m *operation)');s=re.sub(r'm\.(Errors|SourceErrors) = append\(m\.\1, ([^\n]+)\)',lambda x:'m.recordError('+x[2]+', '+str(x[1]=='SourceErrors').lower()+')',s);p.write_text(s)
