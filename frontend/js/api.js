/**
 * FraudLens - Frontend API Client
 * Manages JWT Bearer Token and REST endpoints
 */

const API_BASE = window.location.origin;

class ApiClient {
    constructor() {
        this.tokenKey = "fraudlens_jwt_token";
        this.userKey = "fraudlens_user_info";
    }

    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    setAuth(token, user) {
        localStorage.setItem(this.tokenKey, token);
        localStorage.setItem(this.userKey, JSON.stringify(user));
    }

    clearAuth() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
    }

    getUser() {
        const u = localStorage.getItem(this.userKey);
        return u ? JSON.parse(u) : null;
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = {
            "Content-Type": "application/json",
            ...options.headers,
        };

        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, { ...options, headers });

            if (response.status === 401) {
                this.clearAuth();
                window.dispatchEvent(new CustomEvent("auth:unauthorized"));
                throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Lỗi máy chủ (${response.status})`);
            }

            return await response.json();
        } catch (err) {
            console.error(`API Error on [${options.method || "GET"} ${endpoint}]:`, err);
            throw err;
        }
    }

    // --- Authentication ---
    async login(username, password) {
        const data = await this.request("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ username, password }),
        });
        this.setAuth(data.access_token, {
            user_id: data.user_id,
            username: data.username,
            role: data.role,
        });
        return data;
    }

    async logout() {
        try {
            await this.request("/api/auth/logout", { method: "POST" });
        } finally {
            this.clearAuth();
        }
    }

    async getMe() {
        return this.request("/api/auth/me");
    }

    // --- Cases & Review Queue ---
    async getReviewQueue(params = {}) {
        const q = new URLSearchParams();
        if (params.status_filter) q.append("status_filter", params.status_filter);
        if (params.priority_filter) q.append("priority_filter", params.priority_filter);
        if (params.limit) q.append("limit", params.limit);
        return this.request(`/api/cases/?${q.toString()}`);
    }

    async getCaseDetail(caseId) {
        return this.request(`/api/cases/${caseId}`);
    }

    async updateCaseStatus(caseId, status) {
        return this.request(`/api/cases/${caseId}/status`, {
            method: "PUT",
            body: JSON.stringify({ status }),
        });
    }

    async updateCaseOutcome(caseId, outcome) {
        return this.request(`/api/cases/${caseId}/outcome`, {
            method: "PUT",
            body: JSON.stringify({ outcome }),
        });
    }

    async addCaseNote(caseId, content) {
        return this.request(`/api/cases/${caseId}/notes`, {
            method: "POST",
            body: JSON.stringify({ content }),
        });
    }

    async regenerateBrief(caseId) {
        return this.request(`/api/cases/${caseId}/brief/regenerate`, {
            method: "POST",
        });
    }

    async createManualCase(transactionId, reason, priority = "MEDIUM") {
        return this.request("/api/cases/manual", {
            method: "POST",
            body: JSON.stringify({
                transaction_id: transactionId,
                manual_reason: reason,
                priority,
            }),
        });
    }

    // --- Transactions & Simulation ---
    async getTransactions(params = {}) {
        const q = new URLSearchParams();
        if (params.status) q.append("status", params.status);
        if (params.limit) q.append("limit", params.limit || 50);
        return this.request(`/api/transactions/?${q.toString()}`);
    }

    async simulateBatch(count = 10, injectFault = false) {
        return this.request(`/api/transactions/simulate-batch?count=${count}&inject_fault=${injectFault}`, {
            method: "POST",
        });
    }

    async getSpecialQueue(limit = 50) {
        return this.request(`/api/transactions/special-inspection-queue?limit=${limit}`);
    }

    // --- Audits ---
    async getAuditLogs(params = {}) {
        const q = new URLSearchParams();
        if (params.entity_id) q.append("entity_id", params.entity_id);
        if (params.entity_type) q.append("entity_type", params.entity_type);
        if (params.limit) q.append("limit", params.limit || 50);
        return this.request(`/api/audits/?${q.toString()}`);
    }

    // --- System Reset ---
    async resetDatabase() {
        return this.request("/api/system/reset-db", {
            method: "POST",
        });
    }
}

const api = new ApiClient();
