from pathlib import Path
import json, subprocess
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
product=root/'plugins/categoryeditor/categoryeditor.go'
mutated=here/'mutated-categoryeditor.go.txt'
original=product.read_text();needle='p.enabled = json.RawMessage(`false`)';assert original.count(needle)==1
mutated.write_text(original.replace(needle,'p.enabled = json.RawMessage(`true`)'))
overlay=here/'mutation-overlay.json';overlay.write_text(json.dumps({'Replace':{str(product):str(mutated)}}))
observed=here/'target-observations.json';comparison=here/'comparison.json';saved=observed.read_bytes();saved_comparison=comparison.read_bytes()
try:
    run=subprocess.run(['go','run','-overlay='+str(overlay),'./work/migration-20261105/category-review/_replay/target_replay.go'],cwd=root,text=True,capture_output=True)
    assert run.returncode==0,(run.returncode,run.stderr)
    result=subprocess.run(['python3',str(here/'compare.py')],cwd=root,text=True,capture_output=True)
    (here/'mutation-target-observations.json').write_bytes(observed.read_bytes())
    (here/'mutation-comparison.json').write_bytes(comparison.read_bytes())
    (here/'mutation.log').write_text('Mutation: successful init retains enabled=true instead of auto-disable\n'+run.stdout+run.stderr+result.stdout+result.stderr+'COMPARISON_EXIT='+str(result.returncode)+'\n')
    assert result.returncode==1,'comparison failed to detect removed one-shot reset'
    differences=len(json.loads(comparison.read_text())['differences'])
    print(json.dumps(dict(mutation_detected=True,comparison_exit=result.returncode,differences=differences)))
finally:
    observed.write_bytes(saved);comparison.write_bytes(saved_comparison)
