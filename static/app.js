/**
 * LegalLens — Client Application
 * Navigation, document filter, API calls, markdown rendering, export.
 */

// ═══════════════════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════════════════
const state = {
    documents: [],
    selectedDocs: [],      // empty = all docs
    currentView: 'risk',
    chatHistory: [],
    isLoading: false,
    lastRiskHTML: '',       // persist risk results across tab switches
    lastRiskData: null,    // raw data for PDF export
};

const viewTitles = {
    risk: { title: 'Risk Analysis', sub: 'Identify risky clauses in your legal documents' },
    chat: { title: 'Q&A Chat', sub: 'Ask questions about your documents in any language' },
    eval: { title: 'Evaluation', sub: 'RAG pipeline performance metrics' },
};

// Configure marked for safe rendering
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
    });
}


// ═══════════════════════════════════════════════════════════════════════
//  DOM REFERENCES
// ═══════════════════════════════════════════════════════════════════════
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const views = { risk: $('#view-risk'), chat: $('#view-chat'), eval: $('#view-eval'), welcome: $('#view-welcome') };
const navItems = $$('.nav-item[data-view]');


// ═══════════════════════════════════════════════════════════════════════
//  NAVIGATION
// ═══════════════════════════════════════════════════════════════════════
function switchView(view) {
    state.currentView = view;
    Object.values(views).forEach(v => v.classList.add('hidden'));

    if (state.documents.length === 0) {
        views.welcome.classList.remove('hidden');
    } else {
        views[view]?.classList.remove('hidden');
    }

    navItems.forEach(item => item.classList.toggle('active', item.dataset.view === view));

    const info = viewTitles[view];
    if (info) {
        $('#view-title').textContent = info.title;
        $('#view-subtitle').textContent = info.sub;
    }

    // Restore persisted risk results
    if (view === 'risk' && state.lastRiskHTML) {
        $('#risk-results').innerHTML = state.lastRiskHTML;
    }

    // Update header actions
    updateHeaderActions(view);
}

function updateHeaderActions(view) {
    const el = $('#header-actions');
    el.innerHTML = '';

    if (view === 'risk' && state.lastRiskHTML) {
        el.innerHTML = `
            <button class="btn-secondary" onclick="exportReport()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                Export PDF
            </button>`;
    }

    if (view === 'chat' && state.chatHistory.length > 0) {
        el.innerHTML = `
            <button class="btn-secondary" onclick="exportChat()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                Export PDF
            </button>
            <button class="btn-secondary" onclick="clearChat()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                Clear
            </button>`;
    }
}

navItems.forEach(item => {
    item.addEventListener('click', () => switchView(item.dataset.view));
});


// ═══════════════════════════════════════════════════════════════════════
//  DOCUMENTS + FILTER
// ═══════════════════════════════════════════════════════════════════════
async function loadDocuments() {
    try {
        const res = await fetch('/api/documents');
        const data = await res.json();
        state.documents = data.documents || [];
        state.selectedDocs = []; // reset selection
        renderDocList();
        switchView(state.currentView);
    } catch (e) {
        console.error('Failed to load documents:', e);
    }
}

function renderDocList() {
    const el = $('#doc-list');
    if (state.documents.length === 0) {
        el.innerHTML = '<div style="font-size:0.75rem;color:var(--text-muted);padding:0.3rem 0.6rem;">No documents yet</div>';
        return;
    }

    let html = '<div class="doc-filter-hint">Select documents to filter, or leave all unchecked to search everything</div>';
    state.documents.forEach((d, i) => {
        const checked = state.selectedDocs.includes(d) ? 'checked' : '';
        const selectedClass = state.selectedDocs.includes(d) ? 'selected' : '';
        html += `
        <div class="doc-item ${selectedClass}">
            <input type="checkbox" class="doc-checkbox" data-doc="${escapeHtml(d)}" ${checked}>
            <span class="doc-dot"></span>
            <span class="doc-name-link" onclick="event.stopPropagation();openPdfViewer('${escapeHtml(d)}')" title="Click to preview">${escapeHtml(d)}</span>
            <button class="doc-delete" onclick="event.stopPropagation();deleteDocument('${escapeHtml(d)}')" title="Remove document">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            </button>
        </div>`;
    });
    el.innerHTML = html;

    // Attach listeners
    el.querySelectorAll('.doc-checkbox').forEach(cb => {
        cb.addEventListener('change', onDocFilterChange);
    });
}

