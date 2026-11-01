import json, os, re, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {'多久':'期限', '多长时间':'期限', '几天':'期限', '报账':'报销', '费用':'报销', '如何':'怎么'}
def norm(s):
    for a,b in ALIASES.items(): s=s.replace(a,b)
    return re.sub(r'\s+', '', s.lower())
def grams(s):
    s=norm(s)
    return {s[i:i+2] for i in range(len(s)-1)}

class Tools:
    def __init__(self, path, fail=None):
        self.path=Path(path); self.fail=fail
    def search(self, query):
        if self.fail == 'search': raise RuntimeError('检索服务不可用')
        docs=json.loads(self.path.read_text(encoding='utf-8'))
        q=grams(query); results=[]
        for d in docs:
            for p in d['passages']:
                score=len(q & grams(d['title']+' '+p['text']))
                if score: results.append({'doc_id':d['id'],'version_date':d['version_date'],'passage_id':p['id'],'title':d['title'],'score':score})
        return sorted(results,key=lambda x:-x['score'])
    def read(self, doc_id, passage_id):
        if self.fail == 'read': raise RuntimeError('原文读取服务不可用')
        for d in json.loads(self.path.read_text(encoding='utf-8')):
            for p in d['passages']:
                if d['id']==doc_id and p['id']==passage_id:
                    return {'doc_id':doc_id,'version_date':d['version_date'],'passage_id':passage_id,'text':p['text']}
        raise ValueError('文档或片段不存在')

SYSTEM = '''你是企业知识问答 Agent。每次仅输出一个 JSON 对象，不要 Markdown。你可选动作：
{"action":"search","query":"检索词","reason":"简短理由"}；
{"action":"read","doc_id":"文档ID","passage_id":"片段ID","reason":"简短理由"}；
{"action":"finish","status":"answered|conflict|insufficient|clarification","answer":"答复","citations":[{"doc_id":"ID","passage_id":"ID","quote":"逐字原文"}],"gaps":["资料缺口"]}。
必须先检索并读取原文；仅引用已读片段的逐字原文。充分检索以发现相关冲突；同一问题存在无法按适用范围或优先级消解的不同规定时列出双方引用并要求确认，不得自行选择。仅有单一无冲突证据可回答；不足则说明缺口，不能编造。对于上下文追问结合历史理解，但历史中的事实不是证据。确定回答前必须读取所有检索到的片段，并修复此前失败的同一工具调用；否则结束为资料不足或继续核查。工具失败时可更换动作或结束为资料不足。每步根据工具结果调整，不输出思维链。'''

