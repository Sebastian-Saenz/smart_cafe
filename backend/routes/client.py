import os
import csv
from pathlib import Path
from flask import Blueprint, request, jsonify
from langchain.docstore.document import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from psycopg_pool import PoolTimeout
from config import Config
from extensions import checkpointer

client_bp = Blueprint('client', __name__)
config = Config()

@client_bp.route('/agent', methods=['GET'])
def client_agent():
    id_agente = request.args.get('idagente')
    msg = request.args.get('msg')

    # 1. Leer CSV y preparar documentos para RAG
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    csv_path = os.path.join(base_dir, 'data', 'stock.csv')
    docs = []

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for r in csv.DictReader(csv_file):
            text = (f"Producto: {r['name']}. Precio: S/{r['price']}. "
                    f"Descripción: {r['description']}. Stock: {r['stock']} unidades.")
            docs.append(Document(page_content=text, metadata={'id': r['id']}))

    # 2. Configurar ElasticsearchStore
    store = ElasticsearchStore(
        es_url=config.ES_URL,
        es_user=config.ES_USER,
        es_password=config.ES_PASSWORD,
        index_name="stock",
        embedding=OpenAIEmbeddings(),
        strategy=ElasticsearchStore.ExactRetrievalStrategy()
    )

    # 3. Reindexar el CSV si este cambio
    last_mtime = getattr(store, "_last_mtime", None)
    current_mtime = os.path.getmtime(csv_path)

    if last_mtime != current_mtime:
        print("CSV fue actualizado...")
        if store.client.indices.exists(index="stock"):
            store.client.indices.delete(index="stock")
        store.add_documents(docs)
        store._last_mtime = current_mtime

    # 4. Preparar herramienta RAG
    retriever = store.as_retriever(search_kwargs={"k": 3})

    # prueba = retriever.invoke("Algo dulce")
    # prueba = retriever.invoke("Algo caliente")
    # print([d.page_content for d in prueba])
    
    tool_rag = retriever.as_tool(
        name="stock_search",
        description="Consulta de stock"
    )

    # 5. Inicializamos el modelo
    model = ChatOpenAI(model="gpt-4.1-2025-04-14")

    # 6. Herramientas y Prompt
    tolkit = [tool_rag]
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
            Eres el amable personal de Esencia Cafeteria ☕🍰  
            Siempre inicia con “hola, gracias por contactar con Esencia Cafeteria.”  
            No uses “¡” ni “¿”. Para preguntas, cierra con “?”.  
            Responde en **formato de respuesta directa y conversacional**:  
            “Si, tenemos <producto> a <precio>, deseas delivery o lo quieres recoger en la cafeteria? 😊”  
            Usa **stock_search** inmediatamente en cada consulta.  
            Si no hay datos, responde “Lo siento, no cuento con esa info.”  
            No inventes productos fuera del CSV.  
            Solo indicas “disponible” o “agotado” (nunca cantidades).  
            Máximo 20 palabras por respuesta.

            Flujo de la conversación:
            1. Saluda cálido de parte de Esencia cafeteria y pregunta en que podemos ayudarle.  
            2. Si no sabe, sugiere 2 a 3 opciones populares con más stock.  
            3. Usa **stock_search** y responde con nombre, descripción, precio y disponibilidad.  
            4. Pregunta “¿Recoges en tienda o domicilio (S/4 a 7 aprox.)?”  
            5. Resume el pedido y pregunta si desea algo más.  
            6. Si es domicilio, pide dirección y confirma pago por Yape al 987 654 321.  
            7. Cierra la compra con un “¡Gracias! Nos vemos pronto.”  

            Estilo: entusiasta, cercano, siempre con emojis, muy breve y conversacional.  

        """),
        ("human", "{messages}")
    ])

    # 7. Crear y ejecutar agente
    agent_executor = create_react_agent(model, tolkit, checkpointer=checkpointer, prompt=prompt)
    config_agent = {"configurable": {"thread_id": id_agente}}
    try:
        response = agent_executor.invoke({"messages": [HumanMessage(content=msg)]}, config=config_agent)
    except PoolTimeout:
        pool.check()
        print("error")

    print(response['messages'][-1].content)
    return response['messages'][-1].content
