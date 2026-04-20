const dropArea = document.getElementById("dropArea");
const fileInput = document.getElementById("fileInput");
const selectedFile = document.getElementById("selectedFile");
const submitBtn = document.getElementById("submitBtn");
const uploadForm = document.getElementById("uploadForm");
const taskPanel = document.getElementById("taskPanel");
const taskLine = document.getElementById("taskLine");
const taskMeta = document.getElementById("taskMeta");
const methodsProgress = document.getElementById("methodsProgress");
const progressBar = document.getElementById("progressBar");
const resultPanel = document.getElementById("resultPanel");
const resultsContent = document.getElementById("resultsContent");
const detailModal = document.getElementById("detailModal");
const modalBody = document.getElementById("modalBody");
const detailModalClose = document.getElementById("detailModalClose");
const detailCompareBtn = document.getElementById("detailCompareBtn");
const compareModal = document.getElementById("compareModal");
const compareModalBody = document.getElementById("compareModalBody");
const compareModalClose = document.getElementById("compareModalClose");

let selected = null;
let pollTimer = null;
let visualProgress = 0;
let currentMethodData = {};
let currentDetailResult = null;
let currentDetailMethod = null;

const safeParagraphId = (result) => {
    if (!result) {
        return "—";
    }
    return (result.paragraph_id !== null && result.paragraph_id !== undefined) ? result.paragraph_id : "—";
};

const normalizeText = (value) => (value || "").replace(/\s+/g, " ").trim();

const extractConfidence = (result) => {
    if (!result || !result.primary_distribution || !result.predicted_ministry) {
        return null;
    }
    const score = result.primary_distribution[result.predicted_ministry];
    if (score === undefined || score === null) {
        return null;
    }
    return score;
};

const getMatchForMethod = (methodResults, selectedResult) => {
    if (!Array.isArray(methodResults) || !selectedResult) {
        return null;
    }

    const selectedParagraphId = selectedResult.paragraph_id;
    if (selectedParagraphId !== null && selectedParagraphId !== undefined) {
        const byId = methodResults.find((item) => item?.paragraph_id === selectedParagraphId);
        if (byId) {
            return byId;
        }
    }

    const selectedOriginal = normalizeText(selectedResult.original_paragraph);
    if (selectedOriginal) {
        const byOriginal = methodResults.find((item) => normalizeText(item?.original_paragraph) === selectedOriginal);
        if (byOriginal) {
            return byOriginal;
        }
    }

    const selectedProcessed = normalizeText(selectedResult.paragraph);
    if (selectedProcessed) {
        const byProcessed = methodResults.find((item) => normalizeText(item?.paragraph) === selectedProcessed);
        if (byProcessed) {
            return byProcessed;
        }
    }

    return null;
};

const showCompareModal = (selectedResult, selectedMethod) => {
    const paragraphId = safeParagraphId(selectedResult);
    const originalParagraph = selectedResult?.original_paragraph || "—";
    const processedParagraph = selectedResult?.paragraph || "—";

    const comparisonRows = Object.entries(currentMethodData).map(([methodName, methodData]) => {
        if (methodData?.error) {
            return {
                method: methodName,
                predicted: "Error",
                confidence: "—",
                note: methodData.error,
            };
        }

        const matched = getMatchForMethod(methodData?.results || [], selectedResult);
        if (!matched) {
            return {
                method: methodName,
                predicted: "Not found",
                confidence: "—",
                note: "No matching paragraph found in this method output",
            };
        }

        const predicted = matched.predicted_ministry ? matched.predicted_ministry.replace(/_/g, " ") : "—";
        const confidenceScore = extractConfidence(matched);
        return {
            method: methodName,
            predicted,
            confidence: confidenceScore === null ? "—" : `${(confidenceScore * 100).toFixed(2)}%`,
        };
    });

    const rowsHtml = comparisonRows.map((row) => `
        <tr>
            <td>${row.method}</td>
            <td>${row.predicted}</td>
            <td>${row.confidence}</td>
        </tr>
    `).join("");

    compareModalBody.innerHTML = `
        <div class="compare-section">
            <div class="compare-section-title">Paragraph ID</div>
            <div class="compare-section-text">${paragraphId}</div>
        </div>
        <div class="compare-section">
            <div class="compare-section-title">Original Paragraph</div>
            <div class="compare-section-text">${originalParagraph}</div>
        </div>
        <div class="compare-section">
            <div class="compare-section-title">Processed Paragraph</div>
            <div class="compare-section-text">${processedParagraph}</div>
        </div>
        <div class="compare-table-wrap">
            <table class="compare-table">
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Predicted Ministry</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        </div>
    `;

    detailModal.hidden = true;
    compareModal.hidden = false;
};

const setTaskUi = (text, pct, meta = "", completed = 0, total = 7) => {
    taskPanel.hidden = false;
    taskLine.textContent = text;
    taskMeta.textContent = meta;
    methodsProgress.textContent = `${completed}/${total} methods completed`;
    progressBar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
};

