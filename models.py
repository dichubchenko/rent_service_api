from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid

class OrderStatus(str, Enum):
    #Определяет статусы заказа
    NEW = "new"  # Заказ создан, проверки не проводились
    AWAITING_PAYMENT = "awaiting_payment"  # Проверки пройдены, ожидаем оплату
    AWAITING_RECEIPT = "awaiting_receipt"  # Оплата прошла, ожидаем выдачу
    AWAITING_RETURN = "awaiting_return"  # Вещь выдана, ожидаем возврат
    CANCELLED = "cancelled"  # Заказ отменен
    RETURNED = "returned"  # Заказ завершен (вещь возвращена)

class CancelReason(str, Enum):
    #Причины отмены заказа
    PAYMENT_FAILED = "payment_failed"
    ITEM_NOT_AVAILABLE = "item_not_available"
    ITEM_NOT_FOUND = "item_not_found"
    ITEM_NOT_IN_LOCATION = "item_not_in_location"
    PICKUP_DEADLINE_EXPIRED = "pickup_deadline_expired"
    CLIENT_CANCELLED = "client_cancelled"
    OTHER = "other"

class Order(BaseModel):
    #модель данных о заказе

    id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int
    status: OrderStatus
    cancel_reason: Optional[CancelReason] = None
    cancel_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Client(BaseModel):
    #модель данных о клиенте

    id: int
    name: str
    phone: str
    email: str

    model_config = ConfigDict(from_attributes=True)

class Item(BaseModel):
    #модель данных о вещи

    id: int
    desc: str
    hourly_price: int
    is_available_now: bool
    current_pickup_point_id: int
    reserved_until: Optional[datetime] = Field(default=None)

    model_config = ConfigDict(from_attributes=True)

class Ppoint(BaseModel):

    #модель данных о постомате

    id: int
    address: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)



class OrderCreateRequest(BaseModel):
    #запрос на создание заказа
    client_id: int = Field(..., description="ID клиента", ge=1)
    item_id: int = Field(..., description="ID арендуемой вещи", ge=1)
    pickup_point_id: int = Field(..., description="ID постомата для получения", ge=1)
    rental_duration_hours: int = Field(..., description="Продолжительность аренды в часах", ge=1, le=720)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": 123,
                "item_id": 456,
                "pickup_point_id": 789,
                "rental_duration_hours": 48
            }
        }
    )

class OrderResponse(BaseModel):
    #ответ метода /api/new_order
    id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int
    status: OrderStatus
    cancel_reason: Optional[CancelReason] = None
    cancel_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Модель данных для заглушки отправки в Kafka
class RentalOrderMessage(BaseModel):
    #Сообщение для Kafka о новом заказе на аренду
    order_id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int
    status: OrderStatus
    timestamp: datetime
