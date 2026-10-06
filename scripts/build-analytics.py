import json, os, glob
from collections import Counter, defaultdict
from datetime import datetime, timezone

FILES=sorted(glob.glob("dados/oficial/dados-*.json"))
if not FILES:
    print("Sem dados oficiais ainda; nada a fazer.")
    raise SystemExit(0)

out={
  "generatedAt":datetime.now(timezone.utc).isoformat(),
  "source":"Câmara dos Deputados — arquivos anuais oficiais",
  "totals":{"proposicoes":0,"votacoes":0},
  "autores":Counter(),"partidosAutores":Counter(),"temas":Counter(),"status":Counter(),"tipos":Counter(),
  "votosPartidos":defaultdict(Counter),
  "orientacoesBancadas":defaultdict(Counter),
  "years":{}
}

for path in FILES:
    with open(path,encoding="utf-8") as f:
        d=json.load(f)
    y=str(d["year"])
    yp,yt,ys,ytypes=Counter(),Counter(),Counter(),Counter()
    for p in d.get("proposicoes",[]):
        out["totals"]["proposicoes"]+=1
        ap=p.get("autorPrincipal") or {}
        nome=(ap.get("nome") or "").strip()
        partido=(ap.get("partido") or "").strip()
        if nome: out["autores"][nome]+=1
        if partido:
            out["partidosAutores"][partido]+=1
            yp[partido]+=1
        for t in p.get("temas",[]):
            tema=(t.get("tema") or "").strip()
            if tema:
                out["temas"][tema]+=1
                yt[tema]+=1
        sit=((p.get("status") or {}).get("situacao") or "Não identificado").strip()
        out["status"][sit]+=1; ys[sit]+=1
        tp=(p.get("siglaTipo") or "Não identificado").strip()
        out["tipos"][tp]+=1; ytypes[tp]+=1

    for v in d.get("votacoes",[]):
        out["totals"]["votacoes"]+=1
        for partido,c in (v.get("partidos") or {}).items():
            for k,n in c.items():
                if isinstance(n,int): out["votosPartidos"][partido][k]+=n
        for o in v.get("orientacoes",[]):
            b=(o.get("bancada") or "").strip()
            ori=(o.get("orientacao") or "").strip()
            if b and ori: out["orientacoesBancadas"][b][ori]+=1

    out["years"][y]={
      "proposicoes":len(d.get("proposicoes",[])),
      "votacoes":len(d.get("votacoes",[])),
      "partidosAutores":dict(yp.most_common()),
      "temas":dict(yt.most_common()),
      "status":dict(ys.most_common()),
      "tipos":dict(ytypes.most_common())
    }

for k in ("autores","partidosAutores","temas","status","tipos"):
    out[k]=dict(out[k].most_common())
out["votosPartidos"]={k:dict(v) for k,v in sorted(out["votosPartidos"].items())}
out["orientacoesBancadas"]={k:dict(v) for k,v in sorted(out["orientacoesBancadas"].items())}

os.makedirs("dados/oficial",exist_ok=True)
with open("dados/oficial/analitica.json","w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,separators=(",",":"))
print("Analítica:",out["totals"],"autores",len(out["autores"]),"partidos",len(out["partidosAutores"]))
