import argparse, json
from agent import ROOT, Tools, MockModel, api_model, run
p=argparse.ArgumentParser(); p.add_argument('question'); p.add_argument('--data',default=str(ROOT/'data'/'documents.json')); p.add_argument('--mock',action='store_true'); p.add_argument('--history',default='[]',help='JSON 数组'); p.add_argument('--fail',choices=['search','read']); p.add_argument('--max-steps',type=int,default=12)
a=p.parse_args(); model=MockModel(a.question) if a.mock else api_model
print(json.dumps(run(a.question,Tools(a.data,a.fail),model,json.loads(a.history),a.max_steps),ensure_ascii=False,indent=2))
