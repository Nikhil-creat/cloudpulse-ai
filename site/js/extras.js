(function(){
  'use strict';
  var $=function(i){return document.getElementById(i)};
  function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}

  /* ---- live GitHub activity (public API, cached 10 min) ---- */
  (function(){var box=$('ghlive');if(!box)return;var U='Nikhil-creat',key='cp_gh';
    function render(u,repos){box.textContent='';var st=el('div','ghs');
      [['Public repos',u.public_repos],['Followers',u.followers],['Following',u.following]].forEach(function(p){var d=el('span','',p[0]+': '+p[1]);st.appendChild(d)});box.appendChild(st);
      var list=el('div','');list.appendChild(el('span','','Recently active: '));
      repos.filter(function(r){return !r.fork}).slice(0,5).forEach(function(r,i){if(r.html_url.indexOf('https://github.com/')!==0)return;if(i)list.appendChild(document.createTextNode(' · '));var a=el('a','',r.name);a.href=r.html_url;a.target='_blank';a.rel='noopener';list.appendChild(a)});box.appendChild(list)}
    try{var c=JSON.parse(sessionStorage.getItem(key)||'null');if(c&&Date.now()-c.t<6e5){render(c.u,c.r);return}}catch(e){}
    function j(r){if(!r.ok)throw new Error(r.status);return r.json()}
    Promise.all([fetch('https://api.github.com/users/'+U).then(j),fetch('https://api.github.com/users/'+U+'/repos?sort=pushed&per_page=8').then(j)]).then(function(x){try{sessionStorage.setItem(key,JSON.stringify({t:Date.now(),u:x[0],r:x[1]}))}catch(e){}render(x[0],x[1])}).catch(function(){box.textContent='Live GitHub activity is unavailable right now. See github.com/'+U+'.'})})();

  /* ---- command palette (Ctrl/Cmd+K or /) ---- */
  function go(id){var t=$(id);if(t){t.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth'});}}
  var CMDS=[['Go to Platform',function(){go('platform')}],['Go to Architecture',function(){go('architecture')}],['Inspect the CNN',function(){go('demo')}],['Go to Assistant',function(){go('assistant');var i=$('ain');if(i)setTimeout(function(){i.focus()},400)}],['Go to Security',function(){go('security')}],['Go to Credentials',function(){go('credentials')}],['Go to Roadmap',function(){go('roadmap')}],
    ['Run CNN on an intrusion',function(){go('demo');if(window.__cp)window.__cp.setScenario('intrusion')}],['Run CNN on a cost spike',function(){go('demo');if(window.__cp)window.__cp.setScenario('cost_spike')}],
    ['Open GitHub profile',function(){window.open('https://github.com/Nikhil-creat','_blank','noopener')}],['Open the repository',function(){window.open('https://github.com/Nikhil-creat/cloudpulse-ai','_blank','noopener')}],['Email Nikhil',function(){location.href='mailto:sriramojunikhil66@gmail.com'}]];
  var pal=null,prev=null,sel=0,shown=CMDS;
  function close(){if(!pal)return;pal.remove();pal=null;if(prev&&prev.focus)prev.focus()}
  function paint(ul){ul.textContent='';shown.forEach(function(c,i){var li=el('li','',c[0]);li.setAttribute('role','option');li.setAttribute('aria-selected',i===sel);li.addEventListener('click',function(){close();c[1]()});ul.appendChild(li)})}
  function open(){if(pal)return;prev=document.activeElement;sel=0;shown=CMDS;
    pal=el('div','pal');pal.setAttribute('role','dialog');pal.setAttribute('aria-modal','true');pal.setAttribute('aria-label','Command palette');
    var box=el('div'),inp=el('input');inp.placeholder='Type a command…';inp.setAttribute('aria-label','Command');var ul=el('ul');ul.setAttribute('role','listbox');box.appendChild(inp);box.appendChild(ul);pal.appendChild(box);document.body.appendChild(pal);paint(ul);inp.focus();
    pal.addEventListener('mousedown',function(e){if(e.target===pal)close()});
    inp.addEventListener('input',function(){var q=inp.value.toLowerCase();shown=CMDS.filter(function(c){return c[0].toLowerCase().indexOf(q)>=0});sel=0;paint(ul)});
    inp.addEventListener('keydown',function(e){if(e.key==='ArrowDown'){e.preventDefault();sel=Math.min(shown.length-1,sel+1);paint(ul)}else if(e.key==='ArrowUp'){e.preventDefault();sel=Math.max(0,sel-1);paint(ul)}else if(e.key==='Enter'&&shown[sel]){e.preventDefault();var f=shown[sel][1];close();f()}else if(e.key==='Escape'){close()}else if(e.key==='Tab'){e.preventDefault()}})}
  document.addEventListener('keydown',function(e){var typing=/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement||{}).tagName);
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();pal?close():open()}else if(e.key==='/'&&!typing&&!pal){e.preventDefault();open()}});
  var pb=$('palbtn');if(pb)pb.addEventListener('click',open);

  /* ---- voice in / voice out (browser-native, no extra service) ---- */
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition,mic=$('amic'),sp=$('aspeak');
  if(mic){if(!SR){mic.style.display='none'}else{var rec=null;mic.addEventListener('click',function(){if(rec){rec.stop();return}
    rec=new SR();rec.lang=navigator.language||'en-US';rec.interimResults=false;rec.maxAlternatives=1;mic.setAttribute('aria-pressed','true');mic.textContent='Listening…';
    rec.onresult=function(e){var t=e.results[0][0].transcript;if(t&&window.__cpAsk)window.__cpAsk(t)};
    rec.onend=function(){rec=null;mic.setAttribute('aria-pressed','false');mic.textContent='Mic'};rec.onerror=function(){};rec.start()})}}
  if(sp){if(!('speechSynthesis' in window)){sp.style.display='none'}else{sp.addEventListener('click',function(){var on=sp.getAttribute('aria-pressed')!=='true';sp.setAttribute('aria-pressed',on);if(!on)speechSynthesis.cancel()});
    document.addEventListener('cp:answer',function(e){if(sp.getAttribute('aria-pressed')==='true'){speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(String(e.detail||'').slice(0,500));speechSynthesis.speak(u)}})}}

  /* ---- offline shell (network-first service worker) ---- */
  if('serviceWorker' in navigator&&(location.protocol==='https:'||location.hostname==='localhost')){navigator.serviceWorker.register('sw.js').catch(function(){})}
})();
