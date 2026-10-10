import {test} from 'node:test';
import assert from 'node:assert/strict';
import {declaredHits,discover} from '../public/discovery.js';
test('groups match the producer only; people also match guest credits',()=>{
 const c={title:'舞台',group:'主催劇団',fields:{出演:'客演劇団の俳優Ａ'}};
 assert.deepEqual(declaredHits(c,[{kind:'団体',name:'客演劇団'}]),[]);
 assert.deepEqual(declaredHits(c,[{kind:'主催',name:'主催劇団'}]),['主催「主催劇団」']);
 assert.deepEqual(declaredHits(c,[{kind:'人',name:'俳優a'}]),['人「俳優a」']);
});
test('theme and original author match normalized synopsis and extracted words',()=>{
 const c={title:'物語',synopsis:'家族をめぐるミステリー',words:['孤独な人間']};
 assert.deepEqual(declaredHits(c,[{kind:'題材',name:'ミステリー'},{kind:'題材',name:'孤独'}]),['題材「ミステリー」','題材「孤独」']);
 assert.deepEqual(declaredHits({...c,fields:{原作:'作者'}},[{kind:'原作者',name:'作者'}]),['原作者「作者」']);
});
test('signals override favourites; opening day and ended shows are separated',()=>{
 const items=[{id:'future',title:'舞台',date:'2026-11-01'},{id:'today',title:'舞台',date:'2026-10-10'},{id:'ended',title:'舞台',date:'2026-09-01',end_date:'2026-10-09'}];
 const favs=[{kind:'作品',name:'舞台'}];
 const result=discover(items,favs,[{stage_id:'future',status:'owned'}],'2026-10-10');
 assert.equal(result.favourites.length,0);assert.equal(result.owned[0].id,'future');assert.equal(result.started[0].id,'today');
 assert.equal(Object.values(result).flat().length,2);
 const tracking=discover(items,[],[{stage_id:'future',status:'interest'}],'2026-10-10');assert.equal(tracking.tracking[0].id,'future');
});
