#!/usr/bin/env python3
"""
Módulo de cálculo de peso cru/cozido e porções recomendadas.

Regras nutricionais do sistema:
- Proteína: ~150g por porção (peso cozido)
- Acompanhamento: ~150g por porção (peso cozido)
- Complemento: ~120g por porção (peso cozido)

Fatores de rendimento (cru → cozido):
- Grãos/cereais (arroz, quinoa, lentilha, grão-de-bico, feijão): x2.5
- Carnes, aves e peixes: x0.7 (perda média de 30% de água)
- Legumes cozidos/assados: x0.8 (perda média de 20%)
- Ovos, molhos e purês: x1.0
"""

import re
import unicodedata

GRAMS_PER_PORTION = {
    'proteina': 150,
    'acompanhamento': 150,
    'complemento': 120,
}

def slugify(value: str) -> str:
    """Converte título em slug seguro para nome de arquivo (ex: 'Frango Xadrez' -> 'frango-xadrez')."""
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def get_cooking_factor(nome_ingrediente: str) -> float:
    """Retorna o multiplicador cru→cozido para um ingrediente."""
    nome = (nome_ingrediente or '').lower()
    
    # Grãos e cereais (expandem muito ao cozinhar)
    if any(w in nome for w in [
        'arroz', 'quinoa', 'lentilha', 'grão de bico', 'grão-de-bico',
        'grao de bico', 'feijão', 'feijao', 'macarrão', 'macarrao', 'pene', 'penne'
    ]):
        return 2.5
    
    # Carnes e peixes (perdem líquido)
    if any(w in nome for w in [
        'carne', 'frango', 'peito', 'sobrecoxa', 'coxa', 'filé', 'file',
        'lombo', 'pernil', 'lagarto', 'salmão', 'salmao', 'tilápia', 'tilapia',
        'peixe', 'hambúrguer', 'hamburguer', 'linguiça', 'linguica',
        'almôndega', 'almondega', 'patinho', 'alcatra', 'acém', 'acem'
    ]):
        return 0.7
    
    # Legumes e vegetais
    if any(w in nome for w in [
        'batata', 'mandioca', 'inhame', 'baroa', 'cenoura', 'abóbora',
        'abobora', 'abobrinha', 'berinjela', 'brócolis', 'brocolis',
        'couve-flor', 'couve flor', 'vagem', 'repolho', 'pimentão',
        'pimentao', 'cebola', 'tomate', 'legumes', 'ervilha',
        'banana-da-terra', 'banana da terra'
    ]):
        return 0.8
    
    # Ovos, temperos, azeite, queijo, molhos
    return 1.0

def estimate_unit_weight(nome: str) -> float:
    """Estima o peso CRU de 1 unidade de um ingrediente."""
    nome_lower = (nome or '').lower()
    
    if any(w in nome_lower for w in ['filé', 'file', 'sobrecoxa', 'coxa', 'peito']):
        return 150.0
    if 'ovo' in nome_lower:
        return 60.0
    if 'hambúrguer' in nome_lower or 'hamburguer' in nome_lower:
        return 120.0
    if 'linguiça' in nome_lower or 'linguica' in nome_lower:
        return 100.0
    if 'salmão' in nome_lower or 'salmao' in nome_lower:
        return 150.0
    if 'tilápia' in nome_lower or 'tilapia' in nome_lower:
        return 120.0
    if 'repolho' in nome_lower:
        return 1000.0
    if 'berinjela' in nome_lower:
        return 300.0
    if 'abobrinha' in nome_lower:
        return 250.0
    if 'abóbora' in nome_lower or 'abobora' in nome_lower:
        return 1500.0
    if any(w in nome_lower for w in ['batata', 'mandioca', 'inhame', 'baroa']):
        return 200.0
    if 'banana' in nome_lower:
        return 200.0
    if 'cebola' in nome_lower:
        return 150.0
    if 'cenoura' in nome_lower:
        return 150.0
    if 'tomate' in nome_lower:
        return 150.0
    if 'pimentão' in nome_lower or 'pimentao' in nome_lower:
        return 200.0
    if 'limão' in nome_lower or 'limao' in nome_lower:
        return 60.0
    if 'laranja' in nome_lower:
        return 200.0
    if 'alho-poró' in nome_lower or 'alho poro' in nome_lower:
        return 200.0
    if 'vagem' in nome_lower:
        return 200.0
    if 'brócolis' in nome_lower or 'brocolis' in nome_lower:
        return 400.0
    if 'couve-flor' in nome_lower or 'couve flor' in nome_lower:
        return 500.0
    if 'queijo' in nome_lower or 'muçarela' in nome_lower or 'mussarela' in nome_lower:
        return 30.0
    
    return 120.0

