import csv, io, json, os, re, sys, urllib.request, tempfile
from collections import defaultdict, Counter
from datetime import datetime, timezone

BASE="https://dadosabertos.camara.leg.br/arquivos"
YEARS=range(2003,2027)
OUT="dados/oficial"
os.makedirs(OUT,exist_ok=True)

def open_url(path):
    url=f"{BASE}/{path}"
    req=urllib.request.Request(url,headers={"User-Agent":"compara-brasil/1.0"})
    return urllib.request.urlopen(req,timeout=180)

def read_csv_stream(path):
    with open_url(path) as r:
        wrapper=io.TextIOWrapper(r,encoding="utf-8-sig",newline="")
        yield from csv.DictReader(wrapper,delimiter=";")

def prop_id_from_uri(uri):
    m=re.search(r"/proposicoes/(\d+)",uri or "")
    return m.group(1) if m else ""

def norm_vote(v):
    x=(v or "").strip().lower()
    if x in ("sim","s"): return "S"
    if x in ("não","nao","n"): return "N"
    if "absten" in x: return "A"
    if "obstru" in x: return "O"
    return "OUTRO"

def main():
    global_summary={
      "generatedAt":datetime.now(timezone.utc).isoformat(),
      "source":"Câmara dos Deputados — arquivos anuais oficiais",
      "sourceBase":BASE,
      "period":{"start":2003,"end":2026},
      "totals":{"proposicoes":0,"votacoes":0},
      "years":{},
      "themes":Counter(),"parties":Counter(),"types":Counter(),"status":Counter(),
      "quality":{"semAutorPrincipal":0,"semPartidoAutorPrincipal":0,"semTemaOficial":0,"semStatusOficial":0}
    }

    for year in YEARS:
        print(f"=== {year} ===",flush=True)
        props={}
        try:
            for r in read_csv_stream(f"proposicoes/csv/proposicoes-{year}.csv"):
                pid=(r.get("id") or "").strip()
                if not pid: continue
                st=(r.get("ultimoStatus_descricaoSituacao") or "").strip()
                props[pid]={
                  "id":pid,
                  "siglaTipo":(r.get("siglaTipo") or "").strip(),
                  "numero":(r.get("numero") or "").strip(),
                  "ano":int(r.get("ano") or year),
                  "descricaoTipo":(r.get("descricaoTipo") or "").strip(),
                  "ementa":(r.get("ementa") or "").strip(),
                  "ementaDetalhada":(r.get("ementaDetalhada") or "").strip(),
                  "keywords":(r.get("keywords") or "").strip(),
                  "dataApresentacao":(r.get("dataApresentacao") or "").strip(),
                  "urlInteiroTeor":(r.get("urlInteiroTeor") or "").strip(),
                  "uri":(r.get("uri") or "").strip(),
                  "status":{
                    "dataHora":(r.get("ultimoStatus_dataHora") or "").strip(),
                    "orgao":(r.get("ultimoStatus_siglaOrgao") or "").strip(),
                    "regime":(r.get("ultimoStatus_regime") or "").strip(),
                    "tramitacao":(r.get("ultimoStatus_descricaoTramitacao") or "").strip(),
                    "situacao":st,
                    "despacho":(r.get("ultimoStatus_despacho") or "").strip(),
                    "apreciacao":(r.get("ultimoStatus_apreciacao") or "").strip()
                  },
                  "autores":[],
                  "temas":[]
                }
                global_summary["types"][props[pid]["siglaTipo"] or "Não identificado"]+=1
                global_summary["status"][st or "Não identificado"]+=1
        except Exception as e:
            print("proposicoes error",year,repr(e),file=sys.stderr)
            continue

        # Autores oficiais
        try:
            for r in read_csv_stream(f"proposicoesAutores/csv/proposicoesAutores-{year}.csv"):
                pid=(r.get("idProposicao") or "").strip()
                if pid not in props: continue
                a={
                  "idDeputado":(r.get("idDeputadoAutor") or "").strip(),
                  "nome":(r.get("nomeAutor") or "").strip(),
                  "tipo":(r.get("tipoAutor") or "").strip(),
                  "partido":(r.get("siglaPartidoAutor") or "").strip(),
                  "uf":(r.get("siglaUFAutor") or "").strip(),
                  "ordem":int(r.get("ordemAssinatura") or 0),
                  "proponente":str(r.get("proponente") or "").strip() in ("1","true","True")
                }
                props[pid]["autores"].append(a)
        except Exception as e:
            print("autores error",year,repr(e),file=sys.stderr)

        # Temas oficiais
        try:
            for r in read_csv_stream(f"proposicoesTemas/csv/proposicoesTemas-{year}.csv"):
                pid=prop_id_from_uri(r.get("uriProposicao"))
                if pid not in props: continue
                t={"codigo":(r.get("codTema") or "").strip(),"tema":(r.get("tema") or "").strip(),"relevancia":(r.get("relevancia") or "").strip()}
                props[pid]["temas"].append(t)
        except Exception as e:
            print("temas error",year,repr(e),file=sys.stderr)

        # Compactar / qualidade / contagens
        for p in props.values():
            p["autores"].sort(key=lambda a:(not a["proponente"],a["ordem"] or 9999))
            main=p["autores"][0] if p["autores"] else None
            p["autorPrincipal"]=main
            if not main or not main["nome"]: global_summary["quality"]["semAutorPrincipal"]+=1
            if not main or not main["partido"]: global_summary["quality"]["semPartidoAutorPrincipal"]+=1
            if not p["temas"]: global_summary["quality"]["semTemaOficial"]+=1
            if not p["status"]["situacao"]: global_summary["quality"]["semStatusOficial"]+=1
            if main and main["partido"]: global_summary["parties"][main["partido"]]+=1
            for t in p["temas"]:
                if t["tema"]: global_summary["themes"][t["tema"]]+=1

        # Votações e dados partidários disponíveis
        votacoes={}
        try:
            for r in read_csv_stream(f"votacoes/csv/votacoes-{year}.csv"):
                vid=(r.get("id") or "").strip()
                if not vid: continue
                votacoes[vid]={
                  "id":vid,"data":(r.get("data") or "").strip(),"dataHora":(r.get("dataHoraRegistro") or "").strip(),
                  "orgao":(r.get("siglaOrgao") or "").strip(),
                  "aprovacao":(r.get("aprovacao") or "").strip(),
                  "votosSim":int(r.get("votosSim") or 0),"votosNao":int(r.get("votosNao") or 0),"votosOutros":int(r.get("votosOutros") or 0),
                  "descricao":(r.get("descricao") or "").strip(),
                  "idProposicao":(r.get("ultimaApresentacaoProposicao_idProposicao") or "").strip(),
                  "orientacoes":[],
                  "partidos":{}
                }
        except Exception as e:
            print("votacoes error",year,repr(e),file=sys.stderr)

        # Agregação dos votos individuais por partido
        party_counts=defaultdict(lambda:defaultdict(Counter))
        try:
            for r in read_csv_stream(f"votacoesVotos/csv/votacoesVotos-{year}.csv"):
                vid=(r.get("idVotacao") or "").strip()
                if vid not in votacoes: continue
                partido=(r.get("deputado_siglaPartido") or "").strip() or "Sem partido"
                voto=norm_vote(r.get("voto"))
                party_counts[vid][partido][voto]+=1
        except Exception as e:
            print("votos error",year,repr(e),file=sys.stderr)

        for vid,parties in party_counts.items():
            for partido,cnt in parties.items():
                tot=sum(cnt.values())
                votacoes[vid]["partidos"][partido]={"S":cnt["S"],"N":cnt["N"],"A":cnt["A"],"O":cnt["O"],"outros":cnt["OUTRO"],"total":tot}

        try:
            for r in read_csv_stream(f"votacoesOrientacoes/csv/votacoesOrientacoes-{year}.csv"):
                vid=(r.get("idVotacao") or "").strip()
                if vid not in votacoes: continue
                votacoes[vid]["orientacoes"].append({
                  "bancada":(r.get("siglaBancada") or "").strip(),
                  "orientacao":(r.get("orientacao") or "").strip()
                })
        except Exception as e:
            print("orientacoes error",year,repr(e),file=sys.stderr)

        year_obj={
          "generatedAt":datetime.now(timezone.utc).isoformat(),
          "year":year,
          "source":"Câmara dos Deputados — arquivos anuais oficiais",
          "proposicoes":list(props.values()),
          "votacoes":list(votacoes.values())
        }
        with open(f"{OUT}/dados-{year}.json","w",encoding="utf-8") as fh:
            json.dump(year_obj,fh,ensure_ascii=False,separators=(",",":"))

        ys={
          "proposicoes":len(props),"votacoes":len(votacoes),
          "temas":Counter(),"partidos":Counter(),"tipos":Counter(),"status":Counter()
        }
        for p in props.values():
            ys["tipos"][p["siglaTipo"] or "Não identificado"]+=1
            ys["status"][p["status"]["situacao"] or "Não identificado"]+=1
            if p["autorPrincipal"] and p["autorPrincipal"]["partido"]: ys["partidos"][p["autorPrincipal"]["partido"]]+=1
            for t in p["temas"]:
                if t["tema"]: ys["temas"][t["tema"]]+=1
        global_summary["years"][str(year)]={
          "proposicoes":len(props),"votacoes":len(votacoes),
          "temas":dict(ys["temas"].most_common()),
          "partidos":dict(ys["partidos"].most_common()),
          "tipos":dict(ys["tipos"].most_common()),
          "status":dict(ys["status"].most_common())
        }
        global_summary["totals"]["proposicoes"]+=len(props)
        global_summary["totals"]["votacoes"]+=len(votacoes)
        print(year,len(props),len(votacoes),flush=True)

    for k in ("themes","parties","types","status"):
        global_summary[k]=dict(global_summary[k].most_common())
    with open(f"{OUT}/resumo-oficial.json","w",encoding="utf-8") as fh:
        json.dump(global_summary,fh,ensure_ascii=False,separators=(",",":"))
    print("DONE",global_summary["totals"],global_summary["quality"],flush=True)

if __name__=="__main__":
    main()
