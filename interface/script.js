let todasCargas = [];
let filtros = {};  // { dt: [...], uf: [...], ... }
let ultimaOrdem = {
  coluna: null,
  direcao: 1 // 1 = crescente, -1 = decrescente
};

async function carregarCargas() {
    try {
        const resposta = await fetch('/api/cargas_ativas');
        const novasCargas = await resposta.json();

        // Evita atualização se não mudou nada
        if (JSON.stringify(novasCargas) === JSON.stringify(todasCargas)) {
            return; // Nada mudou
        }

        todasCargas = novasCargas;
        construirFiltros();
        aplicarFiltros();
        document.getElementById("status").innerText = `Última atualização: ${new Date().toLocaleTimeString()}`;
    } catch {
        document.getElementById("status").innerText = "Erro ao carregar cargas.";
    }
}


function construirFiltros() {
    const colunas = ["dt", "peso", "regiao", "data_hora", "origem", "municipio", "uf", "clientes"];
    colunas.forEach(col => {
        const valores = [...new Set(todasCargas.map(c => c[col] || ""))].sort();
        filtros[col] = valores;
    });
}

function aplicarFiltros() {
    let filtroSelecionado = recuperarFiltrosSalvos();

    // Atualiza o estado se o usuário marcou/desmarcou algo nos dropdowns abertos
    const ativos = document.querySelectorAll(".filtro-dropdown");
    ativos.forEach(drop => {
        const coluna = drop.dataset.coluna;
        const checks = drop.querySelectorAll("input[type=checkbox]:checked");
        filtroSelecionado[coluna] = Array.from(checks).map(i => i.value);
    });
    localStorage.setItem("filtrosCargas", JSON.stringify(filtroSelecionado));

    // ===== AQUI ESTAVA FALTANDO =====
    const filtradas = todasCargas.filter(carga =>
        Object.entries(filtroSelecionado).every(([col, valores]) =>
            !valores || valores.length === 0 || valores.includes(carga[col] || "")
        )
    );

    // Ordenação, se houver
    if (ultimaOrdem.coluna) {
        filtradas.sort((a, b) => {
            let va = a[ultimaOrdem.coluna] || "";
            let vb = b[ultimaOrdem.coluna] || "";
            if (!isNaN(Number(va)) && !isNaN(Number(vb))) {
                va = Number(va);
                vb = Number(vb);
            }
            if (va < vb) return -1 * ultimaOrdem.direcao;
            if (va > vb) return 1 * ultimaOrdem.direcao;
            return 0;
        });
    }

    renderizarTabela(filtradas);
}


function renderizarTabela(cargas) {
    const corpo = document.querySelector("#tabela-cargas tbody");
    corpo.innerHTML = "";
    cargas.forEach(carga => {
        const linha = document.createElement("tr");
        linha.innerHTML = `
          <td data-fulltext="${carga.dt}">${carga.dt}</td>
          <td data-fulltext="${carga.peso}">${carga.peso}</td>
          <td data-fulltext="${carga.regiao}">${carga.regiao}</td>
          <td data-fulltext="${carga.data_hora}">${carga.data_hora}</td>
          <td data-fulltext="${carga.origem || ''}">${carga.origem || ''}</td>
          <td data-fulltext="${carga.municipio || ''}">${carga.municipio || ''}</td>
          <td data-fulltext="${carga.uf || ''}">${carga.uf || ''}</td>
          <td data-fulltext="${(carga.clientes || '').split(', ').join('\n')}">${carga.clientes || ''}</td>
        `;



        corpo.appendChild(linha);
    });
}



