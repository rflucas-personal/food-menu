#!/usr/bin/env python3
"""
Validador de integridade das receitas em recipes/*.json.
Usado no CI (GitHub Actions) e localmente antes de commits.
"""

import os
import glob
import json
import sys
from portion_calculator import calculate_recipe_portions, slugify

RECIPES_DIR = os.path.join(os.path.dirname(__file__), '..', 'recipes')

VALID_TIPOS = {'proteina', 'acompanhamento', 'complemento'}

def validate_all():
    files = sorted(glob.glob(os.path.join(RECIPES_DIR, '*.json')))
    if not files:
        print("❌ Nenhuma receita encontrada em recipes/")
        sys.exit(1)

    errors = []
    warnings = []
    
    print(f"🔍 Validando {len(files)} receitas em recipes/...\n")

    for file_path in files:
        basename = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"[{basename}] Erro ao carregar JSON: {e}")
            continue

        # Campos obrigatórios
        for req in ['titulo', 'tipo', 'porcoes', 'ingredientes', 'modo_de_preparo']:
            if req not in data:
                errors.append(f"[{basename}] Campo obrigatório ausente: '{req}'")

        # Validação do tipo
        tipo = data.get('tipo')
        if tipo not in VALID_TIPOS:
            errors.append(f"[{basename}] Tipo inválido '{tipo}'. Deve ser um de: {VALID_TIPOS}")

        # Validação de porções
        porcoes = data.get('porcoes')
        if not isinstance(porcoes, int) or porcoes <= 0:
            errors.append(f"[{basename}] Campo 'porcoes' deve ser inteiro positivo (recebido: {porcoes})")

        # Validação de ingredientes
        ingredientes = data.get('ingredientes', [])
        if not isinstance(ingredientes, list) or len(ingredientes) == 0:
            errors.append(f"[{basename}] 'ingredientes' deve ser uma lista não vazia")
        else:
            for i, ing in enumerate(ingredientes):
                if not isinstance(ing, dict) or 'nome' not in ing:
                    errors.append(f"[{basename}] Ingrediente #{i+1} sem 'nome'")
                qtds = ing.get('quantidade', [])
                if not isinstance(qtds, list):
                    errors.append(f"[{basename}] Quantidade de '{ing.get('nome')}' deve ser uma lista")
                else:
                    for q in qtds:
                        if not isinstance(q, dict) or 'quantidade' not in q or 'unidade_de_medida' not in q:
                            errors.append(f"[{basename}] Medida inválida no ingrediente '{ing.get('nome')}'")

        # Validação de modo de preparo
        preparo = data.get('modo_de_preparo', [])
        if not isinstance(preparo, list) or len(preparo) == 0:
            errors.append(f"[{basename}] 'modo_de_preparo' deve ser uma lista de passos")

        # Verificação do slug do arquivo
        titulo = data.get('titulo', '')
        expected_slug = slugify(titulo)
        # Se nome não bate exatamente com o slug, emitir aviso amigável
        if not basename.startswith(expected_slug[:10]):
            warnings.append(f"[{basename}] Nome do arquivo difere bastante do título '{titulo}'")

    print("=" * 60)
    if warnings:
        print(f"⚠️  {len(warnings)} avisos encontrados:")
        for w in warnings:
            print(f"   {w}")
        print()

    if errors:
        print(f"❌ {len(errors)} erros críticos encontrados:")
        for err in errors:
            print(f"   {err}")
        sys.exit(1)

    print(f"✅ Todas as {len(files)} receitas passaram na validação com sucesso!")

if __name__ == '__main__':
    validate_all()
