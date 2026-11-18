"""Consumer-contract tests only, never real prototype mappings."""
from dataclasses import replace,FrozenInstanceError
from pathlib import Path
import ast
import pytest

from invokers_bot.quest_catalog import (
    CatalogBinding,DefinitionOrigin,QuestDefinition,QuestStaticCatalog,
    QuestActionId,QuestConditionTag,QuestAreaId,QuestCondition,
    EvidenceField,FieldStatus,LookupStatus,DomainHint,domain_hint,
    RewardDescriptor,ResourceReward,
)
from invokers_bot.quests_model import QuestKind

# Fictional ID and versions, deliberately unrelated to actual static content.
PID=123456789
BINDING=CatalogBinding("synthetic-client","synthetic-static","a"*64)
ORIGIN=DefinitionOrigin(BINDING,"b"*64,100,200,120,25)
QUERY={"game_build":BINDING.game_build,"static_revision":BINDING.static_revision}
V=EvidenceField.verified


def definition(action=61,area=4):
    return QuestDefinition(PID,QuestKind.PERIODIC,ORIGIN,
        action_id=V(action),required_amount=V(3),group_or_page=V(1),
        conditions=V((QuestCondition(5,area_id=V(area)),)))


def test_dump_declared_enum_values():
    assert tuple(t.value for t in QuestConditionTag)==tuple(range(1,16))
    assert (QuestActionId.BattleFinish,QuestActionId.RelicUpgrade,QuestActionId.ResourcesSpent)==(61,43,101)
    assert (QuestAreaId.Campaign,QuestAreaId.Tower,QuestAreaId.AsyncPvp)==(1,3,4)


def test_field_states():
    for state in (FieldStatus.UNKNOWN,FieldStatus.ABSENT,FieldStatus.UNSUPPORTED):
        assert EvidenceField(state).value is None
        with pytest.raises(ValueError):
            EvidenceField(state,0)
    assert V(0).value==0
    with pytest.raises(ValueError):
        V(None)


def test_unavailable_and_exact_lookup():
    assert QuestStaticCatalog(BINDING).resolve(PID,**QUERY).status==LookupStatus.CATALOG_UNAVAILABLE
    d=definition()
    catalog=QuestStaticCatalog(BINDING,[d])
    assert catalog.resolve(PID,**QUERY).status==LookupStatus.FOUND
    assert catalog.lookup(PID,**QUERY) is d
    assert catalog.resolve(PID+1,**QUERY).status==LookupStatus.UNKNOWN_PROTOTYPE
    assert catalog.lookup(PID+1,**QUERY) is None
    with pytest.raises(FrozenInstanceError):
        d.prototype_id=1


@pytest.mark.parametrize("version,reason",[
    ({"game_build":"wrong"},LookupStatus.BUILD_MISMATCH),
    ({"static_revision":"wrong"},LookupStatus.REVISION_MISMATCH),
    ({"artifact_sha256":"c"*64},LookupStatus.ARTIFACT_MISMATCH),
])
def test_versions(version,reason):
    result=QuestStaticCatalog(BINDING,[definition()]).resolve(PID,**{**QUERY,**version})
    assert result.status==reason and result.definition is None
    assert domain_hint(result)==DomainHint.UNKNOWN


@pytest.mark.parametrize("action",[0,-1,999999])
def test_unknown_objective(action):
    catalog=QuestStaticCatalog(BINDING,[definition(action)])
    assert catalog.resolve(PID,**QUERY).status==LookupStatus.UNSUPPORTED_OBJECTIVE
    assert catalog.lookup(PID,**QUERY) is None


def test_missing_evidence():
    d=replace(definition(),required_amount=EvidenceField(FieldStatus.UNKNOWN))
    assert QuestStaticCatalog(BINDING,[d]).resolve(PID,**QUERY).status==LookupStatus.UNVERIFIED_OBJECTIVE
    d=replace(definition(),action_id=EvidenceField(FieldStatus.UNSUPPORTED))
    assert QuestStaticCatalog(BINDING,[d]).resolve(PID,**QUERY).status==LookupStatus.UNSUPPORTED_OBJECTIVE


def test_duplicate_and_provenance():
    d=definition()
    with pytest.raises(ValueError,match="duplicate"):
        QuestStaticCatalog(BINDING,[d,d])
    with pytest.raises(ValueError,match="provenance"):
        QuestStaticCatalog(replace(BINDING,static_revision="wrong"),[d])
    with pytest.raises(ValueError):
        replace(ORIGIN,record_size=999)
    with pytest.raises(ValueError):
        replace(d,required_amount=V(-1))


@pytest.mark.parametrize("area,expected",[(1,DomainHint.CAMPAIGN),(3,DomainHint.SPIRE),
    (4,DomainHint.ARENA),(6,DomainHint.CLAN_BOSS),(0,DomainHint.UNKNOWN),(99,DomainHint.UNKNOWN)])
def test_battle_hint(area,expected):
    result=QuestStaticCatalog(BINDING,[definition(area=area)]).resolve(PID,**QUERY)
    assert domain_hint(result)==expected


def test_other_hints_and_no_guess():
    for action,hint in ((43,DomainHint.RELIC),(191,DomainHint.ARENA),(192,DomainHint.ARENA),(121,DomainHint.UNKNOWN)):
        d=replace(definition(action),conditions=V(()))
        assert domain_hint(QuestStaticCatalog(BINDING,[d]).resolve(PID,**QUERY))==hint
    d=definition()
    for conditions in (EvidenceField(FieldStatus.UNKNOWN),V(()),
            V((QuestCondition(5),)),V((QuestCondition(5,area_id=V(4)),QuestCondition(5,area_id=V(1)))),
            V((QuestCondition(99),))):
        x=replace(d,conditions=conditions)
        assert domain_hint(QuestStaticCatalog(BINDING,[x]).resolve(PID,**QUERY))==DomainHint.UNKNOWN


def test_reward_metadata_only():
    reward=RewardDescriptor(experience=V(0),vip_points=V(2),resources=V((ResourceReward(1,3),)))
    d=replace(definition(),reward=V(reward))
    found=QuestStaticCatalog(BINDING,[d]).lookup(PID,**QUERY)
    assert found.reward.value.resources.value==(ResourceReward(1,3),)
    assert found.reward.value.heroes==FieldStatus.UNKNOWN
    with pytest.raises(ValueError):
        replace(reward,heroes=FieldStatus.VERIFIED)


def test_no_input_imports():
    base=Path(__file__).resolve().parents[1]/"src"/"invokers_bot"
    for name in ("static_pack.py","quest_catalog.py"):
        tree=ast.parse((base/name).read_text())
        modules=[n.module or "" for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        modules += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
        assert not any(any(word in m for word in ("input","engine","vision","ocr","action","cv2","pyautogui")) for m in modules)
