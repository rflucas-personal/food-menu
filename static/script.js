// Configuração do GitHub para receitas estáticas
const GITHUB_OWNER = 'rflucas-personal';
const GITHUB_REPO = 'food-menu';
const GITHUB_BRANCH = 'main';
const GITHUB_API_BASE = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}`;
const GITHUB_RAW_BASE = `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_BRANCH}`;

let allRecipes = [];
let groupedRecipes = {
    proteina: [],
    acompanhamento: [],
    complemento: []
};
let meals = [];
let totalPortionsNeeded = 2; // Default 1 day * 2
let totalPortionsAllocated = 0;

document.addEventListener('DOMContentLoaded', () => {
    fetchRecipes();
    
    // Setup listeners
    document.getElementById('dias').addEventListener('input', updateGoals);
    document.getElementById('meal-form').addEventListener('submit', addMeal);
    document.getElementById('btn-generate').addEventListener('click', generateCardapio);
});

async function fetchRecipes() {
    try {
        // Lista arquivos na pasta recipes/ via GitHub API
        const response = await fetch(`${GITHUB_API_BASE}/contents/recipes`);
        
        if (!response.ok) {
            throw new Error(`GitHub API returned ${response.status}`);
        }
        
        const files = await response.json();
        
        // Filtrar apenas arquivos .json
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
        
        // Group by tipo
        allRecipes.forEach(recipe => {
            if (recipe.tipo && groupedRecipes[recipe.tipo]) {
                groupedRecipes[recipe.tipo].push(recipe);
            }
        });
        
        populateSelectors();
        
    } catch (error) {
        console.error('Failed to fetch recipes:', error);
        showToast('Erro', 'Não foi possível carregar as receitas do GitHub.', true);
    }
}

function populateSelectors() {
    const proteinaSelect = document.getElementById('proteina');
    const acompanhamentoSelect = document.getElementById('acompanhamento');
    const complementosContainer = document.getElementById('complementos-container');
    
    // Populate Proteínas
    groupedRecipes.proteina.forEach(recipe => {
        const option = document.createElement('option');
        option.value = recipe.id;
        option.textContent = recipe.titulo;
        proteinaSelect.appendChild(option);
    });
    
    // Populate Acompanhamentos
    groupedRecipes.acompanhamento.forEach(recipe => {
        const option = document.createElement('option');
        option.value = recipe.id;
        option.textContent = recipe.titulo;
        acompanhamentoSelect.appendChild(option);
    });
    
    // Populate Complementos (Checkboxes)
    complementosContainer.innerHTML = '';
    if (groupedRecipes.complemento.length === 0) {
        complementosContainer.innerHTML = '<div class="loading-text">Nenhum complemento encontrado.</div>';
    } else {
        groupedRecipes.complemento.forEach(recipe => {
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.name = 'complemento';
            checkbox.value = recipe.id;
            
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(recipe.titulo));
            
            complementosContainer.appendChild(label);
        });
    }
}

function updateGoals() {
    const dias = parseInt(document.getElementById('dias').value) || 0;
    totalPortionsNeeded = dias * 2;
    document.getElementById('porcoes-meta').textContent = totalPortionsNeeded;
    updateProgress();
}

function addMeal(e) {
    e.preventDefault();
    
    const proteinaId = document.getElementById('proteina').value;
    const acompanhamentoId = document.getElementById('acompanhamento').value;
    const porcoes = parseInt(document.getElementById('porcoes').value) || 0;
    
    // Get checked complementos
    const complementosIds = Array.from(document.querySelectorAll('input[name="complemento"]:checked'))
                                 .map(cb => cb.value);
                                 
    if (!proteinaId || !acompanhamentoId) {
        return; // Native HTML validation should catch this, but just in case
    }
    
    if (totalPortionsAllocated + porcoes > totalPortionsNeeded) {
        alert('Atenção: A quantidade de porções adicionadas excederá a meta de porções baseada nos dias. Por favor, ajuste os dias ou a quantidade desta refeição.');
        return;
    }
    
    const meal = {
        id: 'refeicao_' + Date.now(),
        porcoes: porcoes,
        receitas: [
            { file_id: proteinaId, title: allRecipes.find(r => r.id === proteinaId).titulo },
            { file_id: acompanhamentoId, title: allRecipes.find(r => r.id === acompanhamentoId).titulo },
            ...complementosIds.map(cId => ({ file_id: cId, title: allRecipes.find(r => r.id === cId).titulo }))
        ]
    };
    
    meals.push(meal);
    totalPortionsAllocated += porcoes;
    
    renderMeals();
    updateProgress();
    
    // Reset form
    document.getElementById('proteina').value = '';
    document.getElementById('acompanhamento').value = '';
    document.querySelectorAll('input[name="complemento"]').forEach(cb => cb.checked = false);
    document.getElementById('porcoes').value = 2; // Default
}

function removeMeal(mealId) {
    const mealIndex = meals.findIndex(m => m.id === mealId);
    if (mealIndex > -1) {
        totalPortionsAllocated -= meals[mealIndex].porcoes;
        meals.splice(mealIndex, 1);
        renderMeals();
        updateProgress();
    }
}

function renderMeals() {
    const list = document.getElementById('meal-list');
    
    if (meals.length === 0) {
        list.innerHTML = '<p class="empty-state">Nenhuma refeição adicionada ainda.</p>';
        return;
    }
    
    list.innerHTML = '';
    meals.forEach((meal, index) => {
        const card = document.createElement('div');
        card.className = 'meal-card';
        
        let titlesHtml = meal.receitas.map(r => `• ${r.title}`).join('<br>');
        
        card.innerHTML = `
            <h3>Refeição ${index + 1}</h3>
            <span class="portions-badge">${meal.porcoes} porções</span>
            <p>${titlesHtml}</p>
            <button type="button" class="btn-remove" onclick="removeMeal('${meal.id}')">Remover</button>
        `;
        list.appendChild(card);
    });
}

function updateProgress() {
    document.getElementById('porcoes-atuais').textContent = totalPortionsAllocated;
    
    const progressPercent = Math.min(100, (totalPortionsAllocated / totalPortionsNeeded) * 100);
    document.getElementById('progress-bar').style.width = progressPercent + '%';
    
    // Change color based on completion
    if (progressPercent === 100) {
        document.getElementById('progress-bar').style.background = 'linear-gradient(90deg, #10b981, #059669)';
        document.getElementById('btn-generate').disabled = false;
        document.getElementById('btn-add-meal').disabled = true;
    } else {
        document.getElementById('progress-bar').style.background = 'linear-gradient(90deg, #3b82f6, #10b981)';
        document.getElementById('btn-generate').disabled = true;
        document.getElementById('btn-add-meal').disabled = false;
    }
}

async function generateCardapio() {
    const btn = document.getElementById('btn-generate');
    btn.disabled = true;
    btn.textContent = 'Gerando...';
    
    try {
        const refeicoes = meals.map(meal => ({
            id: meal.id,
            porcoes: meal.porcoes,
            receitas: meal.receitas.map(r => ({ file_id: r.file_id }))
        }));
        
        // Buscar receitas detalhadas e escalar ingredientes no frontend
        const cardapio_gerado = [];
        
        for (const refeicao of refeicoes) {
            const nova_refeicao = {
                refeicao_id: refeicao.id,
                porcoes_desejadas: refeicao.porcoes,
                receitas: []
            };
            
            for (const receitaRef of refeicoes.find(r => r.id === refeicao.id).receitas) {
                try {
                    // Buscar receita original via GitHub Raw
                    const rawResponse = await fetch(`${GITHUB_RAW_BASE}/recipes/${receitaRef.file_id}`);
                    if (!rawResponse.ok) throw new Error('Receita não encontrada');
                    const recipe_data = await rawResponse.json();
                    
                    const porcoes_originais = recipe_data.porcoes || 1;
                    const scale_factor = refeicao.porcoes / porcoes_originais;
                    
                    // Escalar ingredientes
                    const scaled_ingredients = scaleIngredients(recipe_data.ingredientes || [], scale_factor);
                    
                    const receita_escalada = {
                        titulo: recipe_data.titulo,
                        tipo: recipe_data.tipo,
                        porcoes: refeicao.porcoes,
                        ingredientes: scaled_ingredients,
                        modo_de_preparo: recipe_data.modo_de_preparo || [],
                        fonte: recipe_data.fonte || ''
                    };
                    
                    nova_refeicao.receitas.push(receita_escalada);
                } catch (e) {
                    console.error(`Error processing recipe ${receitaRef.file_id}:`, e);
                }
            }
            
            cardapio_gerado.push(nova_refeicao);
        }
        
        // Gerar arquivo para download
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = `cardapio_${timestamp}.json`;
        const blob = new Blob([JSON.stringify(cardapio_gerado, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast('Sucesso!', `O arquivo ${filename} foi baixado com o cardápio gerado.`);
        
    } catch (error) {
        console.error('Error generating cardapio:', error);
        showToast('Erro', 'Ocorreu um erro ao gerar o cardápio.', true);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Gerar Arquivo JSON';
    }
}

function scaleIngredients(ingredientes, scale_factor) {
    const scaled = [];
    for (const ingrediente of ingredientes) {
        const novo = { nome: ingrediente.nome };
        const novas_quantidades = [];
        for (const quant of ingrediente.quantidade || []) {
            try {
                let q = quant.quantidade;
                if (typeof q === 'number') {
                    novas_quantidades.push({
                        quantidade: Math.round(q * scale_factor * 100) / 100,
                        unidade_de_medida: quant.unidade_de_medida || ''
                    });
                } else {
                    novas_quantidades.push(quant);
                }
            } catch {
                novas_quantidades.push(quant);
            }
        }
        novo.quantidade = novas_quantidades;
        scaled.push(novo);
    }
    return scaled;
}

function showToast(title, message, isError = false) {
    const toast = document.getElementById('toast');
    const titleEl = document.getElementById('toast-title');
    const descEl = document.getElementById('toast-desc');
    const iconEl = toast.querySelector('.toast-icon');
    
    titleEl.textContent = title;
    descEl.textContent = message;
    
    if (isError) {
        toast.style.borderLeftColor = 'var(--danger-color)';
        iconEl.textContent = '❌';
    } else {
        toast.style.borderLeftColor = 'var(--success-color)';
        iconEl.textContent = '✅';
    }
    
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 5000);
}

// Viewer Modal Logic (listagem de cardápios locais/baixados)
document.addEventListener('DOMContentLoaded', () => {
    const btnView = document.getElementById('btn-view-cardapios');
    const btnClose = document.getElementById('btn-close-modal');
    const modal = document.getElementById('viewer-modal');
    
    btnView.addEventListener('click', openViewerModal);
    btnClose.addEventListener('click', closeViewerModal);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeViewerModal();
        }
    });
});

function openViewerModal() {
    document.getElementById('viewer-modal').classList.remove('hidden');
    loadCardapiosList();
}

function closeViewerModal() {
    document.getElementById('viewer-modal').classList.add('hidden');
}

async function loadCardapiosList() {
    const listEl = document.getElementById('cardapio-list');
    listEl.innerHTML = '<li class="loading-text">Nenhum cardápio salvo no GitHub. Baixe um cardápio para abrir para impressão.</li>';
    
    try {
        // Tentar listar cardápios salvos no GitHub (pasta cardapios/)
        const response = await fetch(`${GITHUB_API_BASE}/contents/cardapios`);
        
        if (response.ok) {
            const files = await response.json();
            const cardapioFiles = files.filter(f => f.name.startsWith('cardapio_') && f.name.endsWith('.json'));
            
            if (cardapioFiles.length === 0) {
                listEl.innerHTML = '<li class="loading-text">Nenhum cardápio encontrado no GitHub.</li>';
                return;
            }
            
            listEl.innerHTML = '';
            cardapioFiles.forEach(file => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span class="filename">${file.name}</span>
                `;
                li.addEventListener('click', () => {
                    // Abrir print com o arquivo raw do GitHub
                    const rawUrl = `${GITHUB_RAW_BASE}/cardapios/${file.name}`;
                    window.open(`/print.html?file=${encodeURIComponent(rawUrl)}`, '_blank');
                    closeViewerModal();
                });
                listEl.appendChild(li);
            });
        } else {
            listEl.innerHTML = '<li class="loading-text">Não foi acessível listar cardápios no GitHub.</li>';
        }
    } catch (error) {
        console.error('Error loading cardapios:', error);
        listEl.innerHTML = '<li class="loading-text" style="color:var(--danger-color)">Erro ao carregar lista.</li>';
    }
});
