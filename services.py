import asyncio
from datetime import datetime, timedelta
from models import OrderStatus, OrderResponse, OrderCreateRequest, RentalOrderMessage, SMSNotification, CancelReason
from typing import Optional, Dict, List
import json

# --- In-Memory "База данных" (заглушка) ---

# Генератор ID заказов
class OrderIdGenerator:
    def __init__(self):
        self.counter = 1000  # Начинаем с 1000 для наглядности
    
    def generate_id(self) -> int:
        order_id = self.counter
        self.counter += 1
        return order_id

order_id_generator = OrderIdGenerator()

# Заглушка "таблицы" заказов
orders_db: List[OrderResponse] = []

# Заглушка "таблицы" вещей
items_db = {
    456: {
        "id": 456, 
        "name": "Дрель Makita", 
        "hourly_price": 50, 
        "is_available": True, 
        "current_pickup_point_id": 789,
        "reserved_until": None  # Время, до которого вещь забронирована
    },
    457: {
        "id": 457, 
        "name": "Шуруповерт Bosch", 
        "hourly_price": 60, 
        "is_available": False,  # Уже забронирована
        "current_pickup_point_id": 789,
        "reserved_until": datetime(2025, 12, 20, 18, 0, 0)
    },
    458: {
        "id": 458, 
        "name": "Пауэрбанк Xiaomi", 
        "hourly_price": 20, 
        "is_available": True, 
        "current_pickup_point_id": 123,  # Находится в другом постомате
        "reserved_until": None
    }
}

# Заглушка "таблицы" клиентов
clients_db = {
    123: {
        "id": 123, 
        "name": "Иван Иванов", 
        "phone": "+79161234567", 
        "email": "ivan@mail.ru"
    },
    124: {
        "id": 124, 
        "name": "Петр Петров", 
        "phone": "+79167654321", 
        "email": "petr@mail.ru"
    }
}

# Заглушка "таблицы" постоматов
pickup_points_db = {
    789: {
        "id": 789, 
        "address": "ул. Ленина, д. 1", 
        "working_hours": "круглосуточно",
        "is_active": True
    },
    123: {
        "id": 123, 
        "address": "пр. Мира, д. 15", 
        "working_hours": "08:00-22:00",
        "is_active": True
    }
}

# --- Исключения ---

class DatabaseError(Exception):
    """Исключение для ошибок БД."""
    pass

class ItemNotAvailableError(Exception):
    """Исключение, если вещь недоступна."""
    pass

class ItemNotInLocationError(Exception):
    """Исключение, если вещь не в указанном постомате."""
    pass

class ClientNotFoundError(Exception):
    """Исключение, если клиент не найден."""
    pass

class PickupPointNotFoundError(Exception):
    """Исключение, если постомат не найден."""
    pass

# --- Бизнес-логика ---

async def check_item_availability(item_id: int, pickup_point_id: int) -> bool:
    """
    Проверяет возможность выдачи вещи:
    - Существует ли вещь
    - Находится ли она в указанном постомате
    - Не забронирована ли она другим заказом
    """
    print(f"[Проверка доступности] Проверяем вещь {item_id} в постомате {pickup_point_id}")
    
    # Проверяем существование вещи
    if item_id not in items_db:
        raise ItemNotAvailableError(f"Вещь с ID {item_id} не найдена")
    
    item = items_db[item_id]
    
    # Проверяем, что вещь в нужном постомате
    if item["current_pickup_point_id"] != pickup_point_id:
        raise ItemNotInLocationError(
            f"Вещь {item_id} находится в постомате {item['current_pickup_point_id']}, а не в {pickup_point_id}"
        )
    
    # Проверяем доступность вещи
    if not item["is_available"]:
        raise ItemNotAvailableError(f"Вещь {item_id} уже забронирована")
    
    # Проверяем, не истекло ли время бронирования
    if item["reserved_until"] and item["reserved_until"] < datetime.now():
        # Если время брони истекло, освобождаем вещь
        item["is_available"] = True
        item["reserved_until"] = None
    
    return item["is_available"]

async def create_order_in_db(order_data: OrderCreateRequest) -> OrderResponse:
    """
    Создает заказ в БД и резервирует вещь.
    """
    print(f"[Создание заказа] Сохраняем заказ в БД: {order_data}")
    
    # Генерируем ID заказа
    order_id = order_id_generator.generate_id()
    
    # Создаем заказ
    new_order = OrderResponse(
        id=order_id,
        status=OrderStatus.PENDING,
        created_at=datetime.now(),
        **order_data.model_dump()
    )
    
    # Сохраняем заказ
    orders_db.append(new_order)
    
    # Резервируем вещь
    items_db[order_data.item_id]["is_available"] = False
    items_db[order_data.item_id]["reserved_until"] = datetime.now() + timedelta(
        hours=order_data.rental_duration_hours + 1  # +1 час на оформление
    )
    
    print(f"[Создание заказа] Заказ {order_id} создан, вещь {order_data.item_id} забронирована")
    return new_order

