"""Passive configurable A/B/C observation, no input path."""
import time

def observe_transition(facts,state,probes,reader,now=None):
    now=time.monotonic() if now is None else now
    for probe in probes:
        key="probe:"+probe["id"]
        session=facts.get(key)
        def capture():
            return {name:reader(filename,tag) for name,filename,tag in probe["sources"]}
        if state==probe["from"]:
            if session and "B" in session:
                event={**session,"C":capture(),"status":"COMPLETE"}
                facts["diagnostic:"+probe["id"]]=event
                facts.pop(key,None)
                yield event
            elif not session or now-session["sample_at"]>=0.5:
                facts[key]={"A":capture(),"sample_at":now}
        elif state==probe["to"] and session:
            if "B" not in session:
                session["B"]=capture()
                session["sample_at"]=now
            elif now-session["sample_at"]>=0.5:
                session["B_latest"]=capture()
                session["sample_at"]=now
        elif state not in (probe["from"],probe["to"],"unknown"):
            facts.pop(key,None)
