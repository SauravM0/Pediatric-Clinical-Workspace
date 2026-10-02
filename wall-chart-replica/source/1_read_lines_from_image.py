import json,sys
import numpy as np
from PIL import Image
CFG={'girls':dict(f='Images/IAP-Paediatrician-friendly-IAP-Growth-Charts-for-0-18-years-1-746x1024.jpg',x0=92.5,x18=912.5,y0=1285.0,ytop=64.0,ymax=175,T=80,inset=(425,335)),
     'boys':dict(f='Images/IAP-Paediatrician-friendly-IAP-Growth-Charts-for-0-18-years-2-746x1024.png',x0=110.0,x18=778.5,y0=1191.2,ytop=65.5,ymax=195,T=110,inset=(425,372))}
def runs(mask):
    ys=np.where(mask)[0]
    if not len(ys): return []
    out=[];s=p=ys[0]
    for y in ys[1:]:
        if y-p>1: out.append((s,p)); s=y
        p=y
    out.append((s,p)); return out
res={}
for sex,c in CFG.items():
    n=np.array(Image.open(c['f']).convert('RGB')).astype(int); r,g,b=n[...,0],n[...,1],n[...,2]
    T=c['T']; m=((r<T)&(g<T)&(b<T))|((r>140)&(r-g>60)&(r-b>60))
    ppu=(c['y0']-c['ytop'])/c['ymax']; ppx=(c['x18']-c['x0'])/18
    H=[[] for _ in range(7)]; W=[[] for _ in range(7)]
    for x in range(int(c['x0'])+2,int(c['x18'])-1):
        col=m[:,x].copy(); col[:60]=False; col[int(c['y0'])+1:]=False
        if x<c['inset'][0]: col[:c['inset'][1]]=False
        rr=[((s+e)/2,e-s) for s,e in runs(col) if e-s<=9]
        cs=[y for y,_ in rr]
        if len(cs)<7: continue
        if len(cs)>=8:
            gaps=np.diff(cs); k=int(np.argmax(gaps)); up=cs[:k+1]; lo=cs[k+1:]
            if gaps[k]<60: up,lo=cs,[]
        else: up,lo=cs,[]
        age=(x-c['x0'])/ppx
        # single group of 7 -> classify as height or weight by position
        for grp in (up,lo):
            if len(grp)!=7: continue
            tgt=H if (c['y0']-np.median(grp))/ppu>min(100,25+4*age) else W
            for i,y in enumerate(grp[::-1]): tgt[i].append((age,(c['y0']-y)/ppu))
    res[sex]={'height':H,'weight':W,'ppu':ppu}
    for nm,L in (('height',H),('weight',W)):
        a=np.array([p[0] for p in L[3]]) if L[3] else np.array([0.0,0.0]); print(sex,nm,'columns accepted',len(a),'of',int(c['x18']-c['x0']),' gaps>0.25y:',[(round(a[i],2),round(a[i+1],2)) for i in range(len(a)-1) if a[i+1]-a[i]>0.25], 'first',round(a.min(),2),'last',round(a.max(),2))
json.dump({s:{'height':v['height'],'weight':v['weight']} for s,v in res.items()},open(sys.argv[1],'w'))
