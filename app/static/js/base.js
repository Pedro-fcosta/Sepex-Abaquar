const botaoTema=document.getElementById('tema');
const temaSalvo=localStorage.getItem('sepex-tema');
if(temaSalvo) document.documentElement.dataset.tema=temaSalvo;
botaoTema?.addEventListener('click',()=>{const proximo=document.documentElement.dataset.tema==='escuro'?'claro':'escuro';document.documentElement.dataset.tema=proximo;localStorage.setItem('sepex-tema',proximo)});
