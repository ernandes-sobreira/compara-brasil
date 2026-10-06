import json, glob, os, re, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone

FILES=sorted(glob.glob("dados/oficial/dados-*.json"))
OUT="dados/oficial/insights.json"

def key(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode()
    return re.sub(r"[^A-Z0-9]+","",s.upper())

ALIASES={
  "PMDB":"MDB","MBD":"MDB",
  "PR":"PL",
  "PFL":"DEM",
  "PPB":"PP",
  "PRB":"REPUBLICANOS","REPUBLIC":"REPUBLICANOS","REPUB":"REPUBLICANOS","REPUBLICA":"REPUBLICANOS",
  "PMR":"REPUBLICANOS",
  "PTN":"PODEMOS","PODE":"PODEMOS",
  "PPS":"CIDADANIA",
  "PTDOB":"AVANTE",
  "PEN":"PATRIOTA",
  "SD":"SOLIDARIEDADE","SOLIDARI":"SOLIDARIEDADE",
  "PCDOB":"PCdoB","PCDB":"PCdoB",
  "PSBD":"PSDB","PSBB":"PSDB",
  "UNIAO":"UNIÃO",
  "REDE":"REDE",
  "SPART":"SEM PARTIDO","SPARTIDO":"SEM PARTIDO","SEMPARTIDO":"SEM PARTIDO"
}

DISPLAY={
 "PCDOB":"PCdoB","UNIAO":"UNIÃO","REPUBLICANOS":"Republicanos","SOLIDARIEDADE":"Solidariedade",
 "CIDADANIA":"Cidadania","PODEMOS":"Podemos","PATRIOTA":"Patriota","AVANTE":"Avante",
 "SEM PARTIDO":"Sem partido"
}

def canon(raw):
    raw=str(raw or "").strip()
    if not raw:return "Sem partido"
    k=key(raw)
    if k in ALIASES:return ALIASES[k]
    # preserve common official siglas in uppercase
    if k=="PCDOB": return "PCdoB"
    return DISPLAY.get(k,k or "Sem partido")

def add_metric(store,year,party,theme,field,n=1):
    y=store.setdefault(str(year),{})
    p=y.setdefault(party,{})
    m=p.setdefault(theme,{"propostas":0,"votacoes":0,"sim":0,"nao":0,"abst":0,"obstr":0,"outros":0,"maioriaSim":0,"maioriaNao":0,"equilibrado":0,"aprovadas":0,"maioriaSimEmAprovadas":0})
    m[field]+=int(n or 0)

def merge_metric(dst,src):
    for k,v in src.items():dst[k]=dst.get(k,0)+int(v or 0)

if not FILES:
    raise SystemExit("Nenhum arquivo oficial encontrado")

out={
  "generatedAt":datetime.now(timezone.utc).isoformat(),
  "source":"Câmara dos Deputados — arquivos anuais oficiais",
  "scope":{"types":["PL","PDL","PLP","PEC","MPV"],"votes":"nominais"},
  "aliases":defaultdict(Counter),
  "partyTotals":defaultdict(Counter),
  "themeTotals":Counter(),
  "partyThemeByYear":{},
  "partyTheme":{},
  "quality":{"voteEvents":0,"voteEventsLinkedToProp":0,"voteEventsWithoutLinkedProp":0},
  "anomalousRawParties":Counter()
}

for path in FILES:
    with open(path,encoding="utf-8") as f:d=json.load(f)
    year=int(d["year"])
    props=d.get("proposicoes",[])
    votes=d.get("votacoes",[])
    pmap={str(p.get("id")):p for p in props}

    # Propostas por partido e tema
    for p in props:
        a=(p.get("autorPrincipal") or (p.get("autores") or [None])[0] or {})
        raw=(a.get("partido") or "").strip()
        party=canon(raw)
        if raw: out["aliases"][party][raw]+=1
        themes=[(x.get("tema") or "").strip() for x in (p.get("temas") or []) if (x.get("tema") or "").strip()]
        if not themes: themes=["Sem tema oficial"]
        out["partyTotals"][party]["propostas"]+=1
        for theme in themes:
            out["themeTotals"][theme]+=1
            add_metric(out["partyThemeByYear"],year,party,theme,"propostas",1)

    # Votações temáticas: tenta vínculo oficial; se ausente, usa prefixo do ID quando coincide com proposição do mesmo universo.
    for v in votes:
        out["quality"]["voteEvents"]+=1
        pid=str(v.get("idProposicao") or "").strip()
        if pid not in pmap:
            pref=str(v.get("id") or "").split("-")[0]
            if pref in pmap: pid=pref
        prop=pmap.get(pid)
        if prop:
            out["quality"]["voteEventsLinkedToProp"]+=1
            themes=[(x.get("tema") or "").strip() for x in (prop.get("temas") or []) if (x.get("tema") or "").strip()] or ["Sem tema oficial"]
        else:
            out["quality"]["voteEventsWithoutLinkedProp"]+=1
            themes=["Sem tema vinculado"]

        approved=str(v.get("aprovacao") or "")=="1"
        for raw_party,x in (v.get("partidos") or {}).items():
            party=canon(raw_party)
            out["aliases"][party][raw_party]+=1
            s=int(x.get("S") or 0);n=int(x.get("N") or 0);a=int(x.get("A") or 0);o=int(x.get("O") or 0);z=int(x.get("outros") or 0)
            out["partyTotals"][party]["votacoes"]+=1
            out["partyTotals"][party]["sim"]+=s;out["partyTotals"][party]["nao"]+=n
            for theme in themes:
                add_metric(out["partyThemeByYear"],year,party,theme,"votacoes",1)
                add_metric(out["partyThemeByYear"],year,party,theme,"sim",s)
                add_metric(out["partyThemeByYear"],year,party,theme,"nao",n)
                add_metric(out["partyThemeByYear"],year,party,theme,"abst",a)
                add_metric(out["partyThemeByYear"],year,party,theme,"obstr",o)
                add_metric(out["partyThemeByYear"],year,party,theme,"outros",z)
                if s>n:add_metric(out["partyThemeByYear"],year,party,theme,"maioriaSim",1)
                elif n>s:add_metric(out["partyThemeByYear"],year,party,theme,"maioriaNao",1)
                else:add_metric(out["partyThemeByYear"],year,party,theme,"equilibrado",1)
                if approved:
                    add_metric(out["partyThemeByYear"],year,party,theme,"aprovadas",1)
                    if s>n:add_metric(out["partyThemeByYear"],year,party,theme,"maioriaSimEmAprovadas",1)

# Agregado de todos os anos
agg={}
for y,parties in out["partyThemeByYear"].items():
    for party,themes in parties.items():
        pp=agg.setdefault(party,{})
        for theme,m in themes.items():
            mm=pp.setdefault(theme,{})
            merge_metric(mm,m)
out["partyTheme"]=agg

# Alias auditado: registra grafias, mas esconde ruído minúsculo da navegação principal.
out["aliases"]={p:dict(c.most_common()) for p,c in out["aliases"].items()}
out["partyTotals"]={p:dict(v) for p,v in out["partyTotals"].items()}
out["themeTotals"]=dict(out["themeTotals"].most_common())

# principais = pelo menos 25 proposições OU 100 eventos de votação
out["mainParties"]=sorted([
    p for p,v in out["partyTotals"].items()
    if int(v.get("propostas",0))>=25 or int(v.get("votacoes",0))>=100
],key=lambda x:x.upper())

# valores crus muito raros para auditoria, sem poluir a interface
for p,aliases in out["aliases"].items():
    total=sum(aliases.values())
    if p not in out["mainParties"] and total<10:
        for raw,n in aliases.items():out["anomalousRawParties"][raw]+=n
out["anomalousRawParties"]=dict(out["anomalousRawParties"].most_common())

os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f:json.dump(out,f,ensure_ascii=False,separators=(",",":"))
print("insights",len(out["mainParties"]),"partidos",len(out["themeTotals"]),"temas",out["quality"])
