#!/usr/bin/env python3
"""線画セルに自動トーン(髪/服/陰)を挿入 usage: auto_tone.py <in.svg> <out.svg> [hair_g] [cloth_g]"""
import sys,re
import numpy as np
from PIL import Image
from scipy import ndimage
import cairosvg,vtracer
src=open(sys.argv[1]).read()
hair_g=sys.argv[3] if len(sys.argv)>3 else "#cccccc"
cloth_g=sys.argv[4] if len(sys.argv)>4 else "#a8a8a8"
shade_g="#dedede"
vb=re.search(r'viewBox="([^"]+)"',src).group(1); v=list(map(float,vb.split()))
W=min(int(v[2]),900)
cairosvg.svg2png(url=sys.argv[1],write_to="/tmp/a.png",output_width=W,background_color="white")
a=np.array(Image.open("/tmp/a.png").convert("L"))
H2,W2=a.shape
ink=a<128
k=max(7,int(min(a.shape)*0.06))
sil=ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.binary_dilation(ink,np.ones((k,k)))),np.ones((k,k)))
sil=ndimage.binary_fill_holes(sil|ink)
inner=sil&~ink
lab,n=ndimage.label(inner)
ys,xs=np.where(sil)
top,bot=ys.min(),ys.max(); hgt=bot-top
tone=np.zeros(a.shape,np.uint8)
xs2=np.where(sil)[1]; left,right=xs2.min(),xs2.max(); wid=right-left
for i in range(1,n+1):
    m=lab==i; area=m.sum()
    if area<sil.sum()*0.015: continue
    rys=np.where(m)[0]
    cy=rys.mean(); rel=(cy-top)/hgt
    touches_top=(rys.min()-top)<hgt*0.10
    if touches_top: tone[m]=1                     # 髪=上端接続領域を全塗り
    elif 0.45<rel<0.82: tone[m]=2
# 顔窓: 目(上部中央の小インク成分)を検出してトーンを白抜き
ilab,ni=ndimage.label(ink)
isz=ndimage.sum(ink,ilab,range(1,ni+1))
eyes=[]
for j,(sz,o) in enumerate(zip(isz,ndimage.find_objects(ilab)),1):
    if not(sil.sum()*0.0004<sz<sil.sum()*0.03): continue
    ey=(o[0].start+o[0].stop)/2; ex=(o[1].start+o[1].stop)/2
    if 0.10<(ey-top)/hgt<0.45 and left+wid*0.12<ex<right-wid*0.12:
        eyes.append(o)
if eyes:
    ey0=min(o[0].start for o in eyes); ey1=max(o[0].stop for o in eyes)
    ex0=min(o[1].start for o in eyes); ex1=max(o[1].stop for o in eyes)
    eh=max(ey1-ey0,int(hgt*0.04)); ew=max(ex1-ex0,int(wid*0.1))
    fy0=max(0,int(ey0-eh*0.9)); fy1=min(a.shape[0],int(ey1+eh*2.4))
    fx0=max(0,int(ex0-ew*0.30)); fx1=min(a.shape[1],int(ex1+ew*0.30))
    tone[fy0:fy1,fx0:fx1]=0
# 陰: シルエットを左上へずらした残り(右下側の縁)
sh=int(hgt*0.045)
shift=np.zeros_like(sil); shift[:-sh,:-sh]=sil[sh:,sh:]
shade=sil&~shift&~ink
shade[:int(top+hgt*0.42),:]=False   # 顔まわりに陰を落とさない
shade=ndimage.binary_opening(shade,np.ones((3,3)))
def trace_layer(mask,color):
    if mask.sum()<50: return ""
    Image.fromarray(np.where(mask,0,255).astype(np.uint8)).save("/tmp/t.png")
    vtracer.convert_image_to_svg_py("/tmp/t.png","/tmp/t.svg",colormode="binary",mode="spline",filter_speckle=10,corner_threshold=75)
    s=open("/tmp/t.svg").read(); s=re.sub(r'(\d+)\.\d+',r'\1',s)
    inner2=re.sub(r'^.*?<svg[^>]*>','',s,flags=re.S).replace('</svg>','').strip()
    inner2=inner2.replace('fill="#000000"',f'fill="{color}"')
    return inner2
sc=v[2]/W2
layers=trace_layer(tone==1,hair_g)+trace_layer(tone==2,cloth_g)+trace_layer(shade,shade_g)
g=f'<g transform="translate({v[0]},{v[1]}) scale({sc:.4f})">{layers}</g>'
# 白マスク(先頭のsil group)の直後・線の前に挿入
m=re.search(r'(<g transform[^>]*fill="white">.*?</g>)',src,flags=re.S)
if m:
    out=src.replace(m.group(1),m.group(1)+g,1)
else:
    out=re.sub(r'(<svg[^>]*>)',r'\\1'+g,src,count=1)
open(sys.argv[2],"w").write(out)
print("toned:",sys.argv[2])
