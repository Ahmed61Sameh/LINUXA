import os
import tempfile
from types import SimpleNamespace as NS
import stt
import stt_config as cfg
cfg.CONFIDENCE_THRESHOLD=0.4
def seg(text,logprob=-0.1,nsp=.01):
    return NS(text=text,avg_logprob=logprob,no_speech_prob=nsp)

class FakeModel:
    def __init__ (self,segments,language="ar"):
        self.segments=segments
        self.language=language
    def transcribe(self,path,**kwargs):
        info=NS(language=self.language,language_probability=0.99,duration=2.0)
        return iter(self.segments),info

class BrokenModel:
    def transcribe(self,path,**kwargs):
        raise RuntimeError("deliberate failure")    

tmp=tempfile.NamedTemporaryFile(suffix=".mp4",delete=False) 
tmp.close()
FILE=tmp.name

def test_file_not_found():
    r=stt.speech_to_text("no_such_file.wav")
    assert r["ok"] is False
    assert r["error"]=="FILE_NOT_FOUND"
def test_no_speech():
    stt._model=FakeModel([])
    r=stt.speech_to_text(FILE) 
    
    assert r["ok"]is False 
    assert r["error"]=="NO_SPEECH"
def test_low_confidence_keeps_text(): 
    stt._model=FakeModel([seg("open the browser",logprob=-2.0)])   
      
    r=stt.speech_to_text(FILE)
   
    assert r["error"]=="LOW_CONFIDENCE"
    assert r["ok"]is False
    assert r["text"]=="open the browser"
def test_never_raises():
    stt._model=BrokenModel()
    r=stt.speech_to_text(FILE) 
    assert r["error"]=="INTERNAL_ERROR"
def test_success():
    stt._model=FakeModel([seg("افتح المتصفح")])  
    r=stt.speech_to_text(FILE)
    
    assert r["ok"] is True
    assert r["text"]=="افتح المتصفح"
    assert r["error"]is None
if __name__ =="__main__":
    for name,fn in list(globals().items()):
        if name.startswith("test_")and callable(fn):
            fn()
            print("ok",name)
    os.remove(FILE)   
    print("All tests passed")
    