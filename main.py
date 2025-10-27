from fastapi import FastAPI, HTTPException, status
from models import OrderStatus, CancelReason, Order, Client, Item, Ppoint, OrderCreateRequest, OrderResponse, RentalOrderMessage, ItemCreateRequest, ClientCreateRequest
import services
from datetime import datetime
import asyncio
from typing import List

app = FastAPI(
    title="Rental Service API",
    description="API для сервиса краткосрочной аренды вещей",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.post("/api/new_orders",
          response_model=OrderResponse,
          status_code=status.HTTP_201_CREATED,
          summary="Создать заказ на аренду",
          tags=["Orders"])

async def create_order(order_request: OrderCreateRequest):
#def create_order(order_request: OrderCreateRequest):
    """
    Создает новый заказ на аренду вещи.
    
    Логика:
    1. Создает заказ со статусом NEW
    2. Проверяет доступность вещи
    3. Если доступна - обновляет статус на AWAITING_PAYMENT и отправляет в Kafka
    4. Если недоступна - отменяет заказ и отправляет SMS
    """
    try:
        print(f"Получен запрос на создание заказа: {order_request}")
        
        # 1. Создание заказа в БД со статусом NEW
        new_order = await services.create_order_in_db(order_request)
        #new_order = create_order_in_db(order_request)
        print(f"Заказ {new_order} создан")
        
        # 2. Проверка возможности выдачи вещи
        await services.check_item_availability(
        #check_item_availability(
            order_request.item_id,
            order_request.pickup_point_id
        )
        print(f"Проверка доступности пройдена для заказа {new_order}")
        
        # 3. Бронируем вещь
        await services.reserve_item(
        #reserve_item(
            order_request.item_id,
            new_order,
            order_request.rental_duration_hours
        )
        
        # 4. Обновляем статус заказа на AWAITING_PAYMENT
        updated_order = await services.update_order_status(new_order, OrderStatus.AWAITING_PAYMENT)
        #updated_order = update_order_status(new_order, OrderStatus.AWAITING_PAYMENT)
        print(f"Статус заказа {new_order} обновлен на AWAITING_PAYMENT")

        #НУЖНО РАСКОМЕНТИТЬ
        # 5. Подготовка и отправка сообщения в Kafka для сервиса документов
        kafka_message = RentalOrderMessage(
            order_id=updated_order.id,
            client_id=updated_order.client_id,
            item_id=updated_order.item_id,
            pickup_point_id=updated_order.pickup_point_id,
            rental_duration_hours=updated_order.rental_duration_hours,
            status=updated_order.status,
            timestamp=datetime.now()
        )
        
        # Асинхронная отправка в Kafka (fire and forget)
        asyncio.create_task(services.send_to_kafka(kafka_message))
        
        print(f"Заказ {updated_order.id} успешно отправлен в сервис формирования документов")
        return updated_order

    except (services.ItemNotAvailableError, services.ItemNotInLocationError, services.DatabaseError, services.ItemNotFoundInTable, services.ItemNotFoundError) as e:
    #except (ItemNotAvailableError, ItemNotInLocationError, DatabaseError, ItemNotFoundInTable, ItemNotFoundError) as e:
        print(f"Ошибка: {e}")
        
        # Определяем причину отмены
        if isinstance(e, services.DatabaseError):
        # if isinstance(e, DatabaseError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
              )
        elif isinstance(e, services.ItemNotFoundInTable) or isinstance(e, services.ItemNotFoundError):
        #elif isinstance(e, ItemNotFoundInTable) or isinstance(e, ItemNotFoundError):
            cancel_reason = CancelReason.ITEM_NOT_FOUND
        elif isinstance(e, services.ItemNotAvailableError):
        #elif isinstance(e, ItemNotAvailableError):
            cancel_reason = CancelReason.ITEM_NOT_AVAILABLE
        elif isinstance(e, services.ItemNotInLocationError):
        #elif isinstance(e, ItemNotInLocationError):
            cancel_reason = CancelReason.ITEM_NOT_IN_LOCATION
        else:
            cancel_reason = CancelReason.OTHER
        
        # Отмена во время создания заказа
        await services.cancel_order(
        #cancel_order(
            order_request.client_id,
            new_order,
            cancel_reason
        )
        
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )

