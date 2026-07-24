#!/usr/bin/env python3
"""各セルSVGに白シルエット下敷きを焼き込む
raster化→黒画素→穴埋め→輪郭トレース→白fillパスとして最下層に挿入
usage: python3 masker.py <indir> <outdir>
"""
import sys,os,glob,re
import numpy as np, cairosvg, vtracer
from PIL import Image
from scipy import ndimage

indir,outdir=sys.argv[1],sys.argv[2]
os.makedirs(outdir,exist_ok=True)
SCALE=1.0
for f in sorted(glob.glob(indir+"/*.svg")):
    src=open(f).read()
    vb=list(map(float,re.search(r'viewBox="([\d.\s-]+)"',src).group(1).split()))
    X0,Y0,W,H=vb
    cairosvg.svg2png(url=f,write_to="/tmp/m.png",output_width=min(int(W),720),background_color="white")
    a=np.array(Image.open("/tmp/m.png").convert("L"))
    ink=a<128
    k=max(7,int(min(a.shape)*0.08))
    d1=ndimage.distance_transform_edt(~ink)
    dil=d1<=k
    mask=ndimage.binary_fill_holes(dil)
    d2=ndimage.distance_transform_edt(mask)
    mask=d2>k
    mask=ndimage.binary_fill_holes(mask|ink)
    out=np.where(mask,0,255).astype(np.uint8)
    Image.fromarray(out).save("/tmp/mm.png")
    vtracer.convert_image_to_svg_py("/tmp/mm.png","/tmp/mm.svg",colormode="binary",
        mode="spline",filter_speckle=20,corner_threshold=80)
    ms=open("/tmp/mm.svg").read()
    # マスクSVGのパス(translate込み)を白fillに変換して抽出
    mh=float(re.search(r'height="([\d.]+)',ms).group(1))
    sc=H/mh
    sil=[]
    for p in re.findall(r'<path[^>]*/>|<path[^>]*>.*?</path>',ms,flags=re.S):
        p=re.sub(r'fill="[^"]*"','fill="white"',p)
        p=re.sub(r'stroke="[^"]*"','',p)
        sil.append(p)
    sil_g=(f'<g transform="translate({X0:.2f} {Y0:.2f}) scale({sc:.6f})" '
           f'fill="white">{"".join(sil)}</g>')
    sil_g=re.sub(r'(\d+\.\d{2})\d+',r'\1',sil_g)
    # 最下層(開始タグ直後)に挿入
    head=re.search(r'(<svg[^>]*>)',src).group(1)
    open(os.path.join(outdir,os.path.basename(f)),"w").write(
        src.replace(head,head+"\n"+sil_g,1))
print("masked",len(glob.glob(outdir+"/*.svg")),"cells")
