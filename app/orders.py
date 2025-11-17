from __future__ import annotations

from collections import Counter
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class OrderBase(BaseModel):
    customer_name: str = Field(..., min_length=1)
    item: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)


class OrderCreate(OrderBase):
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, min_length=1)
    item: Optional[str] = Field(None, min_length=1)
    quantity: Optional[int] = Field(None, gt=0)
    notes: Optional[Optional[str]] = None
    status: Optional[OrderStatus] = None


class Order(OrderBase):
    id: UUID
    status: OrderStatus = OrderStatus.PENDING
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderReport(BaseModel):
    total: int
    statuses: Dict[OrderStatus, int]


router = APIRouter(prefix="/orders", tags=["orders"])
orders: Dict[UUID, Order] = {}


def _filter_orders(
    *, status: Optional[OrderStatus], created_from: Optional[datetime], created_to: Optional[datetime]
) -> List[Order]:
    result: List[Order] = list(orders.values())
    if status:
        result = [order for order in result if order.status == status]
    if created_from:
        result = [order for order in result if order.created_at >= created_from]
    if created_to:
        result = [order for order in result if order.created_at <= created_to]
    return sorted(result, key=lambda order: order.created_at, reverse=True)


@router.get("", response_model=List[Order])
def list_orders(
    status: Optional[OrderStatus] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
) -> List[Order]:
    return _filter_orders(status=status, created_from=created_from, created_to=created_to)


@router.post("", response_model=Order, status_code=201)
def create_order(order_input: OrderCreate) -> Order:
    now = datetime.utcnow()
    order = Order(id=uuid4(), created_at=now, updated_at=now, **order_input.model_dump())
    orders[order.id] = order
    return order


@router.put("/{order_id}", response_model=Order)
def update_order(order_id: UUID, updates: OrderUpdate) -> Order:
    existing = orders.get(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")

    data = existing.model_dump()
    for field, value in updates.model_dump(exclude_unset=True).items():
        data[field] = value

    data["updated_at"] = datetime.utcnow()
    updated_order = Order(**data)
    orders[order_id] = updated_order
    return updated_order


@router.post("/{order_id}/cancel", response_model=Order)
def cancel_order(order_id: UUID) -> Order:
    existing = orders.get(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    if existing.status == OrderStatus.CANCELLED:
        return existing
    updated_order = existing.model_copy(update={"status": OrderStatus.CANCELLED, "updated_at": datetime.utcnow()})
    orders[order_id] = updated_order
    return updated_order


@router.get("/report", response_model=OrderReport)
def orders_report(
    status: Optional[OrderStatus] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
) -> OrderReport:
    filtered_orders = _filter_orders(status=status, created_from=created_from, created_to=created_to)
    counts = Counter(order.status for order in filtered_orders)
    return OrderReport(total=len(filtered_orders), statuses=dict(counts))


