import unittest,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import history_parse,market,ROOT
class DataTests(unittest.TestCase):
 def test_snapshot(self):
  p=json.loads((ROOT/'data/products.json').read_text());c=json.loads((ROOT/'data/coverage.json').read_text())
  self.assertEqual(len(p),len({x['code'] for x in p}));self.assertEqual(len(p),c['total']);self.assertEqual(sum(x['yield7'] is not None for x in p),c['yieldCount']);self.assertGreater(len(p),500)
 def test_reject_bad_source(self):
  with self.assertRaises(Exception):market(b'[]',b'<html>failure</html>',[])
 def test_reject_wrong_history_type(self):
  raw=json.dumps({'Data':{'LSJZList':[{'NAVTYPE':'2'}]}}).encode()
  with self.assertRaises(ValueError):history_parse(raw)
 def test_missing_history_not_zero(self):
  raw=json.dumps({'Data':{'LSJZList':[{'NAVTYPE':'1','FSRQ':'2026-10-01','DWJZ':'---','LJJZ':'1.2'}]}}).encode();self.assertEqual(history_parse(raw),[])
 def test_yuebao_scope(self):
  y=json.loads((ROOT/'data/yuebao.json').read_text());self.assertFalse(y['currentMembershipVerified']);self.assertFalse(y['completeCurrentUniverse']);self.assertEqual(y['membershipSource']['publishedAt'],'2019-04-22')
if __name__=='__main__':unittest.main()
