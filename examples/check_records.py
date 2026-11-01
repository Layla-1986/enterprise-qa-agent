import json
from pathlib import Path
root=Path('.')
cases=json.loads((root/'examples/inputs.json').read_text(encoding='utf-8-sig'))
expected={'live_answer.json':'answered','live_conflict.json':'conflict','live_missing.json':'insufficient','live_rephrase.json':'conflict','live_followup.json':'conflict','live_failure.json':'insufficient','live_read_failure.json':'insufficient','live_changed.json':'answered'}
for c in cases:
 d=json.loads((root/'examples'/c['file']).read_text(encoding='utf-8-sig'))
 assert d['status']==expected[c['file']],(c['file'],d['status'])
 docs=json.loads((root/c.get('data','data/documents.json')).read_text(encoding='utf-8-sig'))
 passages={(x['id'],p['id']):p['text'] for x in docs for p in x['passages']}
 for citation in d['citations']:
  assert citation['quote'] in passages[(citation['doc_id'],citation['passage_id'])]
 if c.get('fail'): assert any(not t.get('result',{}).get('ok',True) for t in d['trace'] if isinstance(t.get('result'),dict))
 print(c['file'],d['status'],','.join(t['action'] for t in d['trace']))