def parse_unit_to_grams(unidade_raw: str, quantidade: float, nome_ingrediente: str) -> tuple[float, bool]:
    """Converte unidade de medida para gramas em peso CRU. Retorna (gramas, reconhecido)."""
    unidade = (unidade_raw or '').strip().lower()
    
    if unidade in ('a gosto', 'q.b.', 'pitada a gosto') or quantidade == 0:
        return 0.0, True
    
    # Começa explicitamente com kg (ex: "kg (10 filés)", "kg")
    if unidade.startswith('kg'):
        return quantidade * 1000.0, True

    # Começa explicitamente com g
    if re.match(r'^g\b', unidade):
        return quantidade * 1.0, True

    # Extrair gramas no formato "(400 g)" ou "400g"
    g_match = re.search(r'(\d+[\.,]?\d*)\s*g\b', unidade)
    if g_match:
        grams_from_label = float(g_match.group(1).replace(',', '.'))
        return quantidade * grams_from_label, True

    # Extrair kg no formato "(1.5 kg)"
    kg_match = re.search(r'(\d+[\.,]?\d*)\s*kg\b', unidade)
    if kg_match:
        kg_from_label = float(kg_match.group(1).replace(',', '.'))
        return quantidade * kg_from_label * 1000.0, True

    # Normalizações
    unidade_norm = unidade
    unidade_norm = re.sub(r'\b(rasa|rasas|cheia|cheias)\b', '', unidade_norm).strip()
    unidade_norm = re.sub(r'^colheres?\b', 'colher', unidade_norm)
    if unidade_norm == 'colher':
        unidade_norm = 'colher de sopa'
    if 'e meia' in unidade_norm or 'e meio' in unidade_norm:
        unidade_norm = re.sub(r'\s+e\s+mei[ao]', '', unidade_norm)
        quantidade = quantidade * 1.5

    UNIT_MAP = {
        'kg': 1000.0, 'g': 1.0, 'ml': 1.0, 'l': 1000.0, 'litro': 1000.0, 'litros': 1000.0,
        'xícara': 150.0, 'xícaras': 150.0, 'xicara': 150.0, 'xicaras': 150.0,
        'colher de sopa': 15.0, 'colher de chá': 5.0, 'colher de sobremesa': 10.0,
        'dente': 5.0, 'dentes': 5.0, 'ramo': 5.0, 'ramos': 5.0,
        'folha': 3.0, 'folhas': 3.0, 'lata': 400.0, 'latas': 400.0,
        'pacote': 500.0, 'pacotes': 500.0, 'sachê': 50.0, 'sachês': 50.0,
        'pitada': 1.0, 'pitadas': 1.0, 'maço': 150.0, 'maços': 150.0,
        'caixa': 200.0, 'caixas': 200.0, 'fatia': 30.0, 'fatias': 30.0,
    }

    if unidade_norm in UNIT_MAP:
        return quantidade * UNIT_MAP[unidade_norm], True

    if unidade_norm in ('un', 'unidade', 'unidades', 'unid'):
        peso = estimate_unit_weight(nome_ingrediente)
        return quantidade * peso, True

    return 0.0, False

def calculate_recipe_portions(recipe: dict) -> tuple[int, float, list[str]]:
    """
    Calcula as porções recomendadas para uma receita com base no peso cozido estimado.
    Retorna (porções_sugeridas, peso_cozido_total, alertas).
    """
    tipo = recipe.get('tipo', 'proteina').lower()
    grams_per_portion = GRAMS_PER_PORTION.get(tipo, 150)
    
    total_cooked = 0.0
    alerts = []

    for ing in recipe.get('ingredientes', []):
        nome = ing.get('nome', '')
        factor = get_cooking_factor(nome)
        
        for q in ing.get('quantidade', []):
            qtd = q.get('quantidade', 0)
            unidade = q.get('unidade_de_medida', '')
            
            if not isinstance(qtd, (int, float)) or qtd == 0:
                continue
                
            raw_g, recognized = parse_unit_to_grams(unidade, qtd, nome)
            cooked_g = raw_g * factor
            total_cooked += cooked_g
            
            if not recognized:
                alerts.append(f"Unidade não padronizada '{unidade}' em '{nome}'")

    if total_cooked <= 0:
        return 1, 0.0, alerts

    portions = round(total_cooked / grams_per_portion)
    return max(1, portions), total_cooked, alerts
