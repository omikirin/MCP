#!/usr/bin/env python3
"""成分マスク方式の汎用再抽出
usage: python3 reextract.py <png> <rows> <cols> <outdir> <id1,id2,...(行順)>
"""
import sys,os,re,json
import numpy as np
from PIL import Image
from scipy import ndimage
import vtracer
Image.MAX_IMAGE_PIXELS=None
png,rows,cols,outdir=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
ids=sys.argv[5].split(",")
pil=Image.open(png).convert("L")
SC=max(1,3600//pil.width+1)
pil=pil.resize((pil.width*SC,pil.height*SC),Image.LANCZOS)
a=np.array(pil); ink=(a<160); H,W=a.shape
lab,n=ndimage.label(ink,structure=np.ones((3,3)))
sizes=ndimage.sum(ink,lab,range(1,n+1)); objs=ndimage.find_objects(lab)
comps=[{"id":i,"cx":(o[1].start+o[1].stop)/2,"cy":(o[0].start+o[0].stop)/2,"bbox":o}
       for i,(s,o) in enumerate(zip(sizes,objs),1) if s>=300]
ry=np.array([H*(r+0.5)/rows for r in range(rows)])
rx=np.array([W*(c+0.5)/cols for c in range(cols)])
cells={}
for c in comps:
    r=int(np.argmin(abs(ry-c["cy"]))); co=int(np.argmin(abs(rx-c["cx"])))
    cells.setdefault(r*cols+co,[]).append(c)
os.makedirs(outdir,exist_ok=True)
for idx,cid in enumerate(ids):
    if cid=="-": continue
    mem=cells.get(idx,[])
    if not mem: print("empty:",cid); continue
    y0=min(c["bbox"][0].start for c in mem); y1=max(c["bbox"][0].stop for c in mem)
    x0=min(c["bbox"][1].start for c in mem); x1=max(c["bbox"][1].stop for c in mem)
    sel=np.isin(lab[y0:y1,x0:x1],[c["id"] for c in mem])
    crop=np.pad(np.where(sel,0,255).astype(np.uint8),30,constant_values=255)
    Image.fromarray(crop).save("/tmp/c.png")
    out=f"{outdir}/{cid}.svg"
    vtracer.convert_image_to_svg_py("/tmp/c.png",out,colormode="binary",mode="spline",filter_speckle=12,corner_threshold=60)
    s=open(out).read(); s=re.sub(r'(\d+\.\d{2})\d+',r'\1',s)
    w=float(re.search(r'width="([\d.]+)',s).group(1)); h=float(re.search(r'height="([\d.]+)',s).group(1))
    s=s.replace(f'width="{w:g}"',f'viewBox="0 0 {w:g} {h:g}" width="{w:g}"',1)
    open(out,"w").write(s)
print("done",outdir)
