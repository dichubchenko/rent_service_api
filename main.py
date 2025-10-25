from fastapi import FastAPI, HTTPException, status
from models import (
    OrderCreateRequest, 
    OrderResponse, 
    RentalOrderMessage, 
    CancelReason,
    OrderCancelRequest,
    OrderUpdateResponse,
    OrderCancellationMessage  # Добавляем этот импорт
)
import services
from datetime import datetime
import asyncio

app = FastAPI(
    title="Rental Service API",
    description="API для сервиса краткосрочной аренды вещей",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.post("/api/orders",
          response_model=OrderResponse,
          status_code=status.HTTP_201_CREATED,
          summary="Создать заказ на аренду",
          tags=["Orders"])
async def create_order(order_request: OrderCreateRequest):
    """
    Создает новый заказ на аренду вещи.
    
    Внутренняя логика:
    - Проверяет возможность выдачи вещи (наличие в постомате, отсутствие брони)
    - Если вещь доступна: создает заказ в БД и отправляет сообщение в Kafka
    - Если вещь недоступна: отправляет SMS об отмене и возвращает ошибку
    """
    try:
        print(f"🔔 Получен запрос на создание заказа: {order_request}")
        
        # 1. Проверка возможности выдачи вещи
        await services.check_item_availability(
            order_request.item_id,
            order_request.pickup_point_id
        )
        
        # 2. Создание заказа в БД и бронирование вещи
        new_order = await services.create_order_in_db(order_request)
        
        # 3. Подготовка и отправка сообщения в Kafka для сервиса документов
        kafka_message = RentalOrderMessage(
            order_id=new_order.id,
            client_id=new_order.client_id,
            item_id=new_order.item_id,
            pickup_point_id=new_order.pickup_point_id,
            rental_duration_hours=new_order.rental_duration_hours,
            timestamp=datetime.now()
        )
        
        # Асинхронная отправка в Kafka (fire and forget)
        asyncio.create_task(services.send_to_kafka(kafka_message))
        
        print(f"✅ Заказ {new_order.id} успешно создан")
        return new_order

    except services.ItemNotAvailableError as e:
        print(f"❌ Вещь недоступна: {e}")
        # Синхронный запрос в сервис SMS на отмену
        await services.send_sms_cancellation(
            order_request.client_id,
            0,  # order_id еще не создан
            CancelReason.ITEM_ALREADY_BOOKED,
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
    except services.ItemNotInLocationError as e:
        print(f"❌ Вещь не в указанном месте: {e}")
        # Синхронный запрос в сервис SMS на отмену
        await services.send_sms_cancellation(
            order_request.client_id,
            0,  # order_id еще не создан  
            CancelReason.ITEM_WRONG_LOCATION,
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
    except services.ClientNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except services.PickupPointNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except Exception as e:
        print(f"💥 Непредвиденная ошибка: {e}")
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

@app.get("/api/debug/orders", response_model=List[OrderDebugResponse])
async def debug_orders():
    """Эндпоинт для отладки - показывает созданные заказы с полной информацией"""
    return services.orders_db

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





@app.post("/api/orders",
          response_model=OrderResponse,
          status_code=status.HTTP_201_CREATED,
          summary="Создать заказ на аренду",
          tags=["Orders"])
async def create_order(order_request: OrderCreateRequest):
    """
    Создает новый заказ на аренду вещи.
    """
    try:
        print(f"🔔 Получен запрос на создание заказа: {order_request}")
        
        # 1. Проверка возможности выдачи вещи
        await services.check_item_availability(
            order_request.item_id,
            order_request.pickup_point_id
        )
        
        # 2. Создание заказа в БД и бронирование вещи
        new_order = await services.create_order_in_db(order_request)
        
        # 3. Подготовка и отправка сообщения в Kafka для сервиса документов
        kafka_message = services.RentalOrderMessage(
            order_id=new_order.id,
            client_id=new_order.client_id,
            item_id=new_order.item_id,
            pickup_point_id=new_order.pickup_point_id,
            rental_duration_hours=new_order.rental_duration_hours,
            timestamp=datetime.now()
        )
        
        # Асинхронная отправка в Kafka (fire and forget)
        asyncio.create_task(services.send_to_kafka(kafka_message))
        
        print(f"✅ Заказ {new_order.id} успешно создан")
        return new_order

    except services.ItemNotAvailableError as e:
        print(f"❌ Вещь недоступна: {e}")
        # Отмена во время создания заказа
        await services.cancel_order_during_creation(
            order_request.client_id,
            order_request.item_id,
            order_request.pickup_point_id,
            CancelReason.ITEM_ALREADY_BOOKED,
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
    except services.ItemNotInLocationError as e:
        print(f"❌ Вещь не в указанном месте: {e}")
        # Отмена во время создания заказа
        await services.cancel_order_during_creation(
            order_request.client_id,
            order_request.item_id,
            order_request.pickup_point_id,
            CancelReason.ITEM_WRONG_LOCATION,
            str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
        
    except services.ClientNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except services.PickupPointNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except Exception as e:
        print(f"💥 Непредвиденная ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )
