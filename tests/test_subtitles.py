from history_doodle.schemas import WordStamp
from history_doodle.subtitles import build

def test_subtitle_files(tmp_path):
    words=[WordStamp(word="Vikings",start=0,end=.4),WordStamp(word="worked.",start=.4,end=.9)]
    srt,ass=build(words,tmp_path); assert "Vikings worked." in srt.read_text(); assert "\\kf" in ass.read_text(); assert "Avenir Next" in ass.read_text()

