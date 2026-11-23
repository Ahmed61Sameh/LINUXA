import os#بسال بيه هل الملف موجود
import sys#نقرا الكلام في التيرمنال
import json#نكتب بيه النتيجه في ملف
import math#عشان نسبه الثقه
import time #نحسب وقت المعالجه
from faster_whisper import WhisperModel
import stt_config as cfg#import باستخدام الياس
_model=None#بحمل النموزج مره واحتفظ بيه
def get_model():
    global _model#عايز اغير الصندوق اللي بره مش واحد جديد جوه
    if _model is None:
        _model=WhisperModel(
            cfg.MODEL_SIZE,
            device=cfg.DEVICE,
            compute_type=cfg.COMPUTE_TYPE,
            download_root=cfg.MODEL_DIR,
        )
    return _model
def make_result(**kwargs):#داله افتراضيه بتطلعلي نفس الحقول دايما سواء نجح او فشل
    result={
        "ok": False,
        "text": "",
        "language": None,
        "language_probability": 0.0,
        "confidence": 0.0,
        "duration": 0.0,
        "processing_time": 0.0,
        "error": None,
        "detail": "",
    }
    result.update(kwargs)#بستبدل القيم الافتراضيه بالقيم اللي بعتها
    return result
def clean_text(text):
    text=" ".join(text.split())#".splitبتشيل المسافات الزايده وترجع الكلمات لبعض بمسافه واحده
    for w in cfg.WAKE_WORDS:#باخد من بعد الويك ورد للاخر
        if text.lower().startswith(w.lower()):
            text=text[len(w):]   
            break
    text=text.strip(",،.؟?!")   
    if text.lower()in[h.lower()for h in cfg.HALLUCINATIONS]: #لو هلوسه برجع النص فاضي
        return ""
    return text    
def calc_confidence(segments):#avg_logprobز.no_speech_probمتوسطهم
    if not segments:
        return 0.0
    total=0.0
    for s in segments:
        c=math.exp(s.avg_logprob)*(1-s.no_speech_prob)
        total+=max(0.0,min(1.0,c))
    return round(total/len(segments),3)            

def transcribe_once(path,language):
    model=get_model()
    segments,info=model.transcribe(
        path,
        language=language,
        beam_size=cfg.BEAM_SIZE,
        
        
   
        initial_prompt=cfg.INITIAL_PROMPT or None, 
        vad_filter=cfg.VAD_FILTER,

    )
    segments=list(segments)
    text=clean_text(" ".join(s.text.strip()for s in segments))
    return{
        "text": text,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "confidence": calc_confidence(segments) if text else 0.0,
        "duration": round(info.duration, 2),
    }
def run_mode(path):
    mode = cfg.LANGUAGE_MODE
    if mode == "auto":
        return transcribe_once(path, None)
    if mode in ("ar", "en"):
        return transcribe_once(path, mode)
    if mode == "best_of_two":
        ar = transcribe_once(path, "ar")
        en = transcribe_once(path, "en")
        return ar if ar["confidence"] >= en["confidence"] else en
    raise ValueError("bad LANGUAGE_MODE: " + str(mode))
def speech_to_text(wav_path):
        start=time.time()
     
        try:#معناها جرب لو اي سطر جوه عمل خطا بدل ما البرنامج يقع نروح للexcept
            if not wav_path or not os.path.isfile(wav_path):
               return make_result(error="FILE_NOT_FOUND",
                                  detail=f"File not found: {wav_path}")

            r = run_mode(wav_path)
            
            r["processing_time"] = round(time.time() - start, 2)

            if not r["text"]:
                return make_result(error="NO_SPEECH",
                                   detail="No speech detected", **r)

            if r["confidence"] < cfg.CONFIDENCE_THRESHOLD:
                return make_result(error="LOW_CONFIDENCE",
                                   detail="Low confidence, ask the user to repeat", **r)

            return make_result(ok=True, **r)

        except Exception as e:
            return make_result(error="INTERNAL_ERROR",
                               detail=f"{type(e).__name__}: {e}",#اسم نوع الخطا
                               processing_time=round(time.time() - start, 2))
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stt.py audio/t1.mp4")
        sys.exit(1)
    result = speech_to_text(sys.argv[1])
    as_text = json.dumps(result, ensure_ascii=False, indent=2)
    print(as_text)
    with open("result.json", "w", encoding="utf-8") as f:
        f.write(as_text)