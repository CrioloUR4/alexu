import json
from flask import Blueprint, jsonify, request
import threading
import time
from core.suporte import registrar_log
from core.dados import ler_dados_config
from core.navegador import iniciar_navegador
from core.operacoes import acessar_pagina_de_cargas
from playwright.sync_api import sync_playwright
from core.operacoes import executar_ciclo_real, cargas_lista




rotas_api = Blueprint('rotas_api', __name__)

# Variáveis globais de controle
estado_ciclo = {
    "rodando": False,
    "thread": None
}

contexto_global = None
pagina_global = None
playwright_ativo = {"pw": sync_playwright().start()}


def navegador_ativo(pagina):
    try:
        if not pagina or not pagina.context:
            return False
        _ = pagina.title()
        return True
    except:
        return False


# 🔁 Ciclo contínuo em thread
def ciclo_continuo():
    global contexto_global, pagina_global

    from playwright.sync_api import sync_playwright, Error as PlaywrightError
    registrar_log("INFO", "Thread ciclo: iniciando Playwright próprio.")

    with sync_playwright() as pw:
        try:
            contexto, pagina = iniciar_navegador(pw)
        except Exception as e:
            registrar_log("ERRO", f"Falha ao iniciar navegador: {e}")
            estado_ciclo["rodando"] = False
            return

        contexto_global = contexto
        pagina_global = pagina

        try:
            acessar_pagina_de_cargas(contexto, pagina)
        except PlaywrightError as e:
            registrar_log("ERRO", f"Navegador foi fechado antes da leitura inicial. Abortando ciclo. {e}")
            estado_ciclo["rodando"] = False
            return

        while estado_ciclo["rodando"]:
            if not navegador_ativo(pagina):
                registrar_log("ERRO", "Navegador foi fechado durante o ciclo. Encerrando thread.")
                estado_ciclo["rodando"] = False
                return

            try:
                registrar_log("INFO", "Nova varredura automática de cargas iniciada.")
                executar_ciclo_real(contexto, pagina)
                registrar_log("INFO", "Ciclo de cargas finalizado. Reiniciando imediatamente.")
            except PlaywrightError as e:
                registrar_log("ERRO", f"Navegador desconectado. Finalizando ciclo: {e}")
                estado_ciclo["rodando"] = False
                return
            except Exception as e:
                registrar_log("ERRO", f"Erro inesperado no ciclo contínuo: {e}")
                time.sleep(5)

        registrar_log("INFO", "Thread de ciclo finalizada.")
        estado_ciclo["rodando"] = False



# ▶️ Iniciar ciclo contínuo
@rotas_api.route("/api/iniciar", methods=["GET"])
def iniciar():
    if estado_ciclo["rodando"]:
        return jsonify({"mensagem": "Ciclo já está rodando."})

    try:
        registrar_log("INFO", "Iniciando ciclo contínuo: login + ciclo automático (ciclo em thread própria)")
        estado_ciclo["rodando"] = True
        t = threading.Thread(target=ciclo_continuo, daemon=True)
        estado_ciclo["thread"] = t
        t.start()
        return jsonify({"mensagem": "Ciclo contínuo iniciado com sucesso."})
    except Exception as e:
        registrar_log("ERRO", f"Falha ao iniciar ciclo contínuo: {e}")
        estado_ciclo["rodando"] = False
        return jsonify({"erro": str(e)}), 500


# ⏹️ Parar ciclo
@rotas_api.route("/api/parar", methods=["GET"])
def parar():
    estado_ciclo["rodando"] = False
    registrar_log("INFO", "Ciclo foi parado manualmente.")
    return jsonify({"mensagem": "Ciclo parado."})


# 📡 Status do ciclo
@rotas_api.route("/api/status", methods=["GET"])
def status():
    status_atual = "rodando" if estado_ciclo["rodando"] else "parado"
    registrar_log("DEBUG", f"Consulta de status: {status_atual}")
    return jsonify({"status": status_atual})


# 🔧 Teste do config.ini
@rotas_api.route("/api/teste_config", methods=["GET"])
def teste_config():
    login, senha, fornecedor, destinos_ativos, excecoes = ler_dados_config()

    resultado = {
        "login": login,
        "senha": senha,
        "fornecedor": fornecedor,
        "destinos_ativos": destinos_ativos,
        "municipios_excecao": excecoes
    }

    return jsonify(resultado)


# 🔐 Apenas login
@rotas_api.route("/api/login", methods=["GET"])
def login():
    try:
        with sync_playwright() as pw:
            contexto, pagina = iniciar_navegador(pw)
            return jsonify({"mensagem": "Login realizado com sucesso."})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# 🔄 Preparar ambiente de ciclo (mantém para uso manual/avanço futuro)
@rotas_api.route("/api/preparar_ciclo", methods=["GET"])
def preparar_ciclo():
    global contexto_global, pagina_global, playwright_ativo

    try:
        if not navegador_ativo(pagina_global):
            if not playwright_ativo["pw"]:
                playwright_ativo["pw"] = sync_playwright().start()

            contexto_global, pagina_global = iniciar_navegador(playwright_ativo["pw"])

        acessar_pagina_de_cargas(contexto_global, pagina_global)
        return jsonify({"mensagem": "Página de ciclo preparada com sucesso."})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@rotas_api.route("/api/cargas", methods=["GET"])
def api_cargas():
    global contexto_global, pagina_global

    try:
        if not navegador_ativo(pagina_global):
            return jsonify({"erro": "Navegador não está ativo. Use /api/preparar_ciclo primeiro."}), 400

        executar_ciclo_real(contexto_global, pagina_global)
        return jsonify(cargas_lista)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@rotas_api.route("/api/cargas_ativas", methods=["GET"])
def cargas_ativas():
    try:
        with open("data/cargas_ativas.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": f"Erro ao ler cargas_ativas.json: {e}"}), 500

