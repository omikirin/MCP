#!/usr/bin/env python3
"""ミニシート高精細抽出 usage: hires_mini.py <png> <rows> <cols> <outdir> <id1,id2,...>"""
import sys,os,re
import numpy as np
from PIL import Image
from scipy import ndimage
import vtracer
Image.MAX_IMAGE_PIXELS=None
png,rows,cols,outdir=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
ids=sys.argv[5].split(",")
pil=Image.open(png).convert("L")
SC=max(1,8000//pil.width+1)
pil=pil.resize((pil.width*SC,pil.height*SC),Image.LANCZOS)
a=np.array(pil); ink=(a<160); H,W=a.shape
lab,n=ndimage.label(ink,structure=np.ones((3,3)))
sizes=ndimage.sum(ink,lab,range(1,n+1)); objs=ndimage.find_objects(lab)
ch,cw=H/rows,W/cols
cells={}
for i,(s,o) in enumerate(zip(sizes,objs),1):
    if s<600: continue
    cy=(o[0].start+o[0].stop)/2; cx=(o[1].start+o[1].stop)/2
    r=min(int(cy//ch),rows-1); co=min(int(cx//cw),cols-1)
    cells.setdefault(r*cols+co,[]).append({"id":i,"size":s,"bbox":o})
os.makedirs(outdir,exist_ok=True)
for k,cid in enumerate(ids):
    if cid=="-": continue
    mem=cells.get(k,[])
    if not mem: print("empty:",cid); continue
    main=max(mem,key=lambda c:c["size"])
    top=main["bbox"][0].start
    keep=[c for c in mem if c is main or c["bbox"][0].stop>top]
    y0=min(c["bbox"][0].start for c in keep); y1=max(c["bbox"][0].stop for c in keep)
    x0=min(c["bbox"][1].start for c in keep); x1=max(c["bbox"][1].stop for c in keep)
    sel=np.isin(lab[y0:y1,x0:x1],[c["id"] for c in keep])
    crop=np.pad(np.where(sel,0,255).astype(np.uint8),40,constant_values=255)
    Image.fromarray(crop).save("/tmp/c.png")
    out=f"{outdir}/{cid}.svg"
    vtracer.convert_image_to_svg_py("/tmp/c.png",out,colormode="binary",mode="spline",filter_speckle=14,corner_threshold=55,length_threshold=3.5)
    s2=open(out).read(); s2=re.sub(r'(\d+\.\d{2})\d+',r'\1',s2)
    w2=float(re.search(r'width="([\d.]+)',s2).group(1)); h2=float(re.search(r'height="([\d.]+)',s2).group(1))
    s2=s2.replace(f'width="{w2:g}"',f'viewBox="0 0 {w2:g} {h2:g}" width="{w2:g}"',1)
    open(out,"w").write(s2)
print("done",outdir)