const isPdf = (file) => file && file.name.toLowerCase().endsWith(".pdf");

const updateSelectedState = () => {
    submitBtn.disabled = !selected;
    selectedFile.textContent = selected
        ? `Selected: ${selected.name} (${(selected.size / (1024 * 1024)).toFixed(2)} MB)`
        : "";
};

const bindDragDrop = () => {
    ["dragenter", "dragover"].forEach((eventName) => {
        dropArea.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropArea.classList.add("drag");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropArea.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropArea.classList.remove("drag");
        });
    });

    dropArea.addEventListener("drop", (event) => {
        const file = event.dataTransfer?.files?.[0] || null;
        if (file && isPdf(file)) {
            selected = file;
            updateSelectedState();
            return;
        }
        selected = null;
        updateSelectedState();
        window.alert("Only PDF files are allowed.");
    });
};

fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0] || null;
    if (!file) {
        selected = null;
        updateSelectedState();
        return;
    }

    if (!isPdf(file)) {
        selected = null;
        fileInput.value = "";
        updateSelectedState();
        window.alert("Only PDF files are allowed.");
        return;
    }

    selected = file;
    updateSelectedState();
});

const startVisualProgress = () => {
    visualProgress = 6;
    setTaskUi("Uploading file...", visualProgress, "", 0, 7);
    return window.setInterval(() => {
        if (visualProgress < 92) {
            visualProgress += Math.random() * 6;
            setTaskUi("Processing in backend...", visualProgress, "", 0, 7);
        }
    }, 1200);
};

const buildResultsHtml = (outputData) => {
    const methods = Object.keys(outputData);
    currentMethodData = outputData;
    
    let html = `<div class="results-wrapper">
        <div class="method-tabs">`;
    
    methods.forEach((method, idx) => {
        html += `<button class="method-tab ${idx === 0 ? "active" : ""}" data-method="${method}">${method}</button>`;
    });
    
    html += `</div><div class="method-content">`;
    
    methods.forEach((method, idx) => {
        const methodData = outputData[method];
        const isActive = idx === 0 ? "active" : "";
        
        if (methodData.error) {
            html += `<div class="method-pane ${isActive}" data-method="${method}">
                <div class="error-box">Error: ${methodData.error}</div>
            </div>`;
            return;
        }
        
        const results = methodData.results || [];
        const numParagraphs = methodData.num_paragraphs || 0;
        
        html += `<div class="method-pane ${isActive}" data-method="${method}">
            <p class="method-info">Paragraphs processed: ${numParagraphs}</p>
            <div class="results-table-wrapper">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Para ID</th>
                            <th>Text Preview</th>
                            <th>Predicted Ministry</th>
                            <th>Confidence</th>
                        </tr>
                    </thead>
                    <tbody>`;
        
        results.slice(0, 100).forEach((result, rowIdx) => {
            const paraId = safeParagraphId(result);
            const textPreview = (result.paragraph || "").split(" ").slice(0, 8).join(" ").substring(0, 50);
            const predicted = result.predicted_ministry ? result.predicted_ministry.replace(/_/g, " ") : "—";
            
            // Extract confidence score from primary_distribution for predicted ministry
            const score = extractConfidence(result);
            const confidence = score === null ? "—" : `${(score * 100).toFixed(1)}%`;
            
            html += `<tr class="result-row" data-method="${method}" data-row="${rowIdx}" data-para-id="${paraId}">
                <td>${paraId}</td>
                <td>${textPreview}...</td>
                <td>${predicted}</td>
                <td>${confidence}</td>
            </tr>`;
        });
        
        if (results.length > 100) {
            html += `<tr><td colspan="4" style="text-align: center; padding: 1rem; color: #666;">Showing first 100 of ${results.length} rows</td></tr>`;
        }
        
        html += `</tbody></table></div></div>`;
    });
    
    html += `</div></div>`;
    return html;
};

