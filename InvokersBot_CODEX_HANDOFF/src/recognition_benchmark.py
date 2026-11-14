"""Offline-only template matching benchmark; never used to authorize input."""
import cv2
import numpy as np
from time import perf_counter
import json


def match_scales(image, template, scales=(0.85, 1.0, 1.15)):
    if template.ndim != 2 or image.ndim != 2 or template.size == 0 or template.std() < 1:
        raise ValueError('Nonconstant grayscale template required')
    best = None
    for scale in scales:
        w,h = (round(template.shape[1]*scale),round(template.shape[0]*scale))
        if min(w,h)<2 or w>image.shape[1] or h>image.shape[0]:
            continue
        resized = cv2.resize(template,(w,h),interpolation=cv2.INTER_LINEAR)
        if resized.std()<1:
            continue
        _,score,_,point = cv2.minMaxLoc(cv2.matchTemplate(image,resized,cv2.TM_CCOEFF_NORMED))
        result = {'score':float(score),'point':point,'scale':scale}
        if best is None or score>best['score']:
            best=result
    return best


def benchmark():
    rng=np.random.default_rng(42)
    template=rng.integers(0,256,(40,60),dtype=np.uint8)
    rows=[]
    for scales in [(1.0,),(.85,1.0,1.15)]:
        tp=fp=fn=tn=0
        start=perf_counter()
        for scale in (.85,1.,1.15,None):
            for _ in range(10):
                image=rng.integers(0,256,(240,320),dtype=np.uint8)
                if scale is not None:
                    sample=cv2.resize(template,(round(60*scale),round(40*scale)),interpolation=cv2.INTER_LINEAR)
                    h,w=sample.shape
                    image[80:80+h,100:100+w]=sample
                hit=match_scales(image,template,scales)
                detected=hit is not None and hit['score']>=.95
                correct=detected and hit['point']==(100,80)
                if scale is None:
                    fp+=int(detected);tn+=int(not detected)
                else:
                    tp+=int(correct);fn+=int(not correct)
        rows.append(dict(scales=scales,tp=tp,fp=fp,fn=fn,tn=tn,elapsed_ms=(perf_counter()-start)*1000))
    return rows


if __name__=='__main__':
    print(json.dumps(benchmark(),indent=2))
