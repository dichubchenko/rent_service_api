from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

app = FastAPI(title="Rental API", version="1.0.0")

class OrderStatus(str, Enum):
    PENDING = "pending"

class OrderCreateRequest(BaseModel):
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int

class OrderResponse(BaseModel):
    id: int
    client_id: int
    item_id: int
    pickup_point_id: int
    rental_duration_hours: int
    status: OrderStatus
    created_at: datetime

# In-memory storage for demo
orders_db = []
order_counter = 1

@app.post("/api/orders", response_model=OrderResponse, status_code=201)
async def create_order(order_request: OrderCreateRequest):
    global order_counter
    
    # Простая заглушка бизнес-логики
    new_order = OrderResponse(
        id=order_counter,
        status=OrderStatus.PENDING,
        created_at=datetime.now(),
        **order_request.model_dump()
    )
    
    orders_db.append(new_order)
    order_counter += 1
    
    return new_order

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    for order in orders_db:
        if order.id == order_id:
            return order
    raise HTTPException(status_code=404, detail="Order not found")

@app.get("/")
async def root():
    return {"message": "Rental API is running!", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
