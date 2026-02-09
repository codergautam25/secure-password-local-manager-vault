
const API_BASE = "/api";

async function showChangePasswordModal() {
    document.getElementById('change-pw-modal').style.display = 'block';
}

async function closeChangePasswordModal() {
    document.getElementById('change-pw-modal').style.display = 'none';
    document.getElementById('change-pw-form').reset();
}

async function handleChangePassword(e) {
    e.preventDefault();
    const currentPassword = document.getElementById('current-pw').value;
    const newPassword = document.getElementById('new-pw').value;
    const confirmPassword = document.getElementById('confirm-new-pw').value;

    if (newPassword !== confirmPassword) {
        alert("New passwords do not match!");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/change-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        if (res.ok) {
            alert("Master Password Changed Successfully!");
            closeChangePasswordModal();
            // Optional: Logout or just stay logged in (key is updated in backend)
        } else {
            const data = await res.json();
            alert("Error: " + data.detail);
        }
    } catch (err) {
        console.error(err);
        alert("Failed to change password.");
    }
}

async function showImportModal() {
    document.getElementById('import-modal').style.display = 'block';
}

async function closeImportModal() {
    document.getElementById('import-modal').style.display = 'none';
    document.getElementById('import-form').reset();
}

async function handleImport(e) {
    e.preventDefault();
    const fileInput = document.getElementById('import-file');
    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a file.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/import`, {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            alert(data.message);
            closeImportModal();
            loadPasswords(); // Refresh list
        } else {
            const data = await res.json();
            alert("Error: " + data.detail);
        }
    } catch (err) {
        console.error(err);
        alert("Failed to import passwords.");
    }
}


const statusIndicator = document.getElementById("status-indicator");
const authSection = document.getElementById("auth-section");
const dashboardSection = document.getElementById("dashboard-section");
const passwordList = document.getElementById("password-list");
const authForm = document.getElementById('auth-form');
const authTitle = document.getElementById('auth-title');
const authBtn = document.getElementById('auth-btn');
const authMessage = document.getElementById('auth-message');

function escapeHtml(text) {
    if (!text) return text;
    return text.replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Check status on load
checkStatus();

async function checkStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();

        if (data.unlocked) {
            showDashboard();
        } else if (!data.initialized) {
            authTitle.innerText = "Initialize Vault";
            authBtn.innerText = "Create Vault";
            authForm.onsubmit = (e) => handleInit(e);
        } else {
            authTitle.innerText = "Unlock Vault";
            authBtn.innerText = "Unlock";
            authForm.onsubmit = (e) => handleUnlock(e);
        }
    } catch (err) {
        console.error("Error checking status:", err);
    }
}

async function handleInit(e) {
    e.preventDefault();
    const password = document.getElementById('master-password').value;

    const res = await fetch(`${API_BASE}/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
    });

    if (res.ok) {
        showDashboard();
    } else {
        authMessage.innerText = "Setup Failed.";
    }
}

async function handleUnlock(e) {
    e.preventDefault();
    const password = document.getElementById('master-password').value;

    const res = await fetch(`${API_BASE}/unlock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
    });

    if (res.ok) {
        showDashboard();
    } else {
        authMessage.innerText = "Incorrect Password.";
    }
}

async function showDashboard() {
    authSection.style.display = 'none';
    dashboardSection.style.display = 'block';
    statusIndicator.innerText = "Unlocked";
    document.getElementById('lock-btn').style.display = 'block';
    loadPasswords();
}

async function loadPasswords() {
    const res = await fetch(`${API_BASE}/passwords`);
    const passwords = await res.json();

    const list = document.getElementById('password-list');
    list.innerHTML = '';

    passwords.forEach(pw => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td data-label="Service">${escapeHtml(pw.service)}</td>
            <td data-label="Username">${escapeHtml(pw.username)}</td>
            <td data-label="Password">
                <div style="display:flex; gap:5px; align-items:center;">
                    <input type="password" value="${escapeHtml(pw.password)}" readonly id="pw-${pw.id}">
                    <button onclick="toggleVisibility('pw-${pw.id}')">Show</button>
                </div>
            </td>
            <td data-label="Attachments">
                <button onclick="showAttachments(${pw.id}, '${escapeHtml(pw.service)}')" style="font-size:0.9em;">📎 Manage</button>
            </td>
            <td data-label="Actions">
                <button onclick="copyToClipboard('pw-${pw.id}')">Copy</button>
            </td>
        `;
        list.appendChild(row);
    });
}

