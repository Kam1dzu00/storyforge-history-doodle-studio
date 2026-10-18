from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from history_doodle.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("/Users/mihailfedrunov/Documents/Codex/reelmimic-benchmark-isolated/videos/tromelin-hybrid-proofs")
ASSETS = TARGET / "assets"
COMPOSITIONS = TARGET / "compositions"

SPECIAL = {
    "opening": {
        1: '<div class="ocean-pattern"></div><svg class="map" viewBox="0 0 1200 650"><path d="M140 90 C240 130 250 310 190 520 L360 600 L480 520 L400 360 L490 160 Z"/><circle cx="820" cy="320" r="15" class="island-dot"/><path class="route" d="M380 360 C560 420 650 380 820 320"/><g class="boat" transform="translate(380 350)"><path d="M-35 8 L34 8 L20 25 L-22 25 Z"/><path d="M0 8 L0 -42 L28 1 Z"/></g></svg><div class="label madagascar">MADAGASCAR</div><div class="label tromelin">TROMELIN</div>',
        5: '<div class="weather"><div class="sun"></div><div class="moon"></div><div class="rain"></div><div class="year y1">1761</div><div class="year y2">1776</div></div>',
        6: '<div class="native-island"><div class="island"></div><div class="wave w1"></div><div class="wave w2"></div><div class="wave w3"></div></div>',
    },
    "water_bowl": {
        2: '<svg class="well" viewBox="0 0 1200 650"><path d="M0 250 Q360 170 610 250 T1200 250 L1200 650 L0 650Z" class="sand-layer"/><path d="M0 500 Q420 450 1200 510 L1200 650 L0 650Z" class="water-layer"/><path d="M500 250 L440 500 L760 500 L700 250" class="shaft"/><g class="bucket"><path d="M558 420 L640 420 L625 480 L573 480Z"/><path d="M599 420 L599 160"/></g></svg>',
        7: '<div class="bowl"><div class="patch p1"></div><div class="patch p2"></div><div class="patch p3"></div><div class="patch p4"></div><div class="patch p5"></div><div class="patch p6"></div><div class="patch p7"></div></div>',
        8: '<div class="bowl final-bowl"><div class="patch p1"></div><div class="patch p2"></div><div class="patch p3"></div><div class="patch p4"></div><div class="patch p5"></div><div class="patch p6"></div><div class="patch p7"></div></div>',
    },
    "final_rescue": {
        5: '<svg class="rescue-map" viewBox="0 0 1200 650"><ellipse cx="620" cy="330" rx="210" ry="72" class="island-shape"/><path class="attempt a1" d="M120 170 Q350 280 480 315"/><path class="attempt a2" d="M1060 500 Q850 440 760 370"/><path class="attempt a3" d="M110 520 Q380 430 520 370"/><g class="tiny-boat tb1"><path d="M-25 0h50l-12 16h-28z"/></g><g class="tiny-boat tb2"><path d="M-25 0h50l-12 16h-28z"/></g><g class="tiny-boat tb3"><path d="M-25 0h50l-12 16h-28z"/></g></svg><div class="date d1">1775</div><div class="date d2">JUL 1776</div><div class="date d3">29 NOV 1776</div>',
        6: '<div class="watcher"><div class="head"></div><div class="body"></div></div><div class="sail"><div class="mast"></div><div class="canvas"></div></div>',
    },
}

NAMES = {
    "tromelin-proof-opening": "opening",
    "tromelin-proof-water-bowl": "water_bowl",
    "tromelin-proof-final-rescue": "final_rescue",
}

OVERLAY_TARGETS = {
    "opening_m02_weather": SPECIAL["opening"][5],
    "water_m03_well": SPECIAL["water_bowl"][2],
    "rescue_m09_routes": SPECIAL["final_rescue"][5],
}

