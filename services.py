import asyncio
from datetime import datetime, timedelta
from models import OrderStatus, OrderResponse, OrderCreateRequest, RentalOrderMessage
from typing import Optional
import json

# --- In-Memory "База данных" (заглушка) ---
fake_orders_db = []
fake_items_db = {
    456: {"name": "Дрель", "hourly_price": 50, "is_available": True, "current_pickup_point": 789},
    999: {"name": "Пауэрбанк", "hourly_price": 20, "is_available": False, "current_pickup_point": 123},
    888: {"name": "Велосипед", "hourly_price": 100, "is_available": True, "current_pickup_point": 789},
}
fake_clients_db = {
    123: {"name": "Иван Иванов", "phone": "+79161234567", "email": "ivan@mail.ru"}
}
fake_pickup_points_db = {
    789: {"address": "ул. Ленина, д. 1", "working_hours": "круглосуточно"},
    123: {"address": "пр. Мира, д. 15", "working_hours": "08:00-22:00"}
}

order_id_counter = 1

class DatabaseError(Exception):
    """Исключение для ошибок БД."""
    pass

class ItemNotAvailableError(Exception):
    """Исключение, если вещь недоступна."""
    pass

class ClientNotFoundError(Exception):
    """Исключение, если клиент не найден."""
    pass

class PickupPointNotFoundError(Exception):
    """Исключение, если постомат не найден."""
    pass

async def validate_order_data(client_id: int, item_id: int, pickup_point_id: int) -> dict:
    """
    Проверяет существование клиента, вещи и постомата.
    Возвращает данные для расчета цены.
    """
    # Проверка клиента
    if client_id not in fake_clients_db:
        raise ClientNotFoundError(f"Client with id {client_id} not found")
    
    # Проверка постомата
    if pickup_point_id not in fake_pickup_points_db:
        raise PickupPointNotFoundError(f"Pickup point with id {pickup_point_id} not found")
    
    # Проверка вещи
    if item_id not in fake_items_db:
        raise ItemNotAvailableError(f"Item with id {item_id} not found")
    
    item_data = fake_items_db[item_id]
    
    # Проверка доступности вещи
    if not item_data["is_available"]:
        raise ItemNotAvailableError(f"Item with id {item_id} is not available")
    
    # Проверка, что вещь находится в указанном постомате
    if item_data["current_pickup_point"] != pickup_point_id:
        raise ItemNotAvailableError(f"Item with id {item_id} is not available at pickup point {pickup_point_id}")
    
    return item_data

async def reserve_item(item_id: int, order_id: int) -> None:
    """
    Бронирует вещь в БД.
    """
    print(f"[Бронирование] Бронируем вещь {item_id} для заказа {order_id}")
    await asyncio.sleep(0.1)
    
    if item_id not in fake_items_db:
        raise DatabaseError(f"Item {item_id} not found")
    
    # Помечаем вещь как недоступную
    fake_items_db[item_id]["is_available"] = False
    
    # Имитируем возможную ошибку при бронировании
    if item_id == 777:  # специальный ID для тестирования ошибок
        raise DatabaseError("Could not lock database row for item {item_id}")

async def save_order_to_db(order_data: OrderCreateRequest) -> OrderResponse:
    """
    Сохраняет заказ в БД.
    """
    global order_id_counter, fake_orders_db
    print(f"[Сохранение заказа] Сохраняем заказ в БД: {order_data}")

    new_order = OrderResponse(
        id=order_id_counter,
        status=OrderStatus.PENDING,
        created_at=datetime.now(),
        **order_data.model_dump()
    )
    
    fake_orders_db.append(new_order)
    order_id_counter += 1
    return new_order

# --- Заглушки для внешних сервисов ---

async def send_to_kafka(message: RentalOrderMessage):
    """
    Заглушка для отправки сообщения в Kafka.
    В реальности здесь был бы вызов kafka-python или аналогичной библиотеки.
    """
    print(f"[Kafka] Отправка сообщения в топик 'rental-orders':")
    print(f"       Order ID: {message.order_id}")
    print(f"       Client ID: {message.client_id}") 
    print(f"       Item ID: {message.item_id}")
    print(f"       Pickup Point: {message.pickup_point_id}")
    print(f"       Duration: {message.rental_duration_hours} часов")
    print(f"       Timestamp: {message.timestamp}")
    
    # Имитация отправки в Kafka
    await asyncio.sleep(0.5)
    print(f"[Kafka] Сообщение для заказа {message.order_id} успешно отправлено")
    
    # В реальном сервисе документов и платежей:
    # - Рассчитывается итоговая цена (hourly_price * duration)
    # - Формируются документы
    # - Инициируется процесс оплаты
    # - Отправляется уведомление клиенту
