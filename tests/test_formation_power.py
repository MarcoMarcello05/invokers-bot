from dataclasses import replace
import cv2
import numpy as np
import pytest
from invokers_bot.formation_power import Calibration,GlyphReader,normalize_power,sense_formation
from invokers_bot.arena_ranking import PowerSource,rank
from invokers_bot.arena_authorization import ArenaTokenPolicy,authorize,pressure,TokenPressure
from test_arena_authorization import setup

@pytest.mark.parametrize("raw,expected",[("9.368",9368),("9368",9368),("9.425",9425),("9 368",None),("9.36",None),("9.368 9425",None),("0",None),("99.999.999.999",None),("9,368",None)])
def test_normalization(raw,expected):
    assert normalize_power(raw)==expected

def sensor():
    # Synthetic font only; not a game-client calibration.
    glyphs={}
    for ch in "0123456789.":
        img=np.zeros((34,28),np.uint8)
        cv2.putText(img,ch,(2,27),cv2.FONT_HERSHEY_SIMPLEX,.9,255,1,cv2.LINE_8)
        glyphs[ch]=img
    c=Calibration("synthetic",(1536,864),96,(.521,.139,.651,.255))
    reader=GlyphReader(glyphs,c)
    f=np.zeros((864,1536),np.uint8)
    x,y=810,180
    for ch in "9.368":
        t=reader.templates[ch]
        h,w=t.shape
        f[y-h:y,x:x+w]=t
        x+=w+3
    return f,reader

def test_sensor_and_authorization():
    a,c,p,r=setup(12)
    f,reader=sensor()
    power=sense_formation(f,state="formation",confirmed=True,dpi=96,reader=reader,context=p.context,now=10)
    assert power.value==9368 and power.confidence==1 and power.exact and power.validated
    assert power.source==PowerSource.PREBATTLE_NUMERIC_ROI
    candidate=rank(a,power,r,now=10,context=p.context).selected
    auth=authorize(a,candidate,power,ArenaTokenPolicy(),r,now=10)
    assert auth.allowed and auth.token_balance==12 and auth.resulting_balance==11
    assert auth.pressure==TokenPressure.AT_CAP and not auth.fight_authorized

@pytest.mark.parametrize("state,confirmed,dpi,age",[("victory",True,96,0),("formation",False,96,0),("formation",True,120,0),("formation",True,96,3)])
def test_rejected(state,confirmed,dpi,age):
    f,reader=sensor()
    p=sense_formation(f,state=state,confirmed=confirmed,dpi=dpi,reader=reader,context=(("a",1),),observed_at=10,now=10+age)
    assert p.source==PowerSource.UNKNOWN and not p.validated

def test_geometry():
    f,reader=sensor()
    assert sense_formation(f[:-1],state="formation",confirmed=True,dpi=96,reader=reader,context=(1,),now=10).value is None

def test_default_cost():
    assert ArenaTokenPolicy().expected_battle_cost==1