async function deleteDocument(filename) {
    if (!confirm(`Remove "${filename}" from the database? This cannot be undone.`)) return;
    try {
        const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Delete failed');
        }
        const data = await res.json();
        showToast(`Removed ${filename} (${data.chunks_removed} chunks)`, 'success');
        await loadDocuments();
    } catch (e) {
        showToast(`Delete failed: ${e.message}`, 'error');
    }
}

function onDocFilterChange() {
    const checked = [];
    $$('.doc-checkbox:checked').forEach(cb => checked.push(cb.dataset.doc));
    state.selectedDocs = checked;

    // Update visual state
    $$('.doc-item').forEach(item => {
        const cb = item.querySelector('.doc-checkbox');
        item.classList.toggle('selected', cb && cb.checked);
    });
}

function getSourceFilter() {
    return state.selectedDocs.length > 0 ? state.selectedDocs : null;
}


// ═══════════════════════════════════════════════════════════════════════
//  FILE UPLOAD
// ═══════════════════════════════════════════════════════════════════════
const uploadZone = $('#upload-zone');
const uploadInput = $('#upload-input');

uploadZone.addEventListener('click', () => uploadInput.click());
uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});
uploadInput.addEventListener('change', (e) => { handleFiles(e.target.files); e.target.value = ''; });

async function handleFiles(files) {
    for (const file of files) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['pdf', 'docx'].includes(ext)) {
            showToast(`Unsupported format: .${ext}`, 'error');
            continue;
        }

        // Show upload progress in the upload zone
        const zone = $('#upload-zone');
        const originalHTML = zone.innerHTML;
        zone.innerHTML = `
        <div class="upload-progress">
            <div class="upload-step active" id="step-upload"><div class="spinner"></div> Uploading ${escapeHtml(file.name)}...</div>
            <div class="upload-step" id="step-parse">Parsing document...</div>
            <div class="upload-step" id="step-chunk">Chunking text...</div>
            <div class="upload-step" id="step-embed">Generating embeddings...</div>
        </div>`;

        const formData = new FormData();
        formData.append('file', file);

        // Simulate progress steps (actual work is on server)
        const stepTimer = setTimeout(() => {
            _advanceStep('step-upload', 'step-parse');
            setTimeout(() => _advanceStep('step-parse', 'step-chunk'), 2000);
            setTimeout(() => _advanceStep('step-chunk', 'step-embed'), 4000);
        }, 1000);

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            clearTimeout(stepTimer);
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Upload failed');
            }
            showToast(`${file.name} ingested successfully`, 'success');
            await loadDocuments();
        } catch (e) {
            showToast(`Failed: ${e.message}`, 'error');
        }
        zone.innerHTML = originalHTML;
    }
}

function _advanceStep(doneId, activeId) {
    const done = document.getElementById(doneId);
    const active = document.getElementById(activeId);
    if (done) { done.classList.remove('active'); done.classList.add('done'); done.innerHTML = '✓ ' + done.textContent.replace('...',''); }
    if (active) { active.classList.add('active'); active.innerHTML = '<div class="spinner"></div> ' + active.textContent + '...'; }
}


// ═══════════════════════════════════════════════════════════════════════
//  RISK ANALYSIS
// ═══════════════════════════════════════════════════════════════════════
$('#risk-btn').addEventListener('click', runAnalysis);
$('#risk-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') runAnalysis(); });

// Scan All Risks — comprehensive query
$('#scan-all-btn').addEventListener('click', () => {
    $('#risk-input').value = '';
    runAnalysis('Identify all risky clauses including liability, indemnification, termination, payment penalties, confidentiality breaches, non-compete restrictions, warranty disclaimers, and any provisions that could be unfavorable to the signing party');
});

// Suggestion chip clicks
$$('.chip[data-query]').forEach(chip => {
    chip.addEventListener('click', () => {
        $('#risk-input').value = chip.dataset.query;
        runAnalysis();
    });
});