function toggleVisibility(id) {
    const input = document.getElementById(id);
    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }
}

function copyToClipboard(id) {
    const input = document.getElementById(id);
    const originalType = input.type;
    input.type = 'text';
    input.select();
    document.execCommand('copy');
    input.type = originalType;
    alert("Copied!");
}

async function lockVault() {
    await fetch(`${API_BASE}/lock`, { method: 'POST' });
    location.reload();
}

/* Modal Logic */
function showAddModal() {
    document.getElementById('add-modal').style.display = 'block';
}

function closeAddModal() {
    document.getElementById('add-modal').style.display = 'none';
}

function generateRandomPassword() {
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()";
    let password = "";
    for (let i = 0; i < 16; i++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    document.getElementById('new-password').value = password;
}

document.getElementById('add-form').onsubmit = async (e) => {
    e.preventDefault();
    const service = document.getElementById('new-service').value;
    const username = document.getElementById('new-username').value;
    const password = document.getElementById('new-password').value;

    await fetch(`${API_BASE}/passwords`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service, username, password })
    });

    closeAddModal();
    loadPasswords();
};

// --- Attachments ---

async function showAttachments(entryId, serviceName) {
    document.getElementById('attachments-modal').style.display = 'block';
    document.getElementById('attach-title').innerText = `Attachments: ${serviceName}`;
    document.getElementById('attach-entry-id').value = entryId;
    loadAttachments(entryId);
}

async function closeAttachmentsModal() {
    document.getElementById('attachments-modal').style.display = 'none';
    document.getElementById('upload-attachment-form').reset();
}

async function loadAttachments(entryId) {
    const listDiv = document.getElementById('attachment-list');
    listDiv.innerHTML = '<p style="color:#ccc">Loading...</p>';

    try {
        const res = await fetch(`${API_BASE}/passwords/${entryId}/attachments`);
        if (res.ok) {
            const files = await res.json();
            if (files.length === 0) {
                listDiv.innerHTML = '<p style="color:#ccc">No attachments.</p>';
                return;
            }

            let html = '<ul style="list-style:none; padding:0;">';
            files.forEach(f => {
                html += `
                <li style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.05); padding:8px; margin-bottom:5px; border-radius:4px;">
                    <span>📄 ${f.filename}</span>
                    <div>
                        <button onclick="downloadAttachment(${f.id})" style="font-size:0.8em; padding:4px 8px; margin-right:5px;">⬇</button>
                        <button onclick="deleteAttachment(${f.id}, ${entryId})" style="font-size:0.8em; padding:4px 8px; background:#e74c3c;">✖</button>
                    </div>
                </li>`;
            });
            html += '</ul>';
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<p style="color:red">Failed to load.</p>';
        }
    } catch (e) {
        console.error(e);
        listDiv.innerHTML = '<p style="color:red">Error loading attachments.</p>';
    }
}

async function handleUploadAttachment(e) {
    e.preventDefault();
    const entryId = document.getElementById('attach-entry-id').value;
    const fileInput = document.getElementById('attachment-file');
    const file = fileInput.files[0];

    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/passwords/${entryId}/attachments`, {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            fileInput.value = ''; // clear input
            loadAttachments(entryId); // refresh list
        } else {
            alert("Upload failed");
        }
    } catch (e) {
        console.error(e);
        alert("Error uploading file");
    }
}

async function downloadAttachment(attachmentId) {
    window.open(`${API_BASE}/attachments/${attachmentId}`, '_blank');
}

async function deleteAttachment(attachmentId, entryId) {
    if (!confirm("Are you sure you want to delete this file?")) return;

    try {
        const res = await fetch(`${API_BASE}/attachments/${attachmentId}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            loadAttachments(entryId);
        } else {
            alert("Delete failed");
        }
    } catch (e) {
        console.error(e);
    }
}

document.getElementById('change-pw-form').onsubmit = handleChangePassword;
document.getElementById('import-form').onsubmit = handleImport;
document.getElementById('upload-attachment-form').onsubmit = handleUploadAttachment;
