# AGENTS.md — Food Menu (Frontend Estático + GitHub Actions CI/CD)

Este arquivo instrui o agente Open Code sobre como trabalhar com o projeto Food Menu.

O frontend é **100% estático** (HTML/JS/CSS) e lê receitas diretamente do GitHub via **GitHub Raw** (opção A). Não há servidor backend obrigatório.

O projeto suporta **dois fluxos** para cadastro de receitas:

| Fluxo | Como funciona | Custo | Automação |
|-------|--------------|-------|-----------|
| **A — Semi-automático (Open Code local)** | Agente estrutura a receita e salva via `opencode_recipe_agent.py` | Grátis | Manual (sob demanda) |
| **B — Automático (GitHub Actions)** | Issue/PR dispara `recipe_agent.py` com IA no CI/CD e commita direto | Grátis (Gemini free tier) | Automático via webhook |

---

## Visão Geral

Sistema web estático para planejar cardápios semanais com base em um banco de receitas versionado no GitHub, calcular lista de compras e gerar guia de preparo em lote.

**Stack:** HTML/CSS/JS vanilla (frontend estático), persistência em arquivos JSON no GitHub.

**Rodando:** Abra `static/index.html` diretamente no navegador (não precisa de servidor).

---

## Estrutura de Diretórios

```
food-menu/
├── readme.md           # Documentação do usuário
├── AGENTS.md           # Este arquivo (instruções para o agente)
├── .mcp.json           # Configuração de servidores MCP
├── .gitignore
├── app.py              # Backend Flask (mantido por compatibilidade, não necessário)
├── run.sh              # Script para iniciar servidor Flask (opcional)
├── Procfile            # gunicorn app:app (opcional)
├── requirements.txt    # Dependências Python (apenas se usar app.py)
├── recipes/            # Banco de receitas (arquivos .json individuais)
├── cardapios/          # Cardápios versionados no GitHub (opcional)
├── static/             # Frontend estático
│   ├── index.html      # Gerador de Cardápios
│   ├── script.js       # Lógica do Gerador (lê do GitHub Raw)
│   ├── recipes.html    # Gerenciador de Receitas
│   ├── recipes.js      # Lógica do Gerenciador (lê do GitHub Raw)
│   ├── print.html      # Visualização para Impressão
│   ├── print.js        # Lógica de consolidação e renderização
│   └── style.css       # Estilos compartilhados
├── scripts/            # Utilitários Python
│   ├── portion_calculator.py   # Cálculo peso cru/cozido e porções
│   ├── validate_recipes.py     # Validador de integridade das receitas
│   ├── fix_portions.py         # Re-calibra porções de todas as receitas
│   ├── recipe_agent.py         # Agente original (usa GEMINI_API_KEY no CI/CD)
│   ├── opencode_recipe_agent.py # Agente Open Code local (sem chaves externas)
│   └── opencode_github_flow.py # Validador local de issues/PRs via GitHub API
└── .github/            # GitHub Actions CI/CD
    ├── workflows/
    │   ├── ci.yml              # Valida integridade de receitas em push/PR
    │   └── nova-receita.yml    # Agente de IA processa issues/PRs de receita
    ├── ISSUE_TEMPLATE/
    │   └── nova_receita.yml
    └── PULL_REQUEST_TEMPLATE.md
```

---

## Configuração do Frontend Estático

As URLs do GitHub estão definidas no topo de cada arquivo JS:

**`static/script.js` e `static/recipes.js`:**
```js
const GITHUB_OWNER = 'rflucas-personal';
const GITHUB_REPO = 'food-menu';
const GITHUB_BRANCH = 'main';
const GITHUB_API_BASE = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}`;
const GITHUB_RAW_BASE = `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_BRANCH}`;
```

Se mudar o repositório, atualize essas constantes.

---

## Fluxo B — CI/CD Automatizado (GitHub Actions)

Uma Issue com label `nova-receita` ou um PR com label `receita` dispara o GitHub Actions:
1. `recipe_agent.py` processa a receita com IA (Gemini/OpenAI)
2. `validate_recipes.py` valida todas as receitas
3. O bot commita `recipes/<slug>.json` direto na `main`, comenta e fecha a issue/PR

**Pré-requisito no GitHub:**
- Settings → Secrets and variables → Actions → New repository secret
- Nome: `GEMINI_API_KEY` (recomendado) ou `OPENAI_API_KEY`

---

## Fluxo A — Semi-automático (Open Code Local)

```bash
# O agente Open Code estrutura a receita e salva
python scripts/opencode_recipe_agent.py --save receita.json --source "Open Code"

