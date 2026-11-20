#!/bin/bash
###############################################################################
# Food Menu — Fluxo de Trabalho Open Code
#
# Substitui o fluxo do GitHub Actions (nova-receita.yml / ci.yml) para ser
# executado diretamente pelo agente Open Code, sem depender de chaves de API
# externas nem de GitHub Actions.
#
# Comandos:
#   ./opencode-flow.sh nova-receita <arquivo_receita.json> [fonte]
#   ./opencode-flow.sh validar
#   ./opencode-flow.sh calibrar
#   ./opencode-flow.sh listar
#   ./opencode-flow.sh iniciar
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

CMD="${1:-}"

case "$CMD" in
  nova-receita)
    RECEITA_FILE="${2:-}"
    SOURCE="${3:-Open Code}"
    if [[ -z "$RECEITA_FILE" ]]; then
      echo "Uso: ./opencode-flow.sh nova-receita <arquivo_receita.json> [fonte]"
      exit 1
    fi
    if [[ ! -f "$RECEITA_FILE" ]]; then
      echo "❌ Arquivo não encontrado: $RECEITA_FILE"
      exit 1
    fi
    echo "🍳 Processando receita com Open Code..."
    python scripts/opencode_recipe_agent.py --save "$RECEITA_FILE" --source "$SOURCE"
    ;;
  validar)
    echo "🔍 Validando integridade das receitas..."
    python scripts/validate_recipes.py
    ;;
  calibrar)
    echo "🍳 Re-calibrando porções de todas as receitas..."
    python scripts/fix_portions.py
    ;;
  listar)
    echo "📚 Listando receitas..."
    python scripts/opencode_recipe_agent.py --list
    ;;
  iniciar)
    echo "🚀 Iniciando servidor Food Menu..."
    ./run.sh
    ;;
  *)
    echo "Uso: ./opencode-flow.sh <comando> [args]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  nova-receita <arquivo.json> [fonte]  Processar e salvar uma nova receita"
    echo "  validar                               Validar integridade de todas as receitas"
    echo "  calibrar                              Re-calibrar porções de todas as receitas"
    echo "  listar                                Listar todas as receitas cadastradas"
    echo "  iniciar                               Iniciar o servidor Flask (http://localhost:3000)"
    exit 1
    ;;
esac
