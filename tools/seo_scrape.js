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
      return {id,name:x.en,fa:x.fa,cat:catName(catOf(x.cat)),catId:x.cat,year:x.year||null,hero:heroSrc(id)||null,thumb:IMG['t-'+id]||null,
        drawing:DR[id]?IMG['d-'+id]:null,photos,dims,spec,desc,edition:(q('.edbadge b')||{}).textContent||'',editionNote:(q('.edbadge span')||{}).textContent||''}},id);
    out.pieces.push(d);
  }
  await pg.evaluate(()=>{location.hash='#/about'});await pg.waitForTimeout(800);
  out.about=await pg.evaluate(()=>{const m=document.querySelector('main.page.about');if(!m)return null;
    return {title:(m.querySelector('h1')||{}).textContent||'About',paras:[...m.querySelectorAll('p')].map(p=>p.innerText.trim()).filter(Boolean),
      bios:[...m.querySelectorAll('.bios figure')].map(f=>({img:(f.querySelector('img')||{}).getAttribute?f.querySelector('img').getAttribute('src'):null,name:(f.querySelector('figcaption b')||{}).textContent||'',text:(f.querySelector('figcaption p')||{}).textContent||''}))}});
  console.log(JSON.stringify(out));await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