async function runAnalysis(overrideQuery) {
    const query = overrideQuery || $('#risk-input').value.trim();
    if (!query || state.isLoading) return;

    state.isLoading = true;
    $('#risk-btn').disabled = true;
    $('#scan-all-btn').disabled = true;
    const loadingEl = $('#risk-loading');
    const resultsEl = $('#risk-results');
    const suggestionsEl = $('#risk-suggestions');
    resultsEl.innerHTML = '';
    state.lastRiskHTML = '';
    state.lastRiskData = null;
    updateHeaderActions('risk');
    if (suggestionsEl) suggestionsEl.classList.add('hidden');

    const steps = ['Retrieving relevant document chunks', 'Classifying clause types', 'Evaluating risk levels', 'Writing detailed explanations'];
    let stepIdx = 0;
    loadingEl.classList.remove('hidden');
    loadingEl.innerHTML = renderLoading(steps[0]);
    const interval = setInterval(() => {
        stepIdx++;
        if (stepIdx < steps.length) loadingEl.innerHTML = renderLoading(steps[stepIdx]);
    }, 5000);

    try {
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, source_filter: getSourceFilter() }),
        });
        const data = await res.json();
        clearInterval(interval);
        loadingEl.classList.add('hidden');

        const report = data.report || [];
        if (report.length === 0) {
            resultsEl.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:3rem 0;">No relevant clauses found for this topic. Try broadening your search.</div>';
            if (suggestionsEl) suggestionsEl.classList.remove('hidden');
        } else {
            renderRiskResults(report);
            state.lastRiskData = report;
        }
        state.lastRiskHTML = resultsEl.innerHTML;
        updateHeaderActions('risk');
    } catch (e) {
        clearInterval(interval);
        loadingEl.classList.add('hidden');
        resultsEl.innerHTML = `<div style="color:var(--error);padding:1rem;">Analysis failed: ${escapeHtml(e.message)}</div>`;
        if (suggestionsEl) suggestionsEl.classList.remove('hidden');
    }

    state.isLoading = false;
    $('#risk-btn').disabled = false;
    $('#scan-all-btn').disabled = false;
}

function renderLoading(text) {
    return `<div class="loading-bar"><div class="spinner"></div>${escapeHtml(text)}...</div>`;
}

function renderRiskResults(report) {
    const el = $('#risk-results');
    const high = report.filter(r => (r.risk_level || '').toLowerCase() === 'high').length;
    const med = report.filter(r => (r.risk_level || '').toLowerCase() === 'medium').length;
    const low = report.filter(r => (r.risk_level || '').toLowerCase() === 'low').length;

    let html = `
    <div class="stat-row">
        <div class="stat-card"><div class="stat-value total">${report.length}</div><div class="stat-label">Findings</div></div>
        <div class="stat-card"><div class="stat-value high">${high}</div><div class="stat-label">High Risk</div></div>
        <div class="stat-card"><div class="stat-value medium">${med}</div><div class="stat-label">Medium Risk</div></div>
        <div class="stat-card"><div class="stat-value low">${low}</div><div class="stat-label">Low Risk</div></div>
    </div>
    <div class="section-label">Findings</div>`;

    report.forEach((item, i) => {
        const level = (item.risk_level || 'low').toLowerCase();
        const flags = item.risk_flags || [];
        const flagHtml = flags.length > 0
            ? `<span class="risk-flag">Rule flags: ${escapeHtml(flags.join(', '))}</span>`
            : '';
        const excerpt = item.original_excerpt || '';
        const excerptId = `excerpt-${i}`;
        const excerptHtml = excerpt
            ? `<button class="excerpt-toggle" onclick="toggleExcerpt('${excerptId}', this)">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                View original clause text
               </button>
               <div class="excerpt-text" id="${excerptId}">&ldquo;${escapeHtml(excerpt)}&rdquo;</div>`
            : '';

        html += `
        <div class="risk-card ${level}" style="animation-delay:${i * 0.08}s;">
            <div class="risk-header">
                <span class="risk-type">${escapeHtml(item.clause_type || 'Unknown')}</span>
                <span class="risk-badge ${level}">${level}</span>
            </div>
            <div class="risk-body">
                <p>${escapeHtml(item.explanation || '')}</p>
                <p><strong>Impact:</strong> ${escapeHtml(item.why_it_matters || '')}</p>
                <p><strong>Recommendation:</strong> ${escapeHtml(item.suggestion || '')}</p>
                ${excerptHtml}
            </div>
            <div class="risk-meta">
                <span>${escapeHtml(item.source_ref || '')}</span>
                ${flagHtml}
            </div>
        </div>`;
    });

    el.innerHTML = html;
}

