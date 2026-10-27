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

class PublicLiquidityTests(unittest.TestCase):
 def test_members_parser_does_not_execute_javascript(self):
  from import_liquidity import members
  value={'ErrCode':0,'Datas':[{'FCODE':f'{i:06d}','PDATE':'2026-10-23','MINSG':'10','BUY':True,'SHORTNAME':'样本'} for i in range(10)]}
  raw=('var hqb_newdatas=('+json.dumps(value)+');').encode()
  self.assertEqual(len(members(raw)),10)
  with self.assertRaises(ValueError):members(raw+b';fetch("https://example.test")')
 def test_rule_content_change_invalidates_only_affected_capability(self):
  from import_liquidity import refresh,CHECKS,SOURCES
  raw_members={'ErrCode':0,'Datas':[{'FCODE':f'{i:06d}','PDATE':'2026-10-23','MINSG':'10','BUY':True,'SHORTNAME':'样本'} for i in range(10)]}
  def source(url):
   key=next(k for k,(_,u) in SOURCES.items() if u==url)
   if key=='members':return ('var hqb_newdatas=('+json.dumps(raw_members)+');').encode()
   if key=='quick':return b'<html>rules changed</html>'
   return ('<div>'+''.join(CHECKS[key])+'</div>').encode()
  status={'failures':[],'retained':[]};previous={'sources':{'quick':{'valid':True,'checkedAt':'2026-10-24'}}}
  result=refresh(source,previous,status,lambda:'2026-10-26')
  self.assertFalse(result['rules']['bank']['verified']);self.assertTrue(result['rules']['ordinary']['verified']);self.assertTrue(result['rules']['wallet']['verified'])
  self.assertEqual(result['sources']['quick']['checkedAt'],'2026-10-24');self.assertFalse(result['sources']['quick']['valid']);self.assertEqual(len(status['retained']),1)

class MarketDateColumnTests(unittest.TestCase):
 def test_empty_today_column_uses_actual_previous_date(self):
  from unittest.mock import patch
  import refresh
  universe=('var funds='+json.dumps([[f'{i:06d}','X','样本','货币型-普通货币','X'] for i in range(500)])+';').encode()
  rows=[['2026-10-26','2026-10-23']]+[['','','',f'{i:06d}','样本','---','---','---','0.2','0.8%','---','---','','','',''] for i in range(100)]
  class Parser:
   def __init__(self):self.rows=rows
   def feed(self,_):pass
  with patch.object(refresh,'Rows',Parser):products,coverage=market(universe,b'',[])
  self.assertEqual(coverage['quoteDate'],'2026-10-23');self.assertEqual(coverage['latestHeaderDate'],'2026-10-26')
  self.assertEqual(products[0]['dataDate'],'2026-10-23');self.assertEqual(products[0]['yield7'],.8)
 def test_all_empty_columns_rejected(self):
  from unittest.mock import patch
  import refresh
  universe=('var funds='+json.dumps([[f'{i:06d}','X','样本','货币型-普通货币','X'] for i in range(500)])+';').encode()
  rows=[['2026-10-26','2026-10-23']]+[['','','',f'{i:06d}','样本','---','---','---','---','---','---','---','','','',''] for i in range(100)]
  class Parser:
   def __init__(self):self.rows=rows
   def feed(self,_):pass
  with patch.object(refresh,'Rows',Parser):
   with self.assertRaises(ValueError):market(universe,b'',[])

class PartialMarketBatchTests(unittest.TestCase):
 def batch(self,new_count,old_count):
  from unittest.mock import patch
  import refresh
  universe=('var funds='+json.dumps([[f'{i:06d}','X','样本','货币型-普通货币','X'] for i in range(500)])+';').encode()
  rows=[['2026-10-27','2026-10-26']]+[['','','',f'{i:06d}','样本',('0.3' if i<new_count else '---'),('1.1%' if i<new_count else '---'),'---',('0.2' if i<old_count else '---'),('0.8%' if i<old_count else '---'),'---','---','','','',''] for i in range(500)]
  class Parser:
   def __init__(self):self.rows=rows
   def feed(self,_):pass
  with patch.object(refresh,'Rows',Parser):return market(universe,b'',[])
 def test_sparse_new_day_cannot_displace_broad_previous_batch(self):
  products,c=self.batch(12,480)
  self.assertEqual(c['quoteDate'],'2026-10-26');self.assertEqual(c['yieldCount'],480)
  self.assertEqual(c['latestHeaderCompleteCount'],12);self.assertEqual(c['columnCoverage']['2026-10-27'],12)
  self.assertEqual(products[0]['dataDate'],'2026-10-26');self.assertEqual(products[0]['yield7'],.8)
 def test_sufficiently_disclosed_new_day_advances(self):
  _,c=self.batch(450,480);self.assertEqual(c['quoteDate'],'2026-10-27')
 def test_both_sparse_days_fail_closed(self):
  with self.assertRaises(ValueError):self.batch(12,20)

class MarketDateRepairTests(unittest.TestCase):
 def test_only_proven_sparse_date_can_be_repaired(self):
  from refresh import market_date_correction
  current={'quoteDate':'2026-10-26','latestHeaderDate':'2026-10-27','minimumBatchCount':436,'latestHeaderCompleteCount':12,'columnCoverage':{'2026-10-26':544,'2026-10-27':12}}
  result=market_date_correction(current,{'quoteDate':'2026-10-27','yieldCount':12})
  self.assertEqual(result['toDate'],'2026-10-26')
  with self.assertRaises(ValueError):market_date_correction(current,{'quoteDate':'2026-10-27','yieldCount':500})
  with self.assertRaises(ValueError):market_date_correction(current,{'quoteDate':'2026-10-28','yieldCount':12})
