import os
import json
import glob
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_url_path='', static_folder='static')
RECIPES_DIR = os.path.join(os.path.dirname(__file__), 'recipes')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    recipes = []
    recipe_files = glob.glob(os.path.join(RECIPES_DIR, '*.json'))
    
    for file_path in recipe_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                recipe_data = json.load(f)
                recipes.append({
                    'id': os.path.basename(file_path),
                    'titulo': recipe_data.get('titulo', ''),
                    'tipo': recipe_data.get('tipo', ''),
                    'porcoes': recipe_data.get('porcoes', 1),
                    'tags': recipe_data.get('tags', []),
                    'ingredientes': recipe_data.get('ingredientes', []),
                    'modo_de_preparo': recipe_data.get('modo_de_preparo', []),
                    'fonte': recipe_data.get('fonte', '')
                })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    return jsonify(recipes)

import unicodedata
import re

def slugify(value):
    """Convert string to slug (e.g. 'Parmegiana de Frango' -> 'parmegiana-de-frango')"""
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

@app.route('/api/recipes', methods=['POST'])
def create_recipe():
    data = request.json
    if not data or 'titulo' not in data:
        return jsonify({'error': 'Invalid payload, missing titulo'}), 400
        
    filename = slugify(data['titulo']) + '.json'
    file_path = os.path.join(RECIPES_DIR, filename)
    
    if os.path.exists(file_path):
        return jsonify({'error': 'Recipe with this title already exists'}), 400
        
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True, 'id': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<id>', methods=['PUT', 'GET'])
def handle_single_recipe(id):
    if not id.endswith('.json'):
        id += '.json'
        
    file_path = os.path.join(RECIPES_DIR, id)
    
    if request.method == 'GET':
        if not os.path.exists(file_path):
            return jsonify({'error': 'Recipe not found'}), 404
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    if request.method == 'PUT':
        if not os.path.exists(file_path):
            return jsonify({'error': 'Recipe not found'}), 404
            
        data = request.json
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return jsonify({'success': True, 'id': id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def scale_ingredients(ingredientes, scale_factor):
    scaled_ingredientes = []
    for ingrediente in ingredientes:
        novo_ingrediente = {
            'nome': ingrediente.get('nome', '')
        }
        novas_quantidades = []
        for quant in ingrediente.get('quantidade', []):
            try:
                # Tratar casos onde a quantidade é uma string ou algo não multiplicável como 'a gosto'
                q = quant.get('quantidade')
                if isinstance(q, (int, float)):
                    # Aumentar a quantidade e arredondar para 2 casas decimais
                    nova_qtd = round(q * scale_factor, 2)
                else:
                    nova_qtd = q
                    
                novas_quantidades.append({
                    'quantidade': nova_qtd,
                    'unidade_de_medida': quant.get('unidade_de_medida', '')
                })
            except Exception:
                novas_quantidades.append(quant) # fallback seguro
                
        novo_ingrediente['quantidade'] = novas_quantidades
        scaled_ingredientes.append(novo_ingrediente)
        
    return scaled_ingredientes

@app.route('/api/generate', methods=['POST'])
def generate_cardapio():
    data = request.json
    if not data or 'refeicoes' not in data:
        return jsonify({'error': 'Invalid payload'}), 400
        
    refeicoes = data['refeicoes']
    cardapio_gerado = []
    
    for refeicao in refeicoes:
        nova_refeicao = {
            'refeicao_id': refeicao.get('id'),
            'porcoes_desejadas': refeicao.get('porcoes', 0),
            'receitas': []
        }
        
        # Cada refeicao contém referências às receitas escolhidas
        for receita in refeicao.get('receitas', []):
            try:
                # Ler arquivo original
                file_path = os.path.join(RECIPES_DIR, receita['file_id'])
                with open(file_path, 'r', encoding='utf-8') as f:
                    recipe_data = json.load(f)
                    
                porcoes_originais = recipe_data.get('porcoes', 1)
                if porcoes_originais <= 0: porcoes_originais = 1
                
                scale_factor = nova_refeicao['porcoes_desejadas'] / porcoes_originais
                
                # Criar a receita escalada
                receita_escalada = {
                    'titulo': recipe_data.get('titulo', ''),
                    'tipo': recipe_data.get('tipo', ''),
                    'porcoes': nova_refeicao['porcoes_desejadas'],
                    'ingredientes': scale_ingredients(recipe_data.get('ingredientes', []), scale_factor),
                    'modo_de_preparo': recipe_data.get('modo_de_preparo', []),
                    'fonte': recipe_data.get('fonte', '')
                }
                
                nova_refeicao['receitas'].append(receita_escalada)
                
            except Exception as e:
                print(f"Error processing recipe {receita['file_id']}: {e}")
                
        cardapio_gerado.append(nova_refeicao)
        
    # Salvar em arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cardapio_{timestamp}.json"
    cardapios_dir = os.path.join(os.path.dirname(__file__), 'cardapios')
    os.makedirs(cardapios_dir, exist_ok=True)
    file_path = os.path.join(cardapios_dir, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cardapio_gerado, f, indent=2, ensure_ascii=False)
            
        return jsonify({
            'success': True, 
            'message': f'Cardápio gerado com sucesso!',
            'file': filename,
            'cardapio': cardapio_gerado
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cardapios', methods=['GET'])
def list_cardapios():
    base_dir = os.path.join(os.path.dirname(__file__), 'cardapios')
    if not os.path.exists(base_dir):
        return jsonify([])
    cardapio_files = glob.glob(os.path.join(base_dir, 'cardapio_*.json'))
    
    files_info = []
    for file_path in cardapio_files:
        filename = os.path.basename(file_path)
        stats = os.stat(file_path)
        created_time = datetime.fromtimestamp(stats.st_ctime).strftime('%d/%m/%Y %H:%M:%S')
        files_info.append({
            'filename': filename,
            'created_at': created_time,
            'timestamp': stats.st_ctime
        })
        
    # Sort descending by timestamp
    files_info.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify(files_info)

@app.route('/api/cardapios/<filename>', methods=['GET'])
def get_cardapio(filename):
    if not filename.startswith('cardapio_') or not filename.endswith('.json'):
        return jsonify({'error': 'Invalid file name'}), 400
        
    cardapios_dir = os.path.join(os.path.dirname(__file__), 'cardapios')
    file_path = os.path.join(cardapios_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)