function toggleExcerpt(id, btn) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle('open');
        btn.classList.toggle('open');
    }
}


// ═══════════════════════════════════════════════════════════════════════
//  PDF EXPORT — shared styling
// ═══════════════════════════════════════════════════════════════════════
const PDF_STYLES = `
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; line-height: 1.6; padding: 0; }
    .pdf-header { text-align: center; padding: 1.5rem 0 1rem; border-bottom: 2px solid #818cf8; margin-bottom: 1.5rem; }
    .pdf-header h1 { font-size: 1.4rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem; }
    .pdf-header p { font-size: 0.75rem; color: #888; }
    .pdf-footer { text-align: center; font-size: 0.65rem; color: #aaa; padding-top: 1rem; margin-top: 1.5rem; border-top: 1px solid #e5e5e5; }

    /* Summary row */
    .sum-row { display: flex; gap: 0.6rem; margin-bottom: 1.2rem; }
    .sum-card { flex: 1; text-align: center; padding: 0.7rem 0.5rem; border: 1px solid #e0e0e0; border-radius: 6px; }
    .sum-val { font-size: 1.3rem; font-weight: 800; }
    .sum-val.total { color: #818cf8; }
    .sum-val.high { color: #ef4444; }
    .sum-val.med { color: #f59e0b; }
    .sum-val.low { color: #10b981; }
    .sum-lbl { font-size: 0.65rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Risk cards */
    .r-card { border: 1px solid #e0e0e0; border-radius: 6px; padding: 0.8rem 1rem; margin-bottom: 0.6rem; page-break-inside: avoid; }
    .r-card.high { border-left: 3px solid #ef4444; }
    .r-card.medium { border-left: 3px solid #f59e0b; }
    .r-card.low { border-left: 3px solid #10b981; }
    .r-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
    .r-type { font-weight: 700; font-size: 0.85rem; }
    .r-badge { font-size: 0.6rem; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: 10px; }
    .r-badge.high { color: #ef4444; background: #fef2f2; }
    .r-badge.medium { color: #f59e0b; background: #fffbeb; }
    .r-badge.low { color: #10b981; background: #ecfdf5; }
    .r-body { font-size: 0.78rem; color: #444; }
    .r-body p { margin: 0.2rem 0; }
    .r-body strong { color: #1a1a2e; }
    .r-src { font-size: 0.68rem; color: #999; margin-top: 0.4rem; padding-top: 0.4rem; border-top: 1px solid #f0f0f0; }

    /* Chat messages */
    .msg { margin-bottom: 0.8rem; padding: 0.7rem 0.9rem; border-radius: 6px; page-break-inside: avoid; }
    .msg.user { background: #f0f0ff; border-left: 3px solid #818cf8; }
    .msg.assistant { background: #f8f8fa; border-left: 3px solid #d1d5db; }
    .msg-label { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #888; margin-bottom: 0.3rem; }
    .msg.user .msg-label { color: #818cf8; }
    .msg-text { font-size: 0.8rem; color: #333; }
    .msg-text h1, .msg-text h2, .msg-text h3, .msg-text h4 { margin: 0.4rem 0 0.2rem; color: #1a1a2e; }
    .msg-text h1 { font-size: 1rem; } .msg-text h2 { font-size: 0.92rem; } .msg-text h3 { font-size: 0.85rem; }
    .msg-text p { margin: 0.2rem 0; }
    .msg-text ul, .msg-text ol { margin: 0.2rem 0 0.2rem 1.2rem; }
    .msg-text li { margin-bottom: 0.1rem; }
    .msg-text strong { color: #1a1a2e; }
    .msg-text blockquote { border-left: 2px solid #818cf8; padding-left: 0.6rem; color: #666; margin: 0.3rem 0; }
    .msg-text code { background: #eee; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.75rem; }
    .msg-text pre { background: #f5f5f5; padding: 0.5rem; border-radius: 4px; overflow-x: auto; margin: 0.3rem 0; }
    .msg-text table { border-collapse: collapse; width: 100%; margin: 0.3rem 0; }
    .msg-text th, .msg-text td { border: 1px solid #ddd; padding: 0.3rem 0.5rem; font-size: 0.75rem; text-align: left; }
    .msg-text th { background: #f0f0f0; font-weight: 600; }
    .msg-src { font-size: 0.65rem; color: #999; margin-top: 0.3rem; }
    .section-title { font-size: 0.7rem; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.8px; margin: 1rem 0 0.5rem; }
`;

