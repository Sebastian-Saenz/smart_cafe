

def rag_stock_csv():
    """ Consulta el sotck en ../data/stock.csv"""

    return 0

@tool("search_stock", args_schema=ProductRequest)
def search_stock(products: list[str]) -> str:
    """Consulta stock de multiples productos."""
    reindex_csv()
    answers = []
    print(f"===== Search Stock Tool =====")
    for name in products:
        print(f"Producto: {name}")
        docs = retriever.invoke(name)
        if not docs:
            answers.append(f"Sin informacion de {name}")
            continue
        stock = docs[0].metadata.get("stock", 0)
        answers.append(f"{name}: {stock}")
    answer = "; ".join(answers)
    print(answer)
    return answer