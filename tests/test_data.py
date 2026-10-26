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
class RefreshFailureTests(unittest.TestCase):
 def test_acquisition_failure_retains_original_dates(self):
  import tempfile,io,contextlib
  import refresh
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'data').mkdir()
   seed={'products':[{'code':'000198','name':'样本','kind':'货币型-普通货币','yield7':.8,'income':.2,'dataDate':'2026-10-23'}],'coverage':{'quoteDate':'2026-10-23','fetchedAt':'2026-10-24'},'channels':{'000198':{'checkedAt':'2026-10-24'}},'history':{'000198':{'rows':[{'date':'2026-10-23','income':.2,'yield7':.8}],'fetchedAt':'2026-10-24','sourceUrl':'https://example.test'}},'yuebao':{'products':[]}}
   for name,value in seed.items():(root/'data'/f'{name}.json').write_text(json.dumps(value))
   with patch.object(refresh,'ROOT',root),patch.object(refresh,'fetch',side_effect=RuntimeError('network unavailable')),contextlib.redirect_stdout(io.StringIO()):refresh.main()
   status=json.loads((root/'data/status.json').read_text())
   self.assertEqual(status['state'],'failed');self.assertGreaterEqual(len(status['failures']),3);self.assertEqual(len(status['retained']),3);self.assertEqual(status['qualityExclusions'],[])
   self.assertEqual(json.loads((root/'data/history.json').read_text())['000198']['fetchedAt'],'2026-10-24')
   self.assertEqual(status['missingRecords'][0]['dates'],['2026-10-17','2026-10-18','2026-10-19','2026-10-20','2026-10-21','2026-10-22'])
if __name__=='__main__':unittest.main()
