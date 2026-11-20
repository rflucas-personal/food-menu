#!/usr/bin/env python3
"""
Agente de Receitas adaptado para Open Code.

Este módulo é um utilitário usado pelo agente Open Code para:
- Validar e salvar receitas estruturadas em recipes/
- Calibrar porções automaticamente com base no peso cozido (portion_calculator)
- Gerar resumo Markdown da receita processada

Diferente do recipe_agent.py original (que dependia de GEMINI_API_KEY/OPENAI_API_KEY),
este agente NÃO faz chamadas a APIs externas. A estruturação do JSON (extração de
ingredientes, modo de preparo, tipo, etc.) é feita pelo próprio agente Open Code
usando seu modelo de linguagem nativo. Este script apenas valida, calibra e persiste.

Uso (chamado pelo agente Open Code):
    python scripts/opencode_recipe_agent.py --save <receita_json> [--source "Open Code"]

Ou como biblioteca:
    from scripts.opencode_recipe_agent import process_and_save_recipe
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Permitir importação de scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from portion_calculator import calculate_recipe_portions, slugify

RECIPES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recipes'))

# Schema esperado de uma receita (estrutura padronizada do sistema)
REQUIRED_FIELDS = ['titulo', 'tipo', 'tags', 'ingredientes', 'modo_de_preparo']
VALID_TIPOS = {'proteina', 'acompanhamento', 'complemento'}


def validate_recipe(recipe: dict) -> list[str]:
    """Valida os campos obrigatórios e tipos de uma receita. Retorna lista de erros."""
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in recipe or recipe[field] is None:
            errors.append(f"Campo obrigatório ausente: '{field}'")

    tipo = recipe.get('tipo')
    if tipo and tipo not in VALID_TIPOS:
        errors.append(f"Tipo inválido '{tipo}'. Deve ser um de: {VALID_TIPOS}")

    porcoes = recipe.get('porcoes')
    if porcoes is not None and (not isinstance(porcoes, int) or porcoes <= 0):
        errors.append(f"Campo 'porcoes' deve ser inteiro positivo (recebido: {porcoes})")

    ingredientes = recipe.get('ingredientes', [])
    if not isinstance(ingredientes, list) or len(ingredientes) == 0:
        errors.append("'ingredientes' deve ser uma lista não vazia")
    else:
        for i, ing in enumerate(ingredientes):
            if not isinstance(ing, dict) or 'nome' not in ing:
                errors.append(f"Ingrediente #{i+1} sem 'nome'")
            qtds = ing.get('quantidade', [])
            if not isinstance(qtds, list):
                errors.append(f"Quantidade de '{ing.get('nome')}' deve ser uma lista")
            else:
                for q in qtds:
                    if not isinstance(q, dict) or 'quantidade' not in q or 'unidade_de_medida' not in q:
                        errors.append(f"Medida inválida no ingrediente '{ing.get('nome')}'")

    preparo = recipe.get('modo_de_preparo', [])
    if not isinstance(preparo, list) or len(preparo) == 0:
        errors.append("'modo_de_preparo' deve ser uma lista de passos")

    return errors


def normalize_recipe(recipe: dict) -> dict:
    """Normaliza campos opcionais e garante estrutura consistente."""
    normalized = {
        'titulo': recipe['titulo'].strip(),
        'tipo': recipe['tipo'],
        'tags': recipe.get('tags', []),
        'ingredientes': recipe['ingredientes'],
        'modo_de_preparo': recipe['modo_de_preparo'],
        'fonte': recipe.get('fonte', 'Open Code'),
        'porcoes': recipe.get('porcoes', 1),
    }
    return normalized


def save_recipe(recipe: dict, source_label: str = "Open Code") -> dict:
    """
    Valida, calibra porções e salva uma receita em recipes/<slug>.json.
    Retorna dicionário com resultado da operação.
    """
    errors = validate_recipe(recipe)
    if errors:
        return {
            'success': False,
            'errors': errors,
        }

    recipe = normalize_recipe(recipe)

    # Calibrar porções automaticamente com base no peso cozido
    porcoes, peso_cozido, alertas = calculate_recipe_portions(recipe)
    recipe['porcoes'] = porcoes

    slug = slugify(recipe['titulo'])
    filename = f"{slug}.json"
    file_path = os.path.join(RECIPES_DIR, filename)

    os.makedirs(RECIPES_DIR, exist_ok=True)

    is_update = os.path.exists(file_path)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)

    summary_md = generate_summary_markdown(recipe, filename, peso_cozido, is_update, alertas)

    # Salvar resumo em arquivo para o agente ler
    summary_path = os.path.join(os.path.dirname(__file__), '..', 'recipe_summary.md')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_md)

    return {
        'success': True,
        'slug': slug,
        'filename': filename,
        'file_path': file_path,
        'titulo': recipe['titulo'],
        'tipo': recipe['tipo'],
        'porcoes': porcoes,
        'peso_cozido': round(peso_cozido, 1),
        'is_update': is_update,
        'alertas': alertas,
        'summary_md': summary_md,
    }


def generate_summary_markdown(recipe: dict, filename: str, peso_cozido: float,
                              is_update: bool, alertas: list) -> str:
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
    from portion_calculator import get_cooking_factor, parse_unit_to_grams
    for ing in recipe.get('ingredientes', []):
        nome = ing.get('nome')
        factor = get_cooking_factor(nome)
        qtds = []
        for q in ing.get('quantidade', []):
            qtd = q.get('quantidade', 0)
            unid = q.get('unidade_de_medida', '')
            if qtd == 0 or unid == 'a gosto':
                qtds.append("a gosto")
            else:
                qtds.append(f"{qtd} {unid}".strip())
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
    md.append("*Processado pelo Food Menu Open Code Agent 🤖*")
    return "\n".join(md)


def list_recipes() -> list[dict]:
    """Lista todas as receitas disponíveis em recipes/."""
    files = sorted(__import__('glob').glob(os.path.join(RECIPES_DIR, '*.json')))
    recipes = []
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            recipes.append({
                'id': os.path.basename(file_path),
                'titulo': data.get('titulo', ''),
                'tipo': data.get('tipo', ''),
                'porcoes': data.get('porcoes', 1),
                'tags': data.get('tags', []),
            })
        except Exception:
            pass
    return recipes


def main():
    parser = argparse.ArgumentParser(description="Food Menu Open Code Recipe Agent")
    parser.add_argument('--save', help='Caminho de arquivo JSON contendo a receita estruturada')
    parser.add_argument('--source', default='Open Code', help='Identificador da fonte')
    parser.add_argument('--list', action='store_true', help='Listar todas as receitas')
    args = parser.parse_args()

    if args.list:
        recipes = list_recipes()
        print(f"📚 {len(recipes)} receitas encontradas em {RECIPES_DIR}:")
        for r in recipes:
            print(f"  - {r['titulo']} ({r['tipo']}) - {r['porcoes']} porções")
        return

    if args.save:
        if not os.path.exists(args.save):
            print(f"❌ Arquivo não encontrado: {args.save}", file=sys.stderr)
            sys.exit(1)
        with open(args.save, 'r', encoding='utf-8') as f:
            recipe = json.load(f)

        result = save_recipe(recipe, args.source)
        if result['success']:
            print(f"✅ Receita salva em: recipes/{result['filename']}")
            print(f"   Título: {result['titulo']}")
            print(f"   Tipo: {result['tipo']}")
            print(f"   Porções: {result['porcoes']} (~{result['peso_cozido']}g cozido)")
            if result['alertas']:
                print("   Alertas:")
                for a in result['alertas']:
                    print(f"     - {a}")
        else:
            print("❌ Erros de validação:", file=sys.stderr)
            for e in result['errors']:
                print(f"   - {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
