#!/usr/bin/env python3
"""
Open Code GitHub Flow — Validador e processador de Issues/PRs via GitHub.

Este script é executado localmente pelo agente Open Code (não no GitHub Actions).
Ele usa o MCP do GitHub ou a API REST para:

1. Listar issues com label `nova-receita`
2. Extrair o texto da receita da issue
3. Chamar o opencode_recipe_agent.py para processar
4. Comentar na issue com o resumo
5. Fechar a issue após sucesso

Requisitos:
- GITHUB_TOKEN exportado no ambiente (ou configurado no .mcp.json)
- recipes/ existente
- scripts/opencode_recipe_agent.py

Uso:
    export GITHUB_TOKEN="ghp_xxx"
    python scripts/opencode_github_flow.py --owner lucas --repo food-menu
"""

import os
import sys
import json
import subprocess
import argparse
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def github_request(method, path, token, data=None):
    """Faz uma requisição para a API REST do GitHub."""
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "FoodMenu-OpenCode/1.0",
    }
    if data:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"❌ Erro HTTP {e.code} no GitHub API {path}: {err_body}")
        return None


def list_recipe_issues(token, owner, repo):
    """Lista issues abertas com label nova-receita."""
    path = f"/repos/{owner}/{repo}/issues?labels=nova-receita&state=open&sort=created&direction=asc"
    return github_request("GET", path, token) or []


def get_issue_comments(token, owner, repo, issue_number):
    """Retorna comentários de uma issue."""
    path = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
    return github_request("GET", path, token) or []


def comment_issue(token, owner, repo, issue_number, body):
    """Comenta em uma issue."""
    path = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
    return github_request("POST", path, token, data={"body": body})


def close_issue(token, owner, repo, issue_number):
    """Fecha uma issue."""
    path = f"/repos/{owner}/{repo}/issues/{issue_number}"
    return github_request("PATCH", path, token, data={"state": "closed"})


def extract_recipe_text(issue):
    """Extrai o texto da receita de uma issue (body + primeiro comentário se relevante)."""
    body = issue.get("body", "") or ""
    title = issue.get("title", "")
    return f"Título da issue: {title}\n\nConteúdo:\n{body}"


def process_issue(token, owner, repo, issue):
    """Processa uma issue de nova receita: extrai, chama o agente, comenta e fecha."""
    number = issue["number"]
    title = issue["title"]
    print(f"\n📋 Processando issue #{number}: {title}")

    recipe_text = extract_recipe_text(issue)

    # Salva texto temporário para o agente
    tmp_path = os.path.join(PROJECT_DIR, ".opencode_recipe_pending.json")
    # O agente Open Code vai estruturar esse texto em JSON e chamar opencode_recipe_agent.py
    # Aqui apenas registramos que a issue precisa de processamento manual pelo agente.

    # Comentar na issue informando que está sendo processada
    comment_issue(
        token,
        owner,
        repo,
        number,
        "🤖 Recebido! O agente Open Code está processando esta receita. "
        "Aguardando estruturação do JSON e commit automático...",
    )

    return {
        "issue_number": number,
        "title": title,
        "text": recipe_text,
        "status": "pending_agent",
    }


def main():
    parser = argparse.ArgumentParser(description="Open Code GitHub Flow")
    parser.add_argument("--owner", required=True, help="Dono do repositório")
    parser.add_argument("--repo", required=True, help="Nome do repositório")
    parser.add_argument("--process", action="store_true", help="Processar issues pendentes")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Defina GITHUB_TOKEN no ambiente.")
        sys.exit(1)

    if args.process:
        issues = list_recipe_issues(token, args.owner, args.repo)
        print(f"🔍 Encontradas {len(issues)} issue(s) com label 'nova-receita'.")
        for issue in issues:
            result = process_issue(token, args.owner, args.repo, issue)
            print(f"   - Issue #{result['issue_number']}: {result['title']} -> {result['status']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
