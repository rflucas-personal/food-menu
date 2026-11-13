#!/usr/bin/env python3
"""
Utilitário para analisar e re-calibrar porções de todas as receitas em recipes/.
Utiliza a lógica de rendimento cru→cozido de scripts/portion_calculator.py.
"""

import os
import glob
import json
import sys

# Permitir importação de scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from portion_calculator import calculate_recipe_portions

RECIPES_DIR = os.path.join(os.path.dirname(__file__), 'recipes')

def run_fix():
    files = sorted(glob.glob(os.path.join(RECIPES_DIR, '*.json')))
    changes = []

    print(f"🍳 Analisando {len(files)} receitas em {RECIPES_DIR}...\n")

    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            recipe = json.load(f)

        titulo = recipe.get('titulo', os.path.basename(file_path))
        porcoes_atual = recipe.get('porcoes', 1)
        
        calc_porcoes, peso_cozido, alertas = calculate_recipe_portions(recipe)

        if porcoes_atual != calc_porcoes:
            changes.append({
                'path': file_path,
                'titulo': titulo,
                'old': porcoes_atual,
                'new': calc_porcoes,
                'peso': peso_cozido,
                'recipe': recipe
            })
            print(f"✏️  {titulo}: {porcoes_atual} → {calc_porcoes} porções (~{peso_cozido:.0f}g cozido)")

    print("\n" + "=" * 60)
    print(f"Total analisadas: {len(files)}")
    print(f"Precisam de ajuste: {len(changes)}")

    if changes:
        print("\nAplicando correções...")
        for c in changes:
            c['recipe']['porcoes'] = c['new']
            with open(c['path'], 'w', encoding='utf-8') as f:
                json.dump(c['recipe'], f, indent=2, ensure_ascii=False)
        print(f"✅ {len(changes)} receitas atualizadas com sucesso!")
    else:
        print("✅ Todas as receitas já estão com porções perfeitamente calibradas!")

if __name__ == '__main__':
    run_fix()
