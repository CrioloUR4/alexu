import time
from datetime import datetime
from core.dados import ler_dados_config
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from utils.playwright_utils import navegador_ativo
from bs4 import BeautifulSoup
import os
import json

CAMINHO_ATIVAS = "data/cargas_ativas.json"
CAMINHO_HISTORICO = "data/cargas_historico.json"
# Lista global de cargas (acessada pela API)
cargas_lista = []
def acessar_pagina_de_cargas(context, page):
    login, senha, fornecedor, destinos_config, excecoes_config = ler_dados_config()

    print("🔄 Acessando página de cargas...")
    page.goto("https://portal.e-fornecedores.ind.br/Default.aspx?cmp=SUCargaProgramada.ascx&tipo=vnc&menu=yes")
    page.wait_for_load_state('networkidle')

    print("🔘 Clicando no botão de pesquisa...")
    page.wait_for_selector("#ctlLoadedControl_btnPesquisa", timeout=15000)
    page.click("#ctlLoadedControl_btnPesquisa")

    print("⏳ Esperando botão de vínculo...")
    page.wait_for_selector("#ctlLoadedControl_dgRight__ctl3_btnVinculo", timeout=15000)
    page.click("#ctlLoadedControl_dgRight__ctl3_btnVinculo")

    print("➡️ Aguardando página de vínculo carregar...")
    page.wait_for_load_state('networkidle')

    url_atual = page.url
    url_adm = url_atual.replace("SUVinculo.ascx", "Vinculo.ascx")
    page.goto(url_adm)
    page.wait_for_load_state('networkidle')

    print("↩️ Clicando no botão << Voltar...")
    page.wait_for_selector("#ctlLoadedControl_btnVoltar", timeout=15000)
    page.click("#ctlLoadedControl_btnVoltar")

    page.wait_for_load_state('networkidle')
    print("✅ Página de cargas especial carregada com sucesso.")
    time.sleep(1)



def executar_ciclo_real(context, page):
    """
    Executa uma varredura única na grid de cargas:
    - Atualiza a grid
    - Percorre todas as páginas via __doPostBack
    - Armazena as cargas válidas em cargas_lista
    """
    login, senha, fornecedor, ufs_ativas, excecoes = ler_dados_config()
    print("🔄 Atualizando grid de cargas...")

    try:
        if not navegador_ativo(page):
            print(f"[ERRO] {datetime.now()} - Navegador foi fechado durante a leitura. Encerrando ciclo.")
            return

        # Volta para página 1, se possível
        botao_pagina_1 = page.query_selector("input[type='submit'][value='1']")
        if botao_pagina_1:
            botao_pagina_1.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

        # Atualiza grid
        page.evaluate("atualizarCargas()")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        pagina = 1
        cargas_temp = []

        while True:
            if not navegador_ativo(page):
                print(f"[ERRO] {datetime.now()} - Navegador foi fechado durante a leitura. Encerrando ciclo.")
                break

            print(f"📄 Lendo página {pagina}...")
            page.wait_for_selector("#ctlLoadedControl_dgRight", timeout=10000)
            linhas = page.query_selector_all("#ctlLoadedControl_dgRight tr")[1:]

            for linha in linhas:
                colunas = linha.query_selector_all("td")
                if len(colunas) < 11:
                    continue

                carga = {
                    "dt": colunas[0].inner_text().strip(),
                    "peso": colunas[6].inner_text().strip(),
                    "regiao": colunas[9].inner_text().strip(),
                    "data_hora": colunas[10].inner_text().strip()
                }
                cargas_temp.append(carga)

            try:
                proximo = page.query_selector("#ctlLoadedControl_btnProximo")
                if proximo:
                    if proximo.get_attribute("disabled") is not None:
                        print("⛔ Botão [Próximo] desabilitado. Fim das páginas.")
                        break
                    print(f"➡️ Avançando para página {pagina + 1} via __doPostBack...")
                    page.evaluate("__doPostBack('ctlLoadedControl$btnProximo', '')")
                    page.wait_for_load_state("networkidle")
                    time.sleep(1.2)
                    pagina += 1
                else:
                    print("⛔ Botão [Próximo] não encontrado. Encerrando.")
                    break

            except Exception as e:
                print(f"[ERRO] {datetime.now()} - Falha ao avançar para próxima página: {e}")
                break

        print(f"✅ Total de {len(cargas_temp)} cargas coletadas.")
        cargas_lista.clear()
        cargas_lista.extend(cargas_temp)
        preencher_detalhes_das_cargas(context, page)
        salvar_cargas_em_json(cargas_lista)

    except Exception as e:
        print(f"❌ Erro no ciclo: {e}")



