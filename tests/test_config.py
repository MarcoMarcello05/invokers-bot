import json
from invokers_bot.config import load_config

def test_load_config(tmp_path):
    p=tmp_path/"c.json"; p.write_text(json.dumps({"window":{"title_contains":"Invokers"},"states":{},"flows":{},"runtime":{"fps":5}}))
    c=load_config(p)
    assert c.window_title_contains=="Invokers"
    assert c.fps==5
    assert c.stable_frames==2
