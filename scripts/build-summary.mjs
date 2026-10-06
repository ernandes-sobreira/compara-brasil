import { initializeApp } from "firebase/app";
import { getFirestore, collection, query, where, getDocs, terminate } from "firebase/firestore";
import fs from "node:fs";

const firebaseConfig = {
  apiKey: "AIzaSyD2W6MC9hg0MQbr4IAIn-YDauV7MHQaVfM",
  authDomain: "profagua-unemat.firebaseapp.com",
  projectId: "profagua-unemat",
  storageBucket: "profagua-unemat.firebasestorage.app",
  messagingSenderId: "563954651220",
  appId: "1:563954651220:web:89deba47a14541fe06ddc1"
};
const db=getFirestore(initializeApp(firebaseConfig));
const YEARS=[...Array(23)].map((_,i)=>2003+i);

const inc=(o,k,n=1)=>{k=(k??"").toString().trim()||"Não identificado";o[k]=(o[k]||0)+n;};
const top=(o,n=30)=>Object.fromEntries(Object.entries(o).sort((a,b)=>b[1]-a[1]).slice(0,n));

async function docsForYear(name,year){
  const s=await getDocs(query(collection(db,name),where("ano","==",year)));
  return s.docs.map(d=>({id:d.id,...d.data()}));
}

async function main(){
  const summary={
    generatedAt:new Date().toISOString(),
    source:"Firestore profagua-unemat / coleções existentes do COMPARA BRASIL",
    period:{start:2003,end:2025},
    totals:{proposicoes:0,votacoes:0},
    years:{},
    themes:{},
    parties:{},
    status:{},
    types:{},
    missing:{autor:0,partido:0,tema:0,status:0},
    partyVotes:{}
  };

  for(const year of YEARS){
    const ps=await docsForYear("proposicoes",year);
    summary.totals.proposicoes+=ps.length;
    const yr={proposicoes:ps.length,temas:{},partidos:{},status:{},tipos:{},missing:{autor:0,partido:0,tema:0,status:0}};
    for(const p of ps){
      const tema=p.tema||"Não identificado";
      const partido=p.partido||"Não identificado";
      const status=p.status||p.status_original||"Não identificado";
      const tipo=p.tipo||p.siglaTipo||((p.numero||"").split(" ")[0])||"Não identificado";
      inc(summary.themes,tema); inc(yr.temas,tema);
      inc(summary.parties,partido); inc(yr.partidos,partido);
      inc(summary.status,status); inc(yr.status,status);
      inc(summary.types,tipo); inc(yr.tipos,tipo);
      if(!p.autor){summary.missing.autor++;yr.missing.autor++;}
      if(!p.partido){summary.missing.partido++;yr.missing.partido++;}
      if(!p.tema){summary.missing.tema++;yr.missing.tema++;}
      if(!p.status&&!p.status_original){summary.missing.status++;yr.missing.status++;}
    }
    yr.temas=top(yr.temas,50); yr.partidos=top(yr.partidos,50); yr.status=top(yr.status,50); yr.tipos=top(yr.tipos,50);
    summary.years[year]=yr;
    console.log("proposicoes",year,ps.length);
  }

  for(const year of YEARS){
    const vs=await docsForYear("votacoes",year);
    summary.totals.votacoes+=vs.length;
    if(!summary.years[year]) summary.years[year]={proposicoes:0,temas:{},partidos:{},status:{},tipos:{},missing:{}};
    summary.years[year].votacoes=vs.length;
    for(const v of vs){
      for(const [partido,pos] of Object.entries(v.votos||{})){
        if(!summary.partyVotes[partido]) summary.partyVotes[partido]={S:0,N:0,D:0,A:0,total:0};
        const x=summary.partyVotes[partido];
        if(x[pos]!==undefined)x[pos]++; x.total++;
      }
    }
    console.log("votacoes",year,vs.length);
  }

  summary.themes=top(summary.themes,100);
  summary.parties=top(summary.parties,100);
  summary.status=top(summary.status,100);
  summary.types=top(summary.types,100);

  fs.mkdirSync("dados",{recursive:true});
  fs.writeFileSync("dados/resumo-completo.json",JSON.stringify(summary,null,2));
  console.log("TOTAL",summary.totals);
  await terminate(db);
}
main().catch(async e=>{console.error(e);try{await terminate(db)}catch{}process.exit(1);});
