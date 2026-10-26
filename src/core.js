(function(root){
 'use strict';
 const finite=x=>typeof x==='number'&&Number.isFinite(x);
 const age=(date,today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'}))=>date?Math.floor((Date.parse(today+'T00:00:00Z')-Date.parse(date.slice(0,10)+'T00:00:00Z'))/86400000):Infinity;
 const ordinary=p=>p.kind.includes('普通货币');
 function ranked(products,date,metric='yield7'){return products.filter(p=>ordinary(p)&&p.dataDate===date&&finite(p[metric])).sort((a,b)=>b[metric]-a[metric]||a.code.localeCompare(b.code));}
 function limit(text){if(text==='无限额')return Infinity;const m=String(text).match(/^([\d.,]+)(万)?元$/);return m?Number(m[1].replaceAll(',',''))*(m[2]?10000:1):null;}
 function reasons(p,c,options){
  const r=[];const {amount,need,today,date}=options;
  if(!ordinary(p))r.push('浮动净值类别不参加普通货币比较');
  if(p.dataDate!==date||!finite(p.yield7))r.push('缺少同日收益');
  if(age(p.dataDate,today)>3)r.push('收益距今超过3天，暂停匹配');
  if(!c){r.push('渠道门槛及申购规则未知');return r;}
  if(age(c.checkedAt,today)>7)r.push('渠道快照超过7天');
  if(!finite(c.minimum))r.push('起购门槛未知');else if(amount<c.minimum)r.push('未达到起购门槛');
  const max=limit(c.purchaseLimit);if(max===null)r.push('申购上限未知');else if(amount>max)r.push('超过渠道单日申购限额');
  if(max!==null&&finite(c.minimum)&&c.minimum>max)r.push('起购与单日限额冲突');
  if(!['开放申购','限大额'].includes(c.purchaseStatus))r.push('未确认开放申购');
  if(need==='bank')r.push('银行卡快赎额度、时效及资格未验证');
  if(need==='pay')r.push('消费支付功能未验证');
  if(need==='ordinary')r.push('普通赎回到银行卡的到账时间未验证');
  if(need==='wallet')r.push('活期宝极速回款额度、服务时间及资格未验证');
  return r;
 }
 function scenario(amount,days,rate,base,gap=0,fee=0,target=15){
  if(![amount,days,rate,base,gap,fee,target].every(finite)||amount<=0||days<1||days>3660||gap<0||fee<0||target<=0)return null;
  const earned=amount*rate/100*Math.max(0,days-gap)/365-fee;
  const baseline=amount*base/100*days/365;
  return {earned,baseline,delta:earned-baseline,legs:(earned-baseline)/target};
 }
 function replay(h1,h2,start,end,amount){
  if(!start||!end||start>end||!finite(amount)||amount<=0)return {error:'请选择有效金额与起止日期'};
  const a=new Map((h1||[]).map(r=>[r.date,r.income])),b=new Map((h2||[]).map(r=>[r.date,r.income]));
  let first=Date.parse(start+'T00:00:00Z'),last=Date.parse(end+'T00:00:00Z');if(!Number.isFinite(first)||!Number.isFinite(last)||last-first>366*86400000)return {error:'历史回放最多366天'};
  let x=0,y=0,missing=[];for(let day=first;day<=last;day+=86400000){const d=new Date(day).toISOString().slice(0,10);if(!finite(a.get(d))||!finite(b.get(d)))missing.push(d);else{x+=a.get(d);y+=b.get(d);}}
  if(missing.length)return {error:`缺少 ${missing.length} 个自然日的双方完整记录，停止计算（首个：${missing[0]}）`};
  return {earned:amount/10000*x,baseline:amount/10000*y,delta:amount/10000*(x-y),days:(last-first)/86400000+1};
 }
 const api={finite,age,ordinary,ranked,limit,reasons,scenario,replay};if(typeof module==='object')module.exports=api;else root.Fund=api;
})(typeof window==='object'?window:globalThis);
