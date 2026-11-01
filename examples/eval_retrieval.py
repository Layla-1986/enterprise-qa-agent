"""Small synthetic retrieval comparison; run from any working directory."""
import json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from agent import Tools

def baseline(query, docs):
    def grams(s):
        s=re.sub(r'\s+','',s.lower())
        return {s[i:i+2] for i in range(len(s)-1)}
    q=grams(query); out=[]
    for d in docs:
        for p in d['passages']:
            score=len(q & grams(d['title']+' '+p['text']))
            if score: out.append((score,d['id']+'/'+p['id']))
    return [p for _,p in sorted(out,key=lambda x:-x[0])]

def evaluate():
    cases=json.loads((ROOT/'data/retrieval_eval.json').read_text(encoding='utf-8-sig'))
    docs=json.loads((ROOT/'data/documents.json').read_text(encoding='utf-8-sig'))
    methods={'baseline':lambda q:baseline(q,docs),'current':lambda q:[x['doc_id']+'/'+x['passage_id'] for x in Tools(ROOT/'data/documents.json').search(q)]}
    output={}
    for name,fn in methods.items():
        rows=[]
        for case in cases:
            found=fn(case['question']); gold=set(case['relevant']); matched=gold & set(found)
            rows.append({'question':case['question'],'expected':sorted(gold),'retrieved':found,'recall':len(matched)/len(gold) if gold else None,'false_positive':bool(found) if not gold else None})
        positive=[x['recall'] for x in rows if x['recall'] is not None]; negative=[x['false_positive'] for x in rows if x['false_positive'] is not None]
        output[name]={'macro_recall':sum(positive)/len(positive),'negative_false_positive_rate':sum(negative)/len(negative),'cases':rows}
    return output
if __name__=='__main__': print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
