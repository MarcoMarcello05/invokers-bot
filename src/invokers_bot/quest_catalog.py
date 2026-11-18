"""Versioned semantic boundary for independently decoded quest definitions.

IL2CPP declarations establish types/enums, not StaticData record boundaries.
No loader, default prototype meanings, game actions or production catalog rows
are included here. A future strict decoder must supply independently verified
record provenance. This module checks the consumer contract, not that proof.
"""
from dataclasses import dataclass
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Generic, TypeVar
import re

from .quests_model import QuestKind


class QuestActionId(IntEnum):
    # Shared.Choreograph.Models.QuestAction (archived 0.62 dump).
    Unknown=0
    HeroSummon=2
    HeroLevelUp=3
    HeroAscend=4
    HeroAwake=5
    HeroSkillLevelUp=6
    HeroStatsChanged=7
    AnimaSummon=22
    AnimaLevelUp=23
    AnimaEmpower=24
    AnimaSkillLevelUp=25
    RelicCollect=41
    RelicActivate=42
    RelicUpgrade=43
    RelicGetMemoriumFromDestroy=45
    RelicGetGoldFromSell=46
    RelicActivateOrUpgrade=47
    RelicSell=48
    RelicDestroy=49
    AccessoryCollect=51
    AccessoryActivate=52
    AccessoryUpgrade=53
    AccessoryGetMemoriumFromDestroy=55
    AccessoryGetGoldFromSell=56
    AccessoryActivateOrUpgrade=57
    AccessorySell=58
    AccessoryDestroy=59
    BattleFinish=61
    GearUpgrade=71
    GearSell=72
    GearDestroy=73
    QuestComplete=81
    QuestUpgradeProgress=82
    ResourcesSpent=101
    ShopPurchase=121
    PlayerLogIn=141
    ConnectAccount=142
    EnablePushNotifications=144
    ChangeAccountName=145
    ChangeAccountAvatar=146
    ActivateBooster=147
    FormationUpgrade=161
    HeroOrAnimaSummon=181
    HeroOrAnimaSkillLevelUp=182
    ArenaHallUpgrade=191
    ArenaPointsChange=192
    ClientAction=201


class QuestConditionTag(IntEnum):
    Hero=1
    Anima=2
    Relic=3
    Quest=4
    Battle=5
    Resources=6
    Shop=7
    Player=8
    HeroesCollection=9
    AnimasCollection=10
    HeroOrAnima=11
    ArenaHallCollection=12
    ClientAction=13
    Accessory=14
    Gear=15


class QuestAreaId(IntEnum):
    Unknown=0
    Campaign=1
    Dungeon=2
    Tower=3
    AsyncPvp=4
    FactionWars=5
    ClanBoss=6
    Events=7
    InfinityDungeon=8
    Experiment=40
    VFX=54
    GameDesign=56
    Coders=57
    Tools=58
    Misc=99


class FieldStatus(str,Enum):
    VERIFIED="VERIFIED"
    ABSENT="ABSENT"
    UNKNOWN="UNKNOWN"
    UNSUPPORTED="UNSUPPORTED"


T=TypeVar("T")


@dataclass(frozen=True,slots=True)
class EvidenceField(Generic[T]):
    status: FieldStatus
    value: T | None = None

    def __post_init__(self):
        if not isinstance(self.status,FieldStatus) or (
                (self.status==FieldStatus.VERIFIED)!=(self.value is not None)):
            raise ValueError("field value/status disagree")

    @classmethod
    def verified(cls,value):
        return cls(FieldStatus.VERIFIED,value)


UNKNOWN=EvidenceField(FieldStatus.UNKNOWN)


def _i32(value):
    return type(value) is int and -(1<<31)<=value<(1<<31)


def _int_field(field, *, nonnegative=False):
    if not isinstance(field,EvidenceField):
        raise ValueError("explicit field evidence required")
    if field.status==FieldStatus.VERIFIED and (
            not _i32(field.value) or (nonnegative and field.value<0)):
        raise ValueError("invalid verified Int32 field")


@dataclass(frozen=True,slots=True)
class CatalogBinding:
    game_build: str
    static_revision: str
    artifact_sha256: str

    def __post_init__(self):
        if (not isinstance(self.game_build,str) or not self.game_build.strip()
                or not isinstance(self.static_revision,str) or not self.static_revision.strip()
                or not isinstance(self.artifact_sha256,str)
                or not re.fullmatch(r"[0-9a-f]{64}",self.artifact_sha256)):
            raise ValueError("exact catalog build, revision and artifact SHA256 required")


