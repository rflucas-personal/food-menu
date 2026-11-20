// Configuração do GitHub para receitas estáticas
const GITHUB_OWNER = 'rflucas-personal';
const GITHUB_REPO = 'food-menu';
const GITHUB_BRANCH = 'main';
const GITHUB_API_BASE = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}`;
const GITHUB_RAW_BASE = `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_BRANCH}`;

let allRecipes = [];
let currentRecipeId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadRecipes();

    document.getElementById('btn-new-recipe').addEventListener('click', createNewRecipe);
    document.getElementById('recipe-form').addEventListener('submit', saveRecipe);
    document.getElementById('recipe-search').addEventListener('input', filterRecipes);
    document.getElementById('btn-add-ingredient').addEventListener('click', () => addIngredientBlock());
    document.getElementById('btn-add-step').addEventListener('click', () => addStepBlock());
});

async function loadRecipes() {
    const listEl = document.getElementById('recipes-list');
    listEl.innerHTML = '<li class="loading-text">Carregando receitas do GitHub...</li>';

    try {
        // Lista arquivos na pasta recipes/ via GitHub API
        const response = await fetch(`${GITHUB_API_BASE}/contents/recipes`);
        
        if (!response.ok) {
            throw new Error(`GitHub API returned ${response.status}`);
        }
        
        const files = await response.json();
        const jsonFiles = files.filter(f => f.name.endsWith('.json') && f.type === 'file');
        
        // Baixar cada receita via raw URL
        allRecipes = [];
        for (const file of jsonFiles) {
            try {
                const rawResponse = await fetch(`${GITHUB_RAW_BASE}/recipes/${file.name}`);
                if (rawResponse.ok) {
                    const recipeData = await rawResponse.json();
                    allRecipes.push({
                        id: file.name,
                        ...recipeData
                    });
                }
            } catch (err) {
                console.warn(`Falha ao baixar ${file.name}:`, err);
            }
        }
        
        // Ordenar alfabeticamente
        allRecipes.sort((a, b) => a.titulo.localeCompare(b.titulo));
        renderRecipeList(allRecipes);
        
    } catch (error) {
        console.error('Error:', error);
        listEl.innerHTML = '<li style="color:var(--danger-color)">Erro ao carregar receitas do GitHub.</li>';
    }
}

function renderRecipeList(recipes) {
    const listEl = document.getElementById('recipes-list');
    listEl.innerHTML = '';

    if (recipes.length === 0) {
        listEl.innerHTML = '<li class="empty-state">Nenhuma receita encontrada.</li>';
        return;
    }

    recipes.forEach(recipe => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span class="filename">${recipe.titulo}</span>
            <span class="date">${recipe.tipo}</span>
        `;
        if (currentRecipeId === recipe.id) {
            li.classList.add('active');
        }

        li.addEventListener('click', () => {
            document.querySelectorAll('#recipes-list li').forEach(el => el.classList.remove('active'));
            li.classList.add('active');
            loadRecipeToForm(recipe.id);
        });

        listEl.appendChild(li);
    });
}

function filterRecipes(e) {
    const query = e.target.value.toLowerCase();
    const filtered = allRecipes.filter(r => r.titulo.toLowerCase().includes(query));
    renderRecipeList(filtered);
}

async function loadRecipeToForm(id) {
    currentRecipeId = id;
    
    // Mostra o form, esconde o empty state
    document.getElementById('empty-editor-state').classList.add('hidden');
    const form = document.getElementById('recipe-form');
    form.classList.remove('hidden');

    try {
        // Buscar receita via GitHub Raw
        const response = await fetch(`${GITHUB_RAW_BASE}/recipes/${id}`);
        
        if (!response.ok) {
            throw new Error(`Receita não encontrada: ${response.status}`);
        }
        
        const recipe = await response.json();

        // Preencher básicos
        document.getElementById('recipe-id').value = id;
        document.getElementById('titulo').value = recipe.titulo || '';
        document.getElementById('tipo').value = recipe.tipo || 'proteina';
        document.getElementById('porcoes').value = recipe.porcoes || 1;
        document.getElementById('tags').value = (recipe.tags || []).join(', ');
        document.getElementById('fonte').value = recipe.fonte || '';

        // Preencher ingredientes
        const ingContainer = document.getElementById('ingredients-container');
        ingContainer.innerHTML = '';
        (recipe.ingredientes || []).forEach(ing => addIngredientBlock(ing));

        // Preencher passos
        const stepsContainer = document.getElementById('steps-container');
        stepsContainer.innerHTML = '';
        (recipe.modo_de_preparo || []).forEach(step => addStepBlock(step));

    } catch (error) {
        console.error('Error loading recipe:', error);
        showToast('Erro', 'Não foi possível carregar os detalhes da receita.', true);
    }
}