const PDF_OPTIONS = {
    margin: [12, 14, 14, 14],  // top, left, bottom, right in mm
    filename: 'report.pdf',
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, letterRendering: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
};

function generatePDF(contentEl, filename) {
    showToast('Generating PDF...');
    const opts = { ...PDF_OPTIONS, filename };
    html2pdf().set(opts).from(contentEl).save().then(() => {
        showToast('PDF downloaded', 'success');
    }).catch(err => {
        showToast('PDF failed: ' + err.message, 'error');
    });
}


// ═══════════════════════════════════════════════════════════════════════
//  EXPORT RISK REPORT AS PDF
// ═══════════════════════════════════════════════════════════════════════
function exportReport() {
    if (!state.lastRiskData || state.lastRiskData.length === 0) return;
    const report = state.lastRiskData;
    const query = $('#risk-input').value.trim() || 'General';
    const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });

    const high = report.filter(r => (r.risk_level||'').toLowerCase() === 'high').length;
    const med  = report.filter(r => (r.risk_level||'').toLowerCase() === 'medium').length;
    const low  = report.filter(r => (r.risk_level||'').toLowerCase() === 'low').length;

    let cardsHtml = '';
    report.forEach(item => {
        const level = (item.risk_level || 'low').toLowerCase();
        const flags = (item.risk_flags || []).join(', ');
        cardsHtml += `
        <div class="r-card ${level}">
            <div class="r-head">
                <span class="r-type">${escapeHtml(item.clause_type || 'Unknown')}</span>
                <span class="r-badge ${level}">${level}</span>
            </div>
            <div class="r-body">
                <p>${escapeHtml(item.explanation || '')}</p>
                <p><strong>Impact:</strong> ${escapeHtml(item.why_it_matters || '')}</p>
                <p><strong>Recommendation:</strong> ${escapeHtml(item.suggestion || '')}</p>
            </div>
            <div class="r-src">${escapeHtml(item.source_ref || '')}${flags ? ' · Flags: ' + escapeHtml(flags) : ''}</div>
        </div>`;
    });

    const container = document.createElement('div');
    container.innerHTML = `<style>${PDF_STYLES}</style>
    <div class="pdf-header">
        <h1>LegalLens — Risk Analysis Report</h1>
        <p>Topic: ${escapeHtml(query)} · Generated: ${dateStr}</p>
    </div>
    <div class="sum-row">
        <div class="sum-card"><div class="sum-val total">${report.length}</div><div class="sum-lbl">Findings</div></div>
        <div class="sum-card"><div class="sum-val high">${high}</div><div class="sum-lbl">High Risk</div></div>
        <div class="sum-card"><div class="sum-val med">${med}</div><div class="sum-lbl">Medium Risk</div></div>
        <div class="sum-card"><div class="sum-val low">${low}</div><div class="sum-lbl">Low Risk</div></div>
    </div>
    <div class="section-title">Detailed Findings</div>
    ${cardsHtml}
    <div class="pdf-footer">Generated by LegalLens — AI Legal Document Analysis</div>`;

    generatePDF(container, `LegalLens_Risk_Report_${new Date().toISOString().split('T')[0]}.pdf`);
}


// ═══════════════════════════════════════════════════════════════════════
//  EXPORT CHAT SESSION AS PDF
// ═══════════════════════════════════════════════════════════════════════
function exportChat() {
    if (state.chatHistory.length === 0) return;
    const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });

    let messagesHtml = '';
    state.chatHistory.forEach(msg => {
        const label = msg.role === 'user' ? 'You' : 'LegalLens';
        const textContent = msg.role === 'assistant' ? renderMarkdown(msg.content) : escapeHtml(msg.content);
        let srcLine = '';
        if (msg.sources && msg.sources.length > 0) {
            const srcs = msg.sources.map(s => {
                const name = (s.source || '').split(/[\\/]/).pop();
                return `p.${s.page || '?'} (${name})`;
            }).join(' · ');
            srcLine = `<div class="msg-src">Sources: ${srcs}</div>`;
        }
        messagesHtml += `
        <div class="msg ${msg.role}">
            <div class="msg-label">${label}</div>
            <div class="msg-text">${textContent}</div>
            ${srcLine}
        </div>`;
    });

    const container = document.createElement('div');
    container.innerHTML = `<style>${PDF_STYLES}</style>
    <div class="pdf-header">
        <h1>LegalLens — Q&A Session Transcript</h1>
        <p>${state.chatHistory.length} messages · ${dateStr}</p>
    </div>
    <div class="section-title">Conversation</div>
    ${messagesHtml}
    <div class="pdf-footer">Generated by LegalLens — AI Legal Document Analysis</div>`;

    generatePDF(container, `LegalLens_QA_Session_${new Date().toISOString().split('T')[0]}.pdf`);
}


