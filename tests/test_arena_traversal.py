import pytest
from invokers_bot.arena_traversal import View,Row,Bounds,traverse
from invokers_bot.models import GameState
from invokers_bot.wheel import validate_wheel

def view(fp,rows,count=10,digest="a",state=GameState.ARENA_LIST):
    return View(state,digest,1,count,fp,tuple(Row(r,(0,i,10,10)) for i,r in enumerate(rows)))

def run(pages,**kwargs):
    index=[0];ticks=[0.];calls=[]
    def observe():return pages[min(index[0],len(pages)-1)]
    def scroll(delta):
        calls.append(delta);index[0]+=1;return True
    def sleep(n):ticks[0]+=n
    result=traverse(observe,scroll,kwargs.pop("cancelled",lambda:False),Bounds(**kwargs),clock=lambda:ticks[0],sleep=sleep)
    return result,calls

def test_one_page():
    result,calls=run([view("a",["1","2"],2)])
    assert result.reason=="COUNT_REACHED" and not calls

def test_multi_page_overlap():
    result,calls=run([view("a",["1","2"],3),view("b",["2","3"],3)])
    assert result.unique_count==3 and result.reason=="COUNT_REACHED" and calls==[-120]

def test_end_unchanged():
    result,calls=run([view("a",["1"])])
    assert result.reason=="END_UNCHANGED" and len(calls)==1

def test_no_new():
    result,calls=run([view("a",["1"]),view("b",["1"]),view("c",["1"])],no_new_limit=2)
    assert result.reason=="NO_NEW_ROWS" and len(calls)==2

def test_max():
    result,calls=run([view("a",["1"]),view("b",["2"])],max_scrolls=1)
    assert result.reason=="MAX_SCROLLS"

def test_timeout():
    result,calls=run([view("a",["1"])],max_seconds=.05)
    assert result.reason=="TIMEOUT"

def test_cancel():
    result,calls=run([view("a",["1"])],cancelled=lambda:True)
    assert result.reason=="CANCELLED" and not calls

@pytest.mark.parametrize("state,reason",[(GameState.UNKNOWN,"UNKNOWN"),(GameState.FORMATION,"UNEXPECTED_SCREEN")])
def test_screen(state,reason):
    result,calls=run([view("a",["1"]),view("b",["2"],state=state)])
    assert result.reason==reason and len(calls)==1

def test_stale():
    result,calls=run([view("a",["1"]),view("b",["2"],digest="new")])
    assert result.reason=="STALE" and result.digest=="a" and len(calls)==1

@pytest.mark.parametrize("delta",[-120,120,-240])
def test_wheel(delta):
    assert validate_wheel(delta,(.1,.1,.9,.9))[0]==delta

@pytest.mark.parametrize("delta",[0,1,-1201,True])
def test_bad_wheel(delta):
    with pytest.raises(ValueError):
        validate_wheel(delta,(0,0,1,1))
