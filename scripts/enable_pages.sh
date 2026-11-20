#!/bin/bash
###############################################################################
# Habilita o GitHub Pages no repositório com source "GitHub Actions"
# (build_type = workflow), usando o GITHUB_TOKEN do ambiente.
#
# Uso:
#   export GITHUB_TOKEN="ghp_xxx"   # token com scope 'repo'
#   ./scripts/enable_pages.sh [owner] [repo]
#
# Padrões: owner=rflucas-personal  repo=food-menu
###############################################################################

set -euo pipefail

OWNER="${1:-rflucas-personal}"
REPO="${2:-food-menu}"
API="https://api.github.com/repos/${OWNER}/${REPO}/pages"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "❌ GITHUB_TOKEN não está definido. Rode: export GITHUB_TOKEN=\"ghp_xxx\""
  exit 1
fi

echo "🔎 Verificando estado atual do Pages..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" "$API")

if [[ "$STATUS" == "200" ]]; then
  echo "ℹ️  Pages já está habilitado. Atualizando para source 'GitHub Actions'..."
  METHOD="PUT"
  BODY='{"build_type":"workflow"}'
elif [[ "$STATUS" == "404" ]]; then
  echo "🆕 Pages não habilitado. Criando com source 'GitHub Actions'..."
  METHOD="POST"
  BODY='{"build_type":"workflow"}'
else
  echo "❌ Resposta inesperada do GitHub API: HTTP $STATUS"
  echo "   Verifique se o token tem o scope 'repo' e permissão de admin no repositório."
  exit 1
fi

echo "🚀 Enviando requisição ($METHOD $API)..."
RESP=$(curl -s -w "\n%{http_code}" -X "$METHOD" "$API" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  -d "$BODY")

CODE=$(echo "$RESP" | tail -n1)
BODY_RESP=$(echo "$RESP" | sed '$d')

if [[ "$CODE" == "201" || "$CODE" == "204" || "$CODE" == "200" ]]; then
  echo "✅ GitHub Pages habilitado com source 'GitHub Actions'."
  echo "   URL esperada: https://${OWNER}.github.io/${REPO}/"
  echo ""
  echo "▶️  Agora rode o workflow (ou faça um novo push) para publicar:"
  echo "   git commit --allow-empty -m 'ci: trigger pages deploy' && git push"
else
  echo "❌ Falha ao habilitar Pages (HTTP $CODE)"
  echo "$BODY_RESP"
  exit 1
fi
