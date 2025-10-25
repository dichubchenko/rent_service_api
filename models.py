from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum

# --- Pydantic Models (для API) ---

class OrderStatus(str, Enum):
    """Статусы заказа."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class OrderCreateRequest(BaseModel):
    """Тело запроса на создание заказа."""
    client_id: int = Field(..., description="ID клиента", ge=1)
    item_id: int = Field(..., description="ID арендуемой вещи", ge=1)
    pickup_point_id: int = Field(..., description="ID постомата для получения", ge=1)
    rental_duration_hours: int = Field(..., description="Продолжительность аренды в часах", ge=1, le=720)  # макс 30 дней

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Модель для Kafka сообщения
class RentalOrderMessage(BaseModel):
    """Сообщение для Kafka о новом заказе на аренду."""
    order_id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int
    timestamp: datetime