# --- Внешние сервисы (заглушки) ---

async def send_to_kafka(message: RentalOrderMessage):
    """
    Заглушка для отправки сообщения в Kafka.
    В реальности здесь был бы вызов kafka-python или аналогичной библиотеки.
    """
    print(f"\n🎫 [KAFKA] Отправка сообщения в топик 'rental-orders':")
    print(f"   Order ID: {message.order_id}")
    print(f"   Client ID: {message.client_id}") 
    print(f"   Item ID: {message.item_id}")
    print(f"   Pickup Point: {message.pickup_point_id}")
    print(f"   Duration: {message.rental_duration_hours} часов")
    print(f"   Timestamp: {message.timestamp}")
    
    # Имитация отправки в Kafka
    await asyncio.sleep(0.5)
    print(f"✅ [KAFKA] Сообщение для заказа {message.order_id} успешно отправлено\n")

async def cancel_order_in_db(order_id: int, cancel_reason: CancelReason, cancel_details: Optional[str] = None) -> OrderResponse:
    """
    Отменяет заказ в БД и освобождает вещь.
    """
    print(f"[Отмена заказа] Ищем заказ {order_id} для отмены по причине: {cancel_reason}")
    
    # Ищем заказ
    order_to_cancel = None
    for order in orders_db:
        if order.id == order_id:
            order_to_cancel = order
            break
    
    if not order_to_cancel:
        raise DatabaseError(f"Заказ с ID {order_id} не найден")
    
    # Проверяем, что заказ еще не отменен
    if order_to_cancel.status == OrderStatus.CANCELLED:
        raise DatabaseError(f"Заказ {order_id} уже отменен")
    
    # Обновляем статус заказа
    order_to_cancel.status = OrderStatus.CANCELLED
    
    # Освобождаем вещь
    if order_to_cancel.item_id in items_db:
        items_db[order_to_cancel.item_id]["is_available"] = True
        items_db[order_to_cancel.item_id]["reserved_until"] = None
        print(f"[Отмена заказа] Вещь {order_to_cancel.item_id} освобождена")
    
    print(f"[Отмена заказа] Заказ {order_id} отменен по причине: {cancel_reason}")
    return order_to_cancel

async def send_cancellation_to_kafka(message: OrderCancellationMessage):
    """
    Заглушка для отправки сообщения об отмене в Kafka.
    """
    print(f"\n🎫 [KAFKA CANCELLATION] Отправка сообщения об отмене в топик 'order-cancellations':")
    print(f"   Order ID: {message.order_id}")
    print(f"   Client ID: {message.client_id}") 
    print(f"   Item ID: {message.item_id}")
    print(f"   Pickup Point: {message.pickup_point_id}")
    print(f"   Cancel Reason: {message.cancel_reason}")
    print(f"   Cancel Details: {message.cancel_details}")
    print(f"   Timestamp: {message.timestamp}")
    
    # Имитация отправки в Kafka
    await asyncio.sleep(0.5)
    print(f"✅ [KAFKA CANCELLATION] Сообщение об отмене заказа {message.order_id} успешно отправлено\n")

# Также обновим функцию send_sms_cancellation для поддержки разных причин
async def send_sms_cancellation(client_id: int, order_id: int, reason: CancelReason, details: Optional[str] = None):
    """
    Заглушка для синхронного запроса в сервис отправки SMS.
    """
    print(f"\n📱 [SMS SERVICE] Отправка SMS об отмене заказа:")
    print(f"   Client ID: {client_id}")
    print(f"   Order ID: {order_id}")
    print(f"   Reason: {reason}")
    print(f"   Details: {details}")
    
    # Получаем данные клиента для SMS
    client = clients_db.get(client_id)
    if client:
        phone_number = client["phone"]
        
        # Формируем сообщение в зависимости от причины
        reason_messages = {
            CancelReason.PAYMENT_FAILED: "неуспешного списания средств",
            CancelReason.ITEM_ALREADY_BOOKED: "невозможности выдать вещь (уже забронирована)",
            CancelReason.ITEM_WRONG_LOCATION: "невозможности выдать вещь (не в этом постомате)", 
            CancelReason.PICKUP_DEADLINE_EXPIRED: "просроченного дедлайна по выдаче вещи",
            CancelReason.CLIENT_CANCELLED: "отмены клиентом",
            CancelReason.OTHER: "технических причин"
        }
        
        message = f"Заказ {order_id} отменен по причине: {reason_messages.get(reason, 'технических причин')}"
        if details:
            message += f". {details}"
        
        print(f"   To: {phone_number}")
        print(f"   Message: {message}")
        
        # Имитация отправки SMS
        await asyncio.sleep(0.3)
        print(f"✅ [SMS SERVICE] SMS для заказа {order_id} отправлено\n")
    else:
        print(f"⚠️  [SMS SERVICE] Клиент {client_id} не найден, SMS не отправлено\n")