CSS = r"""
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#232b2e;font-family:Arial,Helvetica,sans-serif}#root{position:relative;width:1920px;height:1080px;background:#232b2e;overflow:hidden}#root:after{content:"";position:absolute;inset:0;pointer-events:none;z-index:50;opacity:.12;background-image:repeating-linear-gradient(0deg,transparent 0 5px,rgba(237,227,202,.24) 6px)}
.scene{position:absolute;inset:0;overflow:hidden;background:#42677a}.plate{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(.82) contrast(.96)}.wash{position:absolute;inset:0;background:linear-gradient(90deg,rgba(35,43,46,.18),transparent 42%,rgba(35,43,46,.12));mix-blend-mode:multiply}.vector{position:absolute;inset:0}.chapter{position:absolute;left:74px;top:62px;z-index:20;color:#ede3ca;font-size:20px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;text-shadow:0 2px 12px #232b2e}.caption{position:absolute;left:90px;right:90px;bottom:58px;z-index:30;display:flex;justify-content:center}.caption span{max-width:1440px;padding:14px 24px;background:rgba(35,43,46,.78);border-left:6px solid #d36f3d;color:#ede3ca;font-family:Georgia,serif;font-size:36px;line-height:1.18;text-align:center;text-shadow:0 2px 8px #232b2e}.question .caption span{font-family:Arial,sans-serif;font-weight:800;font-size:50px;letter-spacing:.025em;border-left:0;background:rgba(35,43,46,.7);padding:24px 38px}.question .plate{filter:saturate(.55) brightness(.72)}
.native{background:radial-gradient(ellipse at 55% 42%,#6d9ba3 0,#42677a 44%,#2f4d5b 100%)}.native .plate,.native .wash{display:none}.native .vector:has(.bowl){background:radial-gradient(ellipse at 20% 18%,rgba(255,255,255,.48),transparent 24%),radial-gradient(ellipse at 82% 34%,rgba(109,155,163,.25),transparent 31%),linear-gradient(180deg,#dce4df 0,#c7d5d1 45%,#dcc89b 46%,#b99b6b 100%)}.native .vector:has(.bowl):before{content:"";position:absolute;left:170px;bottom:150px;width:340px;height:220px;border:20px double rgba(128,98,70,.8);border-radius:50%;transform:rotate(-13deg);filter:drop-shadow(0 5px 2px rgba(35,43,46,.24))}.native .vector:has(.bowl):after{content:"";position:absolute;right:130px;bottom:170px;width:430px;height:55px;background:#806246;box-shadow:80px 75px 0 #9b7956;transform:rotate(-12deg);border:6px solid #232b2e;opacity:.86}
.map{position:absolute;left:190px;top:120px;width:1480px;height:720px}.map>path:first-child{fill:#d7be8a;stroke:#232b2e;stroke-width:9}.island-dot{fill:#d36f3d;stroke:#ede3ca;stroke-width:8}.route{fill:none;stroke:#ede3ca;stroke-width:8;stroke-dasharray:18 12}.boat path{fill:#806246;stroke:#232b2e;stroke-width:5}.label,.date{position:absolute;color:#ede3ca;font-size:24px;font-weight:800;letter-spacing:.14em;text-shadow:0 2px 10px #232b2e}.madagascar{left:430px;top:650px;color:#232b2e;text-shadow:0 1px 3px rgba(237,227,202,.95)}.tromelin{left:1260px;top:430px}.ocean-pattern{position:absolute;inset:0;background:repeating-radial-gradient(ellipse at 60% 50%,rgba(109,155,163,.15) 0 3px,transparent 4px 34px)}
.weather{position:absolute;inset:0}.sun,.moon{position:absolute;right:280px;top:130px;width:120px;height:120px;border-radius:50%}.sun{background:#d36f3d;box-shadow:0 0 70px rgba(211,111,61,.55)}.moon{background:#ede3ca;box-shadow:0 0 70px rgba(237,227,202,.4)}.rain{position:absolute;inset:0;background:repeating-linear-gradient(105deg,transparent 0 38px,rgba(109,155,163,.55) 40px 44px,transparent 46px 78px)}.year{position:absolute;bottom:185px;font-size:48px;font-weight:800;color:#ede3ca;text-shadow:0 2px 14px #232b2e}.y1{left:260px}.y2{right:260px}
.native-island{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 65%,rgba(109,155,163,.8),transparent 58%),linear-gradient(180deg,#dce4df 0,#b9d0d1 36%,#42677a 37%,#31596c 100%)}.native-island:before{content:"";position:absolute;left:720px;top:365px;width:410px;height:165px;background:repeating-linear-gradient(78deg,transparent 0 35px,#594a3d 37px 48px,transparent 50px 78px);clip-path:polygon(0 55%,100% 20%,100% 58%,0 90%);opacity:.86;filter:drop-shadow(0 6px 2px rgba(35,43,46,.28))}.native-island .island{position:absolute;left:560px;top:380px;width:800px;height:190px;border-radius:50%;clip-path:polygon(3% 54%,12% 28%,27% 20%,43% 8%,58% 17%,74% 7%,91% 30%,100% 63%,90% 78%,66% 86%,42% 78%,19% 91%,5% 73%);background:linear-gradient(180deg,#e4cf9f,#c2a36d);box-shadow:inset 0 -28px 0 rgba(128,98,70,.28);filter:drop-shadow(0 10px 6px rgba(35,43,46,.28))}.wave{position:absolute;left:-300px;width:2500px;height:90px;border-top:6px solid rgba(237,227,202,.72);border-radius:50%;filter:drop-shadow(0 3px 0 rgba(35,43,46,.12))}.w1{top:290px}.w2{top:600px}.w3{top:760px}
.well{position:absolute;inset:80px 180px;width:1560px;height:820px}.sand-layer{fill:#d7be8a;stroke:#806246;stroke-width:8}.water-layer{fill:#6d9ba3;opacity:.9}.shaft{fill:#232b2e;stroke:#ede3ca;stroke-width:7}.bucket path{fill:#806246;stroke:#ede3ca;stroke-width:7}
.bowl{position:absolute;left:640px;top:260px;width:640px;height:410px;border-radius:40px 40px 260px 260px;background:linear-gradient(100deg,#596369,#aeb2ad 48%,#434b50);border:12px solid #232b2e;box-shadow:0 36px 70px rgba(35,43,46,.35),inset 0 18px 0 rgba(237,227,202,.25)}.bowl:before{content:"";position:absolute;left:-30px;right:-30px;top:-30px;height:64px;border-radius:50%;background:#737d80;border:10px solid #232b2e}.patch{position:absolute;width:92px;height:70px;background:#806246;border:5px solid #232b2e;clip-path:polygon(10% 18%,78% 0,100% 64%,70% 100%,0 76%)}.p1{left:70px;top:80px}.p2{left:220px;top:55px}.p3{left:410px;top:90px}.p4{left:120px;top:220px}.p5{left:290px;top:190px}.p6{left:450px;top:245px}.p7{left:250px;top:305px}.final-bowl{transform:scale(.9);top:290px}
.rescue-map{position:absolute;left:210px;top:120px;width:1500px;height:760px}.island-shape{fill:#d7be8a;stroke:#ede3ca;stroke-width:8}.attempt{fill:none;stroke:#d36f3d;stroke-width:8;stroke-dasharray:22 14}.tiny-boat path{fill:#806246;stroke:#232b2e;stroke-width:5}.date{font-size:34px}.d1{left:210px;top:215px}.d2{right:230px;bottom:215px}.d3{left:240px;bottom:220px}.watcher{position:absolute;left:390px;bottom:185px;width:210px;height:470px}.watcher .head{position:absolute;left:55px;top:0;width:100px;height:110px;border-radius:50%;background:#232b2e}.watcher .body{position:absolute;left:0;top:90px;width:210px;height:380px;border-radius:100px 100px 30px 30px;background:#232b2e;clip-path:polygon(28% 0,72% 0,100% 100%,0 100%)}.sail{position:absolute;right:430px;top:390px;width:110px;height:150px}.mast{position:absolute;left:52px;top:0;width:7px;height:145px;background:#232b2e}.canvas{position:absolute;left:57px;top:8px;width:70px;height:95px;background:#ede3ca;clip-path:polygon(0 0,100% 88%,0 100%);filter:drop-shadow(0 4px 8px rgba(35,43,46,.4))}
"""

