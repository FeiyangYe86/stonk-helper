from stonk_helper.clock import utcnow
from stonk_helper.events.store import EventStore
from stonk_helper.events.types import OrderFilled, OrderPlaced, RiskBreached


def test_append_assigns_monotonic_ids(event_store: EventStore) -> None:
    e1 = OrderPlaced(
        order_id="o1", symbol="AAPL", side="BUY", quantity=10, order_type="MKT", aggregate="o1"
    )
    e2 = OrderPlaced(
        order_id="o2", symbol="MSFT", side="BUY", quantity=5, order_type="MKT", aggregate="o2"
    )
    assert event_store.append(e1) == 1
    assert event_store.append(e2) == 2
    assert event_store.count() == 2


def test_replay_returns_events_in_order(event_store: EventStore) -> None:
    event_store.append(
        OrderPlaced(order_id="o1", symbol="AAPL", side="BUY", quantity=10, order_type="MKT")
    )
    event_store.append(
        OrderFilled(
            order_id="o1",
            fill_id="f1",
            symbol="AAPL",
            side="BUY",
            quantity=10,
            price_usd=180.5,
            commission_usd=1.0,
            executed_at=utcnow(),
        )
    )
    events = list(event_store.replay())
    assert [e["event_type"] for e in events] == ["order_placed", "order_filled"]
    assert events[1]["payload"]["price_usd"] == 180.5


def test_replay_filter_by_type(event_store: EventStore) -> None:
    event_store.append(
        OrderPlaced(order_id="o1", symbol="AAPL", side="BUY", quantity=10, order_type="MKT")
    )
    event_store.append(RiskBreached(rule="max_position", detail="exceeded 5% cap", order_id="o2"))
    placed = list(event_store.replay(event_type="order_placed"))
    breaches = list(event_store.replay(event_type="risk_breached"))
    assert len(placed) == 1
    assert len(breaches) == 1
    assert breaches[0]["payload"]["rule"] == "max_position"


def test_replay_typed_reconstructs_pydantic_models(event_store: EventStore) -> None:
    event_store.append(
        OrderPlaced(order_id="o1", symbol="AAPL", side="BUY", quantity=10, order_type="MKT")
    )
    [typed] = list(event_store.replay_typed())
    assert isinstance(typed, OrderPlaced)
    assert typed.symbol == "AAPL"
    assert typed.side == "BUY"
