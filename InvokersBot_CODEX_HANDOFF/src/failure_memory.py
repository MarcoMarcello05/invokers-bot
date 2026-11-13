"""Persistent verified-outcome memory and conservative campaign retry evidence."""
from copy import deepcopy
import json
import math
from pathlib import Path
import time

from bot_actions import hero_values, section_value


class FailureMemoryError(ValueError):
    pass


def _target_key(target):
    return json.dumps(target, sort_keys=True, separators=(',', ':'))


def account_improvement_signature(state, main_team_ids):
    """Only verified configured team levels/ranks and equipped relic upgrades count.

    Merely changing gear identity does not prove an improvement without the relic
    value model. Gold, XP-only gains, screenshots and manual Arena power are not
    campaign improvement signals.
    """
    if len(main_team_ids) != 6 or len(set(main_team_ids)) != 6:
        return None
    heroes = hero_values(state)
    if heroes is None:
        return None
    by_id = {h.get('inventory_id'): h for h in heroes}
    levels = {}
    for inventory_id in main_team_ids:
        hero = by_id.get(inventory_id)
        if not hero or type(hero.get('level')) is not int or type(hero.get('rank')) is not int:
            return None
        levels[str(inventory_id)] = {'level': hero['level'], 'rank': hero['rank']}
    relics = section_value(state, 'relics')
    equipment = {}
    if relics is not None:
        for relic in relics:
            if relic.get('equipped_hero_id') in main_team_ids:
                equipment[str(relic['inventory_id'])] = {
                    'hero_id': relic['equipped_hero_id'], 'level': relic.get('level'),
                    'rank': relic.get('rank')}
    return {'team_ids': list(main_team_ids), 'heroes': levels,
            'equipment': equipment, 'equipment_known': relics is not None}


def relevant_improvements(before, after):
    if before is None or after is None or before.get('team_ids') != after.get('team_ids'):
        return []
    if not before.get('equipment_known') or not after.get('equipment_known'):
        return []
    improvements = []
    for inventory_id, old in before.get('heroes', {}).items():
        new = after.get('heroes', {}).get(inventory_id, {})
        for field in ('level', 'rank'):
            if type(old.get(field)) is not int or type(new.get(field)) is not int or new[field] < old[field]:
                return []
            if new[field] > old[field]:
                improvements.append(f'Hero {inventory_id} {field}: {old[field]} -> {new[field]}')
    if before.get('equipment_known') and after.get('equipment_known'):
        for inventory_id, old in before.get('equipment', {}).items():
            new = after.get('equipment', {}).get(inventory_id, {})
            if old.get('hero_id') != new.get('hero_id'):
                return []
            for field in ('level', 'rank'):
                if type(old.get(field)) is not int or type(new.get(field)) is not int or new[field] < old[field]:
                    return []
                if new[field] > old[field]:
                    improvements.append(f'Equipped relic {inventory_id} {field}: {old[field]} -> {new[field]}')
    return improvements


