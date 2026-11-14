import numpy as np
from invokers_bot.vision import _crop_roi

def test_crop_roi_normalized():
    f=np.zeros((100,200,3),dtype=np.uint8)
    crop,x,y=_crop_roi(f,[0.25,0.20,0.75,0.80])
    assert crop.shape[:2]==(60,100)
    assert (x,y)==(50,20)
