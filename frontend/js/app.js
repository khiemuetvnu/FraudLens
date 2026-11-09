/**
 * FraudLens - Frontend Application Logic
 * Review Queue, Investigation Workspace, ML Explainability, LLM Brief, RBAC Actions
 */

// Global State
const state = {
    currentUser: null,
    activeTab: "cases",
    currentCase: null,
    queueFilters: {
        status_filter: "",
        priority_filter: "",
    },
};

// --- Toast System ---
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "fa-info-circle";
    if (type === "success") icon = "fa-check-circle";
    if (type === "error") icon = "fa-exclamation-triangle";
    if (type === "warning") icon = "fa-exclamation-circle";

    toast.innerHTML = `
        <i class="fas ${icon} text-lg"></i>
        <div class="flex-1 font-medium">${message}</div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Helpers ---
function formatCurrency(val) {
    if (val === null || val === undefined) return "$0.00";
    return `$${parseFloat(val).toFixed(2)}`;
}

function formatDate(isoStr) {
    if (!isoStr) return "N/A";
    const d = new Date(isoStr);
    return d.toLocaleString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        day: "2-digit",
        month: "2-digit",
        year: "numeric"
    });
}

function renderPriorityBadge(priority) {
    if (priority === "HIGH") {
        return `<span class="badge badge-high"><i class="fas fa-fire"></i> CAO (HIGH)</span>`;
    }
    return `<span class="badge badge-medium"><i class="fas fa-exclamation-circle"></i> VỪA (MEDIUM)</span>`;
}

function renderRoutingBadge(routing) {
    if (routing === "HIGH") return `<span class="badge badge-high">HIGH</span>`;
    if (routing === "MEDIUM") return `<span class="badge badge-medium">MEDIUM</span>`;
    if (routing === "LOW") return `<span class="badge badge-low">LOW</span>`;
    return `<span class="badge badge-unscored">FALLBACK / UNSCORED</span>`;
}

function renderStatusBadge(status) {
    switch (status) {
        case "NEW":
            return `<span class="badge badge-status-new"><i class="fas fa-sparkles"></i> MỚI</span>`;
        case "UNDER_REVIEW":
            return `<span class="badge badge-status-review"><i class="fas fa-user-edit"></i> ĐANG XỬ LÝ</span>`;
        case "NEEDS_MORE_INFO":
            return `<span class="badge badge-status-review"><i class="fas fa-question-circle"></i> CẦN THÊM TT</span>`;
        case "ESCALATED":
            return `<span class="badge badge-status-escalated"><i class="fas fa-arrow-up"></i> CHUYỂN CẤP</span>`;
        case "CLOSED":
            return `<span class="badge badge-status-closed"><i class="fas fa-check-double"></i> ĐÃ ĐÓNG</span>`;
        default:
            return `<span class="badge badge-status-new">${status}</span>`;
    }
}

// --- Authentication UI ---
function updateAuthUI() {
    state.currentUser = api.getUser();
    const userBar = document.getElementById("user-profile-bar");
    const loginModal = document.getElementById("login-modal");

    if (state.currentUser) {
        loginModal.classList.add("hidden");
        userBar.classList.remove("hidden");
        document.getElementById("nav-username").innerText = state.currentUser.username;
        
        const roleBadge = document.getElementById("nav-role-badge");
        roleBadge.innerText = state.currentUser.role.toUpperCase();
        if (state.currentUser.role === "risk_lead") {
            roleBadge.className = "px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30";
        } else if (state.currentUser.role === "admin") {
            roleBadge.className = "px-2 py-0.5 rounded text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30";
        } else {
            roleBadge.className = "px-2 py-0.5 rounded text-xs font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30";
        }

        // Tải dữ liệu ban đầu
        loadActiveTab();
    } else {
        userBar.classList.add("hidden");
        loginModal.classList.remove("hidden");
    }
}

function quickLogin(username, password) {
    document.getElementById("login-username").value = username;
    document.getElementById("login-password").value = password;
    submitLogin();
}

async function submitLogin() {
    const u = document.getElementById("login-username").value.trim();
    const p = document.getElementById("login-password").value;
    const errBox = document.getElementById("login-error");
    errBox.classList.add("hidden");

    if (!u || !p) {
        errBox.innerText = "Vui lòng nhập tên tài khoản và mật khẩu.";
        errBox.classList.remove("hidden");
        return;
    }

    try {
        await api.login(u, p);
        showToast(`Đăng nhập thành công với vai trò ${u}!`, "success");
        updateAuthUI();
    } catch (err) {
        errBox.innerText = err.message || "Đăng nhập thất bại.";
        errBox.classList.remove("hidden");
    }
}

async function handleLogout() {
    try {
        await api.logout();
        showToast("Đã đăng xuất an toàn.", "info");
    } catch (e) {
        api.clearAuth();
    } finally {
        updateAuthUI();
    }
}

// --- Tab Switching ---
function switchTab(tabName) {
    state.activeTab = tabName;
    document.querySelectorAll(".nav-tab").forEach(tab => {
        tab.classList.toggle("active", tab.dataset.tab === tabName);
    });

    document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.toggle("hidden", content.id !== `tab-${tabName}`);
    });

    // Close detail view if switching tabs
    closeCaseDetail();
    loadActiveTab();
}

function loadActiveTab() {
    if (!state.currentUser) return;
    if (state.activeTab === "cases") loadReviewQueue();
    if (state.activeTab === "special") loadSpecialQueue();
    if (state.activeTab === "transactions") loadTransactions();
    if (state.activeTab === "audits") loadAuditLogs();
}

// =========================================================================
// 1. REVIEW QUEUE
// =========================================================================
async function loadReviewQueue() {
    const tbody = document.getElementById("queue-table-body");
    const countBadge = document.getElementById("queue-count-badge");
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i> Đang tải danh sách hồ sơ...</td></tr>`;

    try {
        const cases = await api.getReviewQueue(state.queueFilters);
        countBadge.innerText = `${cases.length} hồ sơ`;

        if (cases.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-12 text-gray-400">
                        <i class="fas fa-inbox text-4xl mb-3 text-gray-600 block"></i>
                        Hàng đợi trống! Bạn có thể chuyển sang tab <b>Giao dịch & Giả lập</b> để nạp giao dịch mới.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = cases.map(c => `
            <tr class="border-b border-gray-800/60 hover:bg-slate-800/40 transition cursor-pointer" onclick="openCaseDetail('${c.case_id}')">
                <td class="py-3 px-4 font-mono text-xs text-blue-400 font-semibold">
                    ${c.case_id.substring(0, 8)}...
                </td>
                <td class="py-3 px-4">
                    <div class="font-medium text-white">${c.merchant || "N/A"}</div>
                    <div class="text-xs text-gray-400 font-mono">${c.transaction_id.substring(0, 16)}...</div>
                </td>
                <td class="py-3 px-4 font-semibold text-emerald-400">
                    ${formatCurrency(c.amt)}
                    <span class="text-xs text-gray-400 block font-normal">${c.category || ""}</span>
                </td>
                <td class="py-3 px-4">
                    ${renderPriorityBadge(c.priority)}
                </td>
                <td class="py-3 px-4">
                    <div class="flex items-center gap-2">
                        <div class="w-12 h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div class="h-full ${parseFloat(c.risk_score || 0) >= 0.7 ? 'bg-red-500' : 'bg-amber-500'}" style="width: ${(parseFloat(c.risk_score || 0) * 100)}%"></div>
                        </div>
                        <span class="text-xs font-mono font-bold">${(parseFloat(c.risk_score || 0) * 100).toFixed(0)}%</span>
                    </div>
                </td>
                <td class="py-3 px-4">
                    ${renderStatusBadge(c.status)}
                    ${c.outcome ? `<span class="badge ml-1 text-xs bg-gray-800 text-gray-300">${c.outcome}</span>` : ""}
                </td>
                <td class="py-3 px-4 text-right">
                    <button class="px-3 py-1 bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white rounded-md text-xs font-medium border border-blue-500/30 transition">
                        Điều tra <i class="fas fa-chevron-right ml-1"></i>
                    </button>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-rose-400">Lỗi nạp hàng đợi: ${err.message}</td></tr>`;
    }
}

// Filter Review Queue
function handleQueueFilterChange() {
    state.queueFilters.status_filter = document.getElementById("filter-status").value;
    state.queueFilters.priority_filter = document.getElementById("filter-priority").value;
    loadReviewQueue();
}

// =========================================================================
// 2. CASE INVESTIGATION WORKSPACE
// =========================================================================
async function openCaseDetail(caseId) {
    const container = document.getElementById("case-detail-modal");
    container.classList.remove("hidden");
    document.getElementById("detail-content").innerHTML = `
        <div class="p-12 text-center text-gray-400">
            <i class="fas fa-circle-notch fa-spin text-4xl mb-3 text-blue-500"></i>
            <div>Đang tải hồ sơ điều tra ${caseId}...</div>
        </div>
    `;

    try {
        const caseData = await api.getCaseDetail(caseId);
        state.currentCase = caseData;
        renderCaseDetailView(caseData);
    } catch (err) {
        showToast("Không thể tải chi tiết case: " + err.message, "error");
        closeCaseDetail();
    }
}

function closeCaseDetail() {
    const container = document.getElementById("case-detail-modal");
    if (container) container.classList.add("hidden");
    state.currentCase = null;
}

function renderCaseDetailView(c) {
    const txn = c.transaction || {};
    const score = c.score || (txn.score || {});
    const brief = c.brief || {};
    const briefContent = brief.content || {};
    const notes = c.notes || [];

    const riskScoreVal = parseFloat(score.risk_score || 0);
    const probVal = parseFloat(score.calibrated_prob || riskScoreVal * 0.96);

    document.getElementById("detail-content").innerHTML = `
        <!-- Header -->
        <div class="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-slate-900/60 sticky top-0 z-10 backdrop-blur">
            <div class="flex items-center gap-3">
                <div class="p-2.5 rounded-lg ${c.priority === 'HIGH' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}">
                    <i class="fas fa-shield-alt text-xl"></i>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h2 class="text-lg font-bold text-white font-mono">Case #${c.case_id.substring(0, 13)}...</h2>
                        ${renderPriorityBadge(c.priority)}
                        ${renderStatusBadge(c.status)}
                    </div>
                    <div class="text-xs text-gray-400">
                        Nguồn: <b>${c.source}</b> ${c.manual_reason ? `(${c.manual_reason})` : ''} • Khởi tạo: ${formatDate(c.created_at)}
                    </div>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <button onclick="closeCaseDetail()" class="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>
        </div>

        <!-- 2 Columns Layout -->
        <div class="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <!-- CỘT TRÁI (Dữ liệu giao dịch, ML Score, LLM Brief) -->
            <div class="lg:col-span-7 space-y-6">
                
                <!-- 1. Giao dịch gốc -->
                <div class="glass-card p-5">
                    <div class="flex items-center justify-between mb-4 border-b border-gray-800/80 pb-3">
                        <div class="flex items-center gap-2 font-semibold text-gray-200">
                            <i class="fas fa-receipt text-blue-400"></i> Dữ liệu Giao dịch Gốc
                        </div>
                        <span class="text-xs font-mono text-gray-500">ID: ${txn.transaction_id || c.transaction_id}</span>
                    </div>

                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                        <div>
                            <span class="text-xs text-gray-500 block">Số tiền giao dịch</span>
                            <span class="text-2xl font-bold text-emerald-400 font-mono">${formatCurrency(txn.amt)}</span>
                        </div>
                        <div>
                            <span class="text-xs text-gray-500 block">Số thẻ (Masked)</span>
                            <span class="text-sm font-semibold text-gray-300 font-mono">**** ${String(txn.cc_num || '').slice(-4)}</span>
                        </div>
                        <div>
                            <span class="text-xs text-gray-500 block">Danh mục</span>
                            <span class="text-sm font-semibold text-gray-300">${txn.category || "N/A"}</span>
                        </div>
                        <div>
                            <span class="text-xs text-gray-500 block">Đơn vị chấp nhận thẻ</span>
                            <span class="text-sm font-semibold text-gray-300">${txn.merchant || "N/A"}</span>
                        </div>
                        <div>
                            <span class="text-xs text-gray-500 block">Thời gian giao dịch</span>
                            <span class="text-xs font-semibold text-gray-300">${formatDate(txn.trans_time)}</span>
                        </div>
                        <div>
                            <span class="text-xs text-gray-500 block">Địa điểm</span>
                            <span class="text-xs font-semibold text-gray-300">${txn.city || ""}, ${txn.state || ""}</span>
                        </div>
                    </div>
                </div>

                <!-- 2. ML Scoring & Explainability (Hot Path) -->
                <div class="glass-card p-5">
                    <div class="flex items-center justify-between mb-4 border-b border-gray-800/80 pb-3">
                        <div class="flex items-center gap-2 font-semibold text-gray-200">
                            <i class="fas fa-brain text-purple-400"></i> Đánh giá Chấm điểm ML (Hot Path)
                        </div>
                        <span class="text-xs font-mono text-gray-500">Model: ${score.model_version || "xgb-v1.0.0"}</span>
                    </div>

                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="bg-slate-900/50 p-3 rounded-lg border border-gray-800">
                            <div class="flex justify-between items-center mb-1">
                                <span class="text-xs text-gray-400">Risk Score</span>
                                <span class="text-base font-bold text-rose-400 font-mono">${(riskScoreVal * 100).toFixed(1)}%</span>
                            </div>
                            <div class="shap-bar-container">
                                <div class="shap-bar-fill bg-rose-500" style="width: ${riskScoreVal * 100}%"></div>
                            </div>
                        </div>
                        <div class="bg-slate-900/50 p-3 rounded-lg border border-gray-800">
                            <div class="flex justify-between items-center mb-1">
                                <span class="text-xs text-gray-400">Xác suất hiệu chỉnh</span>
                                <span class="text-base font-bold text-amber-400 font-mono">${(probVal * 100).toFixed(1)}%</span>
                            </div>
                            <div class="shap-bar-container">
                                <div class="shap-bar-fill bg-amber-500" style="width: ${probVal * 100}%"></div>
                            </div>
                        </div>
                    </div>

                    <!-- SHAP Top Features -->
                    <div>
                        <div class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                            Top Yếu tố Đóng góp Rủi ro (SHAP Explainability)
                        </div>
                        <div class="space-y-2">
                            ${(score.features?.shap_summary || [
                                { feature: "amt_deviation", importance: 0.45, value: txn.amt },
                                { feature: "high_risk_category", importance: 0.35, value: txn.category },
                                { feature: "trans_hour_risk", importance: 0.15, value: "Đêm muộn" }
                            ]).map(item => `
                                <div class="flex items-center text-xs">
                                    <span class="w-40 text-gray-300 font-mono truncate">${item.feature}</span>
                                    <div class="flex-1 mx-3 shap-bar-container">
                                        <div class="shap-bar-fill bg-purple-500" style="width: ${(item.importance * 100)}%"></div>
                                    </div>
                                    <span class="w-12 text-right font-mono text-gray-400">+${(item.importance * 100).toFixed(0)}%</span>
                                </div>
                            `).join("")}
                        </div>
                    </div>
                </div>

                <!-- 3. LLM Case Brief & Checklist (Cold Path) -->
                <div class="glass-card p-5">
                    <div class="flex items-center justify-between mb-4 border-b border-gray-800/80 pb-3">
                        <div class="flex items-center gap-2 font-semibold text-gray-200">
                            <i class="fas fa-robot text-emerald-400"></i> Tóm tắt Điều tra LLM & RAG Playbook
                        </div>
                        <button onclick="handleRegenerateBrief('${c.case_id}')" id="btn-regen-brief" class="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 rounded border border-gray-700 transition flex items-center gap-1.5">
                            <i class="fas fa-sync-alt"></i> Tạo lại Brief
                        </button>
                    </div>

                    <!-- Summary -->
                    <div class="bg-emerald-950/20 border border-emerald-500/20 rounded-lg p-3.5 mb-4 text-sm text-emerald-200/90 leading-relaxed">
                        ${briefContent.summary || "Đang tạo tóm tắt vụ việc..."}
                    </div>

                    <!-- Checklist -->
                    <div class="mb-4">
                        <div class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                            Checklist Xác minh Quy trình (Playbook)
                        </div>
                        <div class="space-y-2">
                            ${(briefContent.investigation_checklist || []).map(item => `
                                <div class="checklist-item flex items-start gap-3">
                                    <input type="checkbox" class="mt-1 accent-emerald-500 cursor-pointer" id="chk-${item.step_id}">
                                    <div class="flex-1">
                                        <div class="text-xs font-bold text-gray-200 flex items-center justify-between">
                                            <span>${item.title}</span>
                                            <span class="font-mono text-blue-400 bg-blue-900/30 px-1.5 py-0.5 rounded text-[10px]">${item.rule_ref}</span>
                                        </div>
                                        <div class="text-xs text-gray-400 mt-0.5">${item.action}</div>
                                    </div>
                                </div>
                            `).join("")}
                        </div>
                    </div>

                    <!-- Citations -->
                    <div>
                        <div class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                            Nguồn Tham chiếu Quy định (Playbook Citations)
                        </div>
                        <div class="flex flex-wrap gap-2">
                            ${(briefContent.playbook_citations || []).map(cit => `
                                <span class="px-2.5 py-1 rounded bg-slate-900 border border-gray-700 text-[11px] text-gray-300 flex items-center gap-1.5">
                                    <i class="fas fa-book-open text-gray-500"></i>
                                    <b>${cit.code}</b>: ${cit.section}
                                </span>
                            `).join("")}
                        </div>
                    </div>
                </div>

            </div>

            <!-- CỘT PHẢI (Hành động Nghiệp vụ, Case Notes, Outcome) -->
            <div class="lg:col-span-5 space-y-6">
                
                <!-- 1. Thao tác Xử lý Trạng thái & Outcome -->
                <div class="glass-card p-5">
                    <h3 class="font-semibold text-gray-200 mb-3 flex items-center gap-2">
                        <i class="fas fa-gavel text-amber-400"></i> Quyết định Xử lý Vụ việc
                    </h3>

                    <!-- Chuyển trạng thái -->
                    <div class="space-y-3 mb-5">
                        <label class="text-xs text-gray-400 block font-medium">Cập nhật Trạng thái</label>
                        <div class="grid grid-cols-2 gap-2">
                            <button onclick="handleUpdateStatus('${c.case_id}', 'UNDER_REVIEW')" class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-gray-700 text-gray-200 transition">
                                <i class="fas fa-play text-blue-400 mr-1"></i> Under Review
                            </button>
                            <button onclick="handleUpdateStatus('${c.case_id}', 'NEEDS_MORE_INFO')" class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded border border-gray-700 text-gray-200 transition">
                                <i class="fas fa-question text-amber-400 mr-1"></i> Thêm thông tin
                            </button>
                        </div>
                        <button onclick="handleUpdateStatus('${c.case_id}', 'ESCALATED')" class="w-full px-3 py-2.5 bg-gradient-to-r from-red-600/30 to-amber-600/30 hover:from-red-600 hover:to-amber-600 text-white text-xs font-bold rounded border border-red-500/40 transition flex items-center justify-center gap-2">
                            <i class="fas fa-level-up-alt text-amber-400"></i> Chuyển cấp cho Risk Lead (Escalate)
                        </button>
                    </div>

                    <!-- Kết luận Outcome & Đóng Case -->
                    <div class="border-t border-gray-800 pt-4">
                        <label class="text-xs text-gray-400 block font-medium mb-1.5">Kết luận Vụ việc (Outcome)</label>
                        <select id="case-outcome-select" class="w-full bg-slate-900 border border-gray-700 rounded-lg p-2.5 text-xs text-white mb-3 focus:outline-none focus:border-blue-500">
                            <option value="CONFIRMED_FRAUD_SIM" ${c.outcome === 'CONFIRMED_FRAUD_SIM' ? 'selected' : ''}>🚨 Gian lận Thật (CONFIRMED_FRAUD_SIM)</option>
                            <option value="DISMISSED" ${c.outcome === 'DISMISSED' ? 'selected' : ''}>✅ Giao dịch Hợp lệ (DISMISSED)</option>
                            <option value="INSUFFICIENT_EVIDENCE" ${c.outcome === 'INSUFFICIENT_EVIDENCE' ? 'selected' : ''}>❓ Chưa đủ chứng cứ (INSUFFICIENT_EVIDENCE)</option>
                        </select>

                        <div class="flex gap-2">
                            <button onclick="handleSaveOutcome('${c.case_id}')" class="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg transition">
                                Lưu Kết Luận
                            </button>
                            <button onclick="handleCloseCase('${c.case_id}')" class="flex-1 px-3 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-lg transition flex items-center justify-center gap-1.5">
                                <i class="fas fa-lock"></i> Đóng Case
                            </button>
                        </div>
                        
                        ${state.currentUser?.role === 'analyst' ? `
                            <div class="mt-2 text-[11px] text-amber-400/90 flex items-center gap-1.5">
                                <i class="fas fa-shield-alt"></i> Phân quyền: Chỉ Risk Lead hoặc Admin mới có thẩm quyền Đóng Case.
                            </div>
                        ` : ''}
                    </div>
                </div>

                <!-- 2. Case Notes (Append-Only) -->
                <div class="glass-card p-5">
                    <h3 class="font-semibold text-gray-200 mb-3 flex items-center gap-2">
                        <i class="fas fa-comments text-blue-400"></i> Ghi nhận Điều tra (Case Notes)
                    </h3>
                    <div class="text-[11px] text-gray-400 mb-3">Nguyên tắc bảo toàn chứng cứ: Ghi chú chỉ được thêm mới (append-only), không sửa/xóa.</div>

                    <!-- Input note form -->
                    <div class="mb-4">
                        <textarea id="new-note-content" rows="3" placeholder="Nhập nhận định điều tra, kết quả phỏng vấn chủ thẻ hoặc thông tin xác minh..." class="w-full bg-slate-900 border border-gray-700 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-blue-500 mb-2"></textarea>
                        <button onclick="handleAddNote('${c.case_id}')" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium transition flex items-center gap-1.5">
                            <i class="fas fa-plus"></i> Thêm Ghi Chú
                        </button>
                    </div>

                    <!-- Timeline Notes -->
                    <div class="space-y-4 max-h-64 overflow-y-auto pr-1">
                        ${notes.length === 0 ? `
                            <div class="text-xs text-gray-500 italic py-2">Chưa có ghi chú nào cho vụ việc này.</div>
                        ` : notes.map(n => `
                            <div class="timeline-item">
                                <div class="timeline-dot"></div>
                                <div class="flex items-center justify-between text-[11px] mb-1">
                                    <span class="font-bold text-gray-300 font-mono">${n.author_username || "Analyst"}</span>
                                    <span class="text-gray-500">${formatDate(n.created_at)}</span>
                                </div>
                                <div class="text-xs text-gray-300 bg-slate-900/60 p-2.5 rounded border border-gray-800/80 leading-relaxed">
                                    ${n.content}
                                </div>
                            </div>
                        `).join("")}
                    </div>
                </div>

            </div>

        </div>
    `;
}

// Action Handlers
async function handleUpdateStatus(caseId, status) {
    try {
        await api.updateCaseStatus(caseId, status);
        showToast(`Đã chuyển trạng thái case sang: ${status}`, "success");
        openCaseDetail(caseId);
        loadReviewQueue();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleSaveOutcome(caseId) {
    const outcome = document.getElementById("case-outcome-select").value;
    try {
        await api.updateCaseOutcome(caseId, outcome);
        showToast(`Đã cập nhật kết luận: ${outcome}`, "success");
        openCaseDetail(caseId);
        loadReviewQueue();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleCloseCase(caseId) {
    if (state.currentUser?.role === 'analyst') {
        showToast("Từ chối: Chuyên viên (Analyst) không có quyền Đóng Case! Cần chuyển cấp (Escalate) cho Risk Lead.", "error");
        return;
    }

    try {
        await api.updateCaseStatus(caseId, "CLOSED");
        showToast("Hồ sơ vụ việc đã được đóng thành công!", "success");
        openCaseDetail(caseId);
        loadReviewQueue();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleAddNote(caseId) {
    const txt = document.getElementById("new-note-content").value.trim();
    if (!txt) {
        showToast("Vui lòng nhập nội dung ghi chú.", "warning");
        return;
    }

    try {
        await api.addCaseNote(caseId, txt);
        showToast("Đã lưu ghi chú chứng cứ mới.", "success");
        openCaseDetail(caseId);
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleRegenerateBrief(caseId) {
    const btn = document.getElementById("btn-regen-brief");
    if (btn) btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Đang tạo lại...`;

    try {
        await api.regenerateBrief(caseId);
        showToast("Tạo lại Brief thành công!", "success");
        openCaseDetail(caseId);
    } catch (err) {
        showToast(err.message, "error");
    }
}

// =========================================================================
// 3. SPECIAL INSPECTION QUEUE (FR-07)
// =========================================================================
async function loadSpecialQueue() {
    const tbody = document.getElementById("special-table-body");
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i> Đang nạp hàng đợi kiểm tra đặc biệt...</td></tr>`;

    try {
        const txns = await api.getSpecialQueue();
        if (txns.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-12 text-gray-400">
                        <i class="fas fa-shield-check text-4xl mb-3 text-emerald-500 block"></i>
                        Không có giao dịch lỗi nào cần cách ly! Mọi giao dịch đầu vào đều đạt chuẩn.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = txns.map(t => {
            const reason = t.score?.features?.error_reason || "Data validation failed";
            return `
                <tr class="border-b border-gray-800/60 hover:bg-slate-800/40 transition">
                    <td class="py-3 px-4 font-mono text-xs text-rose-400 font-semibold">
                        ${t.transaction_id.substring(0, 16)}...
                    </td>
                    <td class="py-3 px-4">
                        <div class="font-medium text-white">${t.merchant}</div>
                        <div class="text-xs text-gray-400 font-mono">Thẻ: ${t.cc_num}</div>
                    </td>
                    <td class="py-3 px-4 font-semibold text-rose-400">
                        ${formatCurrency(t.amt)}
                    </td>
                    <td class="py-3 px-4">
                        <span class="badge badge-unscored">MANUAL_FALLBACK</span>
                    </td>
                    <td class="py-3 px-4 text-xs text-amber-300">
                        <i class="fas fa-exclamation-triangle mr-1"></i> ${reason}
                    </td>
                    <td class="py-3 px-4 text-right">
                        <button onclick="promptManualCase('${t.transaction_id}')" class="px-3 py-1.5 bg-rose-600/30 hover:bg-rose-600 text-rose-300 hover:text-white rounded text-xs font-semibold border border-rose-500/40 transition">
                            <i class="fas fa-folder-plus mr-1"></i> Mở Case Thủ Công
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-rose-400">Lỗi: ${err.message}</td></tr>`;
    }
}

async function promptManualCase(txnId) {
    const reason = prompt("Nhập lý do nghi vấn mở hồ sơ điều tra thủ công cho giao dịch này:", "Phát hiện dấu hiệu tiêm lỗi / thử nghiệm hệ thống bất thường");
    if (!reason) return;

    try {
        const c = await api.createManualCase(txnId, reason, "HIGH");
        showToast(`Đã mở Case thủ công thành công! Case ID: ${c.case_id}`, "success");
        switchTab("cases");
        openCaseDetail(c.case_id);
    } catch (err) {
        showToast(err.message, "error");
    }
}

// =========================================================================
// 4. TRANSACTIONS & SIMULATOR
// =========================================================================
async function loadTransactions() {
    const tbody = document.getElementById("transactions-table-body");
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i> Đang tải danh sách giao dịch...</td></tr>`;

    try {
        const txns = await api.getTransactions({ limit: 50 });
        if (txns.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-12 text-gray-400">Chưa có giao dịch nào trong DB. Bấm nút "Kích hoạt Mô Phỏng" ở trên để nạp dữ liệu!</td></tr>`;
            return;
        }

        tbody.innerHTML = txns.map(t => {
            const score = t.score || {};
            return `
                <tr class="border-b border-gray-800/60 hover:bg-slate-800/40 transition">
                    <td class="py-3 px-4 font-mono text-xs text-blue-400">${t.transaction_id.substring(0, 16)}...</td>
                    <td class="py-3 px-4 font-mono text-xs text-gray-300">**** ${String(t.cc_num || '').slice(-4)}</td>
                    <td class="py-3 px-4 font-medium text-white">${t.merchant}</td>
                    <td class="py-3 px-4 font-mono font-semibold ${parseFloat(t.amt) < 0 ? 'text-red-400' : 'text-emerald-400'}">
                        ${formatCurrency(t.amt)}
                    </td>
                    <td class="py-3 px-4 text-xs text-gray-400">${formatDate(t.trans_time)}</td>
                    <td class="py-3 px-4">${renderRoutingBadge(score.routing)}</td>
                    <td class="py-3 px-4 font-mono text-xs">${score.risk_score ? (parseFloat(score.risk_score) * 100).toFixed(0) + '%' : 'N/A'}</td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-rose-400">Lỗi: ${err.message}</td></tr>`;
    }
}

async function triggerSimulation() {
    const count = parseInt(document.getElementById("sim-count").value || "10", 10);
    const injectFault = document.getElementById("sim-inject-fault").checked;
    const btn = document.getElementById("btn-run-sim");

    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i> Đang phát lại...`;

    try {
        const res = await api.simulateBatch(count, injectFault);
        showToast(`Đã nạp và chấm điểm thành công ${res.length} giao dịch!`, "success");
        loadTransactions();
    } catch (err) {
        showToast("Lỗi mô phỏng: " + err.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fas fa-play mr-1"></i> Bắn Giao dịch Mô phỏng`;
    }
}

// =========================================================================
// 5. AUDIT TRAIL (FR-08)
// =========================================================================
async function loadAuditLogs() {
    const tbody = document.getElementById("audit-table-body");
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i> Đang nạp nhật ký kiểm toán...</td></tr>`;

    try {
        const logs = await api.getAuditLogs({ limit: 50 });
        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-12 text-gray-400">Chưa có bản ghi kiểm toán nào. Mọi thao tác đổi trạng thái trên Case sẽ tự động xuất hiện ở đây.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => {
            const beforeSt = l.before_state?.status || "None";
            const afterSt = l.after_state?.status || "None";
            const outcome = l.after_state?.outcome || l.before_state?.outcome || "";

            return `
                <tr class="border-b border-gray-800/60 hover:bg-slate-800/40 transition">
                    <td class="py-3 px-4 font-mono text-xs text-gray-400">${formatDate(l.occurred_at)}</td>
                    <td class="py-3 px-4 font-bold text-blue-400 font-mono">${l.actor_id}</td>
                    <td class="py-3 px-4 font-mono text-xs text-purple-300">${l.action}</td>
                    <td class="py-3 px-4 font-mono text-xs text-gray-400">${l.entity_type} #${l.entity_id.substring(0, 8)}...</td>
                    <td class="py-3 px-4">
                        <span class="text-xs text-gray-400">${beforeSt}</span>
                        <i class="fas fa-arrow-right mx-1.5 text-xs text-gray-600"></i>
                        <span class="text-xs font-bold text-emerald-400">${afterSt}</span>
                    </td>
                    <td class="py-3 px-4 text-xs font-mono text-amber-300">
                        ${outcome ? `<span class="badge bg-slate-800 border border-amber-500/30 text-amber-300">${outcome}</span>` : ""}
                    </td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-rose-400">Lỗi: ${err.message}</td></tr>`;
    }
}

// =========================================================================
// 6. SYSTEM RESET
// =========================================================================
async function triggerDatabaseReset() {
    if (!confirm("⚠️ BẠN CÓ CHẮC MUỐN XÓA TOÀN BỘ DỮ LIỆU THỬ NGHIỆM?\n\nToàn bộ giao dịch, điểm số, case, brief, note và audit log sẽ được xóa trắng. 4 tài khoản người dùng mặc định sẽ được khởi tạo lại.")) {
        return;
    }

    try {
        await api.resetDatabase();
        showToast("Đã dọn sạch cơ sở dữ liệu về trạng thái ban đầu!", "success");
        loadActiveTab();
    } catch (err) {
        showToast("Lỗi reset DB: " + err.message, "error");
    }
}

// --- Lifecycle Event Listeners ---
window.addEventListener("DOMContentLoaded", () => {
    updateAuthUI();

    // Listen for 401 unauthorized
    window.addEventListener("auth:unauthorized", () => {
        showToast("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "warning");
        updateAuthUI();
    });
});
