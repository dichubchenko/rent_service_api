import asyncio
from datetime import datetime, timedelta
from models import OrderStatus, CancelReason, Order, Client, Item, Ppoint, OrderCreateRequest, OrderResponse, RentalOrderMessage #OrderStatus, OrderResponse, OrderCreateRequest, RentalOrderMessage, SMSNotification, CancelReason
from typing import Optional, Dict, List
import json

#генератор id для заказа
class OrderIdGenerator:
    def __init__(self):
        self.counter = 1000

    def generate_id(self) -> int:
        order_id = self.counter
        self.counter += 1
        return order_id

order_id_generator = OrderIdGenerator()

# Заглушка бд заказов
orders_db: List[Order] = []

# Заглушка бд вещей
items_db: List[Item] = [
    Item(
        id = 456,
        desc = "Дрель Makita",
        hourly_price = 50,
        is_available_now = True,
        current_pickup_point_id=789,
        reserved_until = None
    ),
    Item(
        id = 457,
        desc = "Шуруповерт Bosch",
        hourly_price = 60,
        is_available_now = False,
        current_pickup_point_id = 789,
        reserved_until = datetime(2025, 12, 20, 18, 0, 0)
    ),
    Item(
        id = 458,
        desc = "Пауэрбанк Xiaomi",
        hourly_price = 20,
        is_available_now = True,
        current_pickup_point_id = 123,
        reserved_until = None
    )
]





# Заглушка бд клиентов

clients_db: List[Client] = [
    Client(id = 123, name = 'Иван Иванов', phone = '+79161234567', email = 'ivan@mail.ru'),
    Client(id = 124, name = 'Петр Петров', phone = '+79167654321', email = 'petr@mail.ru')
]


# Заглушка бд постоматов
pickup_points_db: List[Ppoint] = [
    Ppoint(id = 789, address = 'ул. Ленина, д. 1', is_active = True),
    Ppoint(id = 123, address = 'пр. Мира, д. 15', is_active = True)
]

field_and_type_enum_orders = {
        'id': int,
        'client_id': int,
        'item_id': int,
        'pickup_point_id': int,
        'rental_duration_hours': int,
        'status': OrderStatus,
        'cancel_reason': Optional[CancelReason],
        'cancel_details': Optional[str],
        'created_at': datetime,
        'updated_at': datetime
    }
field_and_type_enum_clients = {
        'id': int,
        'name': str,
        'phone': str,
        'email': str
    }
field_and_type_enum_items = {
        'id': int,
        'desc': str,
        'hourly_price': int,
        'is_available_now': bool,
        'current_pickup_point_id': int,
        'reserved_until': Optional[datetime]
    }
field_and_type_enum_ppoints = {
        'id': int,
        'address': str,
        'is_active': bool
    }

# Ошибки

class DatabaseError(Exception):
  #дефолтная ошибка проверок в БД
    pass

class ItemNotAvailableError(Exception):
  #ошибка что вещь уже забронена
    pass

class ItemNotFoundError(Exception):
  #ошибка что вещь не найдена
    pass

class ItemNotInLocationError(Exception):
  #ошибка что вещь не в переданном постомате
    pass

class ItemNotFoundInTable(Exception):
  #ошибка что не нашли объект в базе
    pass

class TableNotFoundInDB(Exception):
  #ошибка что не нашли таблицу в базе
    pass

class FieldNotFoundInTableOrTypeIsAnother(Exception):
  #ошибка что не нашли искомое поле в таблице или оно другого типа
    pass


