#!/usr/bin/env python3
"""
Agente Autônomo para Ingestão e Processamento de Novas Receitas.

Lê texto bruto (de PR, Issue ou arquivo), consulta uma LLM (Gemini ou OpenAI/GitHub Models),
valida e formata o schema exato do app, calcula o peso cozido e as porções nutricionais,
e salva em recipes/<slug>.json.
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
from portion_calculator import calculate_recipe_portions, slugify

RECIPES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recipes'))

SYSTEM_PROMPT = """Você é um assistente especialista em culinária e no sistema Food Menu.
Sua tarefa é converter o texto de uma receita fornecida pelo usuário para o formato JSON estrito esperado pelo sistema.

O JSON DEVE seguir estritamente este formato:
{
  "titulo": "Nome Claro da Receita",
  "tipo": "proteina" | "acompanhamento" | "complemento",
  "tags": ["tag1", "tag2"],
  "ingredientes": [
    {
      "nome": "Nome do ingrediente",
      "quantidade": [
        {
          "quantidade": 1.5,
          "unidade_de_medida": "kg"
        }
      ]
    }
  ],
  "modo_de_preparo": [
    "Passo 1...",
    "Passo 2..."
  ],
  "fonte": "Origem da receita ou autor (opcional)"
}

Regras importantes:
1. 'tipo' DEVE ser EXATAMENTE um destes 3:
   - "proteina": Carnes, frango, peixes, ovos, quibes, hambúrguer, tofu, etc.
   - "acompanhamento": Arroz, massas, purês, batatas, lentilha, grãos principais.
   - "complemento": Legumes assados/refogados, saladas, molhos, vegetais secundários.
2. Unidades de medida recomendadas: "kg", "g", "xícara", "colher de sopa", "colher de chá", "dentes", "un", "lata", "maço", ou "a gosto" (quando a gosto, use quantidade 0).
3. Se o texto contiver medidas caseiras como "1 xícara (200g)", preserve a quantidade numérica e prefira "g" ou mantenha claro na unidade.
4. Responda SOMENTE o bloco JSON puro, sem markdown adicional ou explicações antes ou depois.
"""

def call_gemini(api_key: str, prompt: str) -> dict:
    """Chama a API do Google Gemini."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{SYSTEM_PROMPT}\n\nTexto da receita:\n{prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        content = result['candidates'][0]['content']['parts'][0]['text']
        return json.loads(content)

