import json, tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from agent import Tools, MockModel, run

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'data.json'
        self.docs=[{'id':'D01','version_date':'2026-01-01','title':'报销制度','passages':[{'id':'P01','text':'报销期限为30天。'}]},{'id':'D02','version_date':'2026-02-01','title':'报销制度','passages':[{'id':'P01','text':'报销期限为15天。'}]}]
        self.save()
    def tearDown(self): self.tmp.cleanup()
    def save(self): self.path.write_text(json.dumps(self.docs,ensure_ascii=False),encoding='utf-8')
    def ask(self,q='报销期限多久',fail=None): return run(q,Tools(self.path,fail),MockModel(q))
    def test_conflict_and_changed_source(self):
        a=self.ask(); self.assertEqual(a['status'],'conflict'); self.assertEqual(len(a['citations']),2)
        self.docs.pop(); self.docs[0]['passages'][0]['text']='报销期限为45天。'; self.save()
        b=self.ask(); self.assertEqual(b['status'],'answered'); self.assertIn('45天',b['answer']); self.assertNotIn('30天',b['answer'])
    def test_failure(self): self.assertEqual(self.ask(fail='search')['status'],'insufficient')
    def test_missing(self): self.assertEqual(self.ask('年假政策')['status'],'insufficient')
    def test_limit(self): self.assertEqual(run('报销',Tools(self.path),MockModel('报销'),max_steps=1)['status'],'incomplete')
    def test_fake_quote_rejected(self):
        actions=iter([{'action':'search','query':'报销'},{'action':'read','doc_id':'D01','passage_id':'P01'},{'action':'finish','status':'answered','answer':'1天','citations':[{'doc_id':'D01','passage_id':'P01','quote':'1天'}]}])
        result=run('报销',Tools(self.path),lambda _: next(actions),max_steps=3)
        self.assertEqual(result['status'],'incomplete'); self.assertEqual(result['trace'][-1]['result'],'引用或状态校验失败')
    def test_direct_read_cannot_bypass_search(self):
        actions=iter([{'action':'read','doc_id':'D01','passage_id':'P01'}, {'action':'finish','status':'answered','answer':'30天','citations':[{'doc_id':'D01','passage_id':'P01','quote':'报销期限为30天。'}]}])
        r=run('报销',Tools(self.path),lambda _: next(actions),max_steps=2)
        self.assertEqual(r['status'],'incomplete')
        self.assertFalse(r['trace'][0]['result']['ok'])
    def test_duplicate_conflict_citations_rejected(self):
        actions=iter([{'action':'search','query':'报销'},{'action':'read','doc_id':'D01','passage_id':'P01'},{'action':'finish','status':'conflict','answer':'冲突','citations':[{'doc_id':'D01','passage_id':'P01','quote':'报销期限为30天。'}]*2}])
        r=run('报销',Tools(self.path),lambda _: next(actions),max_steps=3)
        self.assertEqual(r['status'],'incomplete')
    def test_unread_search_result_blocks_answer(self):
        actions=iter([{'action':'search','query':'报销'}, {'action':'read','doc_id':'D01','passage_id':'P01'}, {'action':'finish','status':'answered','answer':'30天','citations':[{'doc_id':'D01','passage_id':'P01','quote':'报销期限为30天。'}]}])
        r=run('报销',Tools(self.path),lambda _: next(actions),max_steps=3)
        self.assertEqual(r['status'],'incomplete')
    def test_failed_search_after_read_blocks_answer(self):
        class FailingSearch(Tools):
            def __init__(self,path): super().__init__(path); self.calls=0
            def search(self,q):
                self.calls+=1
                if self.calls>1: raise RuntimeError('搜索故障')
                return super().search(q)
        self.docs.pop(); self.save()
        actions=iter([{'action':'search','query':'报销'}, {'action':'read','doc_id':'D01','passage_id':'P01'}, {'action':'search','query':'相关规则'}, {'action':'finish','status':'answered','answer':'30天','citations':[{'doc_id':'D01','passage_id':'P01','quote':'报销期限为30天。'}]}])
        r=run('报销',FailingSearch(self.path),lambda _:next(actions),max_steps=4)
        self.assertEqual(r['status'],'incomplete')
    def test_search_does_not_silently_truncate(self):
        self.docs=[{'id':f'D{i:02}', 'version_date':'2026-01-01','title':'报销制度','passages':[{'id':'P01','text':'报销期限为30天。'}]} for i in range(10)]
        self.save(); self.assertEqual(len(Tools(self.path).search('报销期限')),10)
    def test_malformed_citation_does_not_crash(self):
        actions=iter([{'action':'finish','status':'answered','answer':'x','citations':[{'doc_id':[],'passage_id':'P01','quote':'x'}]}])
        result=run('报销',Tools(self.path),lambda _:next(actions),max_steps=1)
        self.assertEqual(result['status'],'incomplete')
    def test_empty_answer_cannot_finish(self):
        result=run('问题',Tools(self.path),lambda _: {'action':'finish','status':'clarification','answer':'','citations':[],'gaps':[]},max_steps=1)
        self.assertEqual(result['status'],'incomplete')
    def test_invalid_gaps_cannot_finish(self):
        result=run('问题',Tools(self.path),lambda _: {'action':'finish','status':'insufficient','answer':'缺少资料','citations':[],'gaps':'缺资料'},max_steps=1)
        self.assertEqual(result['status'],'incomplete')
if __name__=='__main__': unittest.main()