def salvar_cargas_em_json(cargas):
    """
    Salva a lista de cargas em:
    - cargas_ativas.json (atualiza tudo)
    - cargas_historico.json (acumula sem repetir DT)
    """
    os.makedirs("data", exist_ok=True)

    # 🔄 Salva cargas ativas
    with open(CAMINHO_ATIVAS, "w", encoding="utf-8") as f:
        json.dump(cargas, f, ensure_ascii=False, indent=2)

    # 🧠 Atualiza histórico sem duplicar DT
    historico = []
    if os.path.exists(CAMINHO_HISTORICO):
        with open(CAMINHO_HISTORICO, "r", encoding="utf-8") as f:
            historico = json.load(f)

    dts_existentes = {c["dt"] for c in historico if "dt" in c}
    novos = [c for c in cargas if c["dt"] not in dts_existentes]

    historico.extend(novos)

    with open(CAMINHO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

def carregar_detalhes_salvos():
    """Carrega o histórico de cargas detalhadas, se existir"""
    if os.path.exists(CAMINHO_HISTORICO):
        with open(CAMINHO_HISTORICO, "r", encoding="utf-8") as f:
            return {c["dt"]: c for c in json.load(f) if "dt" in c}
    return {}

def salvar_detalhes_no_historico(lista_atual):
    """Atualiza o histórico, sem duplicar DT"""
    historico = []
    if os.path.exists(CAMINHO_HISTORICO):
        with open(CAMINHO_HISTORICO, "r", encoding="utf-8") as f:
            historico = json.load(f)
    # Atualiza ou adiciona detalhes novos
    dts_historico = {c["dt"]: c for c in historico if "dt" in c}
    for c in lista_atual:
        if "origem" in c:  # Só salva se já foi detalhada
            dts_historico[c["dt"]] = c
    # Salva o histórico atualizado
    with open(CAMINHO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(list(dts_historico.values()), f, ensure_ascii=False, indent=2)

def coletar_itens_material(context, dt):
    """
    Acessa a página de itens/material da carga e retorna uma lista de itens:
    [
      {"material": "10018361", "descricao": "BQ 2,25X1300 SAE-1010", "unidade": "KG", "quantidade": "21.230,000"},
      ...
    ]
    """
    url = f"https://portal.e-fornecedores.ind.br/Printer.aspx?cmp=SUItemCargaProgramada.ascx&numdoc=00{dt}"
    print(f"🔍 Coletando ITENS/MATERIAL do DT {dt}...")
    itens = []
    try:
        page = context.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")

        html_tabela = page.evaluate("""
            () => {
                const tabela = document.querySelector('#_ctl8_dgItens');
                return tabela ? tabela.outerHTML : '';
            }
        """)
        page.close()

        if not html_tabela:
            print(f"⚠️ Não encontrou tabela de itens/material no DT {dt}")
            return itens

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_tabela, 'html.parser')
        linhas = soup.find_all("tr")[1:]  # pula cabeçalho

        for linha in linhas:
            colunas = linha.find_all("td")
            if len(colunas) >= 4:
                itens.append({
                    "material": colunas[0].text.strip(),
                    "descricao": colunas[1].text.strip(),
                    "unidade": colunas[2].text.strip(),
                    "quantidade": colunas[3].text.strip().replace('\n', '').replace('\r', '').replace('\xa0', '').strip()
                })
    except Exception as e:
        print(f"⚠️ Erro ao coletar itens/material do DT {dt}: {e}")
    return itens


def preencher_detalhes_das_cargas(context, page):
    """
    Enriquece cada carga da lista apenas se não detalhada ainda
    """
    detalhes_salvos = carregar_detalhes_salvos()
    cargas_modificadas = []

    for carga in cargas_lista:
        dt = carga["dt"]

        # Se já temos detalhes salvos, copia direto
        if dt in detalhes_salvos and all(campo in detalhes_salvos[dt] for campo in ["origem", "clientes", "municipio", "uf", "itens_material"]):
            carga.update({k: detalhes_salvos[dt][k] for k in ["origem", "clientes", "municipio", "uf", "itens_material"]})
            print(f"🔄 Detalhes carregados do histórico para DT {dt}")
            continue

        try:
            # Detalhes padrão (origem, clientes, etc)
            url = f"https://portal.e-fornecedores.ind.br/Printer.aspx?cmp=RemessaCargaProgramada.ascx&numdoc=00{dt}"
            print(f"🔍 Coletando detalhes do DT {dt}...")

            nova_aba = context.new_page()
            nova_aba.goto(url)
            nova_aba.wait_for_load_state("networkidle")

            html_tabela = nova_aba.evaluate("""
                () => {
                    const tabela = document.querySelector('#_ctl8_dgItens');
                    return tabela ? tabela.outerHTML : '';
                }
            """)
            nova_aba.close()

            if not html_tabela:
                print(f"⚠️ Não encontrou tabela de detalhes no DT {dt}")
                continue

            soup = BeautifulSoup(html_tabela, 'html.parser')
            linhas = soup.find_all("tr")[1:]  # ignora cabeçalho

            if not linhas:
                continue

            origem = linhas[0].find_all("td")[0].text.strip()
            clientes = []
            municipios = []
            ufs = []

            for linha in linhas:
                colunas = linha.find_all("td")
                if len(colunas) >= 6:
                    clientes.append(colunas[1].text.strip())
                    municipios.append(colunas[4].text.strip())
                    ufs.append(colunas[5].text.strip())

            carga["origem"] = origem
            carga["clientes"] = ", ".join(clientes)
            carga["municipio"] = ", ".join(municipios)
            carga["uf"] = ", ".join(ufs)

            # NOVO: itens/material detalhados
            carga["itens_material"] = coletar_itens_material(context, dt)

            print(f"✅ Origem/municípios/UF e ITENS preenchidos para {dt}")
            print("🔎 Carga detalhada:", carga)
            cargas_modificadas.append(carga)
        except Exception as e:
            print(f"⚠️ Erro ao preencher detalhes do DT {dt}: {e}")

    # Ao final, salva as modificações no histórico
    salvar_detalhes_no_historico(cargas_modificadas)