def call_openai_compatible(api_key: str, base_url: str, model: str, prompt: str) -> dict:
    """Chama API compatível com OpenAI (OpenAI, GitHub Models, etc.)."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Texto da receita:\n{prompt}"}
        ],
        "response_format": {"type": "json_object"}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        content = result['choices'][0]['message']['content']
        return json.loads(content)

def extract_recipe_json(raw_text: str) -> dict:
    """Tenta chamar o provedor de IA configurado no ambiente."""
    gemini_key = os.getenv('GEMINI_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    github_models_token = os.getenv('GITHUB_TOKEN')

    if gemini_key:
        print("🤖 Processando com Google Gemini Flash...")
        return call_gemini(gemini_key, raw_text)
    elif openai_key:
        print("🤖 Processando com OpenAI API...")
        return call_openai_compatible(openai_key, "https://api.openai.com/v1", "gpt-4o-mini", raw_text)
    elif github_models_token and os.getenv('USE_GITHUB_MODELS') == 'true':
        print("🤖 Processando com GitHub Models...")
        return call_openai_compatible(github_models_token, "https://models.inference.ai.azure.com", "gpt-4o-mini", raw_text)
    else:
        raise RuntimeError(
            "Nenhuma chave de IA configurada! Defina GEMINI_API_KEY (recomendado) ou OPENAI_API_KEY."
        )

def process_recipe_text(raw_text: str, source_label: str = "GitHub PR"):
    print(f"📖 Texto recebido ({len(raw_text)} caracteres).")
    
    # 1. Estruturação com IA
    recipe_data = extract_recipe_json(raw_text)
    
    if not recipe_data.get('titulo'):
        raise ValueError("A IA não conseguiu identificar o título da receita.")

    # 2. Garantir integridade básica
    if not recipe_data.get('fonte'):
        recipe_data['fonte'] = source_label

    # 3. Calcular porções com base no peso cozido e rendimento
    porcoes, peso_cozido, alertas = calculate_recipe_portions(recipe_data)
    recipe_data['porcoes'] = porcoes

    # 4. Determinar nome do arquivo
    slug = slugify(recipe_data['titulo'])
    filename = f"{slug}.json"
    file_path = os.path.join(RECIPES_DIR, filename)

    is_update = os.path.exists(file_path)

    # 5. Salvar JSON
    os.makedirs(RECIPES_DIR, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(recipe_data, f, indent=2, ensure_ascii=False)

    print(f"💾 Salvo com sucesso em: recipes/{filename}")
    print(f"🍽️  Título: {recipe_data['titulo']}")
    print(f"🏷️  Tipo: {recipe_data['tipo']} | Porções calculadas: {porcoes} (~{peso_cozido:.0f}g cozido)")

    # 6. Gerar resumo Markdown para o GitHub (PR/Issue comment)
    summary_md = generate_summary_markdown(recipe_data, filename, peso_cozido, is_update, alertas)
    
    # Escrever no output do GitHub se disponível
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a', encoding='utf-8') as f:
            f.write(f"recipe_slug={slug}\n")
            f.write(f"recipe_file=recipes/{filename}\n")
            f.write(f"recipe_title={recipe_data['titulo']}\n")
            f.write(f"recipe_portions={porcoes}\n")
            f.write(f"is_update={'true' if is_update else 'false'}\n")

    github_summary = os.getenv('GITHUB_STEP_SUMMARY')
    if github_summary:
        with open(github_summary, 'a', encoding='utf-8') as f:
            f.write(summary_md)

    # Salva resumo em arquivo temporário para consumo pelo GitHub Action
    with open('recipe_summary.md', 'w', encoding='utf-8') as f:
        f.write(summary_md)

    return recipe_data, filename

def generate_summary_markdown(recipe: dict, filename: str, peso_cozido: float, is_update: bool, alertas: list) -> str:
    action_text = "atualizada" if is_update else "cadastrada"
    md = []
    md.append(f"## 🍳 Nova Receita {action_text.capitalize()} com Sucesso!\n")
    md.append(f"**Título:** `{recipe['titulo']}`  ")
    md.append(f"**Tipo:** `{recipe['tipo']}` | **Porções calibradas:** `{recipe['porcoes']}` (Rendimento cozido estimado: ~{peso_cozido:.0f}g)  ")
    md.append(f"**Arquivo:** [`recipes/{filename}`](recipes/{filename})  ")
    if recipe.get('tags'):
        md.append(f"**Tags:** {', '.join(f'`{t}`' for t in recipe['tags'])}  ")
    md.append("")
    
    md.append("### 🛒 Ingredientes")
    for ing in recipe.get('ingredientes', []):
        nome = ing.get('nome')
        qtds = []
        for q in ing.get('quantidade', []):
            qtd = q.get('quantidade', 0)
            unid = q.get('unidade_de_medida', '')
            if qtd == 0 or unid == 'a gosto':
                qtds.append("a gosto")
            else:
                qtds.append(f"{qtd} {unid}".strip())
        md.append(f"- **{nome}**: {', '.join(qtds)}")
    md.append("")

    md.append("### 👩‍🍳 Modo de Preparo")
    for i, step in enumerate(recipe.get('modo_de_preparo', []), 1):
        md.append(f"{i}. {step}")
    md.append("")

    if alertas:
        md.append("### ⚠️ Avisos de Calibração")
        for a in alertas:
            md.append(f"- {a}")
        md.append("")

    md.append("---")
    md.append("*Processado automaticamente pelo Food Menu Recipe Agent 🤖*")
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Food Menu Recipe Agent")
    parser.add_argument("--text", help="Texto bruto da receita")
    parser.add_argument("--file", help="Caminho de arquivo contendo a receita")
    parser.add_argument("--source", default="GitHub", help="Identificador da fonte")
    args = parser.parse_args()

    raw_text = ""
    if args.text:
        raw_text = args.text
    elif args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    else:
        # Tenta pegar do ambiente (ex: GITHUB_EVENT)
        raw_text = os.getenv('RECIPE_RAW_CONTENT', '')

    if not raw_text.strip():
        print("❌ Nenhum texto de receita fornecido via --text, --file ou RECIPE_RAW_CONTENT.")
        sys.exit(1)

    try:
        process_recipe_text(raw_text, args.source)
    except Exception as e:
        print(f"❌ Erro durante o processamento da receita: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
