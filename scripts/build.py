from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[1]
def build():
    data={name:json.loads((ROOT/'data'/f'{name}.json').read_text()) if (ROOT/'data'/f'{name}.json').exists() else {} for name in ('products','coverage','channels','yuebao','history','status')}
    # Pack shared fields to keep mobile transfer small.
    for key in ['products']:
        rows=data[key]; common={k:v for k,v in rows[0].items() if all(r.get(k)==v for r in rows)}
        data[key]={'defaults':common,'rows':[{k:v for k,v in r.items() if k not in common} for r in rows]}
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    html=(ROOT/'src/index.html').read_text().replace('/*STYLE*/',(ROOT/'src/style.css').read_text()).replace('/*CORE*/',(ROOT/'src/core.js').read_text()).replace('/*APP*/',(ROOT/'src/app.js').read_text()).replace('"PAYLOAD"',payload)
    (ROOT/'index.html').write_text(html)
    dist=ROOT/'dist'; dist.mkdir(exist_ok=True); (dist/'index.html').write_text(html)
    (dist/'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    print('Built',len(html.encode()),'bytes')
if __name__=='__main__': build()
