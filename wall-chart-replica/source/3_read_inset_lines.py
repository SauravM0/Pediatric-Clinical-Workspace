import json,sys
import numpy as np
from PIL import Image
CFG={'girls':dict(f='Images/IAP-Paediatrician-friendly-IAP-Growth-Charts-for-0-18-years-1-746x1024.jpg',x120=128.6,ppx=5.575,hmax=170,y0=291.25,ppu=2.25),
     'boys':dict(f='Images/IAP-Paediatrician-friendly-IAP-Growth-Charts-for-0-18-years-2-746x1024.png',x120=153.0,ppx=4.2,hmax=180,y0=325.2,ppu=2.614)}
def runs(mask):
    ys=np.where(mask)[0]
    if not len(ys): return []
    out=[];s=p=ys[0]
    for y in ys[1:]:
        if y-p>1: out.append((s,p)); s=y
        p=y
    out.append((s,p)); return out
out={}
for sex,c in CFG.items():
    n=np.array(Image.open(c['f']).convert('RGB')).astype(int); r,g,b=n[...,0],n[...,1],n[...,2]
    if sex=='girls': masks={'OB':(r>110)&(r<215)&(r-g>30)&(r-b>25)&(g<160),'OW':(r>185)&(g>170)&(r-b>28)&(abs(r-g)<30),'UW':(r<95)&(g<95)&(b<95)}
    else: masks={'OB':(r>130)&(r-g>60)&(r-b>45)&(g<110),'OW':(r>190)&(g>150)&(r-b>55)&(abs(r-g)<70),'UW':(r<95)&(g<95)&(b<95)}
    out[sex]={}
    for key,m in masks.items():
        pts=[]; prev=None
        xs=range(int(c['x120'])+1,int(c['x120']+c['ppx']*(c['hmax']-120))+1)
        for x in xs:
            col=m[:int(c['y0'])+1,x].copy(); col[:int(c['y0']-90*c['ppu'])-2]=False
            rr=[(s+e)/2 for s,e in runs(col) if e-s<=7]
            if not rr: continue
            if prev is None:
                # start: choose by expected region (left side)
                exp={'OB':c['y0']-29*c['ppu'],'OW':c['y0']-25*c['ppu'],'UW':c['y0']-18*c['ppu']}[key]
                cand=min(rr,key=lambda y:abs(y-exp))
                if abs(cand-exp)>6: continue
            else:
                cand=min(rr,key=lambda y:abs(y-prev))
                if abs(cand-prev)>4: continue
            prev=cand; pts.append(((x-c['x120'])/c['ppx']+120,(c['y0']-cand)/c['ppu']))
        pts=np.array(pts)
        out[sex][key]=pts
        print(sex,key,len(pts),'x range',pts[0,0].round(1),pts[-1,0].round(1),'start',pts[0,1].round(1),'end',pts[-1,1].round(1))
json.dump({s:{k:v.tolist() for k,v in d.items()} for s,d in out.items()},open(sys.argv[1],'w'))
