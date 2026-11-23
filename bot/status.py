"""Order stages and the owner's actions, shared by the chat buttons and the dashboard.

    new → accepted → baking → decorating → ready → on_way → delivered
                                                   (pickup orders skip on_way)
    rejected: from any stage before ready

The owner may skip the optional middle stages (baking, decorating) and go straight
to ready."""

from __future__ import annotations

FLOW = ["new", "accepted", "baking", "decorating", "ready", "on_way", "delivered"]
ACTIVE = ("new", "accepted", "baking", "decorating", "ready", "on_way")
EMOJI = {"new": "🆕", "accepted": "✅", "baking": "👩‍🍳", "decorating": "🎨", "ready": "🎂",
         "on_way": "🚚", "delivered": "📦", "rejected": "❌"}

# action -> (new status, statuses it may come from)
ACTIONS = {
    "acc": ("accepted", ("new",)),
    "bak": ("baking", ("accepted",)),
    "dec": ("decorating", ("accepted", "baking")),
    "rdy": ("ready", ("accepted", "baking", "decorating")),
    "way": ("on_way", ("ready",)),
    "dlv": ("delivered", ("ready", "on_way")),
    "rej": ("rejected", ("new", "accepted", "baking", "decorating")),
}


def steps(order: dict) -> list[str]:
    """The stages this order goes through (pickup has no 'on the way')."""
    return [s for s in FLOW if not (s == "on_way" and order["method"] == "pickup")]


def next_actions(order: dict) -> list[str]:
    """Buttons to offer the owner, most likely first."""
    st, delivery = order["status"], order["method"] == "delivery"
    return {
        "new": ["acc", "rej"],
        "accepted": ["bak", "rdy", "rej"],
        "baking": ["dec", "rdy"],
        "decorating": ["rdy"],
        "ready": ["way", "dlv"] if delivery else ["dlv"],
        "on_way": ["dlv"],
    }.get(st, [])


def allowed(order: dict, action: str) -> bool:
    if action not in ACTIONS:
        return False
    if action == "way" and order["method"] != "delivery":
        return False
    return order["status"] in ACTIONS[action][1]
