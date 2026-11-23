import sys
import wave
import numpy as np
def inspect(path):
    print("\n==",path)
    try:
        with wave.open(path,"rb")as w:
            rate=w.getframerate()
            channels=w.getnchannels()
            width=w.getsampwidth()
            frames=w.getnframes()
            data=w.readframes(frames)
    except Exception as e:
        print("NOT a valid WAV:",e)    
        return
    duration=frames/rate if rate else 0
    print(f"rate={rate}|channels={channels}|bits={width*8}|duration={duration:.2f}s")
    problems=[]
    if rate !=16000:
        problems.append(f"rate{rate},expected 16000")    
    if channels !=1:
        problems.append(f"channels{channels},expected 1(mono)")
    if duration<0.3:
        problems.append("too short")
    if width==2:
        a=np.frombuffer(data,dtype=np.int16).astype(np.float32)/32768 
        peak=float(np.abs(a).max()) if len(a) else 0.0
        print(f"peak level :{peak:.3f}")     
        if peak <0.02:
            problems.append("very quiet or silent")
        if peak>=0.99:
            problems.append("clipping (too loud)")
    else:
        problems.append("must be 16-bit") 
    for p in problems:
        print("WARNING:",p)    
    if not problems:
        print("OK:file looks good")
for p in sys.argv[1:]:
    inspect(p)          
             