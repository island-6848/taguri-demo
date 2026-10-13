#!/usr/bin/env python3
"""Create explicit public-only renderer input. Never copy owner data wholesale.

The output supplies source catalogue/credits/theme fields only. It intentionally
cannot reconstruct the private owner's base ranking from purchase history.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
from convert_catalogue import public_candidate


PUBLIC_FIELDS = {'出演','作','演出','脚本','翻訳','振付','音楽','美術','照明','音響','衣装','衣裳','舞台監督','宣伝美術','制作','原作','原作者','主催','企画','プロデューサー','劇作・脚本','演奏','指揮','歌唱','作曲','編曲','作詞','監修','団体','出演者','スタッフ','その他'}


def clean_fields(fields):
    # Fields are public credit-role -> human/group names. No arbitrary nested
    # JSON can carry private notes, user IDs or email bodies into the bundle.
    out = {}
    for role, names in fields.items():
        if not isinstance(role,str) or role not in PUBLIC_FIELDS:
            continue
        if role.lower() in {'email','note','user_id','token','cookie','recovery_code','why_b','why_c','_notes'}:
            continue
        if isinstance(names,str):
            out[role] = names[:10000]
        elif isinstance(names,list):
            # Original split_names/parse_credits consume one textual credit
            # field. Preserve source order while rejecting non-string members.
            out[role] = '、'.join([name[:300] for name in names if isinstance(name,str)][:100])[:10000]
    return out


# Tour entries have their own schema; applying the card whitelist recursively
# used to discard theater/date/price and prevent the original region filter.
TOUR_FIELDS = {'stage_id','theater','venue','pref','period','date','end_date','days','price','url','onsale','home_stage_id'}
ROW_FIELDS = {'stage_id','title','date','period','venue','pref','group','synopsis','url','words','end_date','themes','total','b','c','bn','cn','s','both','strong','n_match','why_b','why_c','matched','tour','tour_n','status','id','theater','days','price','onsale','home_stage_id'}

def clean_scalar(value):
    if value is None or isinstance(value,(str,int,float,bool)):
        return value[:20000] if isinstance(value,str) else value
    return None

def clean_sequence(value):
    # Original reason tuples contain only public numeric contribution, role,
    # name, count; never retain arbitrary nested dictionaries/private keys.
    if isinstance(value,list):
        return [clean_sequence(item) for item in value[:1000] if not isinstance(item,dict)]
    return clean_scalar(value)

def clean_tour(value):
    if not isinstance(value,dict):
        return {}
    return {key:clean_scalar(item) for key,item in value.items() if key in TOUR_FIELDS and not isinstance(item,(dict,list))}

def clean_card(value):
    if not isinstance(value,dict):
        return {}
    out={key:clean_sequence(item) for key,item in value.items() if key in ROW_FIELDS and not isinstance(item,dict)}
    if isinstance(value.get('fields'),dict):
        out['fields']=clean_fields(value['fields'])
    if isinstance(value.get('tours'),list):
        out['tours']=[clean_tour(item) for item in value['tours'][:1000] if isinstance(item,dict)]
    return out


def build(catalogue, output, poster_dir=None, assets_dir=None, approved_base=None):
    candidates = []
    seen = set()
    for line in Path(catalogue).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        sid,title,date,venue,url,metadata = public_candidate(raw)
        if sid in seen:
            raise ValueError('Duplicate public stage identifier')
        seen.add(sid)
        meta=json.loads(metadata)
        fields=clean_fields(meta.get('fields',{}))
        row={'stage_id':sid,'title':title,'date':date,'venue':venue,'url':url,'fields':fields,'group':str(meta.get('group',''))[:1000],'synopsis':str(meta.get('synopsis',''))[:20000],'words':[word[:300] for word in meta.get('words',[]) if isinstance(word,str)][:200]}
        row['end_date']=meta['end_date']
        row['period']=f"{date.replace('-','/')}～{row['end_date'].replace('-','/')}"
        if isinstance(raw.get('pref'),str):
            row['pref']=raw['pref'][:20]
        for key in ('theater','days','price','onsale','home_stage_id'):
            if key in raw and not isinstance(raw[key],(dict,list)):
                row[key]=clean_scalar(raw[key])
        if isinstance(raw.get('tours'),list):
            row['tours']=[clean_tour(item) for item in raw['tours'][:1000] if isinstance(item,dict)]
        candidates.append(row)
    files={
        'data/review/candidates.jsonl':'\n'.join(json.dumps(row,ensure_ascii=False) for row in candidates)+'\n',
        'data/credits/credits.jsonl':'\n'.join(json.dumps({'stage_id':r['stage_id'],'title':r['title'],'fields':r['fields']},ensure_ascii=False) for r in candidates)+'\n',
        'data/credits/themes.jsonl':'\n'.join(json.dumps({'id':r['stage_id'],'side':'candidate','words':r['words'],'synopsis':r['synopsis']},ensure_ascii=False) for r in candidates)+'\n',
    }
    # Preserve only an explicitly approved, already public recommendation base.
    # Quotes/private metadata, favourite declarations and mail details are dropped.
    # Its original owner-based ranking remains shared, not per-user recalculation.
    if approved_base:
        raw=json.loads(Path(approved_base).read_text(encoding='utf-8'))
        base={key:[clean_card(item) for item in raw.get(key,[]) if isinstance(item,dict)] for key in ('ranked','favourites','tracking','owned','others','started','recommend')}
        for key in ('n_cand','n_scored'):
            if not isinstance(raw.get(key),int):
                raise ValueError('Approved base lacks original catalogue counts')
            base[key]=raw[key]
        files['data/review/recommend2.json']=json.dumps(base,ensure_ascii=False)
    # No ranking is invented if this approved source is absent.
    poster_names=[]
    if poster_dir:
        if not assets_dir:
            raise ValueError('--assets-dir required for posters')
        target=Path(assets_dir)/'img'
        target.mkdir(parents=True,exist_ok=True)
        for file in sorted(Path(poster_dir).iterdir()):
            if not file.is_file() or file.is_symlink() or not re.fullmatch(r'[A-Za-z0-9_-]+\.(png|jpg|jpeg|webp)',file.name,re.I) or file.stem not in seen:
                continue
            if file.stat().st_size>10*1024*1024:
                raise ValueError('Poster exceeds public asset budget')
            data=file.read_bytes()
            if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or data[:4]==b'RIFF' and data[8:12]==b'WEBP'):
                raise ValueError('Unexpected image format')
            shutil.copyfile(file,target/file.name)
            poster_names.append(file.name)
    manifest={name:hashlib.sha256(body.encode()).hexdigest() for name,body in files.items()}
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('PUBLIC_FILES = '+repr(files)+'\nPOSTER_NAMES = '+repr(tuple(poster_names))+'\nMANIFEST = '+repr(manifest)+'\n',encoding='utf-8')
    return len(candidates)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--poster-dir',type=Path)
    parser.add_argument('--approved-base-recommendation',type=Path,help='Explicitly approved already-public shared ranking; never a private owner backup')
    parser.add_argument('--assets-dir',type=Path)
    args=parser.parse_args()
    try:
        count=build(args.catalogue,args.output,args.poster_dir,args.assets_dir,args.approved_base_recommendation)
    except (OSError,ValueError,KeyError,TypeError):
        parser.exit(1,'Public snapshot build failed. No private database was imported.\n')
    print(f'Built {count} public candidates; original base ranking must be separately provisioned.')
