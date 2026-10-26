"""Import downloaded public source snapshots. Never execute provider JavaScript.
Usage: python3 scripts/import_market.py work/fund-universe.js work/market.html
"""
from pathlib import Path
from html.parser import HTMLParser
import json,re,sys,datetime,hashlib
class Rows(HTMLParser):
 def __init__(self):super().__init__();self.inside=False;self.cell=None;self.rows=[]
 def handle_starttag(self,tag,attrs):
  if tag=='table' and dict(attrs).get('id')=='oTable':self.inside=True
  if self.inside and tag=='tr':self.row=[]
  if self.inside and tag=='td':self.cell=''
 def handle_data(self,s):
  if self.cell is not None:self.cell+=s
 def handle_endtag(self,tag):
  if self.inside and tag=='td' and self.cell is not None:self.row.append(self.cell.strip());self.cell=None
  if self.inside and tag=='tr':self.rows.append(self.row)
  if self.inside and tag=='table':self.inside=False

def number(s):
 try:return float(s.rstrip('%'))
 except (ValueError,AttributeError):return None

def build(universe_file,quotes_file):
 raw=Path(universe_file).read_bytes();text=raw.decode('utf-8-sig');all_funds=json.loads(text[text.index('['):text.rindex(']')+1])
 universe={p[0]:p for p in all_funds if '货币' in p[3]}
 quote_raw=Path(quotes_file).read_bytes();html=quote_raw.decode('gb18030');parser=Rows();parser.feed(html)
 dates=[x for x in parser.rows[0] if re.fullmatch(r'\d{4}-\d{2}-\d{2}',x)]
 if len(dates)!=2:raise ValueError('Unrecognized source date headers')
 quotes={r[3]:r for r in parser.rows if len(r)==16 and re.fullmatch(r'\d{6}',r[3])}
 if len(universe)<500 or len(quotes)<100:raise ValueError('Unexpectedly small coverage; refusing to overwrite')
 now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
 products=[]
 for code in sorted(set(universe)|set(quotes)):
  u=universe.get(code);r=quotes.get(code);name=u[2] if u else r[4].removesuffix('基金吧档案');kind=u[3] if u else '收益表收录（分类待核验）'
  products.append(dict(id=code,code=code,name=name,kind=kind,shareClass=(re.search(r'([A-Z])$',name).group(1) if re.search(r'([A-Z])$',name) else '未分级/未识别'),yield7=number(r[6]) if r else None,income=number(r[5]) if r else None,minimum=None,manager='未获取管理人字段',redemption='销售渠道规则待核验',arrival='按销售渠道及基金文件核验',risk='未获取渠道风险等级',source='天天基金公开货币基金收益表' if r else '天天基金公开基金代码总表',sourceUrl='https://fund.eastmoney.com/HBJJ_pjsyl.html' if r else 'https://fund.eastmoney.com/js/fundcode_search.js',detailUrl=f'https://fund.eastmoney.com/{code}.html',updatedAt=now,dataDate=dates[0] if r else '未获取收益日期',quoteStatus='已获取收益快照' if r and number(r[6]) is not None else '未获取可比收益',purchaseStatus='未核验当前存续/开放/渠道可购状态',quota='各渠道可能不同，未获取已核验规则',cutoff='申请时间与工作日规则待核验',fee='未核验，不以源站销售渠道费用替代',note='货币基金不等于银行存款，不保证本金或收益；历史收益不代表未来表现。',license='公开可访问不等于获准再分发；上线前须审核数据授权',dataMode='公开资料静态快照；无自动更新'))
 manifest=dict(scope='中国境内公开基金资料中分类含“货币”的份额 + 货币基金收益表收录份额；按代码去重',total=len(products),universeCount=len(universe),quoteRows=len(quotes),yieldCount=sum(p['yield7'] is not None for p in products),incomeCount=sum(p['income'] is not None for p in products),missingYieldCount=sum(p['yield7'] is None for p in products),floatingCount=sum('浮动' in p['kind'] for p in products),quoteDate=dates[0],fetchedAt=now,completeness='已覆盖此次两个来源快照；未与监管登记名录逐项核对，不能保证穷尽所有当前存续或在售产品。A/B/C等为独立份额，不等于独立基金数量。',sources=[dict(url='https://fund.eastmoney.com/js/fundcode_search.js',sha256=hashlib.sha256(raw).hexdigest()),dict(url='https://fund.eastmoney.com/HBJJ_pjsyl.html',sha256=hashlib.sha256(quote_raw).hexdigest())])
 Path('data/products.json').write_text(json.dumps(products,ensure_ascii=False,indent=2)+'\n');Path('data/coverage.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');return manifest
if __name__=='__main__':print(json.dumps(build(*sys.argv[1:3]),ensure_ascii=False,indent=2))
