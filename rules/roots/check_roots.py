#!/usr/bin/env python3
import sys, re, pathlib
HV={4,7,8,11,12,13}
def main(ws):
    f=pathlib.Path(ws)/"ROOTS-SCORE.md"
    if not f.exists(): print("VIBE: no ROOTS-SCORE.md. Blocked."); return 1
    rows=re.findall(r"^\|\s*(\d{1,2})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|",f.read_text(),re.M)
    seen,block=set(),[]
    for n,_,st,ptr,wv in rows:
        n=int(n); seen.add(n); st=st.strip().upper()
        if st=="ROOTED" and not ptr.strip() and n in HV: block.append(n)
        if st in{"SEEDLING","ABSENT"} and not wv.strip() and n in HV: block.append(n)
    miss=set(range(1,14))-seen
    if miss: print("VIBE: unscored:",sorted(miss)); return 1
    if block: print("VIBE: HV blockers:",sorted(set(block))); return 1
    print("SYSTEM: soil checked. Cleared to ship."); return 0
if __name__=="__main__": sys.exit(main(sys.argv[1] if len(sys.argv)>1 else "."))