const showRowDetails = (method, rowIdx) => {
    const methodData = currentMethodData[method];
    if (!methodData || !methodData.results || !methodData.results[rowIdx]) return;
    
    const result = methodData.results[rowIdx];
    
    // Build all ministries list from primary_distribution, sorted by confidence descending
    const ministryList = result.primary_distribution ? 
        Object.entries(result.primary_distribution)
            .map(([ministry, score]) => ({
                name: ministry.replace(/_/g, " "),
                score: score
            }))
            .sort((a, b) => b.score - a.score)
            .map((m, i) => `${i + 1}. ${m.name} (${(m.score * 100).toFixed(2)}%)`)
            .join("<br>")
        : "—";
    
    let html = `
        <div class="detail-row">
            <div class="detail-label">Paragraph ID</div>
            <div class="detail-value">${safeParagraphId(result)}</div>
        </div>
        <div class="detail-row">
            <div class="detail-label">Speaker</div>
            <div class="detail-value">${result.speaker || "—"}</div>
        </div>
        <div class="detail-row">
            <div class="detail-label">Processed Paragraph</div>
            <div class="detail-value">${result.paragraph || "—"}</div>
        </div>
        <div class="detail-row">
            <div class="detail-label">Original Paragraph</div>
            <div class="detail-value">${result.original_paragraph || "—"}</div>
        </div>
        <div class="detail-row">
            <div class="detail-label">Predicted Ministry</div>
            <div class="detail-value">${(result.predicted_ministry || "—").replace(/_/g, " ")}</div>
        </div>
        <div class="detail-row">
            <div class="detail-label">All Ministries (Ranked)</div>
            <div class="detail-value">${ministryList}</div>
        </div>
    `;
    
    modalBody.innerHTML = html;
    currentDetailResult = result;
    currentDetailMethod = method;
    detailCompareBtn.disabled = false;
    detailModal.hidden = false;
};

const attachMethodTabListeners = () => {
    document.querySelectorAll(".method-tab").forEach((tab) => {
        tab.addEventListener("click", (e) => {
            const method = e.target.dataset.method;
            
            document.querySelectorAll(".method-tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".method-pane").forEach(p => p.classList.remove("active"));
            
            e.target.classList.add("active");
            document.querySelector(`.method-pane[data-method="${method}"]`)?.classList.add("active");
        });
    });
    
    // Attach click handlers to table rows
    document.querySelectorAll(".result-row").forEach((row) => {
        row.addEventListener("click", () => {
            const method = row.dataset.method;
            const rowIdx = parseInt(row.dataset.row);
            showRowDetails(method, rowIdx);
        });
    });
};

const pollTask = async (taskId) => {
    try {
        const response = await fetch(`/upload/tasks/${taskId}`);
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || "Status check failed");
        }

        const completed = payload.completed_methods || 0;
        const total = payload.total_methods || 7;
        const pct = (completed / total) * 100;
        
        setTaskUi(
            `Task ${payload.status}`,
            payload.status === "completed" ? 100 : pct,
            `Task ID: ${payload.task_id}`,
            completed,
            total
        );

        if (payload.status === "completed") {
            clearInterval(pollTimer);
            pollTimer = null;
            resultPanel.hidden = false;
            
            if (payload.result && payload.result.outputs) {
                resultsContent.innerHTML = buildResultsHtml(payload.result.outputs);
                attachMethodTabListeners();
            }
            
            submitBtn.disabled = false;
        }

        if (payload.status === "failed") {
            clearInterval(pollTimer);
            pollTimer = null;
            resultPanel.hidden = false;
            resultsContent.innerHTML = `<div class="error-box">Processing failed: ${payload.error || "Unknown error"}</div>`;
            submitBtn.disabled = false;
        }
    } catch (error) {
        clearInterval(pollTimer);
        pollTimer = null;
        setTaskUi("Could not fetch task status", visualProgress, String(error), 0, 7);
        submitBtn.disabled = false;
    }
};

uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!selected) {
        return;
    }

    submitBtn.disabled = true;
    resultPanel.hidden = true;

    const progressTimer = startVisualProgress();

    try {
        const formData = new FormData();
        formData.append("file", selected);

        const response = await fetch("/upload/", {
            method: "POST",
            body: formData,
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || "Upload failed");
        }

        setTaskUi("Upload accepted. Task queued...", 20, `Task ID: ${payload.task_id.substring(0, 8)}...`, 0, 7);
        clearInterval(progressTimer);
        pollTimer = window.setInterval(() => pollTask(payload.task_id), 2000);
        pollTask(payload.task_id);
    } catch (error) {
        clearInterval(progressTimer);
        setTaskUi("Upload failed", visualProgress, String(error), 0, 7);
        resultPanel.hidden = false;
        resultsContent.innerHTML = `<div class="error-box">Upload failed: ${error.message}</div>`;
        submitBtn.disabled = false;
    }
});

bindDragDrop();
updateSelectedState();

detailCompareBtn.disabled = true;
detailCompareBtn.addEventListener("click", () => {
    if (!currentDetailResult || !currentDetailMethod) {
        return;
    }
    showCompareModal(currentDetailResult, currentDetailMethod);
});

// Modal close handlers
detailModalClose.addEventListener("click", () => {
    detailModal.hidden = true;
});

compareModalClose.addEventListener("click", () => {
    compareModal.hidden = true;
});

detailModal.addEventListener("click", (e) => {
    if (e.target === detailModal) {
        detailModal.hidden = true;
    }
});

compareModal.addEventListener("click", (e) => {
    if (e.target === compareModal) {
        compareModal.hidden = true;
    }
});

// Close modal on Escape key
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (!compareModal.hidden) {
            compareModal.hidden = true;
            return;
        }
        if (!detailModal.hidden) {
            detailModal.hidden = true;
        }
    }
});