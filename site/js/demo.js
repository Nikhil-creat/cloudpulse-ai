(function(){
  var body=document.body,burger=document.getElementById('burger');
  function setMenu(o){body.classList.toggle('menu-open',o);burger.setAttribute('aria-expanded',o);burger.setAttribute('aria-label',o?'Close menu':'Open menu')}
  burger.addEventListener('click',function(){setMenu(!body.classList.contains('menu-open'))});
  document.querySelectorAll('nav a').forEach(function(a){a.addEventListener('click',function(){setMenu(false)})});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')setMenu(false)});
  window.matchMedia('(min-width:901px)').addEventListener('change',function(m){if(m.matches)setMenu(false)});

  /* ---- heatmap demo (client-side simulation) ---- */
  var M=['cpu','memory','net_in','net_out','disk_io','cost','auth_fail','api_calls'],W=96,H=8,cv=document.getElementById('heat'),cx=cv.getContext('2d');
  var scenario='normal',data=null,seed=7;
  function rnd(){seed=(seed*16807)%2147483647;return seed/2147483647}
  function gen(kind){
    var d=[],r,c;for(r=0;r<H;r++){d.push([]);for(c=0;c<W;c++)d[r].push(.05+rnd()*.04)}
    if(kind==='idle'){for(r=0;r<H;r++)for(c=0;c<W;c++)d[r][c]*=.5;return d}
    for(c=0;c<W;c++){var t=c/W*12.56;d[0][c]+=.35+.2*Math.sin(t);d[1][c]+=.45;d[4][c]+=.2+.1*Math.sin(t+1);d[7][c]+=.3+.15*Math.sin(t)}
    var s=60+Math.floor(rnd()*15);
    if(kind==='cost_spike')for(c=s;c<W;c++){d[5][c]+=.7;d[0][c]+=.3}
    if(kind==='intrusion')for(c=s;c<s+12;c++){d[6][c]+=.85;d[3][c]+=.7}
    return d}
  function color(v){v=Math.max(0,Math.min(1,v));var r=Math.round(255*v),g=Math.round(255*v*.55),b=Math.round(255*(1-v)*.9+20);return 'rgb('+r+','+g+','+b+')'}
  function draw(upTo){cx.clearRect(0,0,W,40);for(var r=0;r<H;r++)for(var c=0;c<W;c++){cx.fillStyle=color(data[r][c]);cx.fillRect(c,r*5,1,5)}
    if(upTo!=null){cx.fillStyle='rgba(255,255,255,.55)';cx.fillRect(upTo,0,1,40)}}
  function classify(d){
    var mean=function(r,a,b){var s=0;for(var c=a;c<b;c++)s+=d[r][c];return s/(b-a)};
    var all=0;for(var r=0;r<H;r++)all+=mean(r,0,W);all/=H;
    var cost=mean(5,70,W)-mean(5,0,40),auth=Math.max.apply(null,d[6])-mean(6,0,40);
    var p={normal:.1,cost_spike:.03,idle:.03,intrusion:.03};
    if(all<.08)p.idle=1.6;else if(cost>.4)p.cost_spike=1.5;else if(auth>.5)p.intrusion=1.5;else p.normal=1.4;
    var z=0,k;for(k in p)z+=p[k];for(k in p)p[k]/=z;return p}
  function setScenario(s){scenario=s;seed=7+s.length;data=gen(s);draw();
    document.querySelectorAll('[data-s]').forEach(function(b){b.setAttribute('aria-pressed',b.dataset.s===s)});
    document.getElementById('res').textContent='Scenario loaded. Run inference to classify the last 24 hours.';document.getElementById('bars').innerHTML=''}
  document.querySelectorAll('[data-s]').forEach(function(b){b.addEventListener('click',function(){setScenario(b.dataset.s)})});
  document.getElementById('run').addEventListener('click',function(){
    var c=0,res=document.getElementById('res');res.textContent='Scanning heatmap…';
    var reduce=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    function done(){draw();if(window.__cpFeat)window.__cpFeat(data);var p=classify(data),best='normal',k;for(k in p)if(p[k]>p[best])best=k;
      res.innerHTML='Prediction: <b>'+best.replace('_',' ')+'</b> at '+(p[best]*100).toFixed(1)+'% confidence'+(best!=='normal'?' · alert would open':'');
      document.getElementById('bars').innerHTML=Object.keys(p).map(function(k){return '<div class="bar"><span>'+k.replace('_',' ')+'</span><i data-w="'+(p[k]*100)+'"></i><span>'+(p[k]*100).toFixed(0)+'%</span></div>'}).join('');
      requestAnimationFrame(function(){document.querySelectorAll('.bar i').forEach(function(i){i.style.width=i.dataset.w+'%'})})}
    if(reduce)return done();
    (function step(){draw(c);c+=3;if(c<W)requestAnimationFrame(step);else done()})()});
  window.__cp={setScenario:setScenario,classify:classify,data:function(){return data}};setScenario('normal');

  /* ---- copilot with HITL gate ---- */
  var log=document.getElementById('log');
  function add(cls,html){var d=document.createElement('div');d.className=cls;d.innerHTML=html;log.appendChild(d);log.scrollTop=log.scrollHeight;return d}
  var PLANS={
    'Find idle EC2 instances and cut cost':{agent:['triage: routing to FinOps agent','finops called metric_summary','finops called list_resources','planner: drafting Terraform, running dry-run'],
      text:'3 instances averaged under 4% CPU for 24 hours. Stopping them saves about $212 a month.',steps:[['Stop i-0a1…, i-0b7…, i-0c4…','low'],['Tag stopped instances finops:review','low']],blast:3},
    'Audit my S3 buckets against CIS':{agent:['triage: routing to Security agent','security called search_runbooks (CIS 2.1.x)','security called list_resources','planner: drafting Terraform, running dry-run'],
      text:'2 buckets fail CIS 2.1.4 (public access block missing) and 1 lacks default encryption.',steps:[['Enable public access block on 2 buckets','medium'],['Enable SSE-KMS on 1 bucket','low']],blast:3}};
  document.querySelectorAll('[data-q]').forEach(function(b){b.addEventListener('click',function(){
    var q=b.dataset.q,p=PLANS[q];add('m-u',q);var a=add('m-a','<span class="t">Swarm engaged…</span>'),i=0;
    var t=setInterval(function(){
      if(i<p.agent.length){a.innerHTML='<span class="t">'+p.agent[i++]+'</span>';log.scrollTop=log.scrollHeight;return}
      clearInterval(t);
      a.innerHTML=p.text+'<div class="plan">'+p.steps.map(function(s){return '<div>• '+s[0]+' <span class="t">('+s[1]+')</span></div>'}).join('')+
        '<div class="t">Blast radius score '+p.blast+' of 10 allowed · dry-run passed</div><div class="row2"><button class="btn btn-solid">Approve</button><button class="btn btn-danger">Reject</button></div></div>';
      var bs=a.querySelectorAll('button');
      bs[0].onclick=function(){a.querySelector('.row2').innerHTML='<span class="t">Approved. Queued for Terraform apply and written to the audit log.</span>'};
      bs[1].onclick=function(){a.querySelector('.row2').innerHTML='<span class="t">Rejected. Nothing was changed.</span>'};
      log.scrollTop=log.scrollHeight},650)})});
})();
