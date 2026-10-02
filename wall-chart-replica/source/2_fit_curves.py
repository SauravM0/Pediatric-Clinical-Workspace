import json,sys,os
import numpy as np
from PIL import Image
from scipy.interpolate import UnivariateSpline
CFG={'girls':dict(f='Images/IAP-Paediatrician-friendly-IAP-Growth-Charts-for-0-18-years-1-746x1024.jpg',x0=92.5,x18=912.5,y0=1285.0,ytop=64.0,ymax=175,T=80),
     'boys':dict(f='Images/IAP-Paediatrician-friendly-IAP-Growth-Charts-for-0-18-years-2-746x1024.png',x0=110.0,x18=778.5,y0=1191.2,ytop=65.5,ymax=195,T=110)}
raw=json.load(open(sys.argv[1]))
def runs(mask):
    ys=np.where(mask)[0]
    if not len(ys): return []
    out=[];s=p=ys[0]
    for y in ys[1:]:
        if y-p>1: out.append((s,p)); s=y
        p=y
    out.append((s,p)); return out
out={}
rep=[]
for sex,c in CFG.items():
    ppu=(c['y0']-c['ytop'])/c['ymax']; ppx=(c['x18']-c['x0'])/18
    n=np.array(Image.open(c['f']).convert('RGB')).astype(int); r,g,b=n[...,0],n[...,1],n[...,2]
    T=c['T']; m=((r<T)&(g<T)&(b<T))|((r>140)&(r-g>60)&(r-b>60))
    # birth anchors from the first plot column(s): envelope of each cluster
    anchors={}
    for xi in (int(c['x0'])+2,int(c['x0'])+3):
        col=m[:,xi].copy(); col[:60]=False; col[int(c['y0'])+1:]=False
        rr=runs(col)
        cs=[(s,e) for s,e in rr]
        # weight blob = lowest run group (largest y), height group above
        gaps=[cs[i+1][0]-cs[i][1] for i in range(len(cs)-1)]
        k=int(np.argmax(gaps)); hi=cs[:k+1]; lo=cs[k+1:]
        if hi and lo:
            anchors.setdefault('h',[]).append((c['y0']-(hi[-1][1]-2.0))/ppu); anchors.setdefault('h_top',[]).append((c['y0']-(hi[0][0]+1.2))/ppu)
            anchors.setdefault('w_bot',[]).append((c['y0']-(lo[-1][1]-1.2))/ppu); anchors.setdefault('w_top',[]).append((c['y0']-(lo[0][0]+1.2))/ppu)
    out[sex]={}
    for meas in ('height','weight'):
        L=raw[sex][meas]; curves=[]
        grid=np.round(np.arange(0,18.0001,0.05),3)
        for i in range(7):
            pts=np.array(L[i]); a,v=pts[:,0],pts[:,1]
            # bin 0.05
            ba=np.floor(a/0.05); ua=np.unique(ba); A=[];V=[]
            for u in ua:
                mm=ba==u; A.append(np.mean(a[mm])); V.append(np.median(v[mm]))
            A=np.array(A);V=np.array(V)
            # outlier removal: residual from running median (5)
            keep=np.ones(len(V),bool)
            for j in range(len(V)):
                nb=V[max(0,j-3):j+4]; 
                if abs(V[j]-np.median(nb))>0.9*(0.5/ppu)*6+0.6*(1 if meas=='height' else 0.3): keep[j]=False
            A,V=A[keep],V[keep]
            sig=0.6/ppu
            w=np.ones(len(A))
            # age-0 anchor
            if meas=='height':
                top=np.mean(anchors['h_top']);bot=np.mean(anchors['h'])
            else:
                top=np.mean(anchors['w_top']);bot=np.mean(anchors['w_bot'])
            v0=bot+(top-bot)*i/6
            a_anchor=2.5/ppx          # the anchor columns sit 2-3 px right of the y axis, i.e. at this age -- not at age 0
            if A[0]>a_anchor: A=np.insert(A,0,a_anchor);V=np.insert(V,0,v0);w=np.insert(w,0,4.0)
            spl=UnivariateSpline(A,V,w=w/sig,k=3,s=len(A)*0.4)
            y=spl(grid)
            # below the anchor age: straight-line extrapolation back to age 0 using the slope just after it
            sl=(spl(a_anchor+0.05)-spl(a_anchor))/0.05
            y=np.where(grid<a_anchor, spl(a_anchor)-sl*(a_anchor-grid), y)
            y=np.maximum.accumulate(y)
            res=spl(A)-V
            rep.append((sex,meas,i,len(A),float(np.sqrt(np.mean(res**2))),float(np.abs(res).max())))
            curves.append([round(float(t),2) for t in y])
        out[sex][meas]=curves
    out[sex]['ages']=[float(t) for t in grid]
    print(sex,'birth anchors',{k:np.round(np.mean(v),1) for k,v in anchors.items()})
for sx,me,i,n,rm,mx in rep:
    print(f'{sx:5s} {me:6s} line{i} n={n:3d} rms={rm:.3f} max={mx:.2f}')
json.dump(out,open(sys.argv[2],'w'))