JS = r"""
const root=document.querySelector('#root');
const tl=gsap.timeline({paused:true});
document.querySelectorAll('.scene').forEach((scene,i)=>{const t=i*7.5;tl.fromTo(scene,{opacity:0},{opacity:1,duration:.45,ease:'power2.out'},t);tl.to(scene,{opacity:0,duration:.4,ease:'power2.in'},t+7.1);tl.fromTo(scene.querySelector('.caption'),{y:35,opacity:0},{y:0,opacity:1,duration:.6,ease:'power3.out'},t+.25)});
document.querySelectorAll('.route,.attempt').forEach((el,i)=>{const len=el.getTotalLength();gsap.set(el,{strokeDasharray:len,strokeDashoffset:len});tl.to(el,{strokeDashoffset:0,duration:4.8,ease:'power2.inOut'},(+el.closest('.scene').dataset.start)+.8+i*.15)});
document.querySelectorAll('.boat').forEach(el=>tl.to(el,{x:440,y:-30,duration:5,ease:'power1.inOut'},.8));
document.querySelectorAll('.weather').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el.querySelector('.sun'),{x:-700,opacity:1},{x:0,opacity:0,duration:5.8,ease:'none'},t+.4);tl.fromTo(el.querySelector('.moon'),{x:-700,opacity:0},{x:0,opacity:1,duration:5.8,ease:'none'},t+.4);tl.fromTo(el.querySelector('.rain'),{x:-100,opacity:0},{x:100,opacity:.75,duration:2.4,repeat:1,yoyo:true},t+2)});
document.querySelectorAll('.wave').forEach((el,i)=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{x:-220-i*80},{x:160+i*100,duration:3.4,repeat:1,yoyo:true,ease:'sine.inOut'},t)});
document.querySelectorAll('.bucket').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{y:-260},{y:70,duration:2.6,ease:'power2.in'},t+.5);tl.to(el,{y:-90,duration:2.8,ease:'power2.out'},t+3.4)});
document.querySelectorAll('.bowl').forEach(el=>{const t=+el.closest('.scene').dataset.start;el.querySelectorAll('.patch').forEach((p,i)=>tl.fromTo(p,{scale:0,rotation:-25,opacity:0},{scale:1,rotation:0,opacity:1,duration:.48,ease:'back.out(1.8)'},t+.55+i*.72))});
document.querySelectorAll('.tiny-boat').forEach((el,i)=>{const t=+el.closest('.scene').dataset.start;gsap.set(el,{x:i===1?1060:120,y:i===0?170:500,opacity:0});tl.to(el,{opacity:1,duration:.3},t+.8+i*1.4);tl.to(el,{x:590,y:330,duration:2.1,ease:'power1.inOut'},t+1+i*1.4)});
document.querySelectorAll('.watcher').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{rotation:-2},{rotation:3,duration:3.1,repeat:1,yoyo:true,ease:'sine.inOut'},t+.2)});document.querySelectorAll('.sail').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{scale:.08,opacity:0},{scale:1,opacity:1,duration:5.8,ease:'power2.out'},t+.7)});
window.__timelines['main']=tl;tl.seek(0);
"""