@dataclass(frozen=True,slots=True)
class DefinitionOrigin:
    """Byte ranges supplied by a future validated table decoder, not a scanner."""
    binding: CatalogBinding
    main_chunk_sha256: str
    table_offset: int
    table_size: int
    record_offset: int
    record_size: int

    def __post_init__(self):
        if (not isinstance(self.binding,CatalogBinding)
                or not isinstance(self.main_chunk_sha256,str)
                or not re.fullmatch(r"[0-9a-f]{64}",self.main_chunk_sha256)
                or any(type(x) is not int for x in (self.table_offset,self.table_size,
                                                     self.record_offset,self.record_size))
                or not 0<=self.table_offset<=self.record_offset
                or min(self.table_size,self.record_size)<=0
                or self.record_offset+self.record_size>self.table_offset+self.table_size):
            raise ValueError("invalid definition provenance")


@dataclass(frozen=True,slots=True)
class QuestCondition:
    tag: int
    area_id: EvidenceField[int] = UNKNOWN
    region_id: EvidenceField[int] = UNKNOWN
    difficulty: EvidenceField[int] = UNKNOWN
    number: EvidenceField[int] = UNKNOWN

    def __post_init__(self):
        if not _i32(self.tag):
            raise ValueError("invalid condition tag")
        for value in (self.area_id,self.region_id,self.difficulty,self.number):
            _int_field(value)
            if self.tag!=QuestConditionTag.Battle and value.status==FieldStatus.VERIFIED:
                raise ValueError("battle-only condition field")


@dataclass(frozen=True,slots=True)
class ResourceReward:
    """Semantic component, not a claim about ImmutableResources wire format."""
    resource_id: int
    amount: int

    def __post_init__(self):
        if not _i32(self.resource_id) or type(self.amount) is not int or self.amount<0:
            raise ValueError("invalid reward component")


@dataclass(frozen=True,slots=True)
class RewardDescriptor:
    experience: EvidenceField[int] = UNKNOWN
    vip_points: EvidenceField[int] = UNKNOWN
    resources: EvidenceField[tuple[ResourceReward,...]] = UNKNOWN
    # Actual child serializers are not yet verified. Do not promote to VERIFIED.
    heroes: FieldStatus = FieldStatus.UNKNOWN
    animas: FieldStatus = FieldStatus.UNKNOWN
    relics: FieldStatus = FieldStatus.UNKNOWN
    accessories: FieldStatus = FieldStatus.UNKNOWN
    avatar_frames: FieldStatus = FieldStatus.UNKNOWN

    def __post_init__(self):
        _int_field(self.experience,nonnegative=True)
        _int_field(self.vip_points,nonnegative=True)
        if not isinstance(self.resources,EvidenceField):
            raise ValueError("explicit reward evidence required")
        if self.resources.status==FieldStatus.VERIFIED and (
                not isinstance(self.resources.value,tuple)
                or not all(isinstance(v,ResourceReward) for v in self.resources.value)
                or len({v.resource_id for v in self.resources.value})!=len(self.resources.value)):
            raise ValueError("invalid reward resource list")
        for status in (self.heroes,self.animas,self.relics,self.accessories,self.avatar_frames):
            if not isinstance(status,FieldStatus) or status==FieldStatus.VERIFIED:
                raise ValueError("unsupported reward child schema")


@dataclass(frozen=True,slots=True)
class QuestDefinition:
    prototype_id: int
    kind: QuestKind
    origin: DefinitionOrigin
    action_id: EvidenceField[int] = UNKNOWN
    required_amount: EvidenceField[int] = UNKNOWN
    group_or_page: EvidenceField[int] = UNKNOWN
    conditions: EvidenceField[tuple[QuestCondition,...]] = UNKNOWN
    reward: EvidenceField[RewardDescriptor] = UNKNOWN

    def __post_init__(self):
        if not _i32(self.prototype_id) or self.prototype_id<=0:
            raise ValueError("invalid prototype ID")
        if not isinstance(self.kind,QuestKind) or not isinstance(self.origin,DefinitionOrigin):
            raise ValueError("verified prototype kind and origin required")
        _int_field(self.action_id)
        _int_field(self.required_amount,nonnegative=True)
        _int_field(self.group_or_page)
        if not isinstance(self.conditions,EvidenceField) or not isinstance(self.reward,EvidenceField):
            raise ValueError("explicit condition/reward evidence required")
        if self.conditions.status==FieldStatus.VERIFIED and (
                not isinstance(self.conditions.value,tuple)
                or not all(isinstance(c,QuestCondition) for c in self.conditions.value)):
            raise ValueError("invalid condition list")
        if self.reward.status==FieldStatus.VERIFIED and not isinstance(self.reward.value,RewardDescriptor):
            raise ValueError("invalid reward descriptor")


class LookupStatus(str,Enum):
    FOUND="FOUND"
    CATALOG_UNAVAILABLE="CATALOG_UNAVAILABLE"
    BUILD_MISMATCH="BUILD_MISMATCH"
    REVISION_MISMATCH="REVISION_MISMATCH"
    ARTIFACT_MISMATCH="ARTIFACT_MISMATCH"
    UNKNOWN_PROTOTYPE="UNKNOWN_PROTOTYPE"
    UNSUPPORTED_OBJECTIVE="UNSUPPORTED_OBJECTIVE"
    UNVERIFIED_OBJECTIVE="UNVERIFIED_OBJECTIVE"


