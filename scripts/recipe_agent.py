#!/usr/bin/env python3
"""
Agente Autônomo para Ingestão e Processamento de Novas Receitas.

Capacidades:
- Suporta texto puro e imagens/fotos de receitas (multimodal via Gemini 2.5 Flash).
- Utiliza Structured Outputs com JSON Schema estrito.
- Calibra porções automaticamente com base no peso cozido e rendimento físico (scripts/portion_calculator.py).
- Salva o arquivo normalizado em recipes/<slug>.json.
- Gera resumo visual Markdown com comparativo de peso cru vs. cozido.
"""

import os
import sys
import json
import re
import base64
import argparse
import urllib.request
import urllib.error
from portion_calculator import calculate_recipe_portions, slugify, get_cooking_factor, parse_unit_to_grams

RECIPES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recipes'))

RECIPE_JSON_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {
            "type": "STRING",
            "description": "Nome claro da receita com primeira letra maiúscula (ex: Salmão ao Molho Pesto)"
        },
        "tipo": {
            "type": "STRING",
            "enum": ["proteina", "acompanhamento", "complemento"],
            "description": "Tipo nutricional: proteina, acompanhamento ou complemento"
        },
        "tags": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Tags em letras minúsculas (ex: ['peixe', 'forno', 'marmita'])"
        },
        "ingredientes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "nome": {"type": "STRING", "description": "Nome do ingrediente"},
                    "quantidade": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "quantidade": {"type": "NUMBER", "description": "Valor numérico (0 se a gosto)"},
                                "unidade_de_medida": {"type": "STRING", "description": "Unidade (kg, g, un, xícara, colher de sopa, dentes, a gosto)"}
                            },
                            "required": ["quantidade", "unidade_de_medida"]
                        }
                    }
                },
                "required": ["nome", "quantidade"]
            }
        },
        "modo_de_preparo": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Passos organizados do modo de preparo"
        },
        "fonte": {
            "type": "STRING",
            "description": "Origem da receita ou autor"
        }
    },
    "required": ["titulo", "tipo", "tags", "ingredientes", "modo_de_preparo"]
}

SYSTEM_INSTRUCTION = """Você é um nutricionista e chef assistente no sistema Food Menu.
Sua missão é extrair receitas de textos ou imagens e convertê-las no formato padronizado do sistema.

Classificação de tipos:
- 'proteina': Carnes (bovina, suína, frango, peixe), ovos, hambúrguer, quibes de carne ou proteína vegetal.
- 'acompanhamento': Arroz, macarrão, purês de batata/mandioca/baroa, lentilha, grãos base.
- 'complemento': Legumes salteados, assados, refogados, vegetais, saladas e molhos.

Padronização de medidas:
- Use preferencialmente 'kg', 'g', 'xícara', 'colher de sopa', 'colher de chá', 'dentes', 'un', 'lata', 'maço' ou 'a gosto' (com quantidade 0).
- Se houver quantidade e gramas (ex: '2 xícaras (400g)'), prefira registrar a quantidade em gramas ou a unidade clara.
- Seja minucioso nos ingredientes e nas instruções de preparo.
"""

def extract_image_urls(text: str) -> list[str]:
    """Detecta links de imagens em Markdown ou URLs diretas."""
    urls = []
    # Markdown ![alt](url)
    md_matches = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', text)
    urls.extend(md_matches)
    
    # HTML <img src="...">
    html_matches = re.findall(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', text)
    urls.extend(html_matches)
    
    # URLs isoladas que terminem com imagem
    direct_urls = re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|webp))', text, re.IGNORECASE)
    urls.extend(direct_urls)
    
    # Remover duplicatas preservando ordem
    seen = set()
    cleaned = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            cleaned.append(u)
    return cleaned

def download_image_b64(url: str) -> tuple[str, str]:
    """Baixa uma imagem e retorna (base64_data, mime_type)."""
    headers = {"User-Agent": "Mozilla/5.0 (FoodMenu-Agent/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        content_type = resp.headers.get_content_type()
        data = resp.read()
        b64 = base64.b64encode(data).decode('utf-8')
        return b64, content_type

def call_gemini_sdk(api_key: str, text: str, image_urls: list[str]) -> dict:
    """Tenta chamar usando o SDK oficial google-genai se instalado."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    client = genai.Client(api_key=api_key)
    contents = []

    # Se houver imagens, adiciona
    for img_url in image_urls[:3]:
        try:
            b64, mime_type = download_image_b64(img_url)
            contents.append(types.Part.from_bytes(data=base64.b64decode(b64), mime_type=mime_type))
            print(f"📷 Imagem incorporada: {img_url[:60]}... ({mime_type})")
        except Exception as e:
            print(f"⚠️ Não foi possível baixar imagem '{img_url}': {e}")

    contents.append(f"{SYSTEM_INSTRUCTION}\n\nTexto / Conteúdo fornecido:\n{text}")

    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_json_schema=RECIPE_JSON_SCHEMA,
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=config
    )
    return json.loads(response.text)

def call_gemini_rest(api_key: str, text: str, image_urls: list[str]) -> dict:
    """Chama a API REST do Gemini 2.5 Flash."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    parts = []
    
    for img_url in image_urls[:3]:
        try:
            b64, mime_type = download_image_b64(img_url)
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64
                }
            })
            print(f"📷 Imagem incorporada (REST): {img_url[:60]}... ({mime_type})")
        except Exception as e:
            print(f"⚠️ Falha ao baixar imagem '{img_url}': {e}")

    parts.append({
        "text": f"{SYSTEM_INSTRUCTION}\n\nTexto / Conteúdo fornecido:\n{text}"
    })

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": RECIPE_JSON_SCHEMA
        }
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        content = result['candidates'][0]['content']['parts'][0]['text']
        return json.loads(content)

