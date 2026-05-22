from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

RunMode = Literal["paper", "shadow", "live"]


class Paths(BaseModel):
    data_dir: Path
    event_store: Path
    ledger: Path
    bars_dir: Path
    logs_dir: Path


class BrokerCfg(BaseModel):
    host: str = "127.0.0.1"
    port: int = 4002
    client_id: int = 1
    account: str = ""


class LoggingCfg(BaseModel):
    level: str = "INFO"
    format: Literal["json", "console"] = "json"


class TimeCfg(BaseModel):
    display_tz: str = "Australia/Sydney"
    market_tz: str = "America/New_York"


class Config(BaseModel):
    run_mode: RunMode = Field(default="paper")
    paths: Paths
    broker: BrokerCfg = BrokerCfg()
    logging: LoggingCfg = LoggingCfg()
    time: TimeCfg = TimeCfg()


def load_config(path: Path | str = "config/default.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    cfg = Config.model_validate(raw)
    for p in (cfg.paths.data_dir, cfg.paths.bars_dir, cfg.paths.logs_dir):
        p.mkdir(parents=True, exist_ok=True)
    return cfg