@dataclass(frozen=True,slots=True)
class LookupResult:
    status: LookupStatus
    definition: QuestDefinition | None = None


def _known_action(definition):
    if definition.action_id.status!=FieldStatus.VERIFIED:
        return None
    try:
        action=QuestActionId(definition.action_id.value)
        return action if action!=QuestActionId.Unknown else None
    except ValueError:
        return None


class QuestStaticCatalog:
    """Index only externally verified definitions. None means no decoded table.

    Invalid/duplicate records reject the entire construction. The empty
    production foundation should be created without definitions until 003.
    """
    def __init__(self,binding: CatalogBinding,definitions=None):
        if not isinstance(binding,CatalogBinding):
            raise ValueError("catalog binding required")
        records={}
        for record in (() if definitions is None else definitions):
            if not isinstance(record,QuestDefinition) or record.origin.binding!=binding:
                raise ValueError("record/catalog provenance mismatch")
            if record.prototype_id in records:
                raise ValueError("duplicate prototype ID")
            records[record.prototype_id]=record
        self._binding=binding
        self._available=definitions is not None
        self._records=MappingProxyType(records)

    @property
    def binding(self):
        return self._binding

    def resolve(self,prototype_id:int,*,game_build:str,static_revision:str,
                artifact_sha256=None) -> LookupResult:
        if game_build!=self.binding.game_build:
            return LookupResult(LookupStatus.BUILD_MISMATCH)
        if static_revision!=self.binding.static_revision:
            return LookupResult(LookupStatus.REVISION_MISMATCH)
        if artifact_sha256 is not None and artifact_sha256!=self.binding.artifact_sha256:
            return LookupResult(LookupStatus.ARTIFACT_MISMATCH)
        if not self._available:
            return LookupResult(LookupStatus.CATALOG_UNAVAILABLE)
        if not _i32(prototype_id) or prototype_id not in self._records:
            return LookupResult(LookupStatus.UNKNOWN_PROTOTYPE)
        record=self._records[prototype_id]
        if record.action_id.status==FieldStatus.UNSUPPORTED:
            return LookupResult(LookupStatus.UNSUPPORTED_OBJECTIVE)
        if record.action_id.status!=FieldStatus.VERIFIED:
            return LookupResult(LookupStatus.UNVERIFIED_OBJECTIVE)
        if _known_action(record) is None:
            return LookupResult(LookupStatus.UNSUPPORTED_OBJECTIVE)
        if record.required_amount.status!=FieldStatus.VERIFIED:
            return LookupResult(LookupStatus.UNVERIFIED_OBJECTIVE)
        return LookupResult(LookupStatus.FOUND,record)

    def lookup(self,prototype_id:int,*,game_build:str,static_revision:str) -> QuestDefinition | None:
        return self.resolve(prototype_id,game_build=game_build,
                            static_revision=static_revision).definition


class DomainHint(str,Enum):
    UNKNOWN="UNKNOWN"
    CAMPAIGN="CAMPAIGN"
    SPIRE="SPIRE"
    ARENA="ARENA"
    RELIC="RELIC"
    CLAN_BOSS="CLAN_BOSS"


def domain_hint(result: LookupResult) -> DomainHint:
    """Coarse non-executable hint, only after a successful catalog lookup.

    BattleFinish needs a positively identified Battle condition and explicit
    AreaId; group/page, prototype ranges and missing conditions never route.
    """
    record=result.definition
    if result.status!=LookupStatus.FOUND or record is None:
        return DomainHint.UNKNOWN
    action=_known_action(record)
    if (action is None or record.required_amount.status!=FieldStatus.VERIFIED
            or record.conditions.status!=FieldStatus.VERIFIED
            or any(c.tag not in QuestConditionTag._value2member_map_ for c in record.conditions.value)):
        return DomainHint.UNKNOWN
    if action==QuestActionId.RelicUpgrade:
        return DomainHint.RELIC
    if action in (QuestActionId.ArenaHallUpgrade,QuestActionId.ArenaPointsChange):
        return DomainHint.ARENA
    if action!=QuestActionId.BattleFinish:
        return DomainHint.UNKNOWN
    battle=[c for c in record.conditions.value if c.tag==QuestConditionTag.Battle]
    if len(battle)!=1 or battle[0].area_id.status!=FieldStatus.VERIFIED:
        return DomainHint.UNKNOWN
    return {QuestAreaId.Campaign:DomainHint.CAMPAIGN,
            QuestAreaId.Tower:DomainHint.SPIRE,
            QuestAreaId.AsyncPvp:DomainHint.ARENA,
            QuestAreaId.ClanBoss:DomainHint.CLAN_BOSS}.get(battle[0].area_id.value,DomainHint.UNKNOWN)
