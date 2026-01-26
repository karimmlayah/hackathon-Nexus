function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`${tab}-panel`).classList.add('active');
}

// File Upload Handling
const fileInput = document.getElementById('file-upload');
const fileNameDisplay = document.getElementById('file-name-display');
const uploadBtn = document.getElementById('upload-btn');

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        fileNameDisplay.textContent = e.target.files[0].name;
        uploadBtn.disabled = false;
        uploadBtn.classList.remove('secondary-btn');
    }
});

async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) return;

    uploadBtn.innerHTML = 'Uploading... <span class="loader"></span>';
    uploadBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (response.ok) {
            updateStats(`Indexed: ${result.filename} (${result.chunks_added} chunks)`);
            uploadBtn.innerHTML = 'Uploaded!';
            setTimeout(() => {
                uploadBtn.innerHTML = 'Upload Data';
                uploadBtn.disabled = false;
                fileNameDisplay.textContent = '';
                fileInput.value = '';
            }, 2000);
        } else {
            alert('Error: ' + result.detail);
            uploadBtn.innerHTML = 'Upload Data';
            uploadBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Upload failed');
        uploadBtn.innerHTML = 'Upload Data';
        uploadBtn.disabled = false;
    }
}

async function crawlUrl() {
    const urlInput = document.getElementById('crawl-url');
    const btn = document.getElementById('crawl-btn');
    const url = urlInput.value.trim();

    if (!url) return;

    btn.innerHTML = 'Crawling... <span class="loader"></span>';
    btn.disabled = true;

    try {
        const response = await fetch('/crawl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        const result = await response.json();
        if (response.ok) {
            updateStats(`Crawled: ${result.url} (${result.chunks_added} chunks)`);
            btn.innerHTML = 'Success!';
            urlInput.value = '';
        } else {
            alert('Error: ' + result.detail);
            btn.innerHTML = 'Initialize';
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Crawl failed');
        btn.innerHTML = 'Initialize';
    } finally {
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = 'Initialize';
        }, 2000);
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    // Add User Message
    addMessage(text, 'user');
    input.value = '';

    // Show Loading System Message
    const loadingId = addMessage('Thinking...', 'system', true);

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_query: text })
        });

        const result = await response.json();

        // Remove loading message
        document.getElementById(loadingId).remove();

        if (response.ok) {
            // result = { answer: "...", products: [{name, price, availability, image_url}, ...] }
            addMessage(result.answer, 'system', false, result.products);
        } else {
            addMessage('Error: ' + (result.detail || 'Unknown error'), 'system');
        }
    } catch (error) {
        document.getElementById(loadingId).remove();
        addMessage('Failed to communicate with the server.', 'system');
    }
}

function addMessage(text, type, isLoading = false, products = []) {
    const container = document.getElementById('messages-container');
    const id = 'msg-' + Date.now();

    let avatarSymbol = type === 'user' ? '👤' : '⚡';
    let contentHtml = text.replace(/\n/g, '<br>');

    // Add structured product info if available
    if (products && products.length > 0) {
        contentHtml += `<div class="product-results">`;
        products.forEach(p => {
            contentHtml += `
                <div class="product-card">
                    ${p.image_url ? `<img src="${p.image_url}" onerror="this.style.display='none'">` : ''}
                    <div class="product-info">
                        <div class="product-name">${p.name}</div>
                        <div class="product-meta">${p.price} • <span class="product-availability">${p.availability}</span></div>
                    </div>
                </div>
            `;
        });
        contentHtml += `</div>`;
    }

    const html = `
        <div class="message ${type}" id="${id}">
            <div class="avatar">${avatarSymbol}</div>
            <div class="content">
                ${contentHtml}
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', html);
    container.scrollTop = container.scrollHeight;
    return id;
}

function updateStats(msg) {
    const stats = document.getElementById('stats-display');
    stats.textContent = msg;
    stats.style.color = '#22c55e';
    setTimeout(() => {
        stats.style.color = '#94a3b8';
    }, 3000);
}
