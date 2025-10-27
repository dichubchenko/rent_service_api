from fastapi import FastAPI, HTTPException, status
from models import OrderStatus, CancelReason, Order, Client, Item, Ppoint, OrderCreateRequest, OrderResponse, RentalOrderMessage
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

@app.get("/api/debug/items")
async def debug_items():
    """Эндпоинт для отладки - показывает текущее состояние вещей"""
    return {"items": services.items_db}

@app.get("/api/debug/orders")
async def debug_orders():
    """Эндпоинт для отладки - показывает созданные заказы"""
    return {"orders": services.orders_db}

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
    
    print("🔄 База данных сброшена к начальному состоянию")
    return {"message": "Database reset successfully", "orders_count": len(services.orders_db)}
