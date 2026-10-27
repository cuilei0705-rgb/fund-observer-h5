"""Parse archived public fee pages; channel facts never imply bank arrival."""
from pathlib import Path
from html.parser import HTMLParser
import json,datetime,hashlib,sys
class TableRows(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.cell=None;self.row=[]
 def handle_starttag(self,t,a):
  if t=='tr':self.row=[]
  if t=='td':self.cell=''
 def handle_data(self,s):
  if self.cell is not None:self.cell+=s
 def handle_endtag(self,t):
  if t=='td' and self.cell is not None:self.row.append(' '.join(self.cell.split()));self.cell=None
  if t=='tr':self.rows.append(self.row)
def amount(s):
 if s is None:return None
 try:return float(s.replace('万元','').replace('元',''))*(10000 if '万' in s else 1)
 except ValueError:return None
def parse(file):
 raw=file.read_bytes()
 try:s=raw.decode('utf-8-sig')
 except UnicodeDecodeError:s=raw.decode('gb18030')
 parser=TableRows();parser.feed(s);facts={}
 keys=['申购状态','赎回状态','申购起点','首次购买','日累计申购限额','普通回活期宝','极速回活期宝','买入确认日','卖出确认日']
 for row in parser.rows:
  for i,item in enumerate(row[:-1]):
   if item in keys:facts[item]=row[i+1]
 if not all(k in facts for k in ['申购状态','申购起点','极速回活期宝']):raise ValueError('Unexpected page structure: '+file.name)
 now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
 conflict=amount(facts['申购起点']) is not None and amount(facts.get('日累计申购限额')) is not None and amount(facts['申购起点'])>amount(facts['日累计申购限额'])
 return dict(checked=True,name='天天基金渠道',url=f'https://fundf10.eastmoney.com/jjfl_{file.stem}.html',checkedAt=now,sourceDate='页面未提供规则生效日期，非账户交易验证',sha256=hashlib.sha256(raw).hexdigest(),path='天天基金 App / 网站 → 搜索基金代码 → 登录、开户及绑卡后核对申购',convenience='销售渠道为天天基金；按公开基金代码、起购与申购规则比较',minimum=amount(facts['申购起点']),minimumText=facts['申购起点'],purchaseStatus=facts['申购状态'],purchaseLimit=facts.get('日累计申购限额','待核验'),ordinary=facts.get('普通回活期宝','待核验'),quickWallet=facts['极速回活期宝'],confirmation=facts.get('卖出确认日','待核验'),bankArrival='见独立公开取用规则；仅官方活期宝关联份额适用银行卡取现规则',quickBank='活期宝关联份额单只每日最高1万元；与极速回活期宝分开判断',directPay='公开业务支付说明为购买基金，不作为日常消费证据',equivalent='按公开取现与支付功能分别比较',warning='页面起购金额高于单日申购限额，存在冲突；可能无法直接买入，需向渠道核实' if conflict else '基金赎回回活期宝与活期宝到银行卡是不同路径；到账和额度见独立公开规则')
if __name__=='__main__':
 records={p.stem:parse(p) for p in Path(sys.argv[1]).glob('*.html')};Path('data/channels.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');print('Imported channel snapshots:',len(records))