def api_model(messages):
    key=os.environ.get('OPENAI_API_KEY'); base=os.environ.get('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/'); model=os.environ.get('OPENAI_MODEL')
    if not key or not model: raise RuntimeError('请设置 OPENAI_API_KEY 和 OPENAI_MODEL')
    req=urllib.request.Request(base+'/chat/completions',data=json.dumps({'model':model,'messages':messages,'temperature':0},ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as response:
        result=json.load(response)
    content=result['choices'][0]['message']['content'].strip()
    if content.startswith('```'): content=re.sub(r'^```(?:json)?\s*|\s*```$', '', content).strip()
    return json.loads(content)

class MockModel:
    """离线脚本模拟器，只验证工具循环；不是模型能力评测。"""
    def __init__(self, question): self.question=question; self.searched=False; self.pending=[]; self.reads=[]
    def __call__(self, messages):
        last=messages[-1]
        if last['role']=='user' and last['content'].startswith('工具结果:'):
            result=json.loads(last['content'][5:])
            if result['action']=='search' and result.get('ok'): self.pending=result['result']
            if result['action']=='read' and result.get('ok'): self.reads.append(result['result'])
            if not result.get('ok'): return {'action':'finish','status':'insufficient','answer':'工具调用失败，无法核实资料，请稍后重试。','citations':[],'gaps':[result['error']]}
        if not self.searched:
            self.searched=True; return {'action':'search','query':self.question,'reason':'查找与问题相关的资料'}
        if self.pending:
            p=self.pending.pop(0); return {'action':'read','doc_id':p['doc_id'],'passage_id':p['passage_id'],'reason':'核对原文及可能的冲突'}
        if not self.reads: return {'action':'finish','status':'insufficient','answer':'未找到相关资料，无法回答。','citations':[],'gaps':['缺少相关制度或产品资料']}
        citations=[{'doc_id':r['doc_id'],'passage_id':r['passage_id'],'quote':r['text']} for r in self.reads]
        nums={n for r in self.reads for n in re.findall(r'\d+\s*天',r['text'])}
        if len(nums)>1: return {'action':'finish','status':'conflict','answer':'检索到不同规定，资料未说明适用范围或优先级，请确认适用制度。','citations':citations,'gaps':['缺少适用范围或优先级']}
        return {'action':'finish','status':'answered','answer':'根据已检索资料：'+'；'.join(r['text'] for r in self.reads),'citations':citations,'gaps':[]}

def run(question, tools, model, history=None, max_steps=12):
    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'question':question,'history':history or []},ensure_ascii=False)}]
    trace=[]; read={}; found=set(); failures=set()
    for step in range(1,max_steps+1):
        try: action=model(messages)
        except Exception as e: return {'status':'model_error','answer':'模型调用失败，无法完成问答。','citations':[],'gaps':[str(e)],'trace':trace}
        if not isinstance(action,dict): return {'status':'model_error','answer':'模型返回格式错误。','citations':[],'gaps':[],'trace':trace}
        kind=action.get('action'); entry={'step':step,'action':kind,'parameters':{k:v for k,v in action.items() if k not in ('action','reason')},'reason':action.get('reason','')}
        if kind=='finish':
            citations=action.get('citations',[]); status=action.get('status')
            valid=isinstance(citations,list) and all(isinstance(c,dict) and isinstance(c.get('quote'),str) and c['quote'] and (c.get('doc_id'),c.get('passage_id')) in read and c['quote'] in read[(c['doc_id'],c['passage_id'])]['text'] for c in citations)
            if status not in ('answered','conflict','insufficient','clarification') or not valid or (status=='answered' and (found-set(read) or failures)) or (status in ('answered','conflict') and not citations) or (status=='conflict' and len({(c['doc_id'],c['passage_id']) for c in citations})<2):
                entry['result']='引用或状态校验失败'; trace.append(entry)
                messages.extend([{'role':'assistant','content':json.dumps(action,ensure_ascii=False)},{'role':'user','content':'工具结果:'+json.dumps({'action':'finish','ok':False,'error':'状态或引用无效，或仍有未读检索结果/未恢复的工具错误；请继续核查或返回资料不足'},ensure_ascii=False)}]); continue
            entry['result']='完成'; trace.append(entry)
            return {'status':status,'answer':action.get('answer',''),'citations':[dict(c,version_date=read[(c['doc_id'],c['passage_id'])]['version_date']) for c in citations],'gaps':action.get('gaps',[]),'trace':trace}
        failure_key=(kind, str(action.get('query','')), str(action.get('doc_id','')), str(action.get('passage_id','')))
        try:
            if kind=='search':
                result=tools.search(action['query']); found.update((item['doc_id'],item['passage_id']) for item in result)
            elif kind=='read':
                
                if (action['doc_id'],action['passage_id']) not in found: raise ValueError('请先检索并确认片段存在于检索结果中')
                result=tools.read(action['doc_id'],action['passage_id']); read[(result['doc_id'],result['passage_id'])]=result
            else: raise ValueError('未知动作')
            failures.discard(failure_key)
            obs={'action':kind,'ok':True,'result':result}
        except Exception as e:
            failures.add(failure_key)
            obs={'action':kind,'ok':False,'error':str(e)}
        entry['result']=obs; trace.append(entry)
        messages.extend([{'role':'assistant','content':json.dumps(action,ensure_ascii=False)},{'role':'user','content':'工具结果:'+json.dumps(obs,ensure_ascii=False)}])
    return {'status':'incomplete','answer':'达到执行步数上限，未完成核实。','citations':[],'gaps':['需要进一步检索或核查'],'trace':trace}
