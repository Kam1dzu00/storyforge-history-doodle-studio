from __future__ import annotations

import argparse
from pathlib import Path
from .pipeline import Pipeline
from .storage import ProjectStore

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    create=sub.add_parser("create"); create.add_argument("title"); create.add_argument("input_file",type=Path); create.add_argument("--mode",choices=["brief","script"],default="brief"); create.add_argument("--minutes",type=int,default=10); create.add_argument("--voice",default="am_michael")
    run=sub.add_parser("run"); run.add_argument("project",type=Path); run.add_argument("--stage",choices=["create_script","plan_video","generate_voice","generate_images","build_subtitles","render_video","full"],default="full")
    a=p.parse_args()
    if a.cmd=="create":
        path=ProjectStore().create(a.title,a.mode,a.minutes*60,a.voice,a.input_file.read_text(encoding="utf-8")); print(path)
    else: getattr(Pipeline(a.project,print),a.stage)()

if __name__=="__main__":main()

