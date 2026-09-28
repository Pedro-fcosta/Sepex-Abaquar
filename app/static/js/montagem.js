const formulario=document.getElementById('form-montagem');
const botao=document.getElementById('confirmar');
const erro=document.getElementById('erro');
const estado=document.getElementById('disponibilidade');
const nomesCoifa={C1:'cônica',C2:'ogival',C3:'elipsoidal'};
const nomesAleta={A1:'trapezoidal reta',A2:'trapezoidal enflechada',A3:'elíptica'};
let codigoAtual='';let disponivel=false;let enviando=false;let requisicao=0;
function escolha(nome){return formulario.querySelector(`input[name="${nome}"]:checked`)?.value}
async function atualizar(){const coifa=escolha('coifa'),aleta=escolha('aleta'),aletas=escolha('aletas'),secoes=escolha('secoes');
 if(!coifa||!aleta||!aletas||!secoes)return;
 codigoAtual=`${coifa}-${aleta}-F${aletas}-S${secoes}`;
 document.getElementById('codigo').textContent=codigoAtual;
 document.getElementById('descricao').textContent=`Coifa ${nomesCoifa[coifa]} · Aleta ${nomesAleta[aleta]} · ${aletas} aletas · ${Number(secoes)*20} cm de corpo`;
 document.getElementById('preview-coifa').className=`preview-coifa ${coifa.toLowerCase()}`;
 document.getElementById('preview-aleta').className=`preview-aleta ${aleta.toLowerCase()}`;
 document.getElementById('preview-corpo').style.width=`${75+Number(secoes)*55}px`;
 estado.textContent='Consultando simulação...';botao.disabled=true;const pedido=++requisicao;
 try{const resposta=await fetch(`/api/configuracoes/${codigoAtual}`);if(!resposta.ok)throw Error('Configuração não encontrada');const dados=await resposta.json();if(pedido!==requisicao)return;
 disponivel=dados.disponivel;estado.classList.toggle('indisponivel',!disponivel);
 estado.textContent=disponivel?(dados.demonstrativo?'Disponível · DEMONSTRAÇÃO com dados fictícios':'Simulação OpenRocket aprovada disponível'):'Sem simulação aprovada. Escolha outra configuração.';
 botao.disabled=!disponivel;
 }catch(e){if(pedido===requisicao){disponivel=false;estado.textContent='Falha ao consultar configuração';botao.disabled=true}}
}
formulario.addEventListener('change',atualizar);atualizar();
formulario.addEventListener('submit',async evento=>{evento.preventDefault();if(enviando||!disponivel||!formulario.reportValidity())return;
 enviando=true;botao.disabled=true;erro.textContent='';
 let identificador=sessionStorage.getItem('sepex-participacao');if(!identificador){identificador=crypto.randomUUID().replaceAll('-','');sessionStorage.setItem('sepex-participacao',identificador)}
 try{const resposta=await fetch('/api/tentativas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:document.getElementById('nome').value,codigo:codigoAtual,identificador_sessao:identificador})});const dados=await resposta.json();if(!resposta.ok)throw Error(dados.erro||'Falha ao registrar');sessionStorage.removeItem('sepex-participacao');location.assign(dados.url_voo)}
 catch(e){erro.textContent=e.message;enviando=false;botao.disabled=false}
});
