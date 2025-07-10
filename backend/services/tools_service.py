from datetime import datetime
from langchain_core.tools import tool
from models.product import StockRequest
from langchain_openai import ChatOpenAI
from utils import get_prompt

llm = ChatOpenAI(model="gpt-4.1-2025-04-14", temperature=0)

@tool
def check_schedule() -> str:
    """Responde si estamos abiertos o cerrados"""
    print(f"===== Check Schedule Tool =====")

    # Devolvemos cerrado por default
    result = "cerrado"

    # Obtenermos la hora actual
    hora_actual = datetime.strptime("14:30", "%H:%M").time() # datetime.now().time()

    # Horarios de atencion
    apertura = datetime.strptime("14:00", "%H:%M").time()
    cierre   = datetime.strptime("20:00", "%H:%M").time()

    if apertura <= hora_actual <= cierre:
        result = "abierto"
    print(f"Hora actual-> {hora_actual}: {result}")
    return result

@tool
def get_order(msg: str) -> list:
    """Extrae una lista de productos y cantidades desde el mensaje del cliente."""
    print(f"===== Check Schedule Tool =====")

    # Generar prompt para la cadena
    prompt = ChatPromptTemplate.from_template(get_prompt("get_order.txt"))

    chain = prompt | llm
    result = chain.invoke({"msg": msg})

    try:
        order_list = eval(result.content)
        print(order_list)
        return order_list
    except Exception as e:
        print("Error en get_order: ", e)
    return []

@tool("search_stock", args_schema=StockRequest, description="Busca stock de un listado de productos")
def search_stock(products: list[str]) -> str:
    reindex_csv()
    results = []
    print(f"===== Search Stock Tool =====")
    for name in products:
        print(f"Producto: {name}")
        docs = retriever.invoke(name)
        stock = docs[0].metadata.get("stock", 0) if docs else 0
        results.append({"name": name, "stock": stock})
    print(results)
    return results

