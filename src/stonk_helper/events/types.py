from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from ..clock import utcnow


class EventBase(BaseModel):
    occurred_at: datetime = Field(default_factory=utcnow)
    aggregate: str | None = None
    correlation_id: str | None = None


class RunModeChanged(EventBase):
    event_type: Literal["run_mode_changed"] = "run_mode_changed"
    event_version: Literal[1] = 1
    from_mode: str
    to_mode: str
    actor: str


class OrderPlaced(EventBase):
    event_type: Literal["order_placed"] = "order_placed"
    event_version: Literal[1] = 1
    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    order_type: str
    limit_price: float | None = None
    strategy: str | None = None


class OrderFilled(EventBase):
    event_type: Literal["order_filled"] = "order_filled"
    event_version: Literal[1] = 1
    order_id: str
    fill_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    price_usd: float
    commission_usd: float
    executed_at: datetime


class RiskBreached(EventBase):
    event_type: Literal["risk_breached"] = "risk_breached"
    event_version: Literal[1] = 1
    rule: str
    detail: str
    order_id: str | None = None


Event = Annotated[
    RunModeChanged | OrderPlaced | OrderFilled | RiskBreached,
    Field(discriminator="event_type"),
]

EventAdapter: TypeAdapter[Event] = TypeAdapter(Event)