# Valida todas as receitas
python scripts/validate_recipes.py

# Re-calibra porções
python scripts/fix_portions.py
```

**Não use** `scripts/recipe_agent.py` original para novas receitas localmente — ele requer `GEMINI_API_KEY` ou `OPENAI_API_KEY`.

---

## MCP GitHub — Validações Locais

O agente Open Code pode usar o **MCP `github`** (configurado em `.mcp.json`) para:

- Listar issues com label `nova-receita`
- Comentar em issues/PRs
- Fechar issues após commit
- Criar branches e commitar receitas
- Verificar status do pipeline CI

Exemplo de uso pelo agente (via ferramentas MCP do Open Code):

```
MCP github: list issues with label nova-receita
MCP github: comment on issue #123 with recipe processing summary
MCP git: commit recipes/ and push to main
```

Comando local alternativo:

```bash
export GITHUB_TOKEN="ghp_xxx"
python scripts/opencode_github_flow.py --owner rflucas-personal --repo food-menu --process
```

---

## Como Executar

```bash
# Abrir o frontend estático diretamente no navegador
open static/index.html

# Ou servir estaticamente (opcional)
python3 -m http.server 8000 --directory static
# Acesse http://localhost:8000/index.html

# Validar receitas
python scripts/validate_recipes.py

# Calibrar porções
python scripts/fix_portions.py
```

---

## Deploy no Google Pages

Por ser 100% estático, o projeto está pronto para Google Pages:

1. Faça push do código para o GitHub (`rflucas-personal/food-menu`)
2. Configure o Google Pages para servir a pasta `static/`
3. Acesse a URL do seu site

O `print.html` aceita um parâmetro URL `?file=<url-do-cardapio-json>` para visualizar/imprimir um cardápio específico.

---

## Convenções de Código

- Nomes de arquivos de receitas em kebab-case: `frango-empanado.json`
- Título da receita com primeira letra maiúscula
- `tipo`: `proteina`, `acompanhamento` ou `complemento`
- `porcoes`: inteiro positivo
- Tags em letras minúsculas
- Código Python segue PEP 8
- Frontend em Vanilla JS/CSS (sem frameworks)

---

## Exemplos de Comandos Úteis

```bash
# Abrir frontend estático
open static/index.html

# Validar receitas
python scripts/validate_recipes.py

# Calibrar porções
python scripts/fix_portions.py

# Salvar nova receita (Fluxo A - Open Code local)
python scripts/opencode_recipe_agent.py --save receita.json --source "Open Code"

# Listar receitas
python scripts/opencode_recipe_agent.py --list

# Validar issues do GitHub (suporte local Fluxo B)
export GITHUB_TOKEN="ghp_xxx"
python scripts/opencode_github_flow.py --owner rflucas-personal --repo food-menu --process
```

---

## Estrutura de Dados de uma Receita

```json
{
  "titulo": "Nome da Receita",
  "porcoes": 4,
  "tags": ["frango", "forno"],
  "tipo": "proteina",
  "ingredientes": [
    {
      "nome": "Frango",
      "quantidade": [
        { "quantidade": 1.0, "unidade_de_medida": "kg" }
      ]
    }
  ],
  "modo_de_preparo": [
    "Passo 1",
    "Passo 2"
  ],
  "fonte": "Issue #123"
}
```

Um ingrediente pode ter múltiplas quantidades. Quando `quantidade` é `0` e `unidade_de_medida` é `"a gosto"`, o ingrediente não é escalado matematicamente.
