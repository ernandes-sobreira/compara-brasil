import csv, io, json, requests, os
from datetime import datetime

BASE="https://dadosabertos.camara.leg.br/arquivos"
KINDS=[
  ("proposicoes","proposicoes"),
  ("proposicoesAutores","proposicoesAutores"),
  ("proposicoesTemas","proposicoesTemas"),
  ("votacoes","votacoes"),
  ("votacoesVotos","votacoesVotos"),
  ("votacoesOrientacoes","votacoesOrientacoes"),
]

def probe(kind,prefix,year):
    url=f"{BASE}/{kind}/csv/{prefix}-{year}.csv"
    r=requests.get(url,timeout=90)
    out={"url":url,"status":r.status_code,"bytes":len(r.content),"content_type":r.headers.get("content-type")}
    if r.ok:
        text=r.content.decode("utf-8-sig",errors="replace")
        sample=text[:200000]
        try:
            reader=csv.reader(io.StringIO(sample))
            header=next(reader,[])
            row=next(reader,[])
            out["header"]=header
            out["first_row"]=row[:len(header)]
        except Exception as e:
            out["parse_error"]=str(e)
    return out

data={"generatedAt":datetime.utcnow().isoformat()+"Z","years":{}}
for y in (2025,2026):
    data["years"][str(y)]={}
    for kind,prefix in KINDS:
        try:
            data["years"][str(y)][kind]=probe(kind,prefix,y)
        except Exception as e:
            data["years"][str(y)][kind]={"error":repr(e)}

os.makedirs("audit",exist_ok=True)
with open("audit/camara-headers.json","w",encoding="utf-8") as f:
    json.dump(data,f,ensure_ascii=False,indent=2)
print(json.dumps(data,ensure_ascii=False,indent=2))