class FailureMemory:
    def __init__(self, path=None, *, cooldown_seconds=300, max_failures=2):
        self.path = Path(path) if path is not None else None
        self.cooldown_seconds, self.max_failures = cooldown_seconds, max_failures
        self.data = {'schema_version': 1, 'failures': {}, 'campaign_defeats': {},
                     'successes': {}, 'last_development_at': None}
        if self.path is not None and self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data, dict):
                    raise FailureMemoryError('Failure memory must be an object')
                # An empty legacy memory is safely migratable; populated unknown
                # schemas must not silently forget failures or cooldowns.
                if 'schema_version' not in data and not data.get('failures') and not data.get('last_failed_campaign'):
                    data = deepcopy(self.data)
                self._validate(data)
                self.data = data
            except (OSError, ValueError, TypeError, KeyError) as error:
                raise FailureMemoryError('Unreadable/invalid failure memory; original file preserved: ' + str(error)) from error

    @staticmethod
    def _validate(data):
        if data.get('schema_version') != 1:
            raise FailureMemoryError('Unsupported failure memory version')
        for key in ('failures', 'campaign_defeats', 'successes'):
            if not isinstance(data.get(key), dict):
                raise FailureMemoryError('Invalid failure memory field ' + key)
        for record in data['failures'].values():
            if not isinstance(record, dict) or type(record.get('count')) is not int or record['count'] < 0:
                raise FailureMemoryError('Invalid failure count')
            if not isinstance(record.get('cooldown_until'), (float, int)) or not math.isfinite(record['cooldown_until']):
                raise FailureMemoryError('Invalid cooldown timestamp')
        for value in data['successes'].values():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise FailureMemoryError('Invalid success timestamp')
        for record in data['campaign_defeats'].values():
            if not isinstance(record, dict) or 'baseline' not in record or not isinstance(record.get('target'), dict):
                raise FailureMemoryError('Invalid campaign defeat')
            baseline = record['baseline']
            if baseline is not None:
                if not isinstance(baseline, dict) or not isinstance(baseline.get('heroes'), dict) or not isinstance(baseline.get('equipment'), dict):
                    raise FailureMemoryError('Invalid campaign improvement baseline')
                ids = baseline.get('team_ids')
                if not isinstance(ids, list) or len(ids) != 6 or len(set(ids)) != 6 or any(type(i) is not int or i <= 0 for i in ids):
                    raise FailureMemoryError('Invalid baseline team identity')
                if any(not isinstance(h, dict) or type(h.get('level')) is not int or type(h.get('rank')) is not int for h in baseline['heroes'].values()):
                    raise FailureMemoryError('Invalid baseline hero progression')
        development = data.get('last_development_at')
        if development is not None and (not isinstance(development, (int, float)) or not math.isfinite(development)):
            raise FailureMemoryError('Invalid development timestamp')

    def save(self):
        self._validate(self.data)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + '.tmp')
            temporary.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            temporary.replace(self.path)

    @property
    def last_development_at(self):
        return self.data['last_development_at']

    def last_success_at(self, kind):
        return self.data['successes'].get(kind)

    def blocked(self, action, now=None):
        record = self.data['failures'].get(action.key)
        return bool(record and record['count'] >= self.max_failures and (time.time() if now is None else now) < record['cooldown_until'])

    def record_failure(self, action, reason, now=None):
        now = time.time() if now is None else now
        previous = self.data['failures'].get(action.key, {})
        self.data['failures'][action.key] = {'count': previous.get('count', 0) + 1,
                                            'last_at': now, 'cooldown_until': now + self.cooldown_seconds,
                                            'reason': str(reason)}
        self.save()

    def record_success(self, action, now=None):
        now = time.time() if now is None else now
        self.data['failures'].pop(action.key, None)
        self.data['successes'][action.kind] = now
        if action.preconditions.get('quest_group') == 'Monthly':
            self.data['successes']['MONTHLY_REVIEW'] = now
        if action.kind in ('HERO_LEVEL', 'HERO_AWAKE', 'HERO_ASCEND'):
            self.data['last_development_at'] = now
        self.save()

    def has_campaign_defeat(self, target):
        return _target_key(target) in self.data['campaign_defeats']

    def record_campaign_defeat(self, target, state, main_team_ids, now=None):
        self.data['campaign_defeats'][_target_key(target)] = {
            'target': deepcopy(target), 'at': time.time() if now is None else now,
            'baseline': account_improvement_signature(state, main_team_ids)}
        self.save()

    def campaign_can_retry(self, target, state, main_team_ids, now=None):
        del now  # Time alone never clears a campaign defeat.
        record = self.data['campaign_defeats'].get(_target_key(target))
        return record is None or bool(relevant_improvements(record['baseline'], account_improvement_signature(state, main_team_ids)))

    def campaign_retry_reason(self, target, state, main_team_ids):
        record = self.data['campaign_defeats'].get(_target_key(target))
        if record is None:
            return 'No recorded defeat for this exact campaign target'
        current = account_improvement_signature(state, main_team_ids)
        if record['baseline'] is None or current is None:
            return 'Configured Main Six improvement baseline is unknown'
        improvements = relevant_improvements(record['baseline'], current)
        return '; '.join(improvements) if improvements else 'No relevant Main Six or equipped-relic improvement since defeat'

    def clear_campaign_defeat_after_verified_win(self, target):
        self.data['campaign_defeats'].pop(_target_key(target), None)
        self.save()