function createNewRecipe() {
    currentRecipeId = null;
    document.querySelectorAll('#recipes-list li').forEach(el => el.classList.remove('active'));
    
    document.getElementById('empty-editor-state').classList.add('hidden');
    const form = document.getElementById('recipe-form');
    form.classList.remove('hidden');
    form.reset();
    
    document.getElementById('recipe-id').value = '';
    document.getElementById('ingredients-container').innerHTML = '';
    document.getElementById('steps-container').innerHTML = '';
    
    addIngredientBlock(); // Adiciona 1 vazio
    addStepBlock(); // Adiciona 1 vazio
    
    document.getElementById('titulo').focus();
}

// --- Dynamic Form Helpers ---

function addIngredientBlock(ingData = null) {
    const container = document.getElementById('ingredients-container');
    const block = document.createElement('div');
    block.className = 'ingredient-block';
    block.style.cssText = 'background: var(--input-bg); padding: 1rem; border-radius: var(--radius-md); border: 1px solid var(--glass-border); position: relative;';

    const nomeValue = ingData ? ingData.nome.replace(/"/g, '&quot;') : '';
    
    let html = `
        <button type="button" class="btn-remove-block" onclick="this.parentElement.remove()" style="position: absolute; top: 0.5rem; right: 0.5rem; background: transparent; border: none; color: var(--danger-color); cursor: pointer; font-size: 1.2rem;">&times;</button>
        <div class="form-group" style="margin-bottom: 0.5rem; width: calc(100% - 2rem);">
            <label>Nome do Ingrediente</label>
            <input type="text" class="ing-nome" value="${nomeValue}" required>
        </div>
        <div class="quantities-container" style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem;">
    `;

    // Add quantities
    const quantidades = ingData && ingData.quantidade && ingData.quantidade.length > 0 ? ingData.quantidade : [{ quantidade: 1, unidade_de_medida: 'un' }];
    
    block.innerHTML = html;
    const quantContainer = block.querySelector('.quantities-container');
    
    quantidades.forEach(q => {
        quantContainer.appendChild(createQuantityRow(q));
    });

    const btnAddQtd = document.createElement('button');
    btnAddQtd.type = 'button';
    btnAddQtd.className = 'btn-outline';
    btnAddQtd.style.cssText = 'padding: 0.2rem 0.5rem; font-size: 0.8rem; width: max-content; border: none; margin-top: 0.25rem;';
    btnAddQtd.innerText = '+ Add Medida';
    btnAddQtd.onclick = () => quantContainer.insertBefore(createQuantityRow(), btnAddQtd);
    
    quantContainer.appendChild(btnAddQtd);
    container.appendChild(block);
}

function createQuantityRow(qData = null) {
    const row = document.createElement('div');
    row.style.cssText = 'display: flex; gap: 0.5rem; align-items: center;';
    
    const qtdValue = qData ? qData.quantidade : 1;
    const isQtdText = typeof qtdValue === 'string';
    const unValue = qData ? qData.unidade_de_medida.replace(/"/g, '&quot;') : 'un';

    row.innerHTML = `
        <input type="${isQtdText ? 'text' : 'number'}" class="ing-qtd" value="${qtdValue}" style="width: 100px;" step="any" required>
        <input type="text" class="ing-un" value="${unValue}" placeholder="Unidade (ex: kg, xícara)" required>
        <button type="button" onclick="this.parentElement.remove()" style="background: transparent; border: none; color: var(--text-secondary); cursor: pointer; width: auto; padding: 0.5rem;">&times;</button>
    `;
    return row;
}

function addStepBlock(stepText = '') {
    const container = document.getElementById('steps-container');
    const row = document.createElement('div');
    row.style.cssText = 'display: flex; gap: 0.5rem; align-items: flex-start;';
    
    row.innerHTML = `
        <textarea class="step-text" style="flex-grow: 1; padding: 0.75rem; border-radius: var(--radius-md); border: 1px solid var(--glass-border); background: var(--input-bg); font-family: inherit; resize: vertical; min-height: 60px;" required>${stepText}</textarea>
        <button type="button" onclick="this.parentElement.remove()" style="background: transparent; border: none; color: var(--danger-color); cursor: pointer; width: auto; padding: 0.5rem; font-size: 1.2rem;">&times;</button>
    `;
    container.appendChild(row);
}

// --- Save Data ---

async function saveRecipe(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save-recipe');
    btn.disabled = true;
    btn.innerText = 'Salvando...';

    const id = document.getElementById('recipe-id').value;
    
    // Build JSON
    const payload = {
        titulo: document.getElementById('titulo').value,
        porcoes: parseFloat(document.getElementById('porcoes').value),
        tags: document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t),
        tipo: document.getElementById('tipo').value,
        fonte: document.getElementById('fonte').value,
        ingredientes: [],
        modo_de_preparo: []
    };

    // Parse Ingredients
    document.querySelectorAll('.ingredient-block').forEach(block => {
        const nome = block.querySelector('.ing-nome').value;
        const qtdRows = block.querySelectorAll('.quantities-container > div'); // Pula o botão add
        const quantidades = [];
        
        qtdRows.forEach(row => {
            const inputQtd = row.querySelector('.ing-qtd');
            if(inputQtd) {
                let val = inputQtd.value;
                if (inputQtd.type === 'number' || !isNaN(val)) {
                    val = parseFloat(val);
                }
                const un = row.querySelector('.ing-un').value;
                quantidades.push({ quantidade: val, unidade_de_medida: un });
            }
        });
        
        if (nome && quantidades.length > 0) {
            payload.ingredientes.push({ nome, quantidade: quantidades });
        }
    });

    // Parse Steps
    document.querySelectorAll('.step-text').forEach(textarea => {
        if (textarea.value.trim()) {
            payload.modo_de_preparo.push(textarea.value.trim());
        }
    });

    // Enviar para GitHub via API (requer GITHUB_TOKEN configurado no navegador ou usar issues)
    try {
        // Como é frontend estático sem backend, não podemos fazer PUT diretamente
        // sem expor o token. Sugerimos usar o fluxo de Issue + GitHub Actions.
        showToast('Atenção', 'Para salvar receitas, abra uma Issue no GitHub com o template "Nova Receita". O agente de IA processará e commitará automaticamente.', true);
        
        // Abrir a página de nova issue do GitHub
        const issueTitle = encodeURIComponent('[Receita]: ' + payload.titulo);
        const issueBody = encodeURIComponent(
            '#### Ingredientes:\n' +
            payload.ingredientes.map(ing => '- ' + ing.quantidade.map(q => q.quantidade + ' ' + q.unidade_de_medida).join(' + ') + ' ' + ing.nome).join('\n') +
            '\n\n#### Modo de Preparo:\n' +
            payload.modo_de_preparo.map((step, i) => (i+1) + '. ' + step).join('\n') +
            '\n\n**Título sugerido:** ' + payload.titulo +
            '\n**Tipo:** ' + payload.tipo +
            '\n**Tags:** ' + payload.tags.join(', ') +
            '\n**Porções:** ' + payload.porcoes
        );
        window.open(`https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/issues/new?title=${issueTitle}&body=${issueBody}`, '_blank');
        
    } catch (error) {
        console.error('Error saving:', error);
        showToast('Erro', error.message, true);
    } finally {
        btn.disabled = false;
        btn.innerText = '💾 Salvar Alterações';
    }
}

// --- Toast ---
function showToast(title, desc, isError = false) {
    const toast = document.getElementById('toast');
    document.getElementById('toast-title').innerText = title;
    document.getElementById('toast-desc').innerText = desc;
    
    toast.style.borderLeftColor = isError ? 'var(--danger-color)' : 'var(--success-color)';
    toast.querySelector('.toast-icon').innerText = isError ? '❌' : '✅';
    
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}
