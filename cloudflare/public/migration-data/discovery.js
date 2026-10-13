// Match the original declared_hits rules, without reusing another user's ranking.
const nz = value => String(value ?? '').normalize('NFKC').replace(/\s/g,'').toLowerCase();
export function declaredHits(candidate,favourites) {
  const blob=nz(`${candidate.title} ${candidate.group??''} ${JSON.stringify(candidate.fields??{})}`);
  const words=(candidate.words??[]).map(nz).filter(Boolean);
  const synopsis=nz(candidate.synopsis);
  const hits=[];
  for(const {kind,name} of favourites) {
    const word=nz(name);if(!word)continue;
    if(['団体','主催'].includes(kind)) {if(nz(candidate.group).includes(word))hits.push(`${kind}「${name}」`);}
    if(['人','作品','原作者'].includes(kind)&&blob.includes(word))hits.push(`${kind}「${name}」`);
    if(['題材','原作者'].includes(kind)&&(words.some(w=>w.includes(word)||word.includes(w))||synopsis.includes(word)))hits.push(`題材「${name}」`);
  }
  return [...new Set(hits)].sort();
}
export function discover(items,favourites,reactions,today) {
  const signals=new Map(reactions.map(r=>[r.stage_id,r.status]));
  const out={favourites:[],tracking:[],owned:[],started:[],others:[]};
  for(const c of items) {
    if((c.end_date??c.date)<today)continue;
    const reasons=declaredHits(c,favourites), status=signals.get(c.id);
    const row={...c,reasons};
    if(status==='owned')out.owned.push(row);
    else if(status==='interest')out.tracking.push(row);
    else if(status==='no')out.others.push(row);
    else if(reasons.length)out[c.date>today?'favourites':'started'].push(row);
  }
  for(const bucket of Object.values(out))bucket.sort((a,b)=>a.date.localeCompare(b.date)||a.title.localeCompare(b.title));
  return out;
}
