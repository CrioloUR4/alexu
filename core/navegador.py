from playwright.sync_api import sync_playwright
from core.dados import ler_dados_config

CONTEXTO_GLOBAL = {}
def iniciar_navegador(playwright):
    login, senha, fornecedor, _, _ = ler_dados_config()

    browser = playwright.chromium.launch(channel="msedge", headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://portal.e-fornecedores.ind.br/default.aspx?cmp=noticias.ascx")
    page.fill("#ctlLoadedControl_txtLogin", login)
    page.fill("#ctlLoadedControl_txtSenha", senha)
    page.press("#ctlLoadedControl_txtSenha", "Enter")

    page.wait_for_selector("#mnuPrincipal_lstEmpresas", timeout=10000)
    page.select_option("#mnuPrincipal_lstEmpresas", "85")

    if fornecedor.lower() == "matriz":
        page.select_option("#mnuPrincipal_lstFornecedor", "222063:0000110588:N")
    else:
        page.select_option("#mnuPrincipal_lstFornecedor", "222063:0000109475:N")

    page.wait_for_load_state("networkidle")
    # Salva no global!

    CONTEXTO_GLOBAL["context"] = context
    CONTEXTO_GLOBAL["page"] = page
    return context, page
