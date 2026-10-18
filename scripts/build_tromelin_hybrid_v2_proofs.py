from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "projects/storyforge-hybrid-tromelin-production-v2"
MIMIC = Path("/Users/mihailfedrunov/Documents/Codex/reelmimic-benchmark-isolated/videos/tromelin-hybrid-v2")
ASSETS = MIMIC / "assets" / "v2"
COMPOSITIONS = MIMIC / "compositions"


V1_ASSETS = Path("/Users/mihailfedrunov/Documents/Codex/reelmimic-benchmark-isolated/videos/tromelin-hybrid-proofs/assets")


def opening(number: int) -> Path:
    return V1_ASSETS / f"opening_shot_{number:03d}.png"


def water(number: int) -> Path:
    return V1_ASSETS / f"water_bowl_shot_{number:03d}.png"


def rescue(number: int) -> Path:
    return V1_ASSETS / f"final_rescue_shot_{number:03d}.png"


PROOFS = {
    "shipwreck_abandonment": [
        (rescue(1), ["ocean", "ship", "sail_rope"], "ship rocks on moving reef water; sail and rigging breathe"),
        (opening(2), ["ocean", "debris", "cloth"], "water moves behind drifting wreck debris and cloth"),
        (opening(3), ["ocean", "boat", "rope"], "escape boat rocks while its rope loosens"),
        (rescue(3), ["ocean", "escape_boat", "passengers"], "loaded escape boat pulls away across animated surf"),
        (opening(4), ["ocean", "survivors", "distant_boat"], "survivors remain as the distant boat recedes"),
        (opening(5), ["ocean", "grass", "foreground_debris"], "empty shore holds while sea and grass continue moving"),
    ],
    "water_repaired_bowl": [
        (water(1), ["ocean", "cup", "ground_shadow"], "dry vessel settles against moving sea and cracked ground"),
        (water(2), ["water", "bucket", "pole"], "illustrated bucket descends, touches water, then rises"),
        (water(3), ["cloth", "drips", "vessels"], "rain cloth flexes and droplets collect in vessels"),
        (water(6), ["hand", "tool", "metal_parts"], "illustrated hand and tool perform two restrained repair motions"),
        (water(8), ["bowl", "patch_1", "patch_2", "patch_3"], "first three StoryForge patch cutouts are hammer-set"),
        (water(8), ["bowl", "patch_4", "patch_5", "patch_6", "patch_7"], "four remaining StoryForge patch cutouts complete the vessel"),
    ],
    "final_rescue": [
        (rescue(5), ["ocean", "boats", "island"], "failed rescue boats drift around the island"),
        (opening(5), ["ocean", "grass", "horizon"], "empty horizon breathes before the sighting"),
        (rescue(6), ["ocean", "survivor", "head", "tiny_sail"], "one survivor turns toward a tiny real illustrated sail"),
        (rescue(4), ["ocean", "group_left", "group_right", "fire"], "other survivors gradually lean and react"),
        (rescue(7), ["ocean", "rescue_ship", "shore_survivors"], "the ship is closer in a new cut; people react on shore"),
        (rescue(8), ["cloth_left", "cloth_mid", "cloth_right", "island"], "emotional hold on recovered cloth and the island beyond"),
    ],
}


BASE_CSS = r"""
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#d8d4c7}#root{position:relative;width:1920px;height:1080px;overflow:hidden;background:#d8d4c7}
#root:after{content:"";position:absolute;inset:0;z-index:100;pointer-events:none;opacity:.08;background-image:repeating-linear-gradient(0deg,transparent 0 4px,rgba(35,43,46,.22) 5px)}
.scene{position:absolute;inset:0;overflow:hidden;background:#d8d4c7}.layer{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform-origin:50% 50%;will-change:transform,opacity}.base{z-index:1}.ocean,.water{z-index:3}.subject,.ship,.boat,.escape_boat,.survivor,.survivors,.group_left,.group_right,.rescue_ship{z-index:7}.detail,.sail_rope,.rope,.cloth,.tiny_sail,.fire,.head,.tool,.hand,.debris,.passengers,.shore_survivors{z-index:9}.foreground_debris,.grass,.vessels,.metal_parts,.island{z-index:11}
.shade{position:absolute;inset:0;z-index:30;pointer-events:none;background:linear-gradient(90deg,rgba(35,43,46,.08),transparent 30%,transparent 75%,rgba(35,43,46,.05));mix-blend-mode:multiply}
"""


