from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    TOKENS = "tokens"
    COMPUTE = "compute"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"


@dataclass
class Resource:
    resource_type: ResourceType
    total_supply: float = 100.0
    allocated: float = 0.0
    price: float = 1.0
    price_elasticity: float = 0.1

    @property
    def available(self) -> float:
        return max(0.0, self.total_supply - self.allocated)

    @property
    def scarcity(self) -> float:
        return 1.0 - self.available / self.total_supply if self.total_supply > 0 else 0.0

    def update_price(self) -> None:
        target = 1.0 + self.scarcity * 5.0
        self.price += self.price_elasticity * (target - self.price)
        self.price = max(0.01, self.price)

    def allocate(self, amount: float) -> bool:
        if amount <= self.available:
            self.allocated += amount
            self.update_price()
            return True
        return False

    def release(self, amount: float) -> None:
        self.allocated = max(0.0, self.allocated - amount)
        self.update_price()


@dataclass
class Bid:
    bidder: str
    resource_type: ResourceType
    amount: float
    max_price: float
    priority: float = 0.5
    timestamp: float = field(default_factory=time.time)

    @property
    def total_cost(self) -> float:
        return self.amount * self.max_price


@dataclass
class Allocation:
    bidder: str
    resource_type: ResourceType
    amount: float
    price_paid: float
    success: bool = True


class ResourceMarket:
    """内部资源市场: 竞价分配有限资源。"""

    def __init__(self):
        self._resources: dict[ResourceType, Resource] = {}
        for rt in ResourceType:
            self._resources[rt] = Resource(resource_type=rt)
        self._bids: list[Bid] = []
        self._allocations: list[Allocation] = []
        self._budgets: dict[str, float] = {}

    def set_budget(self, bidder: str, budget: float) -> None:
        self._budgets[bidder] = budget

    def set_supply(self, resource_type: ResourceType, supply: float) -> None:
        self._resources[resource_type].total_supply = supply

    def submit_bid(self, bid: Bid) -> Allocation:
        resource = self._resources.get(bid.resource_type)
        if resource is None:
            return Allocation(bid.bidder, bid.resource_type, 0, 0, success=False)
        budget = self._budgets.get(bid.bidder, float("inf"))
        cost = bid.amount * resource.price
        if cost > budget:
            affordable = budget / resource.price if resource.price > 0 else 0
            if affordable <= 0:
                return Allocation(bid.bidder, bid.resource_type, 0, 0, success=False)
            cost = affordable * resource.price
            amount = affordable
        else:
            amount = bid.amount
        if resource.price > bid.max_price:
            return Allocation(bid.bidder, bid.resource_type, 0, 0, success=False)
        if resource.allocate(amount):
            self._budgets[bid.bidder] = self._budgets.get(bid.bidder, float("inf")) - cost
            alloc = Allocation(bid.bidder, bid.resource_type, amount, resource.price, success=True)
            self._allocations.append(alloc)
            self._bids.append(bid)
            return alloc
        return Allocation(bid.bidder, bid.resource_type, 0, 0, success=False)

    def release(self, bidder: str, resource_type: ResourceType, amount: float) -> None:
        self._resources[resource_type].release(amount)

    def get_price(self, resource_type: ResourceType) -> float:
        return self._resources[resource_type].price

    def get_market_status(self) -> dict[str, Any]:
        status = {}
        for rt, res in self._resources.items():
            status[rt.value] = {
                "available": res.available,
                "total": res.total_supply,
                "price": res.price,
                "scarcity": res.scarcity,
            }
        return status

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_bids": len(self._bids),
            "total_allocations": len(self._allocations),
            "successful_allocations": sum(1 for a in self._allocations if a.success),
            "market_status": self.get_market_status(),
        }
