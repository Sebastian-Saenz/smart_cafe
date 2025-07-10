from pydantic import BaseModel, Field

class StockRequest(BaseModel):
    products: list[str] = Field(description="Lista de productos solicitados")