@app.get("/")
async def root():
    return {
        "message": "Rental Service API", 
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/api/get_items")
async def get_items():
    #Возвращает все items_db
    return {services.items_db}

@app.get("/api/get_orders")
async def get_orders():
    #Возвращает все orders_db
    return {services.orders_db}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.post("/api/debug/reset")
async def reset_database():
    """
    Сброс всей базы данных к начальному состоянию.
    Только для отладки!
    """
    import services
    import importlib
    importlib.reload(services)  # Перезагружаем модуль services
    
    print("База данных сброшена к начальному состоянию")
    return {"message": "Database reset successfully", "orders_count": len(services.orders_db)}



@app.post("/api/new_items",
          response_model=Item,
          status_code=status.HTTP_201_CREATED,
          summary="Создать новую вещь в базе",
          tags=["Items"])

async def add_new_items(request_data: ItemCreateRequest):
    # Логика:
    # 1. Генерируем id
    # 2. Проверяем наличие такого id в базе
    # 2.1. Если id уже есть в базе генерируем по новой
    # 3. Проверяем наличие current_pickup_point_id в базе
    # 4. Проверяем основные бизнес условия:
    #   desc не пустой
    #   hourly_price > 0
    # 5. Регистрируем в базе


    # Генерируем и проверяем id в базе
    while True:
        try:
          item_id = services.generate_six_digit_id('items_db')
          num_conflict = services.find_in_db_by_attribute('items_db', item_id)
        except(services.ItemNotFoundInTable):
          break
    
    # Проверяем current_pickup_point_id в базе
    try:
      num_conflict = services.find_in_db_by_attribute('pickup_points_db', request_data.current_pickup_point_id)
    except(services.ItemNotFoundInTable):
      #raise(PPointNotFound(f"Не существует pickup_point с id {request_data.current_pickup_point_id}"))

      raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Не существует pickup_point с id {request_data.current_pickup_point_id}"
        )

    # Проверяем бизнес условия

    if request_data.desc == '':
      #raise(Exception(f"Нельзя зарегистрировать item с пустым desc"))

      raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя зарегистрировать item с пустым desc"
        )


    elif request_data.hourly_price <= 0:
      #raise(Exception(f"Нельзя зарегистрировать item с hourly_price <= 0"))

      raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя зарегистрировать item с hourly_price <= 0"
        )
      
    else:
      pass

    


    item_obj = Item(
        id = item_id,
        desc = request_data.desc,
        hourly_price = request_data.hourly_price,
        is_available_now = True,
        current_pickup_point_id = request_data.current_pickup_point_id,
        reserved_until = None
        )
    
    try:
        await services.add_item(item_obj)

    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )

    return(item_obj)


@app.post("/api/new_clients",
          response_model=Client,
          status_code=status.HTTP_201_CREATED,
          summary="Создать нового клиента в базе",
          tags=["Clients"])


async def create_new_client(request_data: ClientCreateRequest):
    # Логика:
    # 1. Генерируем id
    # 2. Проверяем наличие такого id в базе
    # 2.1. Если id уже есть в базе генерируем по новой
    # 3. Проверяем основные бизнес условия:
    #   name не пустой
    #   phone не пустой
    #   email не пустой
    #   phone в базе должны быть уникальны
    #   email в базе должны быть уникальны  
    # 5. Регистрируем в базе


    # Генерируем и проверяем id в базе
    while True:
        try:
          client_id = services.generate_six_digit_id('clients_db')
          num_conflict = services.find_in_db_by_attribute('clients_db', client_id)
        except(services.ItemNotFoundInTable):
          break

    # Проверяем бизнес условия

    if request_data.name == '' or request_data.phone == '' or request_data.email == '':
      #raise(Exception(f"Нельзя зарегистрировать client без полей name, email, phone"))

      raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя зарегистрировать client без полей name, email, phone"
        )
    else:
      pass
      
    num_conflict = -1
    try:
      num_conflict = services.find_in_db_by_attribute('clients_db', request_data.phone, 'phone')
    except(services.ItemNotFoundInTable):
      pass

    if num_conflict != -1:
      #raise(Exception(f"В базе уже есть клиент с phone {request_data.phone}"))

      raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"В базе уже есть клиент с phone {request_data.phone}"
        )

    try:
      num_conflict = services.find_in_db_by_attribute('clients_db', request_data.email, 'email')
    except(services.ItemNotFoundInTable):
      pass
    
    if num_conflict != -1:
      #raise(Exception(f"В базе уже есть клиент с email {request_data.email}"))

      raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"В базе уже есть клиент с email {request_data.email}"
        )

    client_obj = Client(
        id = client_id,
        name = request_data.name,
        phone = request_data.phone,
        email = request_data.email
        )
    
    try:
        await services.add_client(client_obj)
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )

    return(client_obj)