OVERLAY_JS = r"""
const tl=gsap.timeline({paused:true});
document.querySelectorAll('.route,.attempt').forEach((el,i)=>{const len=el.getTotalLength();gsap.set(el,{strokeDasharray:len,strokeDashoffset:len});tl.to(el,{strokeDashoffset:0,duration:4.8,ease:'power2.inOut'},.5+i*.15)});
document.querySelectorAll('.weather').forEach(el=>{tl.fromTo(el.querySelector('.sun'),{x:-700,opacity:1},{x:0,opacity:0,duration:5.8,ease:'none'},.3);tl.fromTo(el.querySelector('.moon'),{x:-700,opacity:0},{x:0,opacity:1,duration:5.8,ease:'none'},.3);tl.fromTo(el.querySelector('.rain'),{x:-100,opacity:0},{x:100,opacity:.75,duration:2.4,repeat:1,yoyo:true},1.8)});
document.querySelectorAll('.bucket').forEach(el=>{tl.fromTo(el,{y:-260},{y:70,duration:2.6,ease:'power2.in'},.5);tl.to(el,{y:-90,duration:2.8,ease:'power2.out'},3.4)});
document.querySelectorAll('.tiny-boat').forEach((el,i)=>{gsap.set(el,{x:i===1?1060:120,y:i===0?170:500,opacity:0});tl.to(el,{opacity:1,duration:.3},.6+i*1.4);tl.to(el,{x:590,y:330,duration:2.1,ease:'power1.inOut'},.8+i*1.4)});
window.__timelines['main']=tl;tl.seek(0);
"""