// ═══════════════════════════════════════════════════════════════════════
//  Q&A CHAT
// ═══════════════════════════════════════════════════════════════════════
$('#chat-btn').addEventListener('click', sendChat);
$('#chat-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') sendChat(); });

async function sendChat() {
    const input = $('#chat-input');
    const query = input.value.trim();
    if (!query || state.isLoading) return;

    state.isLoading = true;
    input.value = '';
    $('#chat-empty')?.remove();
    $('#chat-btn').disabled = true;

    // User message
    state.chatHistory.push({ role: 'user', content: query });
    appendMessage('user', query);
    updateHeaderActions('chat');

    // Loading placeholder
    const loadingId = 'msg-loading-' + Date.now();
    appendLoadingMessage(loadingId);

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                source_filter: getSourceFilter(),
                chat_history: state.chatHistory.slice(0, -1).map(m => ({ role: m.role, content: m.content })),
            }),
        });
        const data = await res.json();
        document.getElementById(loadingId)?.remove();

        const answer = data.answer || 'No answer found.';
        const sources = data.sources || [];
        state.chatHistory.push({ role: 'assistant', content: answer, sources });
        appendMessage('assistant', answer, sources);
    } catch (e) {
        document.getElementById(loadingId)?.remove();
        const errMsg = 'Something went wrong. Please try again.';
        state.chatHistory.push({ role: 'assistant', content: errMsg });
        appendMessage('assistant', errMsg);
    }

    state.isLoading = false;
    $('#chat-btn').disabled = false;
    updateHeaderActions('chat');
}

function renderMarkdown(text) {
    if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
        try {
            return marked.parse(text);
        } catch (e) {
            return escapeHtml(text);
        }
    }
    return escapeHtml(text);
}

function appendMessage(role, text, sources) {
    const el = $('#chat-messages');
    const avatar = role === 'user' ? 'Y' : 'L';
    const label = role === 'user' ? 'You' : 'LegalLens';
    const renderedText = role === 'assistant' ? renderMarkdown(text) : escapeHtml(text);

    let srcHtml = '';
    if (sources && sources.length > 0) {
        const badges = sources.map(s => {
            const name = (s.source || '').split(/[\\/]/).pop();
            return `<span class="source-badge">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
                p.${s.page || '?'} ${name}
            </span>`;
        }).join('');
        srcHtml = `<div class="message-sources">${badges}</div>`;
    }

    el.insertAdjacentHTML('beforeend', `
    <div class="message ${role}">
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-sender">${label}</div>
            <div class="message-text">${renderedText}</div>
            ${srcHtml}
        </div>
    </div>`);

    el.scrollTop = el.scrollHeight;
}

function appendLoadingMessage(id) {
    const el = $('#chat-messages');
    el.insertAdjacentHTML('beforeend', `
    <div class="message assistant" id="${id}">
        <div class="message-avatar">L</div>
        <div class="message-content">
            <div class="message-sender">LegalLens</div>
            <div class="message-text"><div class="spinner" style="margin:0.3rem 0;"></div></div>
        </div>
    </div>`);
    el.scrollTop = el.scrollHeight;
}

function clearChat() {
    state.chatHistory = [];
    const el = $('#chat-messages');
    el.innerHTML = `
    <div class="chat-empty" id="chat-empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>Ask anything about your documents</span>
        <span style="font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem;">Supports English, Hindi, Hinglish, and 100+ languages</span>
    </div>`;
    updateHeaderActions('chat');
    showToast('Chat cleared');
}


// ═══════════════════════════════════════════════════════════════════════
//  EVALUATION
// ═══════════════════════════════════════════════════════════════════════
async function loadEvaluation() {
    try {
        const res = await fetch('/api/eval');
        const data = await res.json();
        renderEval(data);
    } catch (e) {
        $('#eval-grid').innerHTML = '<div style="color:var(--text-muted);">Could not load evaluation data.</div>';
    }
}

