(function(root){
 'use strict';
 const finite=x=>typeof x==='number'&&Number.isFinite(x);
 const age=(date,today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'}))=>date?Math.floor((Date.parse(today+'T00:00:00Z')-Date.parse(date.slice(0,10)+'T00:00:00Z'))/86400000):Infinity;
 const ordinary=p=>p.kind.includes('普通货币');
 function ranked(products,date,metric='yield7'){return products.filter(p=>ordinary(p)&&p.dataDate===date&&finite(p[metric])).sort((a,b)=>b[metric]-a[metric]||a.code.localeCompare(b.code));}
 function limit(text){if(text==='无限额')return Infinity;const m=String(text).match(/^([\d.,]+)(万)?元$/);return m?Number(m[1].replaceAll(',',''))*(m[2]?10000:1):null;}
 function channelFor(p,c,need,liquidity){
  if(!c)return c;const member=liquidity?.members?.[p.code];
  if(!['bank','ordinary'].includes(need)||!member)return c;
  return {...c,name:'天天基金 · 活期宝充值',minimum:member.minimum,minimumText:`${member.minimum}元（活期宝充值）`,
   purchaseStatus:member.buy?c.purchaseStatus:'暂停申购',membershipDate:member.dataDate,route:'huoqibao',
   membershipUrl:liquidity.sources?.members?.url};
 }
 function reasons(p,c,options){
  const r=[];const {amount,need,today,date,liquidity}=options;c=channelFor(p,c,need,liquidity);
  if(!ordinary(p))r.push('浮动净值类别不参加普通货币比较');
  if(p.dataDate!==date||!finite(p.yield7))r.push('缺少同日收益');
  if(age(p.dataDate,today)>3)r.push('收益距今超过3天，暂停匹配');
  if(!c){r.push('渠道门槛及申购规则未知');return r;}
  if(age(c.checkedAt,today)>7)r.push('渠道快照超过7天');
  if(!finite(c.minimum))r.push('起购门槛未知');else if(amount<c.minimum)r.push('未达到起购门槛');
  const max=limit(c.purchaseLimit);if(max===null)r.push('申购上限未知');else if(amount>max)r.push('超过渠道单日申购限额');
  if(max!==null&&finite(c.minimum)&&c.minimum>max)r.push('起购与单日限额冲突');
  if(!['开放申购','限大额'].includes(c.purchaseStatus))r.push('未确认开放申购');
  if(need!=='research'){
   const rule=liquidity?.rules?.[need];
   if(!rule?.verified)r.push('所需公开取用规则未通过本轮来源校验');
   else if(age(rule.checkedAt,today)>7)r.push('公开取用规则超过7天未更新');
  }
  if(['bank','ordinary'].includes(need)){
   const member=liquidity?.members?.[p.code];
   if(!member)r.push('未在本轮官方活期宝关联基金清单内，不套用活期宝取现规则');
   else if(age(member.dataDate,today)>7)r.push('官方活期宝关联清单日期超过7天');
  }
  if(need==='bank'){
   const max=liquidity?.quickDailyLimit;
   if(!finite(max)||max<=0)r.push('公开快速取现额度缺失');
   else if(amount>max)r.push(`本金超过单只基金单日快取${max.toLocaleString('zh-CN')}元上限，无法当天全额快速取出`);
  }
  if(need==='wallet'&&c.quickWallet!=='支持')r.push(c.quickWallet==='不支持'?'销售渠道明确不支持极速回活期宝':'此份额未披露极速回活期宝支持状态');
  if(need==='pay'&&!liquidity?.merchantPaymentVerified)r.push('公开支付业务仅核验到购买基金，未列日常商户消费支付，不纳入消费支付候选');
  return r;
 }
 function scenario(amount,days,rate,base,gap=0,fee=0,target=5){
  if(![amount,days,rate,base,gap,fee,target].every(finite)||amount<=0||days<1||days>3660||gap<0||fee<0||target<=0)return null;
  const earned=amount*rate/100*Math.max(0,days-gap)/365-fee;
  const baseline=amount*base/100*days/365;
  return {earned,baseline,delta:earned-baseline,legs:(earned-baseline)/target};
 }
 function replay(h1,h2,start,end,amount){
  if(!start||!end||start>end||!finite(amount)||amount<=0)return {error:'请选择有效金额与起止日期'};
  const a=new Map((h1||[]).map(r=>[r.date,r.income])),b=new Map((h2||[]).map(r=>[r.date,r.income]));
  let first=Date.parse(start+'T00:00:00Z'),last=Date.parse(end+'T00:00:00Z');if(!Number.isFinite(first)||!Number.isFinite(last)||last-first>=366*86400000)return {error:'历史回放最多366天'};
  let x=0,y=0,missing=[];for(let day=first;day<=last;day+=86400000){const d=new Date(day).toISOString().slice(0,10);if(!finite(a.get(d))||!finite(b.get(d)))missing.push(d);else{x+=a.get(d);y+=b.get(d);}}
  if(missing.length)return {error:`缺少 ${missing.length} 个自然日的双方完整记录，停止计算（首个：${missing[0]}）`};
  return {earned:amount/10000*x,baseline:amount/10000*y,delta:amount/10000*(x-y),days:(last-first)/86400000+1};
 }
 function resolveQuote(product,date,history){
  const p={...product};
  if(!ordinary(p))return p;
  if(p.dataDate===date&&finite(p.yield7)&&finite(p.income))return {...p,quoteOrigin:'market',quoteReason:'收益表同日披露'};
  const row=(history?.rows||[]).find(r=>r.date===date&&finite(r.yield7)&&finite(r.income));
  if(row)return {...p,yield7:row.yield7,income:row.income,dataDate:row.date,updatedAt:row.fetchedAt||history.fetchedAt,source:'天天基金历史收益接口',sourceUrl:row.sourceUrl||history.sourceUrl,quoteOrigin:'history',quoteReason:'收益表缺少同日完整字段，回退到已核验的同日普通货币逐日记录',quoteStatus:'同日历史接口回退'};
  return {...p,yield7:null,income:null,dataDate:null,quoteOrigin:'missing',quoteReason:'收益表及历史接口均无本次披露日的完整可比记录',quoteStatus:'缺少同日行情'};
 }
 function commonWindow(h1,h2,through,maxDays=7){
  const dates=rows=>(rows||[]).filter(r=>finite(r.income)&&r.date<=through).map(r=>r.date).sort();
  const candidateDates=dates(h1),baselineDates=dates(h2),a=new Set(candidateDates),b=new Set(baselineDates),sharedDates=[...a].filter(d=>b.has(d)).sort();
  const end=sharedDates.at(-1);let start=end,days=end?1:0;
  while(start&&days<maxDays){const prev=new Date(Date.parse(start+'T00:00:00Z')-86400000).toISOString().slice(0,10);if(!a.has(prev)||!b.has(prev))break;start=prev;days++;}
  const missing=[];for(let i=maxDays-1;i>=0;i--){const date=new Date(Date.parse(through+'T00:00:00Z')-i*86400000).toISOString().slice(0,10);if(!a.has(date)||!b.has(date))missing.push({date,candidate:!a.has(date),baseline:!b.has(date)});}
  return {start,end,days,candidateDates,baselineDates,sharedDates,missing};
 }
 function healthState(status){
  const failures=[],qualityExclusions=[...(status.qualityExclusions||[])];
  for(const item of status.failures||[]){if(typeof item==='string'&&item.includes('已排除')&&item.includes('缺日拒算'))qualityExclusions.push(item);else failures.push(item);}
  return {...status,failures,qualityExclusions,retained:status.retained||[],missingRecords:status.missingRecords||[]};
 }
 function periodStats(rows,end,days,amount=10000){
  if(!Number.isInteger(days)||days<1||days>366||!finite(amount)||amount<=0||!/^\d{4}-\d{2}-\d{2}$/.test(end))return {complete:false,error:'无效区间'};
  const start=new Date(Date.parse(end+'T00:00:00Z')-(days-1)*86400000).toISOString().slice(0,10),map=new Map((rows||[]).map(r=>[r.date,r.income]));
  let total=0;const missing=[];for(let i=0;i<days;i++){const date=new Date(Date.parse(start+'T00:00:00Z')+i*86400000).toISOString().slice(0,10),income=map.get(date);if(!finite(income))missing.push(date);else total+=income;}
  return {complete:missing.length===0,start,end,days,available:days-missing.length,missing,total:missing.length?null:amount/10000*total,per10k:missing.length?null:total};
 }
 function validDate(value){if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const timestamp=Date.parse(value+'T00:00:00Z');return Number.isFinite(timestamp)&&new Date(timestamp).toISOString().slice(0,10)===value;}
 function validateComparison(value){
  if(!value||value.version!==1||!finite(value.amount)||value.amount<=0||value.amount>1e9||!Number.isInteger(value.term)||value.term<1||value.term>366)return null;
  if(!['research','bank','ordinary','wallet','pay'].includes(value.need)||![value.product,value.baseline].every(x=>typeof x==='string'&&/^\d{6}$/.test(x)))return null;
  if(![value.rate,value.baseRate,value.gap,value.fee,value.target,value.scenario].every(finite)||value.rate< -10||value.rate>20||value.baseRate< -10||value.baseRate>20||!Number.isInteger(value.gap)||value.gap<0||value.gap>365||value.fee<0||value.fee>1e6||value.target<=0||value.target>10000||![-.5,0,.5].includes(value.scenario))return null;
  if(!['quote','manual'].includes(value.rateMode)||!['quote','manual'].includes(value.baseMode)||!validDate(value.dataDate)||!validDate(value.createdDate))return null;
  return Object.fromEntries(['version','amount','term','need','product','baseline','rate','baseRate','gap','fee','target','scenario','rateMode','baseMode','dataDate','createdDate'].map(k=>[k,value[k]]));
 }
 const api={finite,age,ordinary,ranked,limit,channelFor,reasons,scenario,replay,resolveQuote,commonWindow,healthState,periodStats,validateComparison};if(typeof module==='object')module.exports=api;else root.Fund=api;
})(typeof window==='object'?window:globalThis);
