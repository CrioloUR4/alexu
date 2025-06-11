# core/suporte.py
import os
from datetime import datetime

LOG_PATH = "logs/sistema.log"

def registrar_log(nivel, mensagem):
    """
    Registra mensagem com timestamp no arquivo de log.
    Nível pode ser: INFO, ERRO, ALERTA, DEBUG, etc.
    """
    os.makedirs("logs", exist_ok=True)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{nivel}] {agora} - {mensagem}\n"

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(linha)

    print(linha.strip())
