import configparser
import os

def ler_dados_config():
    """
    Lê dados do arquivo assets/config.ini:
    - login, senha, fornecedor
    - UFs ativas (DESTINOS)
    - Municípios em exceção (EXCECOES)
    """
    config = configparser.ConfigParser()
    config_path = "assets/config.ini"

    if not os.path.exists(config_path):
        print(f"[ERRO] Arquivo de configuração não encontrado em {config_path}")
        return "", "", "", [], []

    config.read(config_path, encoding="utf-8")

    # 🔐 Dados do portal
    login = config.get("PORTAL", "login", fallback="")
    senha = config.get("PORTAL", "senha", fallback="")
    fornecedor = config.get("PORTAL", "fornecedor", fallback="matriz")

    # 🌎 UFs ativas
    destinos_ativos = [
        uf.strip().upper()
        for uf, status in config.items("DESTINOS")
        if status.strip().lower() == "ativo"
    ]

    # ⚠️ Municípios em exceção
    try:
        municipios = config.get("EXCECOES", "municipios", fallback="")
        excecoes = [m.strip().upper() for m in municipios.split(",") if m.strip()]
    except:
        excecoes = []

    return login, senha, fornecedor, destinos_ativos, excecoes
