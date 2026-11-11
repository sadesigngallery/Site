// Reads the built catalogue in a headless browser and prints, as JSON, what each
// piece page shows (in English), plus the About page. Used by build.py to write
// the static, search-engine-friendly pages. Usage: node seo_scrape.js http://localhost:PORT/
const {chromium}=require('playwright');
(async()=>{
  const base=process.argv[2];
  const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1100,height:900}});
  await pg.addInitScript(()=>{try{localStorage.setItem('sa-lang','en')}catch(_){}});
  await pg.goto(base+'index.html#/');await pg.waitForTimeout(2500);
  const ids=await pg.evaluate(()=>P.map(x=>x.id));
  const out={pieces:[],about:null};
  for(const id of ids){
    await pg.evaluate(id=>{location.hash='#/p/'+id},id);await pg.waitForTimeout(350);
    const d=await pg.evaluate(id=>{const x=byId(id);const q=s=>document.querySelector(s);
      const dims=[...document.querySelectorAll('.dims>div')].map(c=>{const sm=c.querySelector('small'),bb=c.querySelector('b');return [sm?sm.textContent.trim():'',bb?bb.textContent.replace(/\s+/g,' ').trim():'']});
      const spec=[...document.querySelectorAll('dl.spec dt')].map(dt=>[dt.textContent.trim(),(dt.nextElementSibling?dt.nextElementSibling.innerText:'').replace(/\s+/g,' ').trim()]);
      const desc=[...document.querySelectorAll('.info .desc p')].map(p=>p.textContent.trim()).filter(Boolean);
      const photos=(PH[id]||[]).map(k=>IMG[k]).filter(Boolean);
      const c=catOf(x.cat),grp=x.cat==='piano'?['PIANO','LIMITED EDITION']:[c[1]==='Lighting'?'LIGHTING':c[1]==='Seating'?'SEATING':'TABLES',catName(c).toUpperCase()];
      return {id,name:x.en,fa:x.fa,cat:catName(c),catId:x.cat,grp,yt:(typeof YTV!=='undefined'&&YTV[id])||null,tbb:(PACK.TBB||{})[id]||null,ts:TS[id]||null,year:x.year||null,hero:heroSrc(id)||null,thumb:IMG['t-'+id]||null,
        drawing:DR[id]?IMG['d-'+id]:null,photos,dims,spec,desc,edition:(q('.edbadge b')||{}).textContent||'',editionNote:(q('.edbadge span')||{}).textContent||''}},id);
    out.pieces.push(d);
  }
  // the same piece pages in the catalogue's other languages
  out.langs={};
  for(const L of ['fa','ar','it','fr','de','es','ja','zh']){
    const cx=await b.newContext({viewport:{width:1100,height:900}});const q=await cx.newPage();
    await q.addInitScript(l=>{try{localStorage.setItem('sa-lang',l)}catch(_){}},L);
    await q.goto(base+'index.html#/');await q.waitForTimeout(2500);
    const ui=await q.evaluate(()=>{const T_=t();return {tag:(typeof TAGL!=='undefined'&&(TAGL[L]||TAGL.en))||'',all:(typeof ALLP!=='undefined'&&(ALLP[L]||ALLP.en))||'',contact:T_.contact||'',about:T_.aboutT||'',email:T_.email||''}});
    const ps=[];
    for(const id of ids){
      await q.evaluate(id=>{location.hash='#/p/'+id},id);await q.waitForTimeout(300);
      ps.push(await q.evaluate(id=>{const x=byId(id);const qq=s=>document.querySelector(s);const c=catOf(x.cat);
        return {id,cat:catName(c),dims:[...document.querySelectorAll('.dims>div')].map(c=>{const sm=c.querySelector('small'),bb=c.querySelector('b');return [sm?sm.textContent.trim():'',bb?bb.textContent.replace(/\s+/g,' ').trim():'']}),
          spec:[...document.querySelectorAll('dl.spec dt')].map(dt=>[dt.textContent.trim(),(dt.nextElementSibling?dt.nextElementSibling.innerText:'').replace(/\s+/g,' ').trim()]),
          desc:[...document.querySelectorAll('.info .desc p')].map(p=>p.textContent.trim()).filter(Boolean),
          edition:(qq('.edbadge b')||{}).textContent||'',editionNote:(qq('.edbadge span')||{}).textContent||''}},id));
    }
    out.langs[L]={ui,pieces:ps};await cx.close();
  }
  await pg.evaluate(()=>{location.hash='#/about'});await pg.waitForTimeout(800);
  out.about=await pg.evaluate(()=>{const m=document.querySelector('main.page.about');if(!m)return null;
    return {title:(m.querySelector('h1')||{}).textContent||'About',paras:[...m.querySelectorAll('p')].map(p=>p.innerText.trim()).filter(Boolean),
      bios:[...m.querySelectorAll('.bios figure')].map(f=>({img:(f.querySelector('img')||{}).getAttribute?f.querySelector('img').getAttribute('src'):null,name:(f.querySelector('figcaption b')||{}).textContent||'',text:(f.querySelector('figcaption p')||{}).textContent||''}))}});
  console.log(JSON.stringify(out));await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
