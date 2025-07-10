import os
import csv
from pathlib import Path
from flask import Blueprint, request, jsonify, render_template
from langchain.docstore.document import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from psycopg_pool import PoolTimeout
from config import Config
from extensions import checkpointer
from utils import get_prompt

client_bp = Blueprint('client', __name__)
config = Config()

def get_docs():
    docs = []
    with open(config.CSV_STOCK_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            text = (
                f"Producto: {r['name']}. "
                f"Precio: S/{r['price']}. "
                f"Descripción: {r['description']}. "
                f"Stock: {r['stock']} unidades."
            )
            docs.append(Document(page_content=text, metadata={'id': r['id']}))
    return docs

@client_bp.route('/agent', methods=['GET'])
def client_agent():
    id_agente = request.args.get('idagente')
    msg = request.args.get('msg')

    # 1. Configurar ElasticsearchStore
    store = ElasticsearchStore(
        es_url=config.ES_URL,
        es_user=config.ES_USER,
        es_password=config.ES_PASSWORD,
        index_name="stock",
        embedding=OpenAIEmbeddings()
    )

    # 3. Reindexar el CSV si este cambio
    last_mtime = getattr(store, "_last_mtime", None)
    current_mtime = os.path.getmtime(config.CSV_STOCK_PATH)

    if last_mtime != current_mtime:
        if store.client.indices.exists(index="stock"):
            store.client.indices.delete(index="stock")
        store.add_documents(get_docs())
        store._last_mtime = current_mtime
        print("CSV fue actualizado...")

    # 4. Preparar herramienta RAG
    retriever = store.as_retriever(search_kwargs={"k": 3})
    tool_rag = retriever.as_tool(
        name="stock_search",
        description="Consulta de stock"
    )

    # 5. Inicializamos el modelo
    model = ChatOpenAI(model="gpt-4.1-2025-04-14")

    # 6. Herramientas y Prompt
    tolkit = [tool_rag]
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_prompt("virtual_assistent.txt")),
        ("human", "{messages}")
    ])

    # 7. Crear y ejecutar agente
    agent_executor = create_react_agent(model, tolkit, checkpointer=checkpointer, prompt=prompt)
    config_agent = {"configurable": {"thread_id": id_agente}}
    try:
        print("Enviando solicitud...")
        response = agent_executor.invoke({"messages": [HumanMessage(content=msg)]}, config=config_agent)
        print("Solicitud recibida...")
    except PoolTimeout:
        pool.check()
        print("error")

    # print(response)
    reply = response['messages'][-1].content
    # return response['messages'][-1].content
    return jsonify({"reply": reply})

@client_bp.route('/escribenos', methods=['GET'])
def escribenos():
    return render_template('escribenos.html')