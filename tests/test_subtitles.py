from history_doodle.schemas import WordStamp
from history_doodle.subtitles import build, chunks

def test_subtitle_files(tmp_path):
    words=[WordStamp(word="Vikings",start=0,end=.4),WordStamp(word="worked.",start=.4,end=.9)]
    srt,ass=build(words,tmp_path); assert "Vikings worked." in srt.read_text(); assert "\\kf" in ass.read_text(); assert "Avenir Next" in ass.read_text()

def test_subtitle_safe_chunking():
    words=[WordStamp(word=x,start=i*.2,end=i*.2+.18) for i,x in enumerate("extraordinarily lengthy historical narration remains readable".split())]
    groups=chunks(words)
    assert all(len(g)<=5 and len(" ".join(x.word for x in g))<=34 for g in groups)
