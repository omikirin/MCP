#!/usr/bin/env python3
"""SVG座標の整数丸め(容量-40%)。transform属性は退避して精度保持
usage: svg_shrink.py <in_dir> <out_dir>"""
import sys,os,re,glob,shutil
src,dst=sys.argv[1],sys.argv[2]
shutil.rmtree(dst,ignore_errors=True); os.makedirs(dst)
for f in glob.glob(src+"/*.svg"):
    s=open(f).read()
    guards=[]
    def stash(m):
        guards.append(m.group(0)); return f"__T{len(guards)-1}__"
    s=re.sub(r'transform="[^"]*"',stash,s)
    s=re.sub(r'(\d+)\.\d+',r'\1',s)
    for i,g in enumerate(guards): s=s.replace(f"__T{i}__",g)
    open(os.path.join(dst,os.path.basename(f)),"w").write(s)
print("shrunk:",len(glob.glob(dst+"/*.svg")))