def find_in_db_by_attribute(table: str, value: int | str | datetime, field: str = 'id'):
  #используется для поиска в БД по атрибуту
  if table == 'orders_db':
    tab = orders_db
    field_and_type_enum = field_and_type_enum_orders
  elif table == 'items_db':
    tab = items_db
    field_and_type_enum = field_and_type_enum_items
  elif table == 'clients_db':
    tab = clients_db
    field_and_type_enum = field_and_type_enum_clients
  elif table == 'pickup_points_db':
    tab = pickup_points_db
    field_and_type_enum = field_and_type_enum_ppoints
  else:
    raise TableNotFoundInDB(f"В БД нет таблицы {table}")
  
  if field not in field_and_type_enum:
      raise FieldNotFoundInTableOrTypeIsAnother(f"В таблице {table} нет поля {field}")
  elif field_and_type_enum[field] != type(value):
      raise FieldNotFoundInTableOrTypeIsAnother(f"В таблице {table} поле {field} должно быть типа {field_and_type_enum[field]}")
  else:
      pass
  
  num = None
  find_flg = False
  for i in range(len(tab)):
    if field == 'id':
        field_value = tab[i].id
    elif field == 'client_id':
        field_value = tab[i].client_id
    elif field == 'item_id':
        field_value = tab[i].item_id
    elif field == 'pickup_point_id':
        field_value = tab[i].pickup_point_id
    elif field == 'rental_duration_hours':
        field_value = tab[i].rental_duration_hours
    elif field == 'status':
        field_value = tab[i].status
    elif field == 'cancel_reason':
        field_value = tab[i].cancel_reason
    elif field == 'cancel_details':
        field_value = tab[i].cancel_details
    elif field == 'created_at':
        field_value = tab[i].created_at
    elif field == 'updated_at':
        field_value = tab[i].updated_at
    elif field == 'name':
        field_value = tab[i].name
    elif field == 'phone':
        field_value = tab[i].phone
    elif field == 'email':
        field_value = tab[i].email
    elif field == 'desc':
        field_value = tab[i].desc
    elif field == 'hourly_price':
        field_value = tab[i].hourly_price
    elif field == 'is_available_now':
        field_value = tab[i].is_available_now
    elif field == 'current_pickup_point_id':
        field_value = tab[i].current_pickup_point_id
    elif field == 'reserved_until':
        field_value = tab[i].reserved_until
    elif field == 'address':
        field_value = tab[i].address
    elif field == 'is_active':
        field_value = tab[i].is_active
    
    if field_value == value:
      num = i
      find_flg = True
    else:
      pass
  if find_flg == True:
    return(num)
  else:
    raise ItemNotFoundInTable(f"В таблице {table} нет объекта с {field} == {value}")


async def check_item_availability(item_id: int, pickup_point_id: int) -> bool:
#def check_item_availability(item_id: int, pickup_point_id: int) -> bool:
    #Проверяет возможность выдачи вещи.

    print(f"[Проверка доступности] Проверяем вещь {item_id} в постомате {pickup_point_id}")

    #Ищем вещь в item_db
    item_availible = False
    try:
      item_num = find_in_db_by_attribute('items_db', item_id)
      item_availible = True
    except ItemNotFoundInTable:
      raise ItemNotFoundError(f"Вещь с ID {item_id} не найдена")

    if item_availible == False:
      #если так и не нашли вещь вызываем ошибку
      raise ItemNotFoundError(f"Вещь с ID {item_id} не найдена")

    else:
      #если нашли вещь проверяем доступность
      current_item = items_db[item_num]

      if current_item.current_pickup_point_id != pickup_point_id:
        #если постомат не тот
        item_availible = False
        raise ItemNotInLocationError(
            f"Вещь {item_id} находится в постомате {current_item.current_pickup_point_id}, а не в {pickup_point_id}"
        )

      elif current_item.is_available_now == False:
        item_availible = False
        #проверяем что вещь не забронирована
        raise ItemNotAvailableError(f"Вещь {item_id} уже забронирована")
        #ожидаем консистентность данных и невозможность reserved_until <= current_timestamp
      else:
        print(f"[Результат проверки доступности] Вещь {item_id} в постомате {pickup_point_id} доступна")
    return(item_availible)


async def reserve_item(item_id: int, order_id: int, rental_hours: int) -> None:
#def reserve_item(item_id: int, order_id: int, rental_hours: int) -> None:
    #Бронирует вещь в БД
    print(f"[Бронирование] Бронируем вещь {item_id} для заказа {order_id}")
    #ожидаем что перед бронированием уже проведена проверка доступности => уже точно item_id в item_db

    item_num = None

    try:
      item_num = find_in_db_by_attribute('items_db', item_id)
    except ItemNotFoundInTable:
      raise ItemNotFoundError(f"Вещь с ID {item_id} не найдена")

    # Изменяем items_db
    items_db[item_num].is_available_now = False
    items_db[item_num].reserved_until = datetime.now() + timedelta(hours=rental_hours)

    print(f"[Бронирование] Вещь {item_id} забронирована для заказа {order_id}")

