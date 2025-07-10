from config import Config
config = Config()

def get_prompt(name: str) -> str:
    """Obtener el promtp de la carpeta prompt, segun el nombre del archivo"""
    ruta = f"{config.BASE_DIR}/backend/prompts/{name}"
    prompt = ""
    try:
        with open(ruta, "r") as f:
            prompt = f.read()
    except Exception as e:
        print(f"Error al leer {name}: {e}")

    return prompt

def get_csv(name: str) -> str:
    doc = []
    with open(config.CSV_STOCK_PATH, newline="", encoding="utf-8") as f:
        doc = csv.DictReader(f)

    return docs