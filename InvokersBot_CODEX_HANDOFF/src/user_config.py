"""Persistent user choices. This schema cannot authorize live or premium actions."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import tempfile
from typing import Any


class ConfigError(ValueError):
    pass


def default_game_root() -> str:
    return str(Path(os.environ.get('USERPROFILE', str(Path.home()))) / 'AppData/LocalLow/Hit_Zone/Invokers')


def default_config_path() -> Path:
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.config')))
    return base / 'InvokersBot' / 'user_config.json'


def integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ConfigError(f'{name}: Ganzzahl ab {minimum} erforderlich')
    return value


@dataclass
class ModuleConfig:
    automation: bool = False
    quests: bool = True
    campaign: bool = True
    arena: bool = True
    invokers: bool = True
    bosses: bool = True
    events: bool = True
    relics: bool = True

    def validate(self):
        for name, value in asdict(self).items():
            if type(value) is not bool:
                raise ConfigError(f'Module {name}: true oder false erforderlich')
        return self


@dataclass
class UserConfig:
    schema_version: int = 1
    arena_combat_power: int | None = None
    modules: ModuleConfig = field(default_factory=ModuleConfig)
    game_root: str = field(default_factory=default_game_root)
    static_path: str | None = None
    main_six_ids: list[int] = field(default_factory=list)
    resource_reserves: dict[str, int] = field(default_factory=lambda: {
        'Energy': 0, 'Gold': 0, 'Memorium': 0, 'Arena_Token': 0, 'SI_WildStar': 0,
    })
    main_team_interval_seconds: int = 900

    @property
    def mode(self) -> str:
        return 'DRY_RUN'

    @property
    def actor_enabled(self) -> bool:
        return False

    def module_enabled(self, name: str, require_automation: bool = False) -> bool:
        if name not in ModuleConfig.__dataclass_fields__:
            raise ConfigError(f'Unbekanntes Modul: {name}')
        return bool(getattr(self.modules, name) and (not require_automation or self.modules.automation))

    def validate(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ConfigError('Nicht unterstützte UserConfig-Version')
        if self.arena_combat_power is not None:
            integer(self.arena_combat_power, 'Arena-Kampfkraft', 1)
        if not isinstance(self.modules, ModuleConfig):
            raise ConfigError('modules muss ModuleConfig sein')
        self.modules.validate()
        if not isinstance(self.game_root, str) or not self.game_root.strip():
            raise ConfigError('Spielverzeichnis darf nicht leer sein')
        if self.static_path is not None and (not isinstance(self.static_path, str) or not self.static_path.strip()):
            raise ConfigError('static_path muss ein Pfad oder null sein')
        if not isinstance(self.main_six_ids, list) or len(self.main_six_ids) not in (0, 6):
            raise ConfigError('Main Six: leer lassen oder genau sechs UI-Inventar-IDs angeben')
        for value in self.main_six_ids:
            integer(value, 'Main-Six-ID', 1)
        if len(set(self.main_six_ids)) != len(self.main_six_ids):
            raise ConfigError('Main-Six-IDs müssen eindeutig sein')
        if not isinstance(self.resource_reserves, dict):
            raise ConfigError('Ressourcenreserven müssen ein Objekt sein')
        for name, value in self.resource_reserves.items():
            if not isinstance(name, str) or not name.strip():
                raise ConfigError('Ungültiger Ressourcenname')
            integer(value, f'Reserve {name}')
        integer(self.main_team_interval_seconds, 'Main-Six-Intervall', 1)
        return self

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'UserConfig':
        if not isinstance(data, dict):
            raise ConfigError('UserConfig muss ein JSON-Objekt sein')
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ConfigError('Unbekannte/gesperrte Einstellung: ' + ', '.join(sorted(unknown)))
        data = dict(data)
        modules = data.get('modules', {})
        if not isinstance(modules, dict):
            raise ConfigError('modules muss ein JSON-Objekt sein')
        unknown_modules = set(modules) - set(ModuleConfig.__dataclass_fields__)
        if unknown_modules:
            raise ConfigError('Unbekannte Module: ' + ', '.join(sorted(unknown_modules)))
        data['modules'] = ModuleConfig(**modules)
        return cls(**data).validate()

    @classmethod
    def load(cls, path: Path | str | None = None) -> 'UserConfig':
        path = Path(path) if path is not None else default_config_path()
        if not path.exists():
            return cls().validate()
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ConfigError(f'Konfiguration kann nicht gelesen werden: {error}') from error
        return cls.from_dict(data)

    def save(self, path: Path | str | None = None):
        path = Path(path) if path is not None else default_config_path()
        content = json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + '\n'
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix=path.name + '.', suffix='.tmp',
                                             encoding='utf-8', delete=False) as output:
                temporary = Path(output.name)
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path
