"""Verified public service rules. Parse data as JSON, never execute source JavaScript."""
import datetime as dt
import hashlib
import json
import re
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor

SOURCES = {
    'members': ('活期宝官方关联基金清单', 'https://huoqibao.1234567.com.cn/json/hqb_newdatas.js?t=20200619'),
    'service': ('活期宝官方服务说明', 'https://huoqibao.1234567.com.cn/'),
    'limits': ('普通与快速取现规则', 'https://help.1234567.com.cn/question_885.html'),
    'quick': ('快速取现到账时间', 'https://help.1234567.com.cn/question_1034.html'),
    'ordinary': ('普通取现到账时间', 'https://help.1234567.com.cn/question_1122.html'),
    'wallet': ('极速赎回到活期宝说明', 'https://help.1234567.com.cn/question_834.html'),
    'wallet_alt': ('活期宝转换与赎回说明', 'https://help.1234567.com.cn/question_646.html'),
    'payment': ('天天基金公开业务支付说明', 'https://help.1234567.com.cn/question_890.html'),
    'alipay_payment': ('支付宝官方余额宝消费说明', 'https://cschannel.alipay.com/mobile/helpDetail.htm?help_id=257055'),
}

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self, value): self.parts.append(value)

def text(raw):
    try: source=raw.decode('utf-8-sig')
    except UnicodeDecodeError: source=raw.decode('gb18030')
    p=Text();p.feed(source);return re.sub(r'\s+', '', ''.join(p.parts))

def members(raw):
    source=raw.decode('utf-8-sig').strip()
    match=re.fullmatch(r'var\s+hqb_newdatas\s*=\s*\((\{.*\})\)\s*;?',source,re.S)
    if not match: raise ValueError('活期宝关联清单结构改变')
    value=json.loads(match[1]);rows=value.get('Datas')
    if value.get('ErrCode') not in (0,'0') or not isinstance(rows,list) or len(rows)<10:
        raise ValueError('活期宝关联清单覆盖异常')
    result={}
    for row in rows:
        code=row['FCODE'];date=dt.date.fromisoformat(row['PDATE']).isoformat();minimum=float(row['MINSG'])
        if not re.fullmatch(r'\d{6}',code) or not 0<minimum<1e9 or type(row['BUY']) is not bool:
            raise ValueError('活期宝清单字段异常')
        result[code]={'name':row['SHORTNAME'],'dataDate':date,'minimum':minimum,'buy':row['BUY']}
    return result

CHECKS={
    'service': ('7×24小时','1万元'),
    'limits': ('单只货币基金快速取现单日最高1万元','T+1至T+2个工作日','当日取现，不享受当日收益'),
    'quick': ('最快1秒','无法保证'),
    'ordinary': ('T+1日上午11:00前','下午17:00前'),
    'wallet': ('T+1日充值确认','T+1日20:00前'),
    'wallet_alt': ('T+1日即可充值确认','T+1日20点后'),
    'payment': ('活期宝买基金','卖基金回活期宝','超级转换'),
    'alipay_payment': ('消费支付','可以'),
}

def refresh(fetch, previous, status, now):
    result=json.loads(json.dumps(previous));result.setdefault('sources',{});result.setdefault('members',{})
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={key:pool.submit(fetch,url) for key,(_,url) in SOURCES.items()}
        for key,future in pending.items():
            try:
                raw=future.result();stamp=now()
                if key=='members': result['members']=members(raw)
                else:
                    body=text(raw)
                    if not all(phrase in body for phrase in CHECKS[key]):
                        raise ValueError('公开规则内容发生变化，停止自动确认此项规则')
                result['sources'][key]={'title':SOURCES[key][0],'url':SOURCES[key][1],
                    'checkedAt':stamp,'sha256':hashlib.sha256(raw).hexdigest(),'valid':True}
            except Exception as error:
                status['failures'].append('取用规则 '+key+'：'+str(error))
                if key in result['sources']:
                    source=result['sources'][key]
                    status['retained'].append({'area':'公开取用规则','code':key,'fetchedAt':source.get('checkedAt')})
                    source['valid']=False
    groups={'bank':['members','service','limits','quick'],
            'ordinary':['members','limits','ordinary'],
            'wallet':['wallet','wallet_alt'],'pay':['payment']}
    result['rules']={key:{'verified':all(result['sources'].get(s,{}).get('valid') for s in keys),
        'sourceIds':keys,'checkedAt':min((result['sources'].get(s,{}).get('checkedAt','') for s in keys),default='')}
        for key,keys in groups.items()}
    result.update(version=1,quickDailyLimit=10000,ordinaryTradingDays=[1,2],
        walletTimingConflict=True,merchantPaymentVerified=False,updatedAt=now())
    return result