def call_openai_compatible(api_key: str, base_url: str, model: str, text: str) -> dict:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_INSTRUCTION}\nRetorne o JSON de acordo com o schema esperado."},
            {"role": "user", "content": f"Texto da receita:\n{text}"}
        ],
        "response_format": {"type": "json_object"}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        content = result['choices'][0]['message']['content']
        return json.loads(content)

def extract_recipe_json(raw_text: str) -> dict:
    gemini_key = (os.getenv('GEMINI_API_KEY') or '').strip()
    openai_key = (os.getenv('OPENAI_API_KEY') or '').strip()
    github_models_token = (os.getenv('GITHUB_TOKEN') or '').strip()

    image_urls = extract_image_urls(raw_text)
    if image_urls:
        print(f"🖼️  Detectadas {len(image_urls)} imagens na receita.")

    if gemini_key:
        print("🤖 Processando com Google Gemini 2.5 Flash...")
        res = call_gemini_sdk(gemini_key, raw_text, image_urls)
        if res:
            return res
        return call_gemini_rest(gemini_key, raw_text, image_urls)
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
    print(f"📖 Analisando entrada ({len(raw_text)} caracteres)...")
    
    recipe_data = extract_recipe_json(raw_text)
    
    if not recipe_data.get('titulo'):
        raise ValueError("A IA não conseguiu identificar o título da receita.")

    if not recipe_data.get('fonte'):
        recipe_data['fonte'] = source_label

    porcoes, peso_cozido, alertas = calculate_recipe_portions(recipe_data)
    recipe_data['porcoes'] = porcoes

    slug = slugify(recipe_data['titulo'])
    filename = f"{slug}.json"
    file_path = os.path.join(RECIPES_DIR, filename)

    is_update = os.path.exists(file_path)

    os.makedirs(RECIPES_DIR, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(recipe_data, f, indent=2, ensure_ascii=False)

    print(f"💾 Salvo com sucesso em: recipes/{filename}")
    print(f"🍽️  {recipe_data['titulo']} | Tipo: {recipe_data['tipo']} | Porções: {porcoes} (~{peso_cozido:.0f}g cozido)")

    summary_md = generate_summary_markdown(recipe_data, filename, peso_cozido, is_update, alertas)
    
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

    with open('recipe_summary.md', 'w', encoding='utf-8') as f:
        f.write(summary_md)

    return recipe_data, filename

def generate_summary_markdown(recipe: dict, filename: str, peso_cozido: float, is_update: bool, alertas: list) -> str:
    action_text = "atualizada" if is_update else "cadastrada"
    md = []
    md.append(f"## 🍳 Receita {action_text.capitalize()} com Sucesso!\n")
    md.append(f"**Título:** `{recipe['titulo']}`  ")
    md.append(f"**Tipo:** `{recipe['tipo']}` | **Porções calibradas:** `{recipe['porcoes']}` (Rendimento cozido estimado: **~{peso_cozido:.0f}g**)  ")
    md.append(f"**Arquivo:** [`recipes/{filename}`](recipes/{filename})  ")
    if recipe.get('tags'):
        md.append(f"**Tags:** {', '.join(f'`{t}`' for t in recipe['tags'])}  ")
    if recipe.get('fonte'):
        md.append(f"**Fonte:** {recipe['fonte']}  ")
    md.append("")
    
    md.append("### 🛒 Ingredientes e Rendimento Cru → Cozido")
    for ing in recipe.get('ingredientes', []):
        nome = ing.get('nome')
        factor = get_cooking_factor(nome)
        qtds = []
        raw_g_total = 0.0
        
        for q in ing.get('quantidade', []):
            qtd = q.get('quantidade', 0)
            unid = q.get('unidade_de_medida', '')
            if qtd == 0 or unid == 'a gosto':
                qtds.append("a gosto")
            else:
                qtds.append(f"{qtd} {unid}".strip())
                g, _ = parse_unit_to_grams(unid, qtd, nome)
                raw_g_total += g

        factor_str = f" *(fator {factor}x)*" if factor != 1.0 else ""
        md.append(f"- **{nome}**: {', '.join(qtds)}{factor_str}")
    md.append("")

    md.append("### 👩‍🍳 Modo de Preparo")
    for i, step in enumerate(recipe.get('modo_de_preparo', []), 1):
        md.append(f"{i}. {step}")
    md.append("")

    if alertas:
        md.append("### ⚠️ Observações de Calibração")
        for a in alertas:
            md.append(f"- {a}")
        md.append("")

    md.append("---")
    md.append("*Processado automaticamente pelo Food Menu Recipe Agent com Gemini 2.5 Flash 🤖*")
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Food Menu Recipe Agent")
    parser.add_argument("--text", help="Texto bruto ou URL da receita")
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
        raw_text = os.getenv('RECIPE_RAW_CONTENT', '')

    if not raw_text.strip():
        print("❌ Nenhum texto ou imagem de receita fornecido.")
        sys.exit(1)

    try:
        process_recipe_text(raw_text, args.source)
    except Exception as e:
        print(f"❌ Erro durante o processamento da receita: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
