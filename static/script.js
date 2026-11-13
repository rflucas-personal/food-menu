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
        const response = await fetch('/api/recipes');
        allRecipes = await response.json();
        
        // Group by tipo
        allRecipes.forEach(recipe => {
            if (recipe.tipo && groupedRecipes[recipe.tipo]) {
                groupedRecipes[recipe.tipo].push(recipe);
            }
        });
        
        populateSelectors();
    } catch (error) {
        console.error('Failed to fetch recipes:', error);
        showToast('Erro', 'Não foi possível carregar as receitas.', true);
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
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refeicoes: meals })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('Sucesso!', `O arquivo ${result.file} foi gerado no diretório do projeto.`);
            // Reset for a new plan if desired
        } else {
            showToast('Erro', result.error || 'Falha ao gerar o cardápio', true);
        }
    } catch (error) {
        console.error('Error generating cardapio:', error);
        showToast('Erro', 'Ocorreu um erro de rede.', true);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Gerar Arquivo JSON';
    }
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

// Viewer Modal Logic
document.addEventListener('DOMContentLoaded', () => {
    const btnView = document.getElementById('btn-view-cardapios');
    const btnClose = document.getElementById('btn-close-modal');
    const modal = document.getElementById('viewer-modal');
    
    btnView.addEventListener('click', openViewerModal);
    btnClose.addEventListener('click', closeViewerModal);
    
    // Close on click outside
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
    listEl.innerHTML = '<li class="loading-text">Carregando...</li>';
    
    try {
        const response = await fetch('/api/cardapios');
        const files = await response.json();
        
        if (files.length === 0) {
            listEl.innerHTML = '<li class="loading-text">Nenhum cardápio gerado ainda.</li>';
            return;
        }
        
        listEl.innerHTML = '';
        files.forEach(file => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="filename">${file.filename}</span>
                <span class="date">${file.created_at}</span>
            `;
            li.addEventListener('click', () => {
                // Open new tab for print
                window.open('/print.html?file=' + encodeURIComponent(file.filename), '_blank');
                closeViewerModal();
            });
            listEl.appendChild(li);
        });
    } catch (error) {
        console.error('Error loading files:', error);
        listEl.innerHTML = '<li class="loading-text" style="color:var(--danger-color)">Erro ao carregar lista.</li>';
    }
}
