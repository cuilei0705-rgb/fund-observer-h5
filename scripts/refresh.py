"""Public snapshots; conservative parsing, per-source failure preservation, no JS execution."""
from pathlib import Path
import datetime as dt, json, urllib.request, time, tempfile, os, hashlib, math, subprocess
from concurrent.futures import ThreadPoolExecutor
from import_market import Rows, number
from import_channels import parse as parse_channel

ROOT=Path(__file__).resolve().parents[1]
TZ=dt.timezone(dt.timedelta(hours=8))
def now(): return dt.datetime.now(TZ).isoformat(timespec='seconds')
def read(name, default):
    p=ROOT/'data'/f'{name}.json'
    return json.loads(p.read_text()) if p.exists() else default
def save(name,value):
    path=ROOT/'data'/f'{name}.json'; tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n'); os.replace(tmp,path)
def fetch(url):
    # OS curl uses the platform trust store. TLS verification remains enabled.
    return subprocess.run(['curl','--fail','--silent','--show-error','--location','--retry','1','--retry-max-time','35','--connect-timeout','8','--max-time','15','--user-agent','Mozilla/5.0','--referer','https://fundf10.eastmoney.com/',url],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def market(universe_raw, quote_raw, previous):
    import re
    text=universe_raw.decode('utf-8-sig'); all_funds=json.loads(text[text.index('['):text.rindex(']')+1])
    universe={p[0]:p for p in all_funds if '货币' in p[3]}
    parser=Rows(); parser.feed(quote_raw.decode('gb18030'))
    dates=[x for x in parser.rows[0] if re.fullmatch(r'\d{4}-\d{2}-\d{2}',x)]
    if len(dates)!=2 or dates[0]>dt.date.today().isoformat(): raise ValueError('收益日期结构异常')
    quotes={r[3]:r for r in parser.rows if len(r)==16 and re.fullmatch(r'\d{6}',r[3])}
    if len(universe)<500 or len(quotes)<100: raise ValueError('来源覆盖骤减，保留旧快照')
    old={p['code']:p for p in previous}; products=[]
    for code in sorted(set(universe)|set(quotes)|set(old)):
        u=universe.get(code); r=quotes.get(code); a=dict(old.get(code,{}))
        name=u[2] if u else (r[4].removesuffix('基金吧档案') if r else a['name'])
        kind=u[3] if u else a.get('kind','分类待核验')
        y=number(r[6]) if r else None; income=number(r[5]) if r else None
        if y is not None and (not math.isfinite(y) or abs(y)>100): raise ValueError('年化口径异常')
        a.update(id=code,code=code,name=name,kind=kind,shareClass=re.search(r'([A-Z])$',name).group(1) if re.search(r'([A-Z])$',name) else '未识别',yield7=y,income=income,dataDate=dates[0] if r else None,updatedAt=now(),discoveryStatus='来源本次收录' if u or r else '本次来源未收录；保留追踪，存续待核验',purchaseStatus='存续/开放/渠道可购状态待核验',source='天天基金公开收益表' if r else '天天基金代码总表',sourceUrl='https://fund.eastmoney.com/HBJJ_pjsyl.html' if r else 'https://fund.eastmoney.com/js/fundcode_search.js',detailUrl=f'https://fund.eastmoney.com/{code}.html',dataMode='每日公开快照流水线',quoteStatus='本次有收益' if y is not None else '本次缺失，不以旧值冒充当前')
        products.append(a)
    coverage=dict(total=len(products),universeCount=len(universe),quoteRows=len(quotes),yieldCount=sum(p['yield7'] is not None for p in products),incomeCount=sum(p['income'] is not None for p in products),missingYieldCount=sum(p['yield7'] is None for p in products),floatingCount=sum('浮动' in p['kind'] for p in products),quoteDate=dates[0],fetchedAt=now(),newCodes=sorted((set(universe)|set(quotes))-set(old)),notSeenCount=sum(p['discoveryStatus'].startswith('本次来源未收录') for p in products),scope='公开代码总表中货币类别与收益表并集，按份额代码去重；不是监管全量在售名录',completeness='未与监管名录逐项核对，基金公司及销售渠道覆盖不完整。各份额不等于独立基金；缺失及存续未知均保留。',sources=[{'url':url,'sha256':hashlib.sha256(raw).hexdigest()} for url,raw in [('https://fund.eastmoney.com/js/fundcode_search.js',universe_raw),('https://fund.eastmoney.com/HBJJ_pjsyl.html',quote_raw)]])
    return products,coverage
def history_parse(raw):
    data=json.loads(raw); rows=(data.get('Data') or {}).get('LSJZList')
    if not rows: raise ValueError('历史收益为空')
    result={}
    for row in rows:
        if str(row.get('NAVTYPE'))!='1': continue  # merged intervals are never spread over invented daily rows
        date=dt.date.fromisoformat(row['FSRQ']).isoformat(); income=number(row['DWJZ']); y=number(row['LJJZ'])
        if income is not None and math.isfinite(income): result[date]={'date':date,'income':income,'yield7':y}
    if not any(str(row.get('NAVTYPE'))=='1' for row in rows): raise ValueError('无可验证普通货币逐日记录')
    return sorted(result.values(),key=lambda x:x['date'])
def main():
    print('Starting public snapshot refresh',now(),flush=True)
    status={'attemptedAt':now(),'market':'failed','failures':[],'qualityExclusions':[],'retained':[],'missingRecords':[]}; previous=read('products',[])
    products=previous; coverage=read('coverage',{})
    try:
        products,coverage=market(fetch('https://fund.eastmoney.com/js/fundcode_search.js'),fetch('https://fund.eastmoney.com/HBJJ_pjsyl.html'),previous)
        if coverage['quoteDate']<read('coverage',{}).get('quoteDate',''): raise ValueError('来源日期倒退')
        save('products',products); save('coverage',coverage); status['market']='success'
    except Exception as e:
        status['failures'].append('市场快照：'+str(e));status['retained'].append({'area':'行情','fetchedAt':coverage.get('fetchedAt'),'reason':'获取或结构验证失败，沿用上次市场快照'})
    channels=read('channels',{}); history=read('history',{}); yuebao=read('yuebao',{})
    ordinary=[p for p in products if '普通货币' in p['kind'] and p.get('yield7') is not None and p.get('dataDate')==coverage.get('quoteDate')]
    leaders=sorted(ordinary,key=lambda p:-p['yield7'])[:12]
    codes=sorted(set(channels)|{p['code'] for p in leaders})
    pool=ThreadPoolExecutor(max_workers=4)
    channel_downloads={code:pool.submit(fetch,f'https://fundf10.eastmoney.com/jjfl_{code}.html') for code in codes}
    for code in codes:
        try:
            raw=channel_downloads[code].result()
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/(code+'.html'); path.write_bytes(raw); channels[code]=parse_channel(path)
        except Exception as e:
            status['failures'].append('渠道 '+code+'：'+str(e))
            if code in channels: status['retained'].append({'area':'渠道','code':code,'fetchedAt':channels[code].get('checkedAt')})
        print('Channel checked',code,flush=True)
    save('channels',channels)
    targets=sorted(set(codes)|{p['code'] for p in yuebao.get('products',[])})
    urls={code:f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=40&endDate={coverage.get("quoteDate","")}' for code in targets}
    history_downloads={code:pool.submit(fetch,urls[code]) for code in targets}
    for code in targets:
        url=urls[code]
        try:
            raw=history_downloads[code].result(); rows=history_parse(raw); excluded=sum(str(r.get('NAVTYPE'))!='1' for r in json.loads(raw)['Data']['LSJZList'])
            history[code]={'rows':rows,'excludedMergedOrOtherRows':excluded,'fetchedAt':now(),'sourceUrl':url,'sha256':hashlib.sha256(raw).hexdigest()}
            if excluded: status['qualityExclusions'].append('逐日 '+code+'：已排除 '+str(excluded)+' 条合并区间或不同口径记录；相关缺日拒算')
        except Exception as e:
            status['failures'].append('逐日 '+code+'：'+str(e))
            if code in history: status['retained'].append({'area':'历史','code':code,'fetchedAt':history[code].get('fetchedAt')})
        print('History checked',code,flush=True)
    pool.shutdown()
    save('history',history)
    for code in targets:
        available={r['date'] for r in history.get(code,{}).get('rows',[]) if r.get('income') is not None}
        end=dt.date.fromisoformat(coverage['quoteDate'])
        missing=[(end-dt.timedelta(days=i)).isoformat() for i in range(6,-1,-1) if (end-dt.timedelta(days=i)).isoformat() not in available]
        if missing: status['missingRecords'].append({'area':'历史近7日','code':code,'dates':missing,'impact':'相关区间回放拒算；不影响同日已核验行情'})
    bycode={p['code']:p for p in products}
    for p in yuebao.get('products',[]):
        if p['code'] in bycode and bycode[p['code']].get('dataDate')==coverage.get('quoteDate') and bycode[p['code']].get('yield7') is not None:
            p.update({k:bycode[p['code']][k] for k in ('yield7','income','dataDate','updatedAt','sourceUrl','source')})
        else:
            row=next((r for r in history.get(p['code'],{}).get('rows',[]) if r['date']==coverage.get('quoteDate')),None)
            if row: p.update(yield7=row['yield7'],income=row['income'],dataDate=row['date'],sourceUrl=history[p['code']]['sourceUrl'],updatedAt=history[p['code']]['fetchedAt'])
    yuebao['targetDate']=coverage.get('quoteDate'); yuebao['checkedAt']=now(); save('yuebao',yuebao)
    status.update(finishedAt=now(),channelCount=len(channels),historyCount=len(history),state='success' if not status['failures'] else 'partial' if status['market']=='success' else 'failed')
    save('status',status); print(json.dumps(status,ensure_ascii=False))
if __name__=='__main__': main()
