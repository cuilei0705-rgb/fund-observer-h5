"""Build a dated historical-access comparison sample, never a current on-sale list."""
from pathlib import Path
import json,sys,datetime,hashlib
CODES=['000198','050003','001211','040038','003515','000380','000559','001134','180008','090022','161608','200003','001094','150005','000710','000575','000424','000505','519999','460006']
def build(folder):
 p={p['code']:p for p in json.loads(Path('data/products.json').read_text())};date=json.loads(Path('data/coverage.json').read_text())['quoteDate'];items=[];now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
 for code in CODES:
  f=Path(folder)/(code+'.json');a=dict(p[code]);a.update(yield7=None,income=None,dataDate='未获取',membership='历史接入记录；当前接入及账户可选状态待核验')
  if f.exists():
   raw=f.read_bytes();r=json.loads(raw)['Data']['LSJZList'][0]
   if r['NAVTYPE']!='1':raise ValueError('Unexpected money-fund format')
   def numeric(k):
    try:return float(r[k])
    except (ValueError,TypeError):return None
   a.update(yield7=numeric('LJJZ'),income=numeric('DWJZ'),dataDate=r['FSRQ'],source='天天基金历史收益接口',sourceUrl=f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=1&endDate={date}',updatedAt=now,sha256=hashlib.sha256(raw).hexdigest())
  items.append(a)
 result=dict(sampleCount=len(items),targetDate=date,checkedAt=now,currentMembershipVerified=False,completeCurrentUniverse=False,membershipSource=dict(title='中国基金报：余额宝平台接入货基达20只',url='https://app-web.chnfund.com/fund/202009/t20200923_2381429.html',publishedAt='2019-04-22',note='历史新闻记录，用于定义比较样本；不是2026年当前在售名录。按公开名称匹配对应A类/指定代码。'),serviceSource=dict(title='支付宝余额宝服务协议',url='https://render.alipay.com/p/yuyan/180020010001201259/bank/YEB.htm?page=YEB'),limitation='仅能识别历史接入20只样本中的同日最高；尚不能确认当前余额宝全部可选基金中的最高。',products=items)
 Path('data/yuebao.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 for metric in ['yield7','income']:
  eligible=[a for a in items if a['dataDate']==date and a[metric] is not None];top=max(eligible,key=lambda a:a[metric]);print(metric,len(eligible),top['code'],top['name'],top[metric])
if __name__=='__main__':build(sys.argv[1])
