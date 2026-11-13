# 🍱 Food Menu — Planejador de Cardápios e Marmitas

Sistema web para planejar cardápios semanais com base em um banco de receitas local, calcular automaticamente a lista de compras e gerar um guia de preparo em lote (*batch cooking*) pronto para impressão.

## Índice

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Entidades e Estrutura de Dados](#entidades-e-estrutura-de-dados)
- [Regras de Negócio](#regras-de-negócio)
- [Requisitos](#requisitos)
- [Como Executar](#como-executar)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [API REST](#api-rest)
- [Contribuindo](#contribuindo)

---

## Visão Geral

O **Food Menu** resolve o problema de planejar refeições para vários dias de forma prática. Você seleciona as receitas desejadas, indica quantas porções precisa, e o sistema:

1. **Escala os ingredientes** matematicamente para o número de porções escolhido.
2. **Consolida a lista de compras** somando ingredientes iguais de receitas diferentes.
3. **Gera um guia de preparo** com receitas unificadas (sem repetição) e um roteiro de montagem das marmitas.
4. Salva tudo em um arquivo JSON local, pronto para consulta ou impressão.

---

## Funcionalidades

### Gerador de Cardápios (`index.html`)
- Definir a quantidade de dias do cardápio (1 dia = 2 porções: almoço e jantar).
- Construir refeições selecionando proteína, acompanhamento e complementos.
- Barra de progresso visual indicando quantas porções faltam para completar a meta.
- Geração do cardápio em JSON com ingredientes escalados automaticamente.

### Visualizador de Cardápios (`print.html`)
- Tela dedicada e separada, otimizada para impressão em papel (fundo branco, sem cores desnecessárias).
- **Lista de Compras Consolidada**: Soma todos os ingredientes de todas as receitas do cardápio.
- **Guia de Cozimento**: Receitas consolidadas (se a mesma receita aparece em mais de uma refeição, ela é exibida uma única vez com os totais somados).
- **Guia de Montagem das Marmitas**: Roteiro indicando quantas marmitas montar para cada refeição e quais preparos incluir.

### Gerenciador de Receitas (`recipes.html`)
- Visualizar, editar e criar receitas diretamente pela interface web.
- Formulário dinâmico para ingredientes (com múltiplas unidades de medida) e modo de preparo.
- Busca por texto para localizar receitas rapidamente.
- As alterações são salvas diretamente nos arquivos JSON em `recipes/`.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    NAVEGADOR (Frontend)                  │
│                                                         │
│  index.html ─── script.js    (Gerador de Cardápios)     │
│  recipes.html ─ recipes.js   (Gerenciador de Receitas)  │
│  print.html ─── print.js     (Visualização / Impressão) │
│  style.css                   (Estilos compartilhados)   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (REST API)
┌────────────────────────▼────────────────────────────────┐
│                   SERVIDOR (Backend)                     │
│                                                         │
│  app.py (Flask)                                         │
│  ├── Serve arquivos estáticos de static/                │
│  ├── Lê/Escreve receitas de recipes/*.json              │
│  ├── Escala ingredientes (scale_ingredients)             │
│  └── Gera/Lista cardápios em cardapios/*.json           │
└────────────────────────┬────────────────────────────────┘
                         │ Sistema de Arquivos
┌────────────────────────▼────────────────────────────────┐
│                  DADOS (Arquivos JSON)                   │
│                                                         │
│  recipes/         → Banco de receitas (fonte de verdade)│
│  cardapios/       → Cardápios gerados (saída)           │
└─────────────────────────────────────────────────────────┘
```

**Stack tecnológica:**
- **Backend**: Python 3 + Flask
- **Frontend**: HTML, CSS (Vanilla) e JavaScript (Vanilla)
- **Persistência**: Arquivos JSON no sistema de arquivos local (sem banco de dados)

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

Um cardápio é a coleção de refeições planejadas para um período de dias. Cada cardápio é salvo como um arquivo JSON na pasta `cardapios/`.

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

- **Python** 3.10+
- **Flask** 3.x
- Navegador moderno (Chrome, Firefox, Edge)

### Dependências Python
```
flask
```

---

## Como Executar

```bash
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd food-menu

# 2. Criar o ambiente virtual (uma única vez)
python3 -m venv .venv

# 3. Instalar dependências (uma única vez)
.venv/bin/pip install flask

# 4. Iniciar o servidor
./run.sh
```

O servidor sobe em `http://localhost:3000`. O script `run.sh` ativa o ambiente virtual automaticamente.

---

## Estrutura de Diretórios

```
food-menu/
├── app.py              # Backend Flask (API REST + servidor estático)
├── run.sh              # Script para iniciar a aplicação
├── readme.md           # Este documento
├── recipes/            # Banco de receitas (arquivos JSON individuais)
│   ├── arroz-branco.json
│   ├── frango-empanado.json
│   ├── legumes-assados.json
│   └── ... (60 receitas)
├── cardapios/          # Cardápios gerados pelo sistema
│   ├── cardapio_20260426_130628.json
│   └── ...
├── static/             # Frontend (servido pelo Flask)
│   ├── index.html      # Página: Gerador de Cardápios
│   ├── script.js       # Lógica do Gerador
│   ├── recipes.html    # Página: Gerenciador de Receitas
│   ├── recipes.js      # Lógica do Gerenciador
│   ├── print.html      # Página: Visualização para Impressão
│   ├── print.js        # Lógica de consolidação e renderização
│   └── style.css       # Estilos compartilhados (Light Mode)
└── .venv/              # Ambiente virtual Python (não versionado)
```

---

## API REST

| Método | Rota                        | Descrição                                           |
| ------ | --------------------------- | --------------------------------------------------- |
| `GET`  | `/api/recipes`              | Lista todas as receitas disponíveis                 |
| `GET`  | `/api/recipes/<id>`         | Retorna uma receita específica pelo nome do arquivo |
| `POST` | `/api/recipes`              | Cria uma nova receita                               |
| `PUT`  | `/api/recipes/<id>`         | Atualiza uma receita existente                      |
| `POST` | `/api/generate`             | Gera um cardápio com ingredientes escalados         |
| `GET`  | `/api/cardapios`            | Lista todos os cardápios gerados                    |
| `GET`  | `/api/cardapios/<filename>` | Retorna o conteúdo de um cardápio específico        |

---

## Contribuindo

### Adicionando Receitas

A forma mais simples de contribuir é adicionando novas receitas. Você pode fazer isso de duas maneiras:

1. **Pela interface web**: Acesse `http://localhost:3000/recipes.html`, clique em **"+ Nova"** e preencha o formulário.
2. **Manualmente**: Crie um arquivo `.json` na pasta `recipes/` seguindo a [estrutura de dados da Receita](#receita).

3. **Via GitHub Automático (Agente IA)**:
   - **Pelo Pull Request**: Abra um PR com o título `[Receita] Nome` e cole os ingredientes/preparo no corpo. O Agente de IA formata o JSON, calibra as porções com base no rendimento cru/cozido e commita automaticamente na `main`.
   - **Pela Issue (ótimo no celular)**: Abra uma Issue com a tag `nova-receita` ou use o template de Nova Receita. O Agente processa, gera o commit na `main` e fecha a Issue com o preview da receita.

### Desenvolvendo e Validando

```bash
# Rodar em modo de desenvolvimento (hot-reload ativado por padrão)
./run.sh

# Validar integridade de todas as receitas
python scripts/validate_recipes.py

# Re-calibrar porções com base no peso cozido e rendimento
python fix_portions.py
```

**Convenções:**
- Nomes de arquivos de receitas em kebab-case: `frango-empanado.json`
- Código Python segue PEP 8
- Frontend em Vanilla JS/CSS (sem frameworks ou bundlers)
- Persistência exclusivamente via arquivos JSON locais (sem banco de dados)

### Fluxo de Contribuição

1. Crie uma branch a partir de `main`
2. Faça suas alterações
3. Teste localmente (`./run.sh`)
4. Abra um Pull Request com a descrição das mudanças
