import { initializeApp } from "firebase/app";
import {
  getFirestore, collection, query, where, getCountFromServer,
  getDocs, limit, orderBy
} from "firebase/firestore";
import fs from "node:fs";

const firebaseConfig = {
  apiKey: "AIzaSyD2W6MC9hg0MQbr4IAIn-YDauV7MHQaVfM",
  authDomain: "profagua-unemat.firebaseapp.com",
  projectId: "profagua-unemat",
  storageBucket: "profagua-unemat.firebasestorage.app",
  messagingSenderId: "563954651220",
  appId: "1:563954651220:web:89deba47a14541fe06ddc1"
};

const app=initializeApp(firebaseConfig);
const db=getFirestore(app);

async function countYear(name, year){
  const q=query(collection(db,name),where("ano","==",year));
  const s=await getCountFromServer(q);
  return s.data().count;
}

async function sampleYear(name, year, n=5){
  const q=query(collection(db,name),where("ano","==",year),limit(n));
  const s=await getDocs(q);
  return s.docs.map(d=>({id:d.id,...d.data()}));
}

async function main(){
  const totalProps=(await getCountFromServer(collection(db,"proposicoes"))).data().count;
  const totalVots=(await getCountFromServer(collection(db,"votacoes"))).data().count;

  const years=[];
  for(let year=2003;year<=2026;year++){
    const [proposicoes,votacoes]=await Promise.all([
      countYear("proposicoes",year),
      countYear("votacoes",year)
    ]);
    years.push({year,proposicoes,votacoes});
  }

  const samples={};
  for(const y of years.filter(x=>x.proposicoes>0).map(x=>x.year)){
    const ss=await sampleYear("proposicoes",y,3);
    samples[y]=ss.map(x=>({
      id:x.id,
      ano:x.ano ?? null,
      numero:x.numero ?? null,
      siglaTipo:x.siglaTipo ?? x.tipo ?? null,
      autor:x.autor ?? null,
      partido:x.partido ?? null,
      tema:x.tema ?? null,
      status:x.status ?? null,
      hasEmenta:!!x.ementa,
      keys:Object.keys(x).sort()
    }));
  }

  const out={
    generatedAt:new Date().toISOString(),
    totals:{proposicoes:totalProps,votacoes:totalVots},
    years,
    samples
  };
  fs.mkdirSync("audit",{recursive:true});
  fs.writeFileSync("audit/firestore-audit.json",JSON.stringify(out,null,2));
  console.log(JSON.stringify(out,null,2));
}
main().catch(e=>{console.error(e);process.exit(1);});