MASK_CSS = r"""
/* A: shipwreck / abandonment */
#shipwreck_abandonment-01 .ocean{clip-path:polygon(0 35%,100% 35%,100% 100%,0 100%)}
#shipwreck_abandonment-01 .ship{clip-path:polygon(0 5%,48% 0,52% 87%,0 100%);transform-origin:30% 68%}
#shipwreck_abandonment-01 .sail_rope{clip-path:polygon(7% 0,37% 0,45% 67%,8% 67%);transform-origin:29% 62%}
#shipwreck_abandonment-02 .ocean{clip-path:polygon(0 0,100% 0,100% 47%,0 47%)}
#shipwreck_abandonment-02 .debris{clip-path:polygon(0 5%,70% 12%,70% 68%,0 68%);transform-origin:30% 48%}
#shipwreck_abandonment-02 .cloth{clip-path:polygon(56% 47%,100% 43%,100% 100%,52% 100%);transform-origin:78% 73%}
#shipwreck_abandonment-03 .ocean{clip-path:polygon(0 0,100% 0,100% 56%,0 56%)}
#shipwreck_abandonment-03 .boat{clip-path:polygon(22% 23%,82% 20%,83% 67%,18% 69%);transform-origin:51% 56%}
#shipwreck_abandonment-03 .rope{clip-path:polygon(48% 34%,100% 34%,100% 77%,45% 76%);transform-origin:50% 40%}
#shipwreck_abandonment-04 .ocean{clip-path:polygon(0 24%,100% 24%,100% 100%,0 100%)}
#shipwreck_abandonment-04 .escape_boat{clip-path:polygon(20% 23%,95% 10%,100% 87%,18% 92%);transform-origin:58% 68%}
#shipwreck_abandonment-04 .passengers{clip-path:polygon(29% 25%,88% 15%,90% 71%,26% 74%)}
#shipwreck_abandonment-05 .ocean{clip-path:polygon(0 28%,100% 28%,100% 100%,0 100%)}
#shipwreck_abandonment-05 .survivors{clip-path:polygon(0 18%,80% 14%,78% 100%,0 100%);transform-origin:45% 92%}
#shipwreck_abandonment-05 .distant_boat{clip-path:polygon(72% 17%,100% 12%,100% 55%,69% 54%)}
#shipwreck_abandonment-06 .ocean{clip-path:polygon(0 37%,100% 37%,100% 73%,0 73%)}
#shipwreck_abandonment-06 .grass{clip-path:polygon(0 55%,100% 55%,100% 100%,0 100%);transform-origin:50% 100%}
#shipwreck_abandonment-06 .foreground_debris{clip-path:polygon(0 55%,29% 40%,35% 100%,0 100%)}

/* B: water + repaired bowl */
#water_repaired_bowl-01 .ocean{clip-path:polygon(0 0,100% 0,100% 48%,0 48%)}
#water_repaired_bowl-01 .cup{clip-path:ellipse(18% 38% at 48% 62%);transform-origin:48% 82%}
#water_repaired_bowl-01 .ground_shadow{clip-path:ellipse(25% 12% at 48% 85%)}
#water_repaired_bowl-02 .water{clip-path:ellipse(28% 19% at 54% 74%)}
#water_repaired_bowl-02 .bucket{clip-path:ellipse(14% 20% at 50% 67%);transform-origin:50% 42%}
#water_repaired_bowl-02 .pole{clip-path:polygon(58% 15%,75% 12%,65% 90%,53% 90%);transform-origin:62% 19%}
#water_repaired_bowl-03 .cloth{clip-path:polygon(0 0,76% 0,72% 70%,0 74%);transform-origin:36% 8%}
#water_repaired_bowl-03 .drips{clip-path:polygon(0 31%,73% 31%,72% 92%,0 92%)}
#water_repaired_bowl-03 .vessels{clip-path:polygon(28% 45%,76% 43%,78% 100%,24% 100%)}
#water_repaired_bowl-04 .hand{clip-path:polygon(0 0,72% 0,77% 76%,0 81%);transform-origin:33% 38%}
#water_repaired_bowl-04 .tool{clip-path:polygon(37% 27%,93% 25%,96% 90%,31% 94%);transform-origin:46% 45%}
#water_repaired_bowl-04 .metal_parts{clip-path:polygon(28% 42%,100% 35%,100% 100%,25% 100%)}
#water_repaired_bowl-05 .bowl,#water_repaired_bowl-06 .bowl{clip-path:polygon(24% 46%,76% 45%,78% 88%,22% 89%);transform-origin:50% 85%}
.patch{position:absolute;z-index:14;width:122px;height:104px;background-image:url('assets/v2/patch_source.png');background-size:1920px 1080px;clip-path:polygon(12% 20%,68% 4%,96% 48%,73% 94%,17% 83%,2% 47%);filter:drop-shadow(0 3px 1px rgba(35,43,46,.35));will-change:transform,opacity}
.patch.p1{left:690px;top:690px;background-position:-580px -450px}.patch.p2{left:875px;top:655px;background-position:-790px -430px}.patch.p3{left:1060px;top:690px;background-position:-1140px -450px}.patch.p4{left:650px;top:800px;background-position:-675px -770px}.patch.p5{left:835px;top:820px;background-position:-940px -788px}.patch.p6{left:1015px;top:800px;background-position:-1220px -730px}.patch.p7{left:1170px;top:735px;background-position:-1385px -487px}

/* C: final rescue */
#final_rescue-01 .ocean{clip-path:polygon(0 0,100% 0,100% 100%,0 100%)}
#final_rescue-01 .boats{clip-path:polygon(0 20%,100% 12%,100% 100%,0 100%)}
#final_rescue-01 .island{clip-path:ellipse(48% 47% at 50% 52%)}
#final_rescue-02 .ocean{clip-path:polygon(0 35%,100% 35%,100% 78%,0 78%)}
#final_rescue-02 .grass{clip-path:polygon(0 58%,100% 58%,100% 100%,0 100%);transform-origin:50% 100%}
#final_rescue-02 .horizon{clip-path:polygon(0 26%,100% 26%,100% 52%,0 52%)}
#final_rescue-03 .ocean{clip-path:polygon(0 32%,100% 32%,100% 80%,0 80%)}
#final_rescue-03 .survivor{clip-path:polygon(38% 29%,61% 28%,62% 100%,36% 100%);transform-origin:49% 91%}
#final_rescue-03 .head{clip-path:ellipse(10% 16% at 51% 43%);transform-origin:51% 52%}
#final_rescue-03 .tiny_sail{clip-path:polygon(55% 24%,75% 20%,76% 46%,54% 47%)}
#final_rescue-04 .ocean{clip-path:polygon(0 0,100% 0,100% 54%,0 54%)}
#final_rescue-04 .group_left{clip-path:polygon(0 8%,51% 8%,54% 100%,0 100%);transform-origin:42% 94%}
#final_rescue-04 .group_right{clip-path:polygon(58% 7%,100% 7%,100% 100%,54% 100%);transform-origin:63% 93%}
#final_rescue-04 .fire{clip-path:ellipse(12% 24% at 57% 76%);transform-origin:57% 89%}
#final_rescue-05 .ocean{clip-path:polygon(0 42%,100% 42%,100% 100%,0 100%)}
#final_rescue-05 .rescue_ship{clip-path:polygon(8% 0,86% 0,86% 87%,4% 88%);transform-origin:48% 72%}
#final_rescue-05 .shore_survivors{clip-path:polygon(65% 55%,100% 52%,100% 100%,62% 100%);transform-origin:81% 93%}
#final_rescue-06 .cloth_left{clip-path:polygon(0 52%,52% 44%,56% 100%,0 100%);transform-origin:22% 82%}
#final_rescue-06 .cloth_mid{clip-path:polygon(23% 45%,78% 42%,80% 100%,20% 100%);transform-origin:53% 79%}
#final_rescue-06 .cloth_right{clip-path:polygon(55% 49%,100% 43%,100% 100%,51% 100%);transform-origin:79% 82%}
#final_rescue-06 .island{clip-path:polygon(45% 18%,100% 14%,100% 58%,42% 58%)}
"""


JS = r"""
const tl=gsap.timeline({paused:true});
const scenes=[...document.querySelectorAll('.scene')];
scenes.forEach((scene,i)=>{const t=i*4;tl.fromTo(scene,{opacity:0},{opacity:1,duration:.32,ease:'power2.out'},t);tl.to(scene,{opacity:0,duration:.32,ease:'power2.in'},t+3.68)});

function loop(sel,vars,offset=0){document.querySelectorAll(sel).forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,vars.from,{...vars.to,duration:vars.duration||1.8,repeat:vars.repeat??1,yoyo:true,ease:vars.ease||'sine.inOut'},t+offset)})}
loop('.ocean,.water',{from:{x:-10,y:0},to:{x:10,y:3},duration:1.7,repeat:1});
loop('.ship,.boat,.rescue_ship',{from:{rotation:-.7,y:2},to:{rotation:.8,y:-3},duration:1.8,repeat:1},.15);
loop('.sail_rope,.rope,.cloth',{from:{rotation:-.9,skewX:-.4},to:{rotation:1.2,skewX:.5},duration:1.25,repeat:2},.1);
loop('.grass,.cloth_left,.cloth_mid,.cloth_right',{from:{rotation:-.45},to:{rotation:.65},duration:1.4,repeat:2},.1);
loop('.survivors,.group_left,.group_right,.shore_survivors',{from:{rotation:-.35},to:{rotation:.65},duration:1.8,repeat:1},.3);
loop('.fire',{from:{scaleY:.92,opacity:.86},to:{scaleY:1.08,opacity:1},duration:.55,repeat:5},.05);

document.querySelectorAll('.debris').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{x:-5,rotation:-.25},{x:9,rotation:.3,duration:3.5,ease:'sine.inOut'},t+.15)});
document.querySelectorAll('.escape_boat').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{x:-15,y:5,rotation:-.5},{x:38,y:-2,rotation:.65,duration:3.6,ease:'power1.inOut'},t+.05)});
document.querySelectorAll('.distant_boat').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{x:-8,opacity:1},{x:55,opacity:.58,duration:3.5,ease:'power1.in'},t+.1)});
document.querySelectorAll('.passengers').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{rotation:-.3},{rotation:.45,duration:1.4,repeat:2,yoyo:true,ease:'sine.inOut'},t+.2)});
document.querySelectorAll('.bucket').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{y:-165},{y:82,duration:1.55,ease:'power2.in'},t+.15);tl.to(el,{y:-95,duration:1.65,ease:'power2.out'},t+1.95)});
document.querySelectorAll('.pole').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{rotation:-1},{rotation:1.3,duration:1.7,repeat:1,yoyo:true,ease:'sine.inOut'},t+.2)});
document.querySelectorAll('.drips').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{y:-10,opacity:.48},{y:18,opacity:.9,duration:.85,repeat:3,ease:'none'},t+.1)});
document.querySelectorAll('.hand,.tool').forEach((el,i)=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{rotation:-1.4},{rotation:2.2,duration:.55,repeat:3,yoyo:true,ease:'power2.inOut'},t+.35+i*.12)});
document.querySelectorAll('.patch').forEach((el,i)=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{scale:1.65,rotation:-7,opacity:0,y:-30},{scale:1,rotation:0,opacity:1,y:0,duration:.42,ease:'back.out(1.35)'},t+.4+(i%4)*.7)});
document.querySelectorAll('.bowl').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{y:4},{y:-2,duration:1.7,repeat:1,yoyo:true,ease:'sine.inOut'},t+.2)});
document.querySelectorAll('.survivor').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{rotation:-1.1},{rotation:1.8,duration:2.4,ease:'power2.inOut'},t+.5)});
document.querySelectorAll('.head').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{rotation:-3},{rotation:5,duration:1.4,ease:'power2.inOut'},t+.9)});
document.querySelectorAll('.tiny_sail').forEach(el=>{const t=+el.closest('.scene').dataset.start;tl.fromTo(el,{x:16,opacity:.15},{x:-4,opacity:1,duration:2.7,ease:'power1.out'},t+.55)});
window.__timelines['main']=tl;tl.seek(0);
"""