function abrirFiltro(botao) {
    fecharTodosFiltros();

    const th = botao.parentElement;
    const coluna = th.dataset.coluna;
    const valores = filtros[coluna] || [];

    const container = document.createElement("div");
    container.className = "filtro-dropdown";
    container.dataset.coluna = coluna;

    valores.forEach(v => {
        const label = document.createElement("label");
        const checked = recuperarFiltrosSalvos()[coluna]?.includes(v);
        label.innerHTML = `<input type="checkbox" value="${v}" ${checked ? "checked" : ""}> ${v || "<vazio>"}`;
        container.appendChild(label);
    });

    container.addEventListener("change", aplicarFiltros);

    const wrapper = document.createElement("div");
    wrapper.className = "filtro-container show";
    wrapper.appendChild(container);
    th.appendChild(wrapper);

    document.addEventListener("click", function fechar(e) {
        if (!th.contains(e.target)) {
            wrapper.remove();
            document.removeEventListener("click", fechar);
        }
    });
}

function recuperarFiltrosSalvos() {
    const salvos = localStorage.getItem("filtrosCargas");
    return salvos ? JSON.parse(salvos) : {};
}

function fecharTodosFiltros() {
    document.querySelectorAll(".filtro-container").forEach(e => e.remove());
}

function restaurarOrdemColunas() {
    const ordemSalva = JSON.parse(localStorage.getItem("ordemColunas"));
    if (!ordemSalva) return;

    const tabela = document.getElementById("tabela-cargas");
    const header = tabela.querySelector("thead tr");
    const headers = Array.from(header.children);
    ordemSalva.forEach(index => header.appendChild(headers[index]));
    for (let row of tabela.tBodies[0].rows) {
        const cells = Array.from(row.children);
        ordemSalva.forEach(index => row.appendChild(cells[index]));
    }
}

function salvarOrdemColunas() {
    const header = document.querySelector("#tabela-cargas thead tr");
    const ordem = Array.from(header.children).map(th => th.cellIndex);
    localStorage.setItem("ordemColunas", JSON.stringify(ordem));
}
// Drag & Drop reativo com persistência
const headers = document.querySelectorAll("th");
let dragSrcEl = null;
headers.forEach(th => {
    th.addEventListener("dragstart", e => {
        dragSrcEl = th;
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/html", th.innerHTML);
    });
    th.addEventListener("dragover", e => e.preventDefault());
    th.addEventListener("drop", e => {
        e.preventDefault();
        if (dragSrcEl !== th) {
            const srcIndex = dragSrcEl.cellIndex;
            const tgtIndex = th.cellIndex;
            const tabela = document.getElementById("tabela-cargas");
            for (let linha of tabela.rows) {
                const cells = [...linha.cells];
                if (srcIndex < tgtIndex) {
                    linha.insertBefore(cells[srcIndex], cells[tgtIndex].nextSibling);
                } else {
                    linha.insertBefore(cells[srcIndex], cells[tgtIndex]);
                }
            }
            salvarOrdemColunas();
        }
    });
});

// Função para ordenação crescente/decrescente
function ordenarColuna(botao) {
    const th = botao.parentElement;
    const coluna = th.dataset.coluna;

    // Remove destaque de ordenação de outras colunas
    document.querySelectorAll("#tabela-cargas thead th").forEach(thh => thh.classList.remove("ordenada"));

    if (ultimaOrdem.coluna === coluna) {
        ultimaOrdem.direcao *= -1; // alterna direção
    } else {
        ultimaOrdem.coluna = coluna;
        ultimaOrdem.direcao = 1;
    }
    th.classList.add("ordenada");

    aplicarFiltros(); // já ordena os dados filtrados!
}

// Funções de integração backend (mantém igual)
async function iniciar() {
    const res = await fetch('/api/iniciar');
    const data = await res.json();
    document.getElementById('saida').innerText = data.mensagem;
}
async function parar() {
    const res = await fetch('/api/parar');
    const data = await res.json();
    document.getElementById('saida').innerText = data.mensagem;
}
async function status() {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('saida').innerText = "Status: " + data.status;
}
// Função para criar e exibir menu de contexto na grid




// Inicialização
setInterval(carregarCargas, 5000);
carregarCargas();
restaurarOrdemColunas();

