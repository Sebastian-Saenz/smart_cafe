import os, csv
from flask import Blueprint, request, jsonify, render_template
from pathlib import Path
from langchain.docstore.document import Document
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from psycopg_pool import PoolTimeout
from config import Config
from extensions import checkpointer
from utils import get_prompt
from models.product import StockRequest

client_bp = Blueprint('client', __name__)
config = Config()

def load_docs():
    docs = []
    with open(config.CSV_STOCK_PATH, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            content = (
                f"Producto: {r['name']}. "
                f"Precio: S/{r['price']}. "
                f"Descripción: {r['description']}. "
                f"Stock: {r['stock']} unidades."
            )
            docs.append(Document(page_content=content, metadata={'stock': int(r['stock'])}))
    return docs

store = ElasticsearchStore(
    es_url=config.ES_URL,
    es_user=config.ES_USER,
    es_password=config.ES_PASSWORD,
    index_name="stock",
    embedding=OpenAIEmbeddings()
)

retriever = store.as_retriever(search_kwargs={"k": 1}) # k=numero de conicidencias

def reindex_csv():
    mtime = os.path.getmtime(config.CSV_STOCK_PATH)
    if getattr(store, "_last_mtime", None) != mtime:
        if store.client.indices.exists(index="stock"):
            store.client.indices.delete(index="stock")
        store.add_documents(load_docs())
        store._last_mtime = mtime

# @tool("search_stock", args_schema=StockRequest, description="Busca stock de un listado de productos")
# def search_stock(products: list[str]) -> str:
#     """Consulta stock de multiples productos."""
#     reindex_csv()
#     answers = []
#     print(f"===== Search Stock Tool =====")
#     for name in products:
#         print(f"Producto: {name}")
#         docs = retriever.invoke(name)
#         if not docs:
#             answers.append(f"Sin informacion de {name}")
#             continue
#         stock = docs[0].metadata.get("stock", 0)
#         answers.append(f"{name}: {stock}")
#     answer = "; ".join(answers)
#     print(answer)
#     return answer

@tool("search_stock", args_schema=StockRequest, description="Busca stock de un listado de productos")
def search_stock(products: list[str]) -> str:
    """Consulta stock de multiples productos."""
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

@client_bp.route('/agent', methods=['GET'])
def client_agent():
    id_agente = request.args.get('idagente')
    msg = request.args.get('msg', '')

    model = ChatOpenAI(model="gpt-4.1-2025-04-14")
    # model = ChatOpenAI(model="gpt-4.1-mini-2025-04-14")
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_prompt("virtual_assistent.txt")),
        ("human", "{messages}")
    ])

    agent = create_react_agent(
        model,
        tools=[search_stock],
        checkpointer=checkpointer,
        prompt=prompt
    )

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=msg)]},
            config={"configurable": {"thread_id": id_agente}}
        )
        reply = result['messages'][-1].content
    except PoolTimeout:
        reply = "Ups, hubo un problema 😕"

    return jsonify({"reply": reply})

@client_bp.route('/escribenos', methods=['GET'])
def escribenos():
    return render_template('escribenos.html')