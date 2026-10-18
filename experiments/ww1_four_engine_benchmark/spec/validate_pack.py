#!/usr/bin/env python3
import json
from pathlib import Path
p=Path(__file__).resolve().parent
story=json.loads((p/'MASTER_STORYBOARD.json').read_text())
assert story['fps']==30 and story['frame_count']==1800 and story['duration_seconds']==60
assert len(story['scenes'])==8
assert all(story['scenes'][i]['end']==story['scenes'][i+1]['start'] for i in range(7))
assert story['scenes'][0]['start']==0 and story['scenes'][-1]['end']==60
with (p/'FRAME_BY_FRAME_1800.jsonl').open() as f:
    for i,line in enumerate(f):
        item=json.loads(line)
        assert item['frame']==i
        assert item['scene']==next(s['id'] for s in story['scenes'] if s['start']<=i/30<s['end'])
    assert i==1799
print('PASS: 8 continuous scenes, 1,800 sequential frame cues at 30fps / 60s')
