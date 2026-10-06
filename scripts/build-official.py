import csv, io, json, os, re, time, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

BASE="https://dadosabertos.camara.leg.br/arquivos"
YEARS=list(range(2003,2027))
OUT="dados/oficial"
os.makedirs(OUT,exist_ok=True)

def open_url(path,tries=4):
    url=f"{BASE}/{path}"
    last=None
    for k in range(tries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"compara-brasil/2.0"})
            return urllib.request.urlopen(req,timeout=240)
        except Exception as e:
            last=e
            if k<tries-1: time.sleep(2*(k+1))
    raise last

def rows(path):
    with open_url(path) as r:
        yield from csv.DictReader(io.TextIOWrapper(r,encoding="utf-8-sig",newline=""),delimiter=";")

def safe_rows(path):
    try:
        yield from rows(path)
    except Exception as e:
        print("AVISO",path,repr(e),flush=True)

def pid_from_uri(uri):
    m=re.search(r"/proposicoes/(\d+)",uri or "")
    return m.group(1) if m else ""

def vote_code(v):
    x=(v or "").strip().lower()
    if x=="sim": return "S"
    if x in ("não","nao"): return "N"
    if "absten" in x: return "A"
    if "obstru" in x: return "O"
    return "X"

def process_year(year):
    print("INÍCIO",year,flush=True)
    props={}
    for r in rows(f"proposicoes/csv/proposicoes-{year}.csv"):
        pid=(r.get("id") or "").strip()
        if not pid: continue
        props[pid]={
          "id":pid,
          "siglaTipo":(r.get("siglaTipo") or "").strip(),
          "numero":(r.get("numero") or "").strip(),
          "ano":int(r.get("ano") or year),
          "descricaoTipo":(r.get("descricaoTipo") or "").strip(),
          "ementa":(r.get("ementa") or "").strip(),
          "dataApresentacao":(r.get("dataApresentacao") or "").strip(),
          "urlInteiroTeor":(r.get("urlInteiroTeor") or "").strip(),
          "uri":(r.get("uri") or "").strip(),
          "status":{
            "dataHora":(r.get("ultimoStatus_dataHora") or "").strip(),
            "orgao":(r.get("ultimoStatus_siglaOrgao") or "").strip(),
            "regime":(r.get("ultimoStatus_regime") or "").strip(),
            "tramitacao":(r.get("ultimoStatus_descricaoTramitacao") or "").strip(),
            "situacao":(r.get("ultimoStatus_descricaoSituacao") or "").strip(),
            "despacho":(r.get("ultimoStatus_despacho") or "").strip(),
            "apreciacao":(r.get("ultimoStatus_apreciacao") or "").strip()
          },
          "autores":[],
          "temas":[]
        }

    # Apenas autoria principal/proponente no índice anual.
    candidates=defaultdict(list)
    for r in safe_rows(f"proposicoesAutores/csv/proposicoesAutores-{year}.csv"):
        pid=(r.get("idProposicao") or "").strip()
        if pid not in props: continue
        try: ordem=int(r.get("ordemAssinatura") or 9999)
        except: ordem=9999
        candidates[pid].append({
          "idDeputado":(r.get("idDeputadoAutor") or "").strip(),
          "nome":(r.get("nomeAutor") or "").strip(),
          "tipo":(r.get("tipoAutor") or "").strip(),
          "partido":(r.get("siglaPartidoAutor") or "").strip(),
          "uf":(r.get("siglaUFAutor") or "").strip(),
          "ordem":ordem,
          "proponente":str(r.get("proponente") or "").strip()=="1"
        })
    for pid,arr in candidates.items():
        arr.sort(key=lambda a:(not a["proponente"],a["ordem"]))
        if arr: props[pid]["autores"]=[arr[0]]

    for r in safe_rows(f"proposicoesTemas/csv/proposicoesTemas-{year}.csv"):
        pid=pid_from_uri(r.get("uriProposicao"))
        if pid in props:
            props[pid]["temas"].append({
              "codigo":(r.get("codTema") or "").strip(),
              "tema":(r.get("tema") or "").strip(),
              "relevancia":(r.get("relevancia") or "").strip()
            })

    votes={}
    for r in safe_rows(f"votacoes/csv/votacoes-{year}.csv"):
        vid=(r.get("id") or "").strip()
        if not vid: continue
        votes[vid]={
          "id":vid,
          "data":(r.get("data") or "").strip(),
          "dataHora":(r.get("dataHoraRegistro") or "").strip(),
          "orgao":(r.get("siglaOrgao") or "").strip(),
          "aprovacao":(r.get("aprovacao") or "").strip(),
          "votosSim":int(r.get("votosSim") or 0),
          "votosNao":int(r.get("votosNao") or 0),
          "votosOutros":int(r.get("votosOutros") or 0),
          "descricao":(r.get("descricao") or "").strip(),
          "idProposicao":(r.get("ultimaApresentacaoProposicao_idProposicao") or "").strip(),
          "orientacoes":[],
          "partidos":{}
        }

    pcounts=defaultdict(lambda:defaultdict(Counter))
    for r in safe_rows(f"votacoesVotos/csv/votacoesVotos-{year}.csv"):
        vid=(r.get("idVotacao") or "").strip()
        if vid not in votes: continue
        party=(r.get("deputado_siglaPartido") or "").strip() or "Sem partido"
        pcounts[vid][party][vote_code(r.get("voto"))]+=1
    for vid,pm in pcounts.items():
        for party,c in pm.items():
            votes[vid]["partidos"][party]={
              "S":c["S"],"N":c["N"],"A":c["A"],"O":c["O"],"outros":c["X"],"total":sum(c.values())
            }

    for r in safe_rows(f"votacoesOrientacoes/csv/votacoesOrientacoes-{year}.csv"):
        vid=(r.get("idVotacao") or "").strip()
        if vid in votes:
            votes[vid]["orientacoes"].append({
              "bancada":(r.get("siglaBancada") or "").strip(),
              "orientacao":(r.get("orientacao") or "").strip()
            })

    themes=Counter();parties=Counter();types=Counter();statuses=Counter()
    q={"semAutorPrincipal":0,"semPartidoAutorPrincipal":0,"semTemaOficial":0,"semStatusOficial":0}
    for p in props.values():
        a=p["autores"][0] if p["autores"] else None
        if not a or not a["nome"]:q["semAutorPrincipal"]+=1
        if not a or not a["partido"]:q["semPartidoAutorPrincipal"]+=1
        elif a["partido"]:parties[a["partido"]]+=1
        if not p["temas"]:q["semTemaOficial"]+=1
        for t in p["temas"]:
            if t["tema"]:themes[t["tema"]]+=1
        st=p["status"]["situacao"]
        if not st:q["semStatusOficial"]+=1
        statuses[st or "Não identificado"]+=1
        types[p["siglaTipo"] or "Não identificado"]+=1

    party_votes=defaultdict(Counter);orientation=defaultdict(Counter)
    for v in votes.values():
        for party,x in v["partidos"].items():
            for k in ("S","N","A","O","outros","total"):party_votes[party][k]+=int(x.get(k,0))
        for o in v["orientacoes"]:
            if o["bancada"] and o["orientacao"]:orientation[o["bancada"]][o["orientacao"]]+=1

    obj={"generatedAt":datetime.now(timezone.utc).isoformat(),"year":year,"source":"Câmara dos Deputados — arquivos anuais oficiais","proposicoes":list(props.values()),"votacoes":list(votes.values())}
    path=f"{OUT}/dados-{year}.json"
    with open(path,"w",encoding="utf-8") as fh:json.dump(obj,fh,ensure_ascii=False,separators=(",",":"))

    result={
      "year":year,"proposicoes":len(props),"votacoes":len(votes),
      "themes":dict(themes),"parties":dict(parties),"types":dict(types),"statuses":dict(statuses),
      "quality":q,
      "partyVotes":{k:dict(v) for k,v in party_votes.items()},
      "orientations":{k:dict(v) for k,v in orientation.items()},
      "bytes":os.path.getsize(path)
    }
    print("FIM",year,len(props),len(votes),"bytes",result["bytes"],flush=True)
    return result

