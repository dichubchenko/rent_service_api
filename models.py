from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid

# --- Pydantic Models (для API) ---

class OrderStatus(str, Enum):
    """Статусы заказа."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class CancelReason(str, Enum):
    """Причины отмены заказа."""
    ITEM_NOT_AVAILABLE = "item_not_available"
    ITEM_NOT_IN_LOCATION = "item_not_in_location"
    CLIENT_CANCELLED = "client_cancelled"

class OrderCreateRequest(BaseModel):
    """Тело запроса на создание заказа."""
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
    """Тело ответа после создания заказа."""
    id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int
    status: OrderStatus
    cancel_reason: Optional[CancelReason] = None  # Добавляем поле причины отмены
    cancel_details: Optional[str] = None  # Добавляем поле деталей отмены
    created_at: datetime
    updated_at: datetime  # Добавляем поле времени обновления

    model_config = ConfigDict(from_attributes=True)

class OrderDebugResponse(BaseModel):
    """Модель для отладочного вывода заказов."""
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

class CancelRequest(BaseModel):
    """Тело запроса на отмену заказа."""
    order_id: int
    reason: CancelReason
    details: Optional[str] = None

# Модель для Kafka сообщения
class RentalOrderMessage(BaseModel):
    """Сообщение для Kafka о новом заказе на аренду."""
    order_id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int
    timestamp: datetime

class SMSNotification(BaseModel):
    """Модель для отправки SMS уведомления."""
    client_id: int
    order_id: int
    message: str
    phone_number: str

class CancelReason(str, Enum):
    """Причины отмены заказа."""
    PAYMENT_FAILED = "payment_failed"
    ITEM_ALREADY_BOOKED = "item_already_booked"
    ITEM_WRONG_LOCATION = "item_wrong_location"
    PICKUP_DEADLINE_EXPIRED = "pickup_deadline_expired"
    CLIENT_CANCELLED = "client_cancelled"
    OTHER = "other"

class OrderCancelRequest(BaseModel):
    """Тело запроса на отмену заказа."""
    cancel_reason: CancelReason
    details: Optional[str] = Field(None, description="Дополнительная информация об отмене")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cancel_reason": "payment_failed",
                "details": "Недостаточно средств на карте"
            }
        }
    )

class OrderUpdateResponse(BaseModel):
    """Ответ при обновлении заказа."""
    order_id: int
    status: OrderStatus
    cancel_reason: Optional[CancelReason] = None
    message: str

    model_config = ConfigDict(from_attributes=True)

# Модель для Kafka сообщения об отмене
class OrderCancellationMessage(BaseModel):
    """Сообщение для Kafka об отмене заказа."""
    order_id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    cancel_reason: CancelReason
    cancel_details: Optional[str] = None
    timestamp: datetime
