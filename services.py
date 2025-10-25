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

async def send_sms_cancellation(client_id: int, order_id: int, reason: CancelReason):
    """
    Заглушка для синхронного запроса в сервис отправки SMS.
    """
    print(f"\n📱 [SMS SERVICE] Отправка SMS об отмене заказа:")
    print(f"   Client ID: {client_id}")
    print(f"   Order ID: {order_id}")
    print(f"   Reason: {reason}")
    
    # Получаем данные клиента для SMS
    client = clients_db.get(client_id)
    if client:
        phone_number = client["phone"]
        
        # Формируем сообщение в зависимости от причины
        if reason == CancelReason.ITEM_NOT_AVAILABLE:
            message = f"Заказ {order_id} отменен. Вещь недоступна для бронирования."
        elif reason == CancelReason.ITEM_NOT_IN_LOCATION:
            message = f"Заказ {order_id} отменен. Вещь отсутствует в выбранном месте."
        else:
            message = f"Заказ {order_id} отменен."
        
        print(f"   To: {phone_number}")
        print(f"   Message: {message}")
        
        # Имитация отправки SMS
        await asyncio.sleep(0.3)
        print(f"✅ [SMS SERVICE] SMS для заказа {order_id} отправлено\n")
    else:
        print(f"⚠️  [SMS SERVICE] Клиент {client_id} не найден, SMS не отправлено\n")


