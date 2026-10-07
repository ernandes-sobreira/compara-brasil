
(function(){
  function esc(v){ return typeof h==='function' ? h(v) : String(v||''); }
  function nfmt(v){ return typeof fmt==='function' ? fmt(v) : String(v||0); }
  function val(id){ var e=document.getElementById(id); return e?e.value:''; }

  function pairInfo(a,b){
    if(!a||!b||!ST.insights) return null;
    var key=[a,b].sort().join('|');
    var d=ST.insights.pairSimilarity&&ST.insights.pairSimilarity[key];
    if(d) return d;
    var arr=(ST.insights.similarParties&&ST.insights.similarParties[a]||[]).concat(ST.insights.divergentParties&&ST.insights.divergentParties[a]||[]);
    var x=arr.find(function(z){return z.partido===b;});
    if(!x) return null;
    return {partidos:[a,b],coincidenciaPct:x.coincidenciaPct,votacoesComuns:x.votacoesComuns,mesmaDirecao:x.iguais,direcaoOposta:x.opostas};
  }

  function summary(p,year){
    var t=partyTotalsFor(p,year)||{};
    var co=t.coesaoPct;
    if(co==null && Number(t.coesaoN||0)>0) co=100*Number(t.coesaoSoma||0)/Number(t.coesaoN);
    return {
      propostas:Number(t.propostas||0),
      normas:Number(t.normas||0),
      votacoes:Number(t.votacoes||0),
      coesao:co==null?null:Number(co),
      maioriaSim:Number(t.maioriaSim||0),
      maioriaNao:Number(t.maioriaNao||0)
    };
  }

  function themeRows(a,b,year){
    var A=insightThemesFor(a,year)||{}, B=insightThemesFor(b,year)||{};
    var names=Array.from(new Set(Object.keys(A).concat(Object.keys(B))));
    return names.map(function(t){
      return {tema:t,a:A[t]||{},b:B[t]||{}};
    }).filter(function(x){
      return Number(x.a.propostas||0)+Number(x.a.votacoes||0)+Number(x.b.propostas||0)+Number(x.b.votacoes||0)>0;
    }).sort(function(x,y){
      var sx=Number(x.a.propostas||0)+Number(x.a.votacoes||0)+Number(x.b.propostas||0)+Number(x.b.votacoes||0);
      var sy=Number(y.a.propostas||0)+Number(y.a.votacoes||0)+Number(y.b.propostas||0)+Number(y.b.votacoes||0);
      return sy-sx;
    });
  }

  function populate(){
    if(!ST.insights) return;
    var parties=ST.insights.mainParties||[];
    ['compPartyA','compPartyB'].forEach(function(id){
      var s=document.getElementById(id); if(!s) return;
      var current=s.value;
      s.innerHTML='<option value="">Escolha</option>';
      parties.forEach(function(p){
        var o=document.createElement('option');o.value=p;o.textContent=p;s.appendChild(o);
      });
      if(parties.indexOf(current)>=0) s.value=current;
    });
    var y=document.getElementById('compYear');
    if(y){
      var cur=y.value;
      y.innerHTML='<option value="">2003–2026</option>';
      (ANOS||[]).forEach(function(a){var o=document.createElement('option');o.value=a;o.textContent=a;y.appendChild(o);});
      if(cur) y.value=cur;
    }
  }

  function renderBars(a,b,rows){
    function make(id,field){
      if(ST.CH[id]){ST.CH[id].destroy();delete ST.CH[id];}
      var el=document.getElementById(id); if(!el) return;
      var top=rows.slice(0,12);
      ST.CH[id]=new Chart(el.getContext('2d'),{
        type:'bar',
        data:{labels:top.map(function(x){return x.tema;}),datasets:[
          {label:a,data:top.map(function(x){return Number(x.a[field]||0);}),backgroundColor:'#2563eb',borderRadius:5},
          {label:b,data:top.map(function(x){return Number(x.b[field]||0);}),backgroundColor:'#00a86b',borderRadius:5}
        ]},
        options:{responsive:true,indexAxis:'y',plugins:{legend:{labels:{font:{size:9}}}},scales:{x:{beginAtZero:true},y:{ticks:{font:{size:9}}}}}
      });
    }
    make('cmpPropsChart','propostas');
    make('cmpVotesChart','votacoes');
  }

  function renderTimeline(a,b){
    var el=document.getElementById('cmpTimeline'); if(!el) return;
    if(ST.CH.cmpTimeline){ST.CH.cmpTimeline.destroy();delete ST.CH.cmpTimeline;}
    var years=Object.keys(ST.summary&&ST.summary.years||{}).sort(function(x,y){return Number(x)-Number(y);});
    ST.CH.cmpTimeline=new Chart(el.getContext('2d'),{
      type:'line',
      data:{labels:years,datasets:[
        {label:a+' propostas',data:years.map(function(y){return Number(ST.insights.partyTotalsByYear&&ST.insights.partyTotalsByYear[y]&&ST.insights.partyTotalsByYear[y][a]&&ST.insights.partyTotalsByYear[y][a].propostas||0);}),borderColor:'#2563eb',pointRadius:2,tension:.2},
        {label:b+' propostas',data:years.map(function(y){return Number(ST.insights.partyTotalsByYear&&ST.insights.partyTotalsByYear[y]&&ST.insights.partyTotalsByYear[y][b]&&ST.insights.partyTotalsByYear[y][b].propostas||0);}),borderColor:'#00a86b',pointRadius:2,tension:.2},
        {label:a+' votações',data:years.map(function(y){return Number(ST.insights.partyTotalsByYear&&ST.insights.partyTotalsByYear[y]&&ST.insights.partyTotalsByYear[y][a]&&ST.insights.partyTotalsByYear[y][a].votacoes||0);}),borderColor:'#7c3aed',borderDash:[5,4],pointRadius:1,tension:.2},
        {label:b+' votações',data:years.map(function(y){return Number(ST.insights.partyTotalsByYear&&ST.insights.partyTotalsByYear[y]&&ST.insights.partyTotalsByYear[y][b]&&ST.insights.partyTotalsByYear[y][b].votacoes||0);}),borderColor:'#ea580c',borderDash:[5,4],pointRadius:1,tension:.2}
      ]},
      options:{responsive:true,plugins:{legend:{labels:{font:{size:9}}}},scales:{y:{beginAtZero:true},x:{ticks:{font:{size:9}}}}}
    });
  }

  window.swapCompareParties=function(){
    var a=document.getElementById('compPartyA'),b=document.getElementById('compPartyB'); if(!a||!b)return;
    var x=a.value;a.value=b.value;b.value=x;window.renderCompare();
  };

  window.renderCompare=function(){
    var box=document.getElementById('compareDashboard'); if(!box) return;
    if(!ST.insights){box.innerHTML='<div class="al al-w"><span>⏳</span><div>Preparando os dados comparativos...</div></div>';return;}
    populate();
    var a=val('compPartyA'),b=val('compPartyB'),year=val('compYear');
    if(!a||!b){box.innerHTML='<div class="al al-i"><span>ℹ️</span><div>Escolha o Partido A e o Partido B. O painel aplica os mesmos critérios aos dois.</div></div>';return;}
    if(a===b){box.innerHTML='<div class="al al-w"><span>⚠️</span><div>Escolha dois partidos diferentes.</div></div>';return;}

    var A=summary(a,year),B=summary(b,year),pair=pairInfo(a,b),rows=themeRows(a,b,year);
    var cap=year?'Ano '+year:'Período completo';
    var noteA=partyLineageNote(a)||'',noteB=partyLineageNote(b)||'';
    var pairHtml='';
    if(pair){
      var p=Number(pair.coincidenciaPct||0);
      pairHtml='<div class="pair-box"><div class="bxh">🤝 Quando os dois aparecem nas mesmas votações</div><div class="pair-meter"><i style="width:'+Math.max(0,Math.min(100,p))+'%"></i></div><div class="deep-grid"><div class="deep-metric"><b>'+p.toFixed(1)+'%</b><span>mesma direção majoritária</span></div><div class="deep-metric"><b>'+nfmt(pair.votacoesComuns)+'</b><span>votações comparáveis</span></div><div class="deep-metric"><b>'+nfmt(pair.mesmaDirecao!=null?pair.mesmaDirecao:pair.iguais)+'</b><span>mesma direção</span></div><div class="deep-metric"><b>'+nfmt(pair.direcaoOposta!=null?pair.direcaoOposta:pair.opostas)+'</b><span>direções opostas</span></div></div><div class="legend-note">Compara a direção majoritária SIM/NÃO dos votos individuais dos deputados nas votações em comum. Não é uma medida de proximidade ideológica.</div></div>';
    }else{
      pairHtml='<div class="al al-i"><span>ℹ️</span><div>Não há resumo pareado suficiente para calcular coincidência entre estes dois partidos.</div></div>';
    }

    var cloudAP=partyWordsFor(a,year,'propostas'),cloudAV=partyWordsFor(a,year,'votacoes');
    var cloudBP=partyWordsFor(b,year,'propostas'),cloudBV=partyWordsFor(b,year,'votacoes');

    box.innerHTML=
      '<div class="compare-head">'+
        '<div class="compare-party"><div class="kicker">PARTIDO A</div><h2>'+esc(a)+'</h2><div class="small-note">'+esc(noteA)+'</div><div class="compare-mini"><div><b>'+nfmt(A.propostas)+'</b><span>propostas</span></div><div><b>'+nfmt(A.normas)+'</b><span>viraram norma</span></div><div><b>'+nfmt(A.votacoes)+'</b><span>votações</span></div><div><b>'+(A.coesao==null?'—':A.coesao.toFixed(1)+'%')+'</b><span>coesão</span></div></div></div>'+
        '<div class="compare-vs">VS<br><span>'+esc(cap)+'</span></div>'+
        '<div class="compare-party"><div class="kicker">PARTIDO B</div><h2>'+esc(b)+'</h2><div class="small-note">'+esc(noteB)+'</div><div class="compare-mini"><div><b>'+nfmt(B.propostas)+'</b><span>propostas</span></div><div><b>'+nfmt(B.normas)+'</b><span>viraram norma</span></div><div><b>'+nfmt(B.votacoes)+'</b><span>votações</span></div><div><b>'+(B.coesao==null?'—':B.coesao.toFixed(1)+'%')+'</b><span>coesão</span></div></div></div>'+
      '</div>'+
      pairHtml+
      '<div class="bx"><div class="bxh">📊 Em quais temas cada um aparece?</div><div class="small-note" style="margin-bottom:10px">Mesma escala para os dois. Propostas e votações são dimensões diferentes e ficam separadas.</div><div class="compare-charts"><div class="analysis-card"><div class="kicker">PROPOSTAS POR TEMA</div><canvas id="cmpPropsChart" height="390"></canvas></div><div class="analysis-card"><div class="kicker">VOTAÇÕES POR TEMA</div><canvas id="cmpVotesChart" height="390"></canvas></div></div></div>'+
      '<div class="bx"><div class="bxh">☁️ Palavras que mais aparecem</div><div class="compare-clouds"><div class="compare-cloud-party"><h3>'+esc(a)+'</h3><div class="kicker">NAS PROPOSTAS</div>'+wordCloudHTML(cloudAP)+'<div class="kicker" style="margin-top:14px">NOS ASSUNTOS VOTADOS</div>'+wordCloudHTML(cloudAV)+'</div><div class="compare-cloud-party"><h3>'+esc(b)+'</h3><div class="kicker">NAS PROPOSTAS</div>'+wordCloudHTML(cloudBP)+'<div class="kicker" style="margin-top:14px">NOS ASSUNTOS VOTADOS</div>'+wordCloudHTML(cloudBV)+'</div></div></div>'+
      '<div class="bx"><div class="bxh">🧾 Tema por tema</div><div class="tw"><table class="compare-topic-table"><thead><tr><th>Tema</th><th>'+esc(a)+' propostas</th><th>'+esc(b)+' propostas</th><th>'+esc(a)+' votações</th><th>'+esc(b)+' votações</th><th>'+esc(a)+' maioria SIM</th><th>'+esc(b)+' maioria SIM</th></tr></thead><tbody>'+
      rows.slice(0,25).map(function(x){return '<tr><td><strong>'+esc(x.tema)+'</strong></td><td>'+nfmt(x.a.propostas)+'</td><td>'+nfmt(x.b.propostas)+'</td><td>'+nfmt(x.a.votacoes)+'</td><td>'+nfmt(x.b.votacoes)+'</td><td>'+nfmt(x.a.maioriaSim)+'</td><td>'+nfmt(x.b.maioriaSim)+'</td></tr>';}).join('')+
      '</tbody></table></div></div>'+
      (year?'':'<div class="bx"><div class="bxh">📈 Como mudou ao longo do tempo</div><canvas id="cmpTimeline" height="300"></canvas></div>')+
      '<div class="bx"><div class="bxh">🗳 Casos concretos em que os dois participaram</div>'+(year?'<div id="compareCases"><button class="btn btn-p" onclick="loadCompareCases()">Carregar votações de '+esc(year)+'</button><div class="legend-note">Mostra assunto, resultado e números SIM/NÃO dos dois partidos na mesma votação.</div></div>':'<div class="al al-i"><span>📅</span><div>Escolha um ano no topo para abrir casos concretos sem carregar todos os anos no celular.</div></div>')+'</div>';

    setTimeout(function(){renderBars(a,b,rows);if(!year)renderTimeline(a,b);},30);
  };

  window.loadCompareCases=async function(){
    var box=document.getElementById('compareCases'),a=val('compPartyA'),b=val('compPartyB'),year=Number(val('compYear')); if(!box||!a||!b||!year)return;
    box.innerHTML='<div class="ldg" style="padding:24px"><div class="spin"></div><div class="ldg-t">Carregando votações comuns...</div></div>';
    try{
      var d=await loadYearOfficial(year),items=[];
      (d.votacoes||[]).forEach(function(v){
        var cp={};
        Object.entries(v.partidos||{}).forEach(function(pair){
          var p=canonParty(pair[0]),x=pair[1];
          if(!cp[p])cp[p]={S:0,N:0,A:0,O:0,outros:0,total:0};
          ['S','N','A','O','outros','total'].forEach(function(k){cp[p][k]+=Number(x&&x[k]||0);});
        });
        if(!cp[a]||!cp[b])return;
        var da=cp[a].S>cp[a].N?'S':cp[a].N>cp[a].S?'N':'D';
        var db=cp[b].S>cp[b].N?'S':cp[b].N>cp[b].S?'N':'D';
        var sub=v.assunto||null,themes=propThemes(sub);
        items.push({v:v,pa:cp[a],pb:cp[b],da:da,db:db,sub:sub,themes:themes});
      });
      items.sort(function(x,y){return String(y.v.data||'').localeCompare(String(x.v.data||''));});
      if(!items.length){box.innerHTML='<div class="al al-i"><span>ℹ️</span><div>Nenhuma votação comum encontrada neste ano.</div></div>';return;}
      box.innerHTML='<div class="al al-g"><span>✅</span><div><strong>'+nfmt(items.length)+'</strong> votações de '+year+' com participação dos dois partidos.</div></div><div class="compare-case-grid">'+items.slice(0,30).map(function(x){
        var title=x.sub?plainEmenta(x.sub.ementa||''):plainEmenta(x.v.descricao||'Votação nominal');
        var relation=(x.da!=='D'&&x.db!=='D')?(x.da===x.db?'mesma direção majoritária':'direções majoritárias opostas'):'sem direção majoritária clara';
        return '<div class="compare-case"><div class="vlabel">'+esc(x.v.data||'—')+' · '+esc(x.v.orgao||'—')+'</div><h4>'+esc(title)+'</h4>'+(x.themes.length?'<div>'+x.themes.slice(0,2).map(function(t){return '<span class="tag" style="margin:2px">'+esc(t)+'</span>';}).join('')+'</div>':'')+'<div class="compare-directions"><div class="compare-dir"><span>'+esc(a)+'</span><b>'+(x.da==='S'?'Maioria SIM':x.da==='N'?'Maioria NÃO':'Equilibrado')+'</b>'+nfmt(x.pa.S)+' sim · '+nfmt(x.pa.N)+' não</div><div class="compare-dir"><span>'+esc(b)+'</span><b>'+(x.db==='S'?'Maioria SIM':x.db==='N'?'Maioria NÃO':'Equilibrado')+'</b>'+nfmt(x.pb.S)+' sim · '+nfmt(x.pb.N)+' não</div></div><div class="small-note"><strong>Resultado:</strong> '+(String(x.v.aprovacao)==='1'?'Aprovada':String(x.v.aprovacao)==='0'?'Não aprovada':'Não marcado')+' · '+relation+'</div><div class="inline-actions"><button class="btn btn-s" onclick="openCompareVote('+year+',\''+esc(x.v.id)+'\')">Ver votação completa</button></div></div>';
      }).join('')+'</div>';
    }catch(e){
      box.innerHTML='<div class="erro"><p>'+esc(e.message)+'</p><button class="btn btn-s" onclick="loadCompareCases()">Tentar novamente</button></div>';
    }
  };

  window.openCompareVote=async function(year,id){
    var d=await loadYearOfficial(year),old=ST.vots;
    ST.vots=d.votacoes||[];abrirVot(id);ST.vots=old;
  };

  window.addEventListener('load',function(){setTimeout(populate,150);});
})();
