#!/usr/bin/env python3
import sys,os,re
import numpy as np
from PIL import Image
from scipy import ndimage
import vtracer
Image.MAX_IMAGE_PIXELS=None
png,start=sys.argv[1],int(sys.argv[2])
outdir="backgrounds_lib"; os.makedirs(outdir,exist_ok=True)
pil=Image.open(png).convert("L")
SC=max(1,3600//pil.width+1)
pil=pil.resize((pil.width*SC,pil.height*SC),Image.LANCZOS)
a=np.array(pil); H,W=a.shape
rows,cols=4,5
ch,cw=H/rows,W/cols
for idx in range(20):
    r,c=divmod(idx,cols)
    cell=a[int(r*ch):int((r+1)*ch),int(c*cw):int((c+1)*cw)]
    ink=(cell<160)
    lab,n=ndimage.label(ink,structure=np.ones((3,3)))
    sizes=ndimage.sum(ink,lab,range(1,n+1)); objs=ndimage.find_objects(lab)
    keep=[]
    for i,(s,o) in enumerate(zip(sizes,objs),1):
        if s<80: continue
        bh=o[0].stop-o[0].start; bw=o[1].stop-o[1].start
        cy=(o[0].start+o[0].stop)/2; cx=(o[1].start+o[1].stop)/2
        # ラベル(BG###)除去: 上部18%・左45%・小型の成分
        if cy<cell.shape[0]*0.14 and cx<cell.shape[1]*0.5 and bh<cell.shape[0]*0.1:
            continue
        keep.append(i)
    if not keep: print("empty BG%03d"%(start+idx)); continue
    sel=np.isin(lab,keep)
    ys,xs=np.where(sel)
    y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    crop=np.where(sel[y0:y1+1,x0:x1+1],0,255).astype(np.uint8)
    Image.fromarray(crop).save("/tmp/b.png")
    out=f"{outdir}/BG{start+idx:03d}.svg"
    vtracer.convert_image_to_svg_py("/tmp/b.png",out,colormode="binary",mode="spline",filter_speckle=8,corner_threshold=60)
    s2=open(out).read(); s2=re.sub(r'(\d+\.\d{2})\d+',r'\1',s2)
    w=float(re.search(r'width="([\d.]+)',s2).group(1)); h=float(re.search(r'height="([\d.]+)',s2).group(1))
    s2=s2.replace(f'width="{w:g}"',f'viewBox="0 0 {w:g} {h:g}" width="{w:g}"',1)
    open(out,"w").write(s2)
print("sheet done", start)