def main():
    results=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(process_year,y):y for y in YEARS}
        for fut in as_completed(futs):
            y=futs[fut]
            try:results.append(fut.result())
            except Exception as e:
                print("ERRO ANO",y,repr(e),flush=True)
                raise

    results.sort(key=lambda x:x["year"])
    summary={
      "generatedAt":datetime.now(timezone.utc).isoformat(),
      "source":"Câmara dos Deputados — arquivos anuais oficiais",
      "sourceBase":BASE,
      "period":{"start":min(x["year"] for x in results),"end":max(x["year"] for x in results)},
      "totals":{"proposicoes":0,"votacoes":0},
      "years":{},
      "themes":Counter(),"parties":Counter(),"types":Counter(),"status":Counter(),
      "quality":{"semAutorPrincipal":0,"semPartidoAutorPrincipal":0,"semTemaOficial":0,"semStatusOficial":0},
      "partyVotes":defaultdict(Counter),"orientations":defaultdict(Counter)
    }
    for x in results:
        summary["totals"]["proposicoes"]+=x["proposicoes"];summary["totals"]["votacoes"]+=x["votacoes"]
        summary["years"][str(x["year"])]={
          "proposicoes":x["proposicoes"],"votacoes":x["votacoes"],
          "temas":x["themes"],"partidosAutores":x["parties"],"tipos":x["types"],"status":x["statuses"],"bytes":x["bytes"]
        }
        summary["themes"].update(x["themes"]);summary["parties"].update(x["parties"]);summary["types"].update(x["types"]);summary["status"].update(x["statuses"])
        for k,v in x["quality"].items():summary["quality"][k]+=v
        for p,c in x["partyVotes"].items():summary["partyVotes"][p].update(c)
        for p,c in x["orientations"].items():summary["orientations"][p].update(c)

    for k in ("themes","parties","types","status"):summary[k]=dict(summary[k].most_common())
    summary["partyVotes"]={k:dict(v) for k,v in sorted(summary["partyVotes"].items())}
    summary["orientations"]={k:dict(v) for k,v in sorted(summary["orientations"].items())}
    with open(f"{OUT}/resumo-oficial.json","w",encoding="utf-8") as fh:json.dump(summary,fh,ensure_ascii=False,separators=(",",":"))
    print("DONE",summary["totals"],summary["quality"],flush=True)

if __name__=="__main__":main()
