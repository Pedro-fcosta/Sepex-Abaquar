const pagina=document.querySelector('.voo-pagina');const id=pagina.dataset.id;
const titulo=document.getElementById('titulo-voo'),contagem=document.getElementById('contagem'),foguete=document.getElementById('foguete-voo'),altitude=document.getElementById('altitude-atual');
function esperar(ms){return new Promise(resolve=>setTimeout(resolve,ms))}
function quadro(pontos,t){if(t<=pontos[0].tempo_s)return pontos[0].altitude_m;for(let i=1;i<pontos.length;i++){if(t<=pontos[i].tempo_s){const a=pontos[i-1],b=pontos[i],f=(t-a.tempo_s)/(b.tempo_s-a.tempo_s);return a.altitude_m+(b.altitude_m-a.altitude_m)*f}}return pontos.at(-1).altitude_m}
async function iniciar(){try{const resposta=await fetch(`/api/voo/${id}`);if(!resposta.ok)throw Error('Não foi possível carregar o voo');const dados=await resposta.json(),t=dados.tentativa;
 document.getElementById('tipo-trajetoria').textContent=dados.pontos.length?'Trajetória baseada na série temporal importada do OpenRocket.':'Animação ilustrativa. Os indicadores oficiais vêm somente do resultado armazenado.';
 for(const n of [3,2,1]){contagem.textContent=n;await esperar(750)}contagem.textContent='LANÇAR!';titulo.textContent='Decolagem';await esperar(500);contagem.textContent='';
 const pontos=dados.pontos,temSerie=pontos.length>1,duracao=temSerie?pontos.at(-1).tempo_s:(t.tempo_apogeu_s||7)*1.5;
 const apogeu=t.apogeu_m,tempoApogeu=t.tempo_apogeu_s||duracao*.65,escala=Math.max(apogeu,1);
 const inicio=performance.now(),duracaoVisual=7000;
 await new Promise(resolve=>{function animar(agora){const progresso=Math.min(1,(agora-inicio)/duracaoVisual),tempo=progresso*duracao;
 // Sem série, a curva é exclusivamente visual e jamais é salva ou usada como resultado.
 const altura=temSerie?quadro(pontos,tempo):apogeu*Math.max(0,1-Math.pow((tempo-tempoApogeu)/Math.max(tempoApogeu,duracao-tempoApogeu),2));
 altitude.textContent=`${Math.round(altura)} m`;foguete.style.bottom=`${18+Math.max(0,altura)/escala*72}%`;
 if(progresso<1)requestAnimationFrame(animar);else resolve()}requestAnimationFrame(animar)});
 titulo.textContent='Voo concluído';document.getElementById('ver-resultado').classList.remove('oculto');
 }catch(e){titulo.textContent=e.message;document.getElementById('ver-resultado').classList.remove('oculto')}}
iniciar();
