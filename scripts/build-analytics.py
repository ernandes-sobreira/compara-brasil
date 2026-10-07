import json, glob, os, re, unicodedata, itertools
from collections import Counter, defaultdict
from datetime import datetime, timezone

FILES=sorted(glob.glob("dados/oficial/dados-*.json"))
OUT="dados/oficial/insights.json"

def key(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode()
    return re.sub(r"[^A-Z0-9]+","",s.upper())

ALIASES={
  "PMDB":"MDB","MBD":"MDB","PMBD":"MDB","PR":"PL","PFL":"DEM","PPB":"PP",
  "PRB":"Republicanos","REPUBLIC":"Republicanos","REPUB":"Republicanos","REPUBLICA":"Republicanos","REPUBLICANOS":"Republicanos","REPUBLI":"Republicanos","PMR":"Republicanos",
  "PTN":"Podemos","PODE":"Podemos","PODEMOS":"Podemos","PPS":"Cidadania","CIDADANIA":"Cidadania",
  "PTDOB":"Avante","AVANTE":"Avante","PEN":"Patriota","PATRIOTA":"Patriota","PATRI":"Patriota",
  "SD":"Solidariedade","SDD":"Solidariedade","SOLIDARI":"Solidariedade","SOLIDARIED":"Solidariedade","SOLIDARIEDADE":"Solidariedade",
  "PCDOB":"PCdoB","PCDB":"PCdoB","PSBD":"PSDB","PSBB":"PSDB","PSDC":"DC","UNIAO":"UNIÃO","REDE":"REDE","MISSAO":"MISSÃO",
  "SPART":"Sem partido","SPARTIDO":"Sem partido","SEMPARTIDO":"Sem partido"
}
DISPLAY={"PCDOB":"PCdoB","UNIAO":"UNIÃO","REPUBLICANOS":"Republicanos","SOLIDARIEDADE":"Solidariedade","CIDADANIA":"Cidadania","PODEMOS":"Podemos","PATRIOTA":"Patriota","AVANTE":"Avante","SEMPARTIDO":"Sem partido","MISSAO":"MISSÃO"}

def canon(raw):
    raw=str(raw or "").strip()
    if not raw:return "Sem partido"
    k=key(raw)
    return ALIASES.get(k,DISPLAY.get(k,k or "Sem partido"))

STOP=set("""
a ao aos as o os de da das do dos e em no na nos nas para por com sem sobre sob entre que
um uma uns umas seu sua seus suas ser estar foi foram sera serão tem ter como mais menos
lei leis projeto projetos proposicao proposicoes artigo artigos art altera alterar alteracao
dispoe institui estabelece cria criar acrescenta modifica regulamenta federal nacional
brasil brasileira brasileiro outras providencias nova novo novos novas ambito forma termos
numero nro fica ficam passa passam objetivo objeto mediante acerca referente relativo relativa
relativos relativas bem assim conforme fins fim seguinte seguintes
""".split())

def strip_acc(s):
    return unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()

def words(text):
    toks=re.findall(r"[A-Za-zÀ-ÿ]{4,}",str(text or "").lower())
    out=[]
    for w in toks:
        n=strip_acc(w)
        if n in STOP or len(n)<4: continue
        if n.startswith("deputad") or n.startswith("senad"): continue
        out.append(w)
    return out

def add_doc_words(counter,text):
    # uma menção por documento evita ementas longas dominarem a nuvem
    counter.update(set(words(text)))

def add_metric(store,year,party,theme,field,n=1):
    y=store.setdefault(str(year),{})
    p=y.setdefault(party,{})
    m=p.setdefault(theme,{
      "propostas":0,"normas":0,"arquivadas":0,"votacoes":0,
      "sim":0,"nao":0,"abst":0,"obstr":0,"outros":0,
      "maioriaSim":0,"maioriaNao":0,"equilibrado":0,
      "aprovadas":0,"maioriaSimEmAprovadas":0,
      "coesaoSoma":0.0,"coesaoN":0
    })
    m[field]+=n

def merge_metric(dst,src):
    for k,v in src.items():dst[k]=dst.get(k,0)+v

if not FILES: raise SystemExit("Nenhum arquivo oficial encontrado")

out={
  "generatedAt":datetime.now(timezone.utc).isoformat(),
  "source":"Câmara dos Deputados — arquivos anuais oficiais",
  "scope":{"types":["PL","PDL","PLP","PEC","MPV"],"votes":"nominais"},
  "aliases":defaultdict(Counter),
  "partyTotals":defaultdict(Counter),
  "partyTotalsByYear":defaultdict(lambda:defaultdict(Counter)),
  "themeTotals":Counter(),
  "partyThemeByYear":{},
  "partyTheme":{},
  "themeVoteByYear":defaultdict(Counter),
  "themeVoteTotals":Counter(),
  "partyWords":defaultdict(lambda:{"propostas":Counter(),"votacoes":Counter()}),
  "partyWordsByYear":defaultdict(lambda:defaultdict(lambda:{"propostas":Counter(),"votacoes":Counter()})),
  "partyNormExamples":defaultdict(list),
  "quality":{"voteEvents":0,"voteEventsLinkedToProp":0,"voteEventsWithoutLinkedProp":0},
  "anomalousRawParties":Counter()
}

pair=defaultdict(lambda:{"comuns":0,"iguais":0,"opostos":0})

for path in FILES:
    with open(path,encoding="utf-8") as f:d=json.load(f)
    year=int(d["year"])
    props=d.get("proposicoes",[])
    votes=d.get("votacoes",[])
    pmap={str(p.get("id")):p for p in props}

    for p in props:
        a=(p.get("autorPrincipal") or (p.get("autores") or [None])[0] or {})
        raw=(a.get("partido") or "").strip()
        party=canon(raw)
        if raw: out["aliases"][party][raw]+=1
        themes=[(x.get("tema") or "").strip() for x in (p.get("temas") or []) if (x.get("tema") or "").strip()] or ["Sem tema oficial"]
        status=((p.get("status") or {}).get("situacao") or "").strip()
        is_norm=status=="Transformado em Norma Jurídica"
        is_arch="Arquiv" in status
        out["partyTotals"][party]["propostas"]+=1
        out["partyTotalsByYear"][str(year)][party]["propostas"]+=1
        if is_norm:
            out["partyTotals"][party]["normas"]+=1
            out["partyTotalsByYear"][str(year)][party]["normas"]+=1
            out["partyNormExamples"][party].append({
              "id":p.get("id"),"ano":year,"tipo":p.get("siglaTipo"),"numero":p.get("numero"),
              "ementa":p.get("ementa") or "","temas":themes
            })
        if is_arch:
            out["partyTotals"][party]["arquivadas"]+=1
            out["partyTotalsByYear"][str(year)][party]["arquivadas"]+=1
        add_doc_words(out["partyWords"][party]["propostas"],p.get("ementa"))
        add_doc_words(out["partyWordsByYear"][str(year)][party]["propostas"],p.get("ementa"))
        for theme in themes:
            out["themeTotals"][theme]+=1
            add_metric(out["partyThemeByYear"],year,party,theme,"propostas",1)
            if is_norm:add_metric(out["partyThemeByYear"],year,party,theme,"normas",1)
            if is_arch:add_metric(out["partyThemeByYear"],year,party,theme,"arquivadas",1)

    for v in votes:
        out["quality"]["voteEvents"]+=1
        pid=str(v.get("idProposicao") or "").strip()
        if pid not in pmap:
            pref=str(v.get("id") or "").split("-")[0]
            if pref in pmap: pid=pref
        prop=pmap.get(pid)
        subject=prop or (v.get("assunto") or None)
        if subject:
            out["quality"]["voteEventsLinkedToProp"]+=1
            themes=[(x.get("tema") or "").strip() for x in (subject.get("temas") or []) if (x.get("tema") or "").strip()] or ["Sem tema oficial"]
            subject_text=subject.get("ementa") or v.get("descricao") or ""
        else:
            out["quality"]["voteEventsWithoutLinkedProp"]+=1
            themes=["Sem tema vinculado"]
            subject_text=v.get("descricao") or ""

        approved=str(v.get("aprovacao") or "")=="1"
        for theme in themes:
            out["themeVoteByYear"][str(year)][theme]+=1
            out["themeVoteTotals"][theme]+=1

        # Primeiro agrega grafias equivalentes dentro da própria votação
        cv=defaultdict(Counter)
        for raw_party,x in (v.get("partidos") or {}).items():
            party=canon(raw_party); out["aliases"][party][raw_party]+=1
            for k in ("S","N","A","O","outros","total"):cv[party][k]+=int(x.get(k) or 0)

        dirs={}
        for party,x in cv.items():
            s=int(x["S"]);n=int(x["N"]);a=int(x["A"]);o=int(x["O"]);z=int(x["outros"])
            out["partyTotals"][party]["votacoes"]+=1
            out["partyTotals"][party]["sim"]+=s;out["partyTotals"][party]["nao"]+=n
            out["partyTotalsByYear"][str(year)][party]["votacoes"]+=1
            out["partyTotalsByYear"][str(year)][party]["sim"]+=s;out["partyTotalsByYear"][str(year)][party]["nao"]+=n
            add_doc_words(out["partyWords"][party]["votacoes"],subject_text)
            add_doc_words(out["partyWordsByYear"][str(year)][party]["votacoes"],subject_text)

            denom=s+n
            if denom:
                coesao=max(s,n)/denom
                out["partyTotals"][party]["coesaoSoma"]+=coesao
                out["partyTotals"][party]["coesaoN"]+=1
                out["partyTotalsByYear"][str(year)][party]["coesaoSoma"]+=coesao
                out["partyTotalsByYear"][str(year)][party]["coesaoN"]+=1
                dirs[party]="S" if s>n else "N" if n>s else "D"
            if s>n:
                out["partyTotals"][party]["maioriaSim"]+=1
                out["partyTotalsByYear"][str(year)][party]["maioriaSim"]+=1
            elif n>s:
                out["partyTotals"][party]["maioriaNao"]+=1
                out["partyTotalsByYear"][str(year)][party]["maioriaNao"]+=1
            if approved:
                out["partyTotals"][party]["aprovadas"]+=1
                out["partyTotalsByYear"][str(year)][party]["aprovadas"]+=1
                if s>n:
                    out["partyTotals"][party]["maioriaSimEmAprovadas"]+=1
                    out["partyTotalsByYear"][str(year)][party]["maioriaSimEmAprovadas"]+=1

            for theme in themes:
                add_metric(out["partyThemeByYear"],year,party,theme,"votacoes",1)
                for field,val in (("sim",s),("nao",n),("abst",a),("obstr",o),("outros",z)):add_metric(out["partyThemeByYear"],year,party,theme,field,val)
                if s>n:add_metric(out["partyThemeByYear"],year,party,theme,"maioriaSim",1)
                elif n>s:add_metric(out["partyThemeByYear"],year,party,theme,"maioriaNao",1)
                else:add_metric(out["partyThemeByYear"],year,party,theme,"equilibrado",1)
                if denom:
                    add_metric(out["partyThemeByYear"],year,party,theme,"coesaoSoma",max(s,n)/denom)
                    add_metric(out["partyThemeByYear"],year,party,theme,"coesaoN",1)
                if approved:
                    add_metric(out["partyThemeByYear"],year,party,theme,"aprovadas",1)
                    if s>n:add_metric(out["partyThemeByYear"],year,party,theme,"maioriaSimEmAprovadas",1)

        # Semelhança de direção majoritária em votações comuns
        ps=sorted([p for p,dire in dirs.items() if dire in ("S","N")])
        for p1,p2 in itertools.combinations(ps,2):
            z=pair[(p1,p2)];z["comuns"]+=1
            if dirs[p1]==dirs[p2]:z["iguais"]+=1
            else:z["opostos"]+=1

# Agrega partyTheme
agg={}
for y,parties in out["partyThemeByYear"].items():
    for party,themes in parties.items():
        pp=agg.setdefault(party,{})
        for theme,m in themes.items():
            mm=pp.setdefault(theme,{})
            merge_metric(mm,m)
out["partyTheme"]=agg

# Formata totais e índices
def final_totals(src):
    d={}
    for p,v in src.items():
        x=dict(v)
        n=float(x.get("coesaoN",0) or 0);s=float(x.get("coesaoSoma",0) or 0)
        x["coesaoPct"]=round(100*s/n,1) if n else None
        d[p]=x
    return d

out["aliases"]={p:dict(c.most_common()) for p,c in out["aliases"].items()}
out["partyTotals"]=final_totals(out["partyTotals"])
out["partyTotalsByYear"]={y:final_totals(parties) for y,parties in out["partyTotalsByYear"].items()}
out["themeTotals"]=dict(out["themeTotals"].most_common())
out["themeVoteTotals"]=dict(out["themeVoteTotals"].most_common())
out["themeVoteByYear"]={y:dict(c) for y,c in out["themeVoteByYear"].items()}

out["mainParties"]=sorted([p for p,v in out["partyTotals"].items() if p!="Sem partido" and (int(v.get("propostas",0))>=25 or int(v.get("votacoes",0))>=100)],key=lambda x:x.upper())

# Nuvens: top 45 palavras
out["partyWords"]={p:{k:[[w,n] for w,n in c.most_common(45)] for k,c in z.items()} for p,z in out["partyWords"].items()}
out["partyWordsByYear"]={y:{p:{k:[[w,n] for w,n in c.most_common(35)] for k,c in z.items()} for p,z in parties.items()} for y,parties in out["partyWordsByYear"].items()}

# Exemplos de normas: mais recentes
out["partyNormExamples"]={p:sorted(v,key=lambda x:(x["ano"],int(x.get("numero") or 0)),reverse=True)[:15] for p,v in out["partyNormExamples"].items()}

# Pares semelhantes / divergentes
sim=defaultdict(list)
for (p1,p2),z in pair.items():
    if z["comuns"]<50:continue
    score=100*z["iguais"]/z["comuns"]
    item1={"partido":p2,"coincidenciaPct":round(score,1),"votacoesComuns":z["comuns"],"iguais":z["iguais"],"opostas":z["opostos"]}
    item2={"partido":p1,**{k:v for k,v in item1.items() if k!="partido"}}
    sim[p1].append(item1);sim[p2].append(item2)
out["similarParties"]={}
out["divergentParties"]={}
for p,arr in sim.items():
    out["similarParties"][p]=sorted(arr,key=lambda x:(-x["coincidenciaPct"],-x["votacoesComuns"]))[:8]
    out["divergentParties"][p]=sorted(arr,key=lambda x:(x["coincidenciaPct"],-x["votacoesComuns"]))[:8]

for p,aliases in out["aliases"].items():
    total=sum(aliases.values())
    if p not in out["mainParties"] and total<10:
        for raw,n in aliases.items():out["anomalousRawParties"][raw]+=n
out["anomalousRawParties"]=dict(out["anomalousRawParties"].most_common())

os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f:json.dump(out,f,ensure_ascii=False,separators=(",",":"))
print("insights",len(out["mainParties"]),"partidos",len(out["themeTotals"]),"temas",out["quality"])