async def send_sms_cancellation(client_id: int, reason: CancelReason, order_id: int = None):
#def send_sms_cancellation(client_id: int, reason: CancelReason, order_id: int = None):
    #Заглушка для запроса в сервис отправки SMS.

    print(f"\n [SMS SERVICE] Отправка SMS об отмене заказа:")
    print(f"   Client ID: {client_id}")
    print(f"   Order ID: {order_id}")
    print(f"   Reason: {reason}")

    # Получаем данные клиента для SMS
    client_num = None

    try:
      client_num = find_in_db_by_attribute('clients_db', client_id)
      phone_number = clients_db[client_num].phone

      # Формируем сообщение в зависимости от причины
      if order_id is None:
          reason = CancelReason.OTHER
          message = f"Заказ отменен."
      elif reason == CancelReason.ITEM_NOT_AVAILABLE:
          message = f"Заказ {order_id} отменен. Вещь недоступна для бронирования."
      elif reason == CancelReason.ITEM_NOT_FOUND:
          message = f"Заказ {order_id} отменен. Заказанной вещи не существует."
      elif reason == CancelReason.ITEM_NOT_IN_LOCATION:
          message = f"Заказ {order_id} отменен. Вещь отсутствует в выбранном месте."
      else:
          message = f"Заказ {order_id} отменен."

      print(f"   To: {phone_number}")
      print(f"   Message: {message}")

      # Имитация отправки SMS
      await asyncio.sleep(0.3)
      #asyncio.sleep(0.3)
      if order_id is None:
        print("[SMS SERVICE] SMS для заказа отправлено")
      else:
        print(f"[SMS SERVICE] SMS для заказа {order_id} отправлено\n")

    except ItemNotFoundInTable:
      print(f"[SMS SERVICE] Клиент {client_id} не найден, SMS не отправлено\n")
      raise ItemNotFoundInTable(f"Клиент с ID {client_id} не найден")

async def create_order_in_db(order_data: OrderCreateRequest) -> OrderResponse:
#def create_order_in_db(order_data: OrderCreateRequest) -> OrderResponse:
    #создание заказа
    print(f"[Создание заказа] Сохраняем заказ в БД: {order_data}")
    try:
      order_id = order_id_generator.generate_id()
      now = datetime.now()
      
      # Создаем заказ со статусом NEW
      new_order = Order(
          id = order_id,
          client_id = order_data.client_id,
          item_id = order_data.item_id,
          pickup_point_id = order_data.pickup_point_id,
          rental_duration_hours = order_data.rental_duration_hours,
          status = OrderStatus.NEW,
          cancel_reason = None,
          cancel_details = None,
          created_at = now,
          updated_at = now
      )
      
      orders_db.append(new_order)
      print(f"[Создание заказа] Заказ {order_id} создан")
    except:
      raise DatabaseError(f"Заказ не создан")
    return order_id

async def update_order_status(order_id: int, new_status: OrderStatus) -> Order:
#def update_order_status(order_id: int, new_status: OrderStatus) -> Order:
    #Функция обновляет статус у заказа
    print(f"[Обновление статуса] Заказ {order_id} -> {new_status}")
    
    # Ищем заказ
    order_num = None
    try:
      order_num = find_in_db_by_attribute('orders_db', order_id)
    except ItemNotFoundInTable:
      raise ItemNotFoundError(f"Заказ с ID {order_id} не найден")
    
    
    if order_num:
      orders_db[order_num].status = new_status
      orders_db[order_num].updated_at = datetime.now()
    
    print(f"[Обновление статуса] Статус заказа {order_id} обновлен на {new_status}")
    return orders_db[order_num]

async def cancel_order(client_id: int, order_id: int, cancel_reason: CancelReason, error_details: str = None) -> None:
#def cancel_order(client_id: int, order_id: int, cancel_reason: CancelReason, error_details: str = None) -> None:
    #Функция отмены заказа
    if error_details is None:
      print(f"Отмена заказа по причине: {cancel_reason}")
    else:
      print(f"Отмена заказа по причине: {cancel_reason}. Детали: {error_details}")
    
    #обновляем статус заказа
    order_num = None
    try:
      order_num = find_in_db_by_attribute('orders_db', order_id)
    except ItemNotFoundInTable:
      raise ItemNotFoundError(f"Заказ с ID {order_id} не найден")

    orders_db[order_num].status = OrderStatus.CANCELLED
    orders_db[order_num].cancel_reason = cancel_reason
    orders_db[order_num].cancel_details = error_details

    await send_sms_cancellation(client_id, order_id, cancel_reason)
    #send_sms_cancellation(client_id, cancel_reason, order_id)