function renderEval(data) {
    const summary = data.summary || {};
    const metrics = [
        { key: 'faithfulness', name: 'Faithfulness', target: 0.85 },
        { key: 'answer_relevancy', name: 'Answer Relevancy', target: 0.80 },
        { key: 'context_precision', name: 'Context Precision', target: 0.75 },
        { key: 'context_recall', name: 'Context Recall', target: 0.75 },
    ];

    let gridHtml = '';
    metrics.forEach(m => {
        const score = summary[m.key];
        if (score != null && score > 0) {
            const passed = score >= m.target;
            const cls = passed ? 'pass' : 'fail';
            const txt = passed ? 'Pass' : 'Below target';
            gridHtml += `
            <div class="eval-card">
                <div class="eval-score">${Math.round(score * 100)}%</div>
                <div class="eval-name">${m.name}</div>
                <div class="eval-tag ${cls}">${txt} (target ${Math.round(m.target * 100)}%)</div>
            </div>`;
        } else {
            gridHtml += `
            <div class="eval-card">
                <div class="eval-score" style="color:var(--text-muted);">&mdash;</div>
                <div class="eval-name">${m.name}</div>
                <div class="eval-tag" style="color:var(--text-muted);">Not evaluated</div>
            </div>`;
        }
    });
    $('#eval-grid').innerHTML = gridHtml;

    const perQ = data.per_question || [];
    if (perQ.length === 0) {
        $('#eval-questions').innerHTML = '<div style="color:var(--text-muted);font-size:0.82rem;">No per-question data available.</div>';
        return;
    }

    let qHtml = '';
    perQ.forEach((q, i) => {
        const question = q.user_input || '';
        const answer = q.response || '';
        const ref = q.reference || '';
        const mKeys = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall'];
        const mLabels = ['Faithfulness', 'Relevancy', 'Precision', 'Recall'];
        let metricsHtml = '<div class="q-metrics">';
        mKeys.forEach((k, idx) => {
            const v = q[k];
            metricsHtml += `<div class="q-metric"><div class="q-metric-val">${typeof v === 'number' ? v.toFixed(2) : '—'}</div><div class="q-metric-lbl">${mLabels[idx]}</div></div>`;
        });
        metricsHtml += '</div>';

        qHtml += `
        <div class="q-item" onclick="this.classList.toggle('open')">
            <div class="q-header">
                <div><span class="q-num">Q${i + 1}</span>${escapeHtml(question.substring(0, 100))}${question.length > 100 ? '...' : ''}</div>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
            <div class="q-body">
                <div class="q-body-inner">
                    <p><strong>Question:</strong> ${escapeHtml(question)}</p>
                    <p><strong>Answer:</strong> ${escapeHtml(answer.substring(0, 500))}${answer.length > 500 ? '...' : ''}</p>
                    <p><strong>Expected:</strong> ${escapeHtml(ref)}</p>
                    ${metricsHtml}
                </div>
            </div>
        </div>`;
    });
    $('#eval-questions').innerHTML = qHtml;
}


// ═══════════════════════════════════════════════════════════════════════
//  TOAST
// ═══════════════════════════════════════════════════════════════════════
function showToast(message, type = '') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(8px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}


// ═══════════════════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════════════════
function escapeHtml(str) {
    if (!str) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return String(str).replace(/[&<>"']/g, c => map[c]);
}


// ═══════════════════════════════════════════════════════════════════════
//  PDF VIEWER
// ═══════════════════════════════════════════════════════════════════════
function openPdfViewer(filename) {
    const viewer = $('#pdf-viewer');
    const frame = $('#pdf-viewer-frame');
    const title = $('#pdf-viewer-title');
    title.textContent = filename;
    frame.src = `/api/file/${encodeURIComponent(filename)}`;
    viewer.classList.remove('hidden');
}

function closePdfViewer() {
    const viewer = $('#pdf-viewer');
    const frame = $('#pdf-viewer-frame');
    viewer.classList.add('hidden');
    frame.src = '';
}

// Close PDF viewer with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePdfViewer();
});


// ═══════════════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════════════
(async function init() {
    await loadDocuments();
    loadEvaluation();
})();
