"""Render original fragments with a temporary, synthetic account for UI checks."""
import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'/'taguri'),str(ROOT/'tools'/'review')]
import rate_performances as R
import feedback as FB
directory=tempfile.TemporaryDirectory()
R.DB=Path(directory.name)/'records.db'
FB.DB=R.DB
import app as APP
APP.DB=R.DB
APP.RR.load=lambda: ({'ranked':[],'favourites':[],'tracking':[],'owned':[],'others':[],'started':[]},[])
user_id='f'*32
APP.seed_demo_works(user_id)
screens={'rate':APP._rate_body,'unrated':APP._unrated_body,'register':APP._register_body,'notes':APP._notes_body,'works':APP._works_body,'settings':APP._settings_body}
out={}
for name,render in screens.items():
    out[name]={'ok':True,'title':name,'body_html':render(user_id),'demo_mode':True}
Path(sys.argv[1]).write_text(json.dumps(out,ensure_ascii=False),encoding='utf8')
