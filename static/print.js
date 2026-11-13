document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const filename = urlParams.get('file');

    if (!filename) {
        document.getElementById('content').innerHTML = '<p class="danger-color">Nenhum arquivo especificado.</p>';
        return;
    }

    loadPrintData(filename);
});

async function loadPrintData(filename) {
    try {
        const response = await fetch(`/api/cardapios/${filename}`);
        const cardapio = await response.json();

        if (cardapio.error) {
            throw new Error(cardapio.error);
        }

        renderPrintView(filename, cardapio);

    } catch (error) {
        console.error(error);
        document.getElementById('content').innerHTML = '<p style="color:red">Erro ao carregar os dados para impressão.</p>';
    }
}

function consolidateIngredients(cardapio) {
    const list = {};

    cardapio.forEach(refeicao => {
        refeicao.receitas.forEach(receita => {
            receita.ingredientes.forEach(ing => {
                const nome = ing.nome.trim();
                if (!list[nome]) {
                    list[nome] = {};
                }

                ing.quantidade.forEach(q => {
                    const unidade = q.unidade_de_medida.trim() || 'un';
                    
                    if (!list[nome][unidade]) {
                        list[nome][unidade] = {
                            sum: 0,
                            isText: false,
                            textValues: new Set()
                        };
                    }

                    if (typeof q.quantidade === 'number') {
                        list[nome][unidade].sum += q.quantidade;
                    } else {
                        list[nome][unidade].isText = true;
                        list[nome][unidade].textValues.add(q.quantidade);
                    }
                });
            });
        });
    });

    return list;
}

function consolidateRecipes(cardapio) {
    const recipesMap = {};
    
    cardapio.forEach(ref => {
        ref.receitas.forEach(rec => {
            const titulo = rec.titulo;
            if (!recipesMap[titulo]) {
                // Deep copy the first time we see it
                recipesMap[titulo] = JSON.parse(JSON.stringify(rec));
            } else {
                // Sum portions
                recipesMap[titulo].porcoes += rec.porcoes;
                
                // Sum ingredients
                rec.ingredientes.forEach(ing => {
                    let targetIng = recipesMap[titulo].ingredientes.find(i => i.nome === ing.nome);
                    if (!targetIng) {
                        recipesMap[titulo].ingredientes.push(JSON.parse(JSON.stringify(ing)));
                    } else {
                        // Sum quantities
                        ing.quantidade.forEach(q => {
                            let targetQ = targetIng.quantidade.find(tq => tq.unidade_de_medida === q.unidade_de_medida);
                            if (!targetQ) {
                                targetIng.quantidade.push(JSON.parse(JSON.stringify(q)));
                            } else {
                                if (typeof q.quantidade === 'number') {
                                    targetQ.quantidade += q.quantidade;
                                }
                            }
                        });
                    }
                });
            }
        });
    });
    
    // Sort recipes by type: proteina -> acompanhamento -> complemento
    const typeOrder = { 'proteina': 1, 'acompanhamento': 2, 'complemento': 3 };
    const result = Object.values(recipesMap);
    result.sort((a, b) => {
        let orderA = typeOrder[a.tipo] || 99;
        let orderB = typeOrder[b.tipo] || 99;
        return orderA - orderB;
    });
    
    return result;
}

function renderPrintView(filename, cardapio) {
    const contentEl = document.getElementById('content');
    
    // 1. Generate Consolidated List
    const consolidatedIngs = consolidateIngredients(cardapio);
    
    let html = `
        <div style="margin-bottom: 2rem;">
            <h1>Cardápio Planejado</h1>
            <p style="color: var(--text-secondary)">Arquivo: ${filename}</p>
        </div>
    `;

    html += `
        <div class="consolidated-list">
            <h2>🛒 Lista de Compras Consolidada</h2>
            <ul class="consolidated-items">
    `;

    const sortedNames = Object.keys(consolidatedIngs).sort();
    
    sortedNames.forEach(nome => {
        const unids = consolidatedIngs[nome];
        const amounts = [];

        Object.keys(unids).forEach(u => {
            const data = unids[u];
            if (data.isText) {
                amounts.push(Array.from(data.textValues).join(', '));
            } else if (data.sum > 0) {
                const num = Number.isInteger(data.sum) ? data.sum : data.sum.toFixed(2).replace('.', ',');
                amounts.push(`${num} ${u}`);
            }
        });

        html += `<li><strong>${nome}</strong>: <span style="float: right">${amounts.join(' + ')}</span></li>`;
    });

    html += `
            </ul>
        </div>
        <hr style="border: 0; border-top: 1px solid var(--glass-border); margin: 2rem 0;">
    `;

    // 2. Render Consolidated Recipes (Batch Cooking Guide)
    const consolidatedRecs = consolidateRecipes(cardapio);
    html += `<h2>👨‍🍳 Guia de Cozimento (Receitas Consolidadas)</h2>`;
    html += `<div style="margin-bottom: 3rem;">`;
    
    consolidatedRecs.forEach(receita => {
        let ingredientsHtml = receita.ingredientes.map(ing => {
            let qtdText = ing.quantidade.map(q => {
                let amount = typeof q.quantidade === 'number' ? q.quantidade.toString().replace('.', ',') : q.quantidade;
                return `${amount} ${q.unidade_de_medida}`;
            }).join(' + ');
            return `<li><strong>${ing.nome}</strong>: ${qtdText}</li>`;
        }).join('');
        
        let prepHtml = receita.modo_de_preparo.map(step => `<li style="margin-bottom: 0.5rem;">${step}</li>`).join('');
        
        html += `
            <div class="recipe-card" style="page-break-inside: avoid;">
                <h3 style="margin-bottom:1rem; border-bottom: 1px dashed var(--glass-border); padding-bottom: 0.5rem;">
                    ${receita.titulo} <span style="font-size: 1rem; font-weight: normal; color: var(--text-secondary)">(${receita.tipo}) - Preparar ${receita.porcoes} porções no total</span>
                </h3>
                <h5 style="margin-bottom: 0.5rem; color: var(--text-secondary)">Ingredientes Somados:</h5>
                <ul class="ingredients-list">
                    ${ingredientsHtml}
                </ul>
                <h5 style="margin-bottom: 0.5rem; margin-top: 1.5rem; color: var(--text-secondary)">Modo de Preparo Único:</h5>
                <ol class="prep-list">
                    ${prepHtml}
                </ol>
            </div>
        `;
    });
    
    html += `</div>`;

    // 3. Render Assembly Guide
    html += `
        <hr style="border: 0; border-top: 1px solid var(--glass-border); margin: 2rem 0;">
        <h2>🍱 Guia de Montagem das Marmitas</h2>
        <ul style="list-style-type: none; padding-left: 0; margin-bottom: 3rem; display: flex; flex-direction: column; gap: 1rem;">
    `;
    
    cardapio.forEach((ref, index) => {
        let recipeNames = ref.receitas.map(r => r.titulo).join(' + ');
        html += `<li style="padding: 1rem; border: 1px solid var(--glass-border); border-radius: var(--radius-md); background: var(--input-bg); page-break-inside: avoid;">
            <strong style="display: block; font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--accent-color);">Refeição ${index + 1} <span style="color: var(--text-secondary); font-size: 0.9rem">(${ref.porcoes_desejadas} marmitas)</span></strong> 
            Montar com: ${recipeNames}
        </li>`;
    });
    html += '</ul>';

    contentEl.innerHTML = html;
}
