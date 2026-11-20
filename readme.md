# 🍱 Food Menu — Planejador de Cardápios e Marmitas

Sistema web estático para planejar cardápios semanais com base em um banco de receitas versionado no GitHub, calcular automaticamente a lista de compras e gerar um guia de preparo em lote (*batch cooking*) pronto para impressão.

O frontend é **100% estático** (HTML/JS/CSS) e lê as receitas diretamente do GitHub via **GitHub Raw** (opção A), sem necessidade de servidor backend.

## Índice

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Entidades e Estrutura de Dados](#entidades-e-estrutura-de-dados)
- [Regras de Negócio](#regras-de-negócio)
- [Requisitos](#requisitos)
- [Como Executar](#como-executar)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Servidores MCP](#servidores-mcp)
- [Dois Fluxos de Trabalho](#dois-fluxos-de-trabalho)
- [Contribuindo](#contribuindo)

---

## Visão Geral

O **Food Menu** resolve o problema de planejar refeições para vários dias de forma prática. Você seleciona as receitas desejadas, indica quantas porções precisa, e o sistema:

1. **Escala os ingredientes** matematicamente para o número de porções escolhido.
2. **Consolida a lista de compras** somando ingredientes iguais de receitas diferentes.
3. **Gera um guia de preparo** com receitas unificadas (sem repetição) e um roteiro de montagem das marmitas.
4. Gera um arquivo `.json` para download, pronto para consulta ou impressão.

---

## Funcionalidades

### Gerador de Cardápios (`index.html`)
- Definir a quantidade de dias do cardápio (1 dia = 2 porções: almoço e jantar).
- Construir refeições selecionando proteína, acompanhamento e complementos.
- Barra de progresso visual indicando quantas porções faltam para completar a meta.
- Geração do cardápio em JSON com ingredientes escalados automaticamente (feito no navegador).
- Download do arquivo `cardapio_YYYYMMDD_HHMMSS.json`.

### Visualizador de Cardápios (`print.html`)
- Tela dedicada e separada, otimizada para impressão em papel (fundo branco, sem cores desnecessárias).
- Aceita um arquivo JSON de cardápio via parâmetro URL (`?file=<url-do-json>`).
- **Lista de Compras Consolidada**: Soma todos os ingredientes de todas as receitas do cardápio.
- **Guia de Cozimento**: Receitas consolidadas (se a mesma receita aparece em mais de uma refeição, ela é exibida uma única vez com os totais somados).
- **Guia de Montagem das Marmitas**: Roteiro indicando quantas marmitas montar para cada refeição e quais preparos incluir.

### Gerenciador de Receitas (`recipes.html`)
- Visualizar e editar receitas diretamente pela interface web (leituras via GitHub Raw).
- Formulário dinâmico para ingredientes (com múltiplas unidades de medida) e modo de preparo.
- Busca por texto para localizar receitas rapidamente.
- **Salvar**: Como é frontend estático sem backend, o botão "Salvar" abre uma Issue no GitHub com o template de Nova Receita. O agente de IA processa e commita automaticamente via GitHub Actions.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    NAVEGADOR (Frontend Estático)         │
│                                                         │
│  index.html ─── script.js    (Gerador de Cardápios)     │
│  recipes.html ─ recipes.js   (Gerenciador de Receitas)  │
│  print.html ─── print.js     (Visualização / Impressão) │
│  style.css                   (Estilos compartilhados)   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS (GitHub API + Raw)
┌────────────────────────▼────────────────────────────────┐
│                 GITHUB (rflucas-personal/food-menu)     │
│                                                         │
│  └─ recipes/      → Banco de receitas (fonte de verdade)│
│  └─ cardapios/    → Cardápios versionados (opcional)    │
│  └─ .github/      → Workflows CI/CD (Issues → IA)       │
└─────────────────────────────────────────────────────────┘
```

**Stack tecnológica:**
- **Frontend**: HTML, CSS (Vanilla) e JavaScript (Vanilla) — 100% estático
- **Persistência**: Arquivos JSON versionados no GitHub (sem servidor, sem banco de dados)
- **Leitura de receitas**: GitHub API (listar pasta) + GitHub Raw (baixar arquivos)
- **Cadastro de receitas**: GitHub Issues + GitHub Actions + `recipe_agent.py` (IA)

---

## Entidades e Estrutura de Dados

### Receita

Uma receita é a unidade fundamental do sistema. Cada receita é um arquivo `.json` individual dentro da pasta `recipes/`.

```json
{
  "titulo": "Almôndega de Carne com Molho de Tomate",
  "porcoes": 20,
  "tags": ["carne", "almondega", "molho-de-tomate", "panela"],
  "tipo": "proteina",
  "ingredientes": [
    {
      "nome": "Carne moída",
      "quantidade": [
        { "quantidade": 1.2, "unidade_de_medida": "kg" }
      ]
    },
    {
      "nome": "Sal",
      "quantidade": [
        { "quantidade": 0.0, "unidade_de_medida": "a gosto" }
      ]
    }
  ],
  "modo_de_preparo": [
    "Misturar a carne moída com farinha de aveia, ovo, sal e pimenta-do-reino.",
    "Moldar as almôndegas e assar no forno a 200°C por 25 minutos."
  ],
  "fonte": "Marmitas da Semana - Cardápio 4"
}
```

| Campo             | Tipo            | Descrição                                                               |
| ----------------- | --------------- | ----------------------------------------------------------------------- |
| `titulo`          | `string`        | Nome da receita                                                         |
| `porcoes`         | `number`        | Quantidade de porções que a receita rende na proporção original         |
| `tags`            | `string[]`      | Palavras-chave para categorização                                       |
| `tipo`            | `string`        | Classificação da receita: `proteina`, `acompanhamento` ou `complemento` |
| `ingredientes`    | `Ingrediente[]` | Lista de ingredientes com quantidades                                   |
| `modo_de_preparo` | `string[]`      | Lista ordenada de passos de preparo                                     |
| `fonte`           | `string`        | Referência de onde a receita foi extraída                               |

### Ingrediente

```json
{
  "nome": "Carne moída",
  "quantidade": [
    { "quantidade": 1.2, "unidade_de_medida": "kg" }
  ]
}
```

Um ingrediente pode ter **múltiplas quantidades** com unidades de medida distintas (ex: peso e volume). Quando a `quantidade` é `0.0` e a `unidade_de_medida` é `"a gosto"`, o ingrediente não é escalado matematicamente.

### Refeição

Uma refeição é a composição de receitas que formam um prato completo:

| Componente     | Quantidade | Obrigatório |
| -------------- | ---------- | ----------- |
| Proteína       | 1          | Sim         |
| Acompanhamento | 1          | Sim         |
| Complemento(s) | 1 ou mais  | Sim         |

### Cardápio

Um cardápio é a coleção de refeições planejadas para um período de dias.

```json
[
  {
    "refeicao_id": 1,
    "porcoes_desejadas": 4,
    "receitas": [
      {
        "titulo": "Frango Empanado",
        "tipo": "proteina",
        "porcoes": 4,
        "ingredientes": [ "..." ],
        "modo_de_preparo": [ "..." ],
        "fonte": "..."
      }
    ]
  }
]
```

---

## Regras de Negócio

### Planejamento
1. **1 dia = 2 porções** (almoço e jantar). Se o usuário configura 7 dias, a meta total é de 14 porções.
2. O gerador de cardápio só permite a finalização quando a soma das porções de todas as refeições atinge exatamente a meta calculada.
3. Cada refeição deve conter pelo menos uma proteína, um acompanhamento e um complemento.

### Escalonamento de Ingredientes
4. A quantidade de cada ingrediente é multiplicada por um **fator de escala**: `porções_desejadas / porções_originais_da_receita`.
5. Quantidades numéricas são arredondadas para **2 casas decimais**.
6. Quantidades textuais (ex: `"a gosto"`) **não são escaladas** e são preservadas como estão.

### Consolidação (Tela de Impressão)
7. **Ingredientes** iguais (mesmo nome e unidade) de receitas diferentes são **somados** na lista de compras.
8. **Receitas** iguais (mesmo título) de refeições diferentes são **consolidadas**: suas porções e ingredientes são somados, e o modo de preparo é exibido uma única vez.
9. Itens com quantidade `"a gosto"` aparecem uma única vez na lista consolidada, sem repetição.

### Receitas
10. O nome do arquivo de uma receita é o *slug* do título (ex: `"Parmegiana de Frango"` → `parmegiana-de-frango.json`).
11. Não é possível criar duas receitas com o mesmo título (o sistema rejeita a duplicidade).

---

## Requisitos

- Navegador moderno (Chrome, Firefox, Edge)
- Acesso à internet (para ler receitas do GitHub Raw)

Não é necessário instalar Python, Flask ou qualquer servidor para usar o frontend estático.

---

## Como Executar

### Apenas abrir no navegador

Como é um frontend estático, basta abrir o arquivo `static/index.html` diretamente no navegador:

```bash
# Abrir diretamente
open static/index.html

# Ou usar qualquer servidor estático simples (opcional)
python3 -m http.server 8000 --directory static
# Acesse http://localhost:8000/index.html
```

### Deploy no Google Pages

O projeto está pronto para deploy no **Google Pages** (ou GitHub Pages, Netlify, Vercel, etc.) por ser 100% estático:

1. Faça push do código para o GitHub
2. Configure o Google Pages para servir a pasta `static/`
3. Acesse a URL do seu site

---

## Estrutura de Diretórios

```
food-menu/
├── readme.md           # Este documento
├── AGENTS.md           # Instruções para o agente Open Code
├── .mcp.json           # Configuração de servidores MCP
├── .gitignore
├── app.py              # Backend Flask (mantido por compatibilidade, não necessário)
├── run.sh              # Script para iniciar o servidor Flask (opcional)
├── Procfile            # gunicorn app:app (opcional)
├── requirements.txt    # Dependências Python (apenas se usar app.py)
├── recipes/            # Banco de receitas (arquivos .json individuais)
│   ├── arroz-branco.json
│   ├── frango-empanado.json
│   └── ... (60 receitas)
├── cardapios/          # Cardápios versionados no GitHub (opcional)
│   └── cardapio_20260426_130628.json
├── static/             # Frontend estático
│   ├── index.html      # Página: Gerador de Cardápios
│   ├── script.js       # Lógica do Gerador (lê do GitHub Raw)
│   ├── recipes.html    # Página: Gerenciador de Receitas
│   ├── recipes.js      # Lógica do Gerenciador (lê do GitHub Raw)
│   ├── print.html      # Página: Visualização para Impressão
│   ├── print.js        # Lógica de consolidação e renderização
│   └── style.css       # Estilos compartilhados (Light Mode)
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

## Servidores MCP

O projeto está configurado com os seguintes servidores MCP (definidos em `.mcp.json`) para trabalhar com Open Code:

| Servidor | Utilidade no projeto |
|----------|---------------------|
| `filesystem` | Ler e gravar arquivos de `recipes/`, `cardapios/`, `static/` e `scripts/` |
| `git` | Operações Git: commit, branch, diff, log, push |
| `memory` | Memória persistente para contexto do projeto entre sessões do Open Code |
| `sequential-thinking` | Raciocínio passo a passo para planejamento de cardápios e validação de receitas |
| `github` | Issues, PRs e comentários (opcional, requer `GITHUB_PERSONAL_ACCESS_TOKEN`) |
| `fetch` | Busca de conteúdo web para receitas externas e referências |

---

## Dois Fluxos de Trabalho

O projeto suporta dois modos de operação:

| Fluxo | Como funciona | Custo | Automação |
|-------|--------------|-------|-----------|
| **A — Semi-automático (Open Code local)** | O agente Open Code estrutura a receita e salva via `opencode_recipe_agent.py` | Grátis | Manual (sob demanda) |
| **B — Automático (GitHub Actions)** | Issue/PR dispara `recipe_agent.py` com IA no CI/CD e commita direto | Grátis (Gemini free tier) | Automático via webhook |

---

### Fluxo B — CI/CD Automatizado (Recomendado)

Uma Issue com label `nova-receita` ou um PR com label `receita` dispara o GitHub Actions, que executa o `recipe_agent.py` com IA, valida as receitas, commita direto na `main`, comenta e fecha a issue/PR automaticamente.

**Pré-requisito no GitHub:**
- Settings → Secrets and variables → Actions → New repository secret
- Nome: `GEMINI_API_KEY` (recomendado, tem free tier) ou `OPENAI_API_KEY`

**Como usar:**
1. Abra uma Issue com o template "🍳 Cadastrar Nova Receita" ou um PR com label `receita`.
2. O workflow `.github/workflows/nova-receita.yml` processa a receita com IA.
3. O bot commita `recipes/<slug>.json`, comenta e fecha a issue/PR.
4. O workflow `.github/workflows/ci.yml` valida a integridade de todas as receitas em cada push/PR.

---

### Fluxo A — Semi-automático (Open Code Local)

Se preferir não usar GitHub Actions nem chave de API, processe receitas manualmente pelo agente Open Code:

```bash
python scripts/opencode_recipe_agent.py --save receita.json --source "Open Code"
```

O agente valida, calibra as porções com base no peso cozido e salva em `recipes/<slug>.json`.

**Não use** `scripts/recipe_agent.py` original para novas receitas localmente — ele requer `GEMINI_API_KEY` ou `OPENAI_API_KEY`. Use sempre `scripts/opencode_recipe_agent.py`.

---

### Adicionando Receitas (qualquer fluxo)

1. **Pela interface web**: Abra `recipes.html`, clique em **"+ Nova"** e preencha o formulário. Clicar em "Salvar" abrirá uma Issue no GitHub com os dados preenchidos.
2. **Manualmente**: Crie um arquivo `.json` na pasta `recipes/` seguindo a [estrutura de dados da Receita](#receita).
3. **Via Issue/PR (Fluxo B)**: Abra uma Issue ou PR no GitHub; o agente de IA processa automaticamente.

---

### Desenvolvendo e Validando

```bash
# Validar integridade de todas as receitas
python scripts/validate_recipes.py

# Re-calibrar porções com base no peso cozido e rendimento
python scripts/fix_portions.py

# Listar receitas (Open Code local)
python scripts/opencode_recipe_agent.py --list
```

**Convenções:**
- Nomes de arquivos de receitas em kebab-case: `frango-empanado.json`
- Título da receita com primeira letra maiúscula
- `tipo`: `proteina`, `acompanhamento` ou `complemento`
- `porcoes`: inteiro positivo
- Tags em letras minúsculas
- Código Python segue PEP 8
- Frontend em Vanilla JS/CSS (sem frameworks ou bundlers)
- Persistência exclusivamente via arquivos JSON locais (sem banco de dados)

---

### Fluxo de Contribuição (Fluxo B)

1. Abra uma Issue com o template "🍳 Cadastrar Nova Receita" ou um PR com label `receita`.
2. O GitHub Actions processa automaticamente com IA.
3. O bot commita a receita em `recipes/<slug>.json` e fecha a issue/comenta no PR.
4. O workflow `ci.yml` valida a integridade de todas as receitas em cada push/PR.

### Fluxo de Contribuição (Fluxo A - Open Code local)

1. Crie uma branch a partir de `main`
2. Adicione/edite receitas em `recipes/`
3. Teste localmente (abra `static/index.html` no navegador e `python scripts/validate_recipes.py`)
4. Abra um Pull Request com a descrição das mudanças
