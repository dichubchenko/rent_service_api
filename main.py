from fastapi import FastAPI, HTTPException, status
from models import OrderCreateRequest, OrderResponse, RentalOrderMessage
import services
from datetime import datetime
import asyncio

app = FastAPI(
    title="Rental Service API",
    description="API для сервиса краткосрочной аренды вещей",
    version="1.0.0"
)

@app.post("/api/orders",
          response_model=OrderResponse,
          status_code=status.HTTP_201_CREATED,
          summary="Создать заказ на аренду",
          tags=["Orders"])
async def create_order(order_request: OrderCreateRequest):
    """
    Создает новый заказ на аренду вещи.

    Внутри выполняет:
    - Проверку существования клиента, вещи и постомата
    - Проверку доступности вещи в указанном постомате
    - Если все проверки пройдены, создает заказ в БД
    - Бронирует вещь
    - Отправляет асинхронное сообщение в Kafka для сервиса документов и платежей
    """
    try:
        # 1. Валидация данных и проверка доступности
        item_data = await services.validate_order_data(
            order_request.client_id,
            order_request.item_id, 
            order_request.pickup_point_id
        )

        # 2. Сохранение заказа в БД (со статусом PENDING)
        new_order = await services.save_order_to_db(order_request)

        # 3. Бронирование вещи
        await services.reserve_item(order_request.item_id, new_order.id)

        # 4. Подготовка и отправка сообщения в Kafka
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

        # 5. Возвращаем клиенту данные созданного заказа
        return new_order

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
    except services.ItemNotAvailableError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except services.DatabaseError as e:
        print(f"Database error during order creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again."
        )
    except Exception as e:
        print(f"Unexpected error during order creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )

@app.get("/")
async def root():
    return {"message": "Rental Service API is running!"}