def build(project_name: str, proof: str) -> None:
    project = ROOT / "projects" / project_name
    plan = ProjectStore().load_plan(project)
    ASSETS.mkdir(parents=True, exist_ok=True); COMPOSITIONS.mkdir(parents=True, exist_ok=True)
    for shot in plan.shots:
        shutil.copy2(project / shot.image_path, ASSETS / f"{proof}_{shot.id}.png")
    shutil.copy2(project / "audio/narration.wav", ASSETS / f"{proof}_narration.wav")
    sections=[]
    for index, shot in enumerate(sorted(plan.shots,key=lambda x:x.order),1):
        special=SPECIAL.get(proof,{}).get(index,"")
        classes = ["scene", "clip"]
        if shot.question_beat:
            classes.append("question")
        engine_route = getattr(shot.engine_route, "value", shot.engine_route)
        if engine_route == "mimic_native_scene":
            classes.append("native")
        cls = " ".join(classes)
        caption=html.escape(shot.narration_context.replace("“","").replace("”",""))
        sections.append(f'<section id="{proof}-scene-{index:02d}" class="{cls}" data-start="{(index-1)*7.5}" data-duration="7.5" data-track-index="0"><img class="plate" src="assets/{proof}_{shot.id}.png"><div class="wash"></div><div class="vector">{special}</div><div class="caption"><span>{caption}</span></div></section>')
    document=f'''<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{CSS}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="60" data-width="1920" data-height="1080"><audio id="{proof}-narration" src="assets/{proof}_narration.wav" data-start="0" data-duration="60" data-track-index="30" data-volume="1"></audio><audio id="{proof}-music" src="assets/proof_music.wav" data-start="0" data-duration="60" data-track-index="31" data-volume="0.11"></audio>{''.join(sections)}</div><script>{JS}</script></body></html>'''
    (COMPOSITIONS / f"{proof}.html").write_text(document,encoding="utf-8")


def build_overlays() -> None:
    transparent_css = CSS + """
html,body,#root,.scene,.vector{background:transparent!important}
#root:after{opacity:.055}
.scene{opacity:1!important}
"""
    for name, markup in OVERLAY_TARGETS.items():
        document = f'''<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{transparent_css}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="7.5" data-width="1920" data-height="1080"><section id="{name}" class="scene clip" data-start="0" data-duration="7.5" data-track-index="0"><div class="vector">{markup}</div></section></div><script>{OVERLAY_JS}</script></body></html>'''
        (COMPOSITIONS / f"overlay_{name}.html").write_text(document, encoding="utf-8")


if __name__ == "__main__":
    for project_name, proof in NAMES.items():
        build(project_name, proof)
    build_overlays()
    print(TARGET)