ROLE_CLASS = {
    "ocean": "ocean", "water": "water", "ship": "ship subject", "boat": "boat subject",
    "escape_boat": "escape_boat subject", "rescue_ship": "rescue_ship subject", "survivor": "survivor subject",
    "survivors": "survivors subject", "group_left": "group_left subject", "group_right": "group_right subject",
    "sail_rope": "sail_rope detail", "rope": "rope detail", "cloth": "cloth detail", "head": "head detail",
    "tiny_sail": "tiny_sail detail", "fire": "fire detail", "tool": "tool detail", "hand": "hand detail",
    "debris": "debris detail", "passengers": "passengers detail", "shore_survivors": "shore_survivors detail",
}


def build() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    COMPOSITIONS.mkdir(parents=True, exist_ok=True)
    (MIMIC / "renders").mkdir(parents=True, exist_ok=True)
    for proof, scenes in PROOFS.items():
        sections = []
        proof_layers = OUT / "proofs" / proof / "layers"
        proof_layers.mkdir(parents=True, exist_ok=True)
        source_audio = {
            "shipwreck_abandonment": V1_ASSETS / "opening_narration.wav",
            "water_repaired_bowl": V1_ASSETS / "water_bowl_narration.wav",
            "final_rescue": V1_ASSETS / "final_rescue_narration.wav",
        }[proof]
        shutil.copy2(source_audio, ASSETS / f"{proof}_narration.wav")
        for idx, (source, roles, movement) in enumerate(scenes, 1):
            package = proof_layers / f"shot_{idx:02d}"
            package.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, package / "background.png")
            shutil.copy2(source, ASSETS / f"{proof}_{idx:02d}_background.png")
            layer_html = []
            for role in roles:
                shutil.copy2(source, package / f"{role}.png")
                shutil.copy2(source, ASSETS / f"{proof}_{idx:02d}_{role}.png")
                cls = ROLE_CLASS.get(role, role)
                layer_html.append(f'<img class="layer {cls}" src="assets/v2/{proof}_{idx:02d}_{role}.png">')
            manifest = {
                "proof": proof,
                "shot": idx,
                "source_artwork": str(source),
                "background": "background.png",
                "raster_layers": [f"{role}.png" for role in roles],
                "motion_contract": movement,
                "engine": "HyperFrames layered cutout",
                "art_owner": "StoryForge",
                "vectors": [],
            }
            (package / "motion_contract.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            sections.append(
                f'<section id="{proof}-{idx:02d}" class="scene clip" data-start="{(idx-1)*4}" data-duration="4" data-track-index="0">'
                f'<img class="layer base" src="assets/v2/{proof}_{idx:02d}_background.png">'
                f'{"".join(layer_html)}<div class="shade"></div></section>'
            )
        document = f'''<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{BASE_CSS}{MASK_CSS}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="24" data-width="1920" data-height="1080"><audio id="{proof}-narration" src="assets/v2/{proof}_narration.wav" data-start="0" data-duration="24" data-track-index="30" data-volume="1"></audio>{"".join(sections)}</div><script>{JS}</script></body></html>'''
        (COMPOSITIONS / f"{proof}.html").write_text(document, encoding="utf-8")

    shutil.copy2(water(7), ASSETS / "patch_source.png")
    (MIMIC / "hyperframes.json").write_text(json.dumps({"media": {"autoProxy": True}}, indent=2) + "\n", encoding="utf-8")
    (MIMIC / "package.json").write_text(json.dumps({"name": "tromelin-hybrid-v2", "private": True}, indent=2) + "\n", encoding="utf-8")
    print(MIMIC)


if __name__ == "__main__":
    build()
