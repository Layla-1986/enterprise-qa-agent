"""Rerun live examples with configured model. Writes outputs, never credentials."""
import concurrent.futures, json, os, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
cases=json.loads((root/'examples/inputs.json').read_text(encoding='utf-8-sig'))
def run(case):
    args=[sys.executable,'-X','utf8','src/main.py',case['question']]
    for flag in ('data','fail'):
        if flag in case: args.extend(['--'+flag,case[flag]])
    if 'history' in case: args.extend(['--history',json.dumps(case['history'],ensure_ascii=False)])
    result=subprocess.run(args,cwd=root,text=True,encoding='utf-8',capture_output=True,check=True)
    output=json.loads(result.stdout)
    (root/'examples'/case['file']).write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return case['file']+': '+output['status']
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for result in executor.map(run,cases): print(result)
