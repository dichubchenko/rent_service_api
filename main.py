from fastapi import FastAPI, HTTPException, status
from models import OrderCreateRequest, OrderResponse, RentalOrderMessage, CancelReason
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



# Добавляем в main.py после существующих эндпоинтов

@app.patch("/api/orders/{order_id}",
          response_model=OrderUpdateResponse,
          summary="Отменить заказ",
          tags=["Orders"])
async def cancel_order(order_id: int, cancel_request: OrderCancelRequest):
    """
    Отменяет заказ по указанной причине.
    
    Внутренняя логика:
    - Обновляет статус заказа на 'cancelled'
    - Освобождает забронированную вещь
    - Отправляет асинхронное сообщение в Kafka для сервиса SMS
    """
    try:
        print(f"🔔 Получен запрос на отмену заказа {order_id}: {cancel_request}")
        
        # 1. Отменяем заказ в БД и освобождаем вещь
        cancelled_order = await services.cancel_order_in_db(
            order_id, 
            cancel_request.cancel_reason,
            cancel_request.details
        )
        
        # 2. Подготовка и отправка сообщения в Kafka для сервиса SMS
        kafka_message = services.OrderCancellationMessage(
            order_id=cancelled_order.id,
            client_id=cancelled_order.client_id,
            item_id=cancelled_order.item_id,
            pickup_point_id=cancelled_order.pickup_point_id,
            cancel_reason=cancel_request.cancel_reason,
            cancel_details=cancel_request.details,
            timestamp=datetime.now()
        )
        
        # Асинхронная отправка в Kafka (fire and forget)
        asyncio.create_task(services.send_cancellation_to_kafka(kafka_message))
        
        print(f"✅ Заказ {order_id} успешно отменен")
        
        return OrderUpdateResponse(
            order_id=cancelled_order.id,
            status=cancelled_order.status,
            cancel_reason=cancel_request.cancel_reason,
            message=f"Заказ отменен по причине: {cancel_request.cancel_reason}"
        )

    except services.DatabaseError as e:
        print(f"❌ Ошибка при отмене заказа: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"💥 Непредвиденная ошибка при отмене заказа: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during order cancellation."
        )
