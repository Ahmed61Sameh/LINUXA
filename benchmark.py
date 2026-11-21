import csv
import re
import sys
import stt_config as cfg
if len(sys.argv)>1:
    cfg.MODEL_SIZE=sys.argv[1]
if len(sys.argv)>2:
    cfg.LANGUAGE_MODE=sys.argv[2]   
import stt     
def normalize(text):
    text=text.lower()
    text=re.sub(r"[\u064B-\u0652\u0640]","",text)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه")):
        text=text.replace(a,b)
    text=re.sub(r"[^\w\s]"," ",text)  
    return[cfg.APP_SYNONYMS.get(w,w)for w in text.split()]  
def wer (ref,hyp):
    if not ref:
        return 0.0 if not hyp else 1.0
    d=[[0]*(len(hyp)+1)for _ in range (len(ref)+1)]
    for i in range(len(ref)+1):
        d[i][0]=i
    for j in range(len(hyp)+1):
        d[0][j]=j
    for i in range(1,len(ref)+1):
        for j in range(1,len(hyp)+1):
            cost=0 if ref[i-1]==hyp[j-1] else 1 
            d[i][j]=min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+cost) 
    return d[len(ref)][len(hyp)]/len(ref)              
def run_all():
    rows = []
    with open("test_cases.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            r = stt.speech_to_text(row["file"])
            rows.append({
                "file": row["file"],
                "ref": row["reference"],
                "hyp": r["text"],
                "cat": row["category"],
                "wer": wer(normalize(row["reference"]), normalize(r["text"])),
                "conf": r["confidence"],
                "time": r["processing_time"],
                "error": r["error"],
            })
            print("done:", row["file"])
    return rows
def write_report(rows):
    name = f"benchmark_{cfg.MODEL_SIZE}_{cfg.LANGUAGE_MODE}.txt"
    out = open(name, "w", encoding="utf-8")

    def show(line=""):
        print(line)
        out.write(line + "\n")

    show(f"model: {cfg.MODEL_SIZE} | language mode: {cfg.LANGUAGE_MODE} | "
         f"VAD: {cfg.VAD_FILTER}")

    show("\n--- every sentence ---")
    for r in rows:
        show(f"{r['file']} | WER={r['wer']:.2f} | conf={r['conf']} | {r['error']}")
        show(f"   real: {r['ref']}")
        show(f"   got : {r['hyp']}")
    show("\n--- category averages ---")
    for cat in sorted(set(r["cat"] for r in rows)):
        g = [r for r in rows if r["cat"] == cat]
        show(f"{cat}: WER={sum(x['wer'] for x in g) / len(g):.2f} | "
             f"time={sum(x['time'] for x in g) / len(g):.1f}s | count={len(g)}")

    total = sum(r["wer"] for r in rows) / len(rows)
    show(f"\noverall WER: {total:.2f}")
    errors = [r for r in rows if r["error"] in ("FILE_NOT_FOUND", "INTERNAL_ERROR")]
    show(f"files with FILE_NOT_FOUND or INTERNAL_ERROR: {len(errors)}") 
    show("\n--- threshold table (correct = WER <= 0.25) ---")
    show("threshold | wrong accepted | correct rejected")
    for i in range(1, 10):
        t = i / 10
        bad = sum(1 for r in rows if r["wer"] > 0.25 and r["conf"] >= t)
        good = sum(1 for r in rows if r["wer"] <= 0.25 and r["conf"] < t)
        show(f"{t:.1f}       | {bad}              | {good}")

    out.close()
    print(f"\nsaved to {name}")
if __name__ == "__main__":
    write_report(run_all())        