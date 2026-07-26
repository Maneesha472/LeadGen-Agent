// Global state variables
let currentExecutionId = null;
let logEventSource = null;
let dashboardCharts = {};

// API URLs
const API_BASE = "/api";

// DOM Elements
const navItems = document.querySelectorAll(".nav-item");
const tabPanels = document.querySelectorAll(".tab-panel");
const headerTitle = document.getElementById("header-title");
const headerSubtitle = document.getElementById("header-subtitle");
const simulationBadge = document.getElementById("simulation-badge");

// Dashboard Elements
const statFound = document.getElementById("stat-found");
const statValidated = document.getElementById("stat-validated");
const statSent = document.getElementById("stat-sent");
const statReplies = document.getElementById("stat-replies");
const executionsTableBody = document.querySelector("#executions-table tbody");

// Agent Runner Elements
const agentForm = document.getElementById("agent-form");
const terminalLogs = document.getElementById("terminal-logs");
const clearConsoleBtn = document.getElementById("clear-console-btn");
const runProgressBar = document.getElementById("run-progress-bar");
const runProgressText = document.getElementById("run-progress-text");
const submitRunBtn = document.getElementById("submit-run-btn");
const logFoundCount = document.getElementById("log-found-count");
const logValidCount = document.getElementById("log-valid-count");
const logSentCount = document.getElementById("log-sent-count");

// Leads Manager Elements
const leadsTableBody = document.querySelector("#leads-table tbody");
const leadSearch = document.getElementById("lead-search");
const filterStatus = document.getElementById("filter-status");
const refreshLeadsBtn = document.getElementById("refresh-leads-btn");
const exportLeadsBtn = document.getElementById("export-leads-btn");

// Modal Elements
const leadModal = document.getElementById("lead-modal");
const closeModalBtn = document.getElementById("close-modal-btn");
const modalLeadName = document.getElementById("modal-lead-name");
const modalLeadRole = document.getElementById("modal-lead-role");
const modalLeadEmail = document.getElementById("modal-lead-email");
const modalLeadPhone = document.getElementById("modal-lead-phone");
const modalLeadLinkedin = document.getElementById("modal-lead-linkedin");
const modalCompName = document.getElementById("modal-comp-name");
const modalCompWeb = document.getElementById("modal-comp-web");
const modalCompIndustry = document.getElementById("modal-comp-industry");
const modalCompPhone = document.getElementById("modal-comp-phone");
const modalCompLinkedin = document.getElementById("modal-comp-linkedin");
const modalCompAddress = document.getElementById("modal-comp-address");
const modalOutreachSection = document.getElementById("modal-outreach-section");
const modalOutreachSubject = document.getElementById("modal-outreach-subject");
const modalOutreachDate = document.getElementById("modal-outreach-date");
const modalOutreachBody = document.getElementById("modal-outreach-body");
const modalOutreachStatus = document.getElementById("modal-outreach-status");
const modalOutreachResponse = document.getElementById("modal-outreach-response");
const modalOutreachResponseContainer = document.getElementById("modal-outreach-response-container");

// Settings Elements
const settingsEngineForm = document.getElementById("settings-engine-form");
const settingsSmtpForm = document.getElementById("settings-smtp-form");
const settingSimulationMode = document.getElementById("setting-simulation-mode");
const settingDelay = document.getElementById("setting-delay");
const settingMaxResults = document.getElementById("setting-max-results");
const settingSmtpHost = document.getElementById("setting-smtp-host");
const settingSmtpPort = document.getElementById("setting-smtp-port");
const settingSmtpUser = document.getElementById("setting-smtp-user");
const settingSmtpPass = document.getElementById("setting-smtp-pass");
const settingSmtpTls = document.getElementById("setting-smtp-tls");
const settingsLlmForm = document.getElementById("settings-llm-form");
const settingGroqKey = document.getElementById("setting-groq-key");

// Notification Area
const toastContainer = document.getElementById("toast-container");

// App Init
function startApp() {

    initTabs();
    initLeadsManager();
    initAgentRunner();
    initCampaignsManager();
    initAuth();
    checkSession();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startApp);
} else {
    startApp();
}

// Authentication and session wrapper
async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem("token");
    const headers = {
        ...options.headers,
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        localStorage.removeItem("token");
        showAuthScreen();
    }
    
    return response;
}

function checkSession() {
    const token = localStorage.getItem("token");
    if (token) {
        hideAuthScreen();
        initSettings();
        refreshDashboardData();
        fetchAndRenderLeads();
    } else {
        showAuthScreen();
    }
}

function showAuthScreen() {
    document.getElementById("auth-container").classList.remove("hidden");
    document.querySelector(".app-container").classList.add("hidden");
}

function hideAuthScreen() {
    document.getElementById("auth-container").classList.add("hidden");
    document.querySelector(".app-container").classList.remove("hidden");
}

function initAuth() {
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const goToSignup = document.getElementById("go-to-signup");
    const goToLogin = document.getElementById("go-to-login");
    const logoutBtn = document.getElementById("logout-btn");

    goToSignup.addEventListener("click", (e) => {
        e.preventDefault();
        loginForm.classList.add("hidden");
        signupForm.classList.remove("hidden");
    });

    goToLogin.addEventListener("click", (e) => {
        e.preventDefault();
        signupForm.classList.add("hidden");
        loginForm.classList.remove("hidden");
    });

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const submitBtn = loginForm.querySelector("button[type='submit']");
        const originalText = submitBtn.innerHTML;
        const email = document.getElementById("login-email").value.trim();
        const password = document.getElementById("login-password").value;

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Signing In...';

        try {
            const res = await fetchWithAuth(`${API_BASE}/auth/login-json`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            if (res.ok) {
                const data = await res.json();
                localStorage.setItem("token", data.access_token);
                hideAuthScreen();
                showToast("Welcome back!", "success");
                
                initSettings();
                refreshDashboardData();
                fetchAndRenderLeads();
            } else {
                const data = await res.json();
                showToast(data.detail || "Authentication failed. Check your credentials.", "error");
            }
        } catch (err) {

            showToast("Network error trying to sign in.", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });

    signupForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const submitBtn = signupForm.querySelector("button[type='submit']");
        const originalText = submitBtn.innerHTML;
        const email = document.getElementById("signup-email").value.trim();
        const password = document.getElementById("signup-password").value;
        const confirmPassword = document.getElementById("signup-confirm-password").value;




        if (password !== confirmPassword) {
            showToast("Passwords do not match.", "error");
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating Account...';


        try {
            const res = await fetchWithAuth(`${API_BASE}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            if (res.ok) {
                const successModal = document.getElementById("success-modal");
                const successModalBtn = document.getElementById("success-modal-btn");
                
                successModal.classList.add("active");
                
                const proceedToLogin = () => {
                    successModal.classList.remove("active");
                    signupForm.classList.add("hidden");
                    loginForm.classList.remove("hidden");
                    document.getElementById("login-email").value = email;
                    successModalBtn.removeEventListener("click", proceedToLogin);
                };
                
                successModalBtn.addEventListener("click", proceedToLogin);
            } else {
                const data = await res.json();
                showToast(data.detail || "Failed to create account.", "error");
                if (data.detail === "Email address already registered.") {
                    showToast("Redirecting you to Sign In...", "info");
                    setTimeout(() => {
                        signupForm.classList.add("hidden");
                        loginForm.classList.remove("hidden");
                        document.getElementById("login-email").value = email;
                        document.getElementById("login-password").focus();
                    }, 1200);
                }
            }
        } catch (err) {

            showToast("Network error trying to register.", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });

    logoutBtn.addEventListener("click", () => {
        localStorage.removeItem("token");
        showAuthScreen();
        showToast("Logged out successfully.", "info");
    });

    // Toggle password visibility
    document.querySelectorAll(".toggle-password-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (input.type === "password") {
                input.type = "text";
                btn.classList.remove("fa-eye");
                btn.classList.add("fa-eye-slash");
            } else {
                input.type = "password";
                btn.classList.remove("fa-eye-slash");
                btn.classList.add("fa-eye");
            }
        });
    });
}

// Toast Notifications Helper
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let iconClass = "fa-info-circle";
    if (type === "success") iconClass = "fa-check-circle";
    if (type === "error") iconClass = "fa-triangle-exclamation";
    
    toast.innerHTML = `
        <i class="fa-solid ${iconClass} toast-icon ${type}"></i>
        <div class="toast-message">${message}</div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto dismiss
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(30px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// 1. TABS MANAGEMENT
function initTabs() {
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const targetTab = item.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });

}

function switchTab(tabId) {
    // Update active tab menu
    navItems.forEach(n => {
        if (n.getAttribute("data-tab") === tabId) {
            n.classList.add("active");
        } else {
            n.classList.remove("active");
        }
    });

    // Update active tab panel
    tabPanels.forEach(panel => {
        if (panel.id === tabId) {
            panel.classList.add("active");
        } else {
            panel.classList.remove("active");
        }
    });

    // Update Header Text dynamically
    const headerTitles = {
        "dashboard": { title: "Executive Dashboard", subtitle: "Real-time business discovery and automated outreach telemetry." },
        "run-agent": { title: "Agent Controller", subtitle: "Instruct the scraping agent to search and dispatch communication." },
        "leads": { title: "Leads Database Directory", subtitle: "Manage, export, and examine validated business targets." },
        "campaigns": { title: "Campaign Outreach Manager", subtitle: "Launch email outreach campaigns independently to your scraped leads." },
        "settings": { title: "Engine Configurations", subtitle: "Update scraping modes and configure SMTP email setups." }
    };

    if (headerTitles[tabId]) {
        headerTitle.textContent = headerTitles[tabId].title;
        headerSubtitle.textContent = headerTitles[tabId].subtitle;
    }

    // Tab specific load actions
    if (tabId === "dashboard") {
        refreshDashboardData();
    } else if (tabId === "leads") {
        fetchAndRenderLeads();
    } else if (tabId === "campaigns") {
        fetchCampaignsHistory();
        populateCampaignSourceDropdown();
    }
}

// 2. SETTINGS
async function initSettings() {
    try {
        const response = await fetchWithAuth(`${API_BASE}/settings`);
        if (response.ok) {
            const config = await response.json();
            populateSettingsUI(config);
        }
    } catch (error) {
        showToast("Error loading system settings", "error");
    }

    // Engine settings form submission
    settingsEngineForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        saveSystemConfig();
    });

    // SMTP settings form submission
    settingsSmtpForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        saveSystemConfig();
    });

    // LLM settings form submission
    if (settingsLlmForm) {
        settingsLlmForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            saveSystemConfig();
        });
    }
}

function populateSettingsUI(config) {
    if (settingSimulationMode) {
        if (settingSimulationMode.type === "checkbox") {
            settingSimulationMode.checked = config.simulation_mode;
        } else {
            settingSimulationMode.value = config.simulation_mode;
        }
    }
    settingDelay.value = config.scraping_delay;
    settingMaxResults.value = config.max_search_results;
    
    settingSmtpHost.value = config.smtp_host || "";
    settingSmtpPort.value = config.smtp_port || 587;
    settingSmtpUser.value = config.smtp_username || "";
    settingSmtpPass.value = config.smtp_password || "";
    settingSmtpTls.checked = config.smtp_use_tls !== false;
    
    if (settingGroqKey) settingGroqKey.value = config.groq_api_key || "";

    updateSimulationBadge(config.simulation_mode);
}

function updateSimulationBadge(isSimulated) {
    if (!simulationBadge) return;
    if (isSimulated) {
        simulationBadge.className = "badge badge-purple";
        simulationBadge.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Simulation Mode Active';
    } else {
        simulationBadge.className = "badge badge-sent";
        simulationBadge.innerHTML = '<i class="fa-solid fa-globe"></i> Live Scraping Mode Active';
    }
}

async function saveSystemConfig() {
    const config = {
        smtp_host: settingSmtpHost.value.trim(),
        smtp_port: parseInt(settingSmtpPort.value) || 587,
        smtp_username: settingSmtpUser.value.trim(),
        smtp_password: settingSmtpPass.value.trim(),
        smtp_use_tls: settingSmtpTls.checked,
        simulation_mode: false,
        scraping_delay: parseFloat(settingDelay.value) || 2.0,
        max_search_results: parseInt(settingMaxResults.value) || 10,
        groq_api_key: settingGroqKey ? settingGroqKey.value.trim() : "",
    };

    try {
        const response = await fetchWithAuth(`${API_BASE}/settings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showToast("System configurations saved successfully", "success");
            updateSimulationBadge(config.simulation_mode);
        } else {
            const data = await response.json();
            showToast(data.detail || "Error saving configurations", "error");
        }
    } catch (error) {
        showToast("Network error saving configurations", "error");
    }
}

// 3. DASHBOARD TAB
async function refreshDashboardData() {
    try {
        const reportsRes = await fetchWithAuth(`${API_BASE}/reports`);
        const executionsRes = await fetchWithAuth(`${API_BASE}/executions`);
        
        if (reportsRes.ok && executionsRes.ok) {
            const reports = await reportsRes.json();
            const executions = await executionsRes.json();
            
            // Populate stats counters
            statFound.textContent = reports.summary.total_found;
            statValidated.textContent = reports.summary.valid_leads;
            statSent.textContent = reports.summary.emails_sent;
            statReplies.textContent = reports.summary.replies;
            
            // Render charts
            renderFunnelChart(reports.funnel);
            renderCategoriesChart(reports.categories);
            
            // Render execution table
            renderExecutionsTable(executions);
        }
    } catch (error) {
        showToast("Error updating dashboard statistics", "error");
    }
}

function renderFunnelChart(funnelData) {
    const ctx = document.getElementById('funnelChart').getContext('2d');
    
    if (dashboardCharts.funnel) {
        dashboardCharts.funnel.destroy();
    }
    
    dashboardCharts.funnel = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Discovered Companies', 'Validated Leads', 'Emails Sent', 'Replies Logged'],
            datasets: [{
                data: [funnelData.discovered, funnelData.validated, funnelData.contacted, funnelData.replied],
                backgroundColor: [
                    'rgba(139, 92, 246, 0.45)', // Purple
                    'rgba(59, 130, 246, 0.45)',  // Blue
                    'rgba(6, 182, 212, 0.45)',   // Cyan
                    'rgba(16, 185, 129, 0.45)'   // Green
                ],
                borderColor: [
                    '#8b5cf6', '#3b82f6', '#06b6d4', '#10b981'
                ],
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    titleFont: { family: 'Outfit' },
                    bodyFont: { family: 'Inter' }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
                }
            }
        }
    });
}

function renderCategoriesChart(categories) {
    const ctx = document.getElementById('categoriesChart').getContext('2d');
    
    if (dashboardCharts.categories) {
        dashboardCharts.categories.destroy();
    }
    
    const labels = Object.keys(categories);
    const data = Object.values(categories);
    
    if (labels.length === 0) {
        // Fallback display
        labels.push("No data");
        data.push(1);
    }
    
    dashboardCharts.categories = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(139, 92, 246, 0.55)',
                    'rgba(6, 182, 212, 0.55)',
                    'rgba(16, 185, 129, 0.55)',
                    'rgba(245, 158, 11, 0.55)',
                    'rgba(239, 68, 68, 0.55)'
                ],
                borderColor: 'rgba(13, 18, 30, 0.8)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Inter', size: 11 },
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }
            }
        }
    });
}

function renderExecutionsTable(executions) {
    executionsTableBody.innerHTML = "";
    
    if (executions.length === 0) {
        executionsTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">No runs have been performed. Click "Run Agent" to start.</td>
            </tr>
        `;
        return;
    }
    
    executions.slice(0, 10).forEach(exec => {
        const tr = document.createElement("tr");
        
        let statusBadgeClass = "badge-new";
        if (exec.status === "Completed") statusBadgeClass = "badge-replied";
        if (exec.status === "Failed") statusBadgeClass = "badge-failed";
        
        const startTime = new Date(exec.created_at).toLocaleString();
        
        tr.innerHTML = `
            <td>#${exec.id}</td>
            <td class="bold-txt">${escapeHtml(exec.category)}</td>
            <td>${escapeHtml(exec.location)}</td>
            <td>${startTime}</td>
            <td>${exec.total_found}</td>
            <td>${exec.valid_leads}</td>
            <td>${exec.sent_count}</td>
            <td><span class="badge ${statusBadgeClass}">${exec.status}</span></td>
        `;
        executionsTableBody.appendChild(tr);
    });
}

// 4. RUN AGENT / TELEMETRY
function initAgentRunner() {
    const targetMode = document.getElementById("target-mode");
    const bulkInputsRow = document.getElementById("bulk-inputs-row");
    const singleInputRow = document.getElementById("single-input-row");
    const keywordsGroup = document.getElementById("keywords-group");

    const csvUploadRow = document.getElementById("csv-upload-row");

    targetMode.addEventListener("change", () => {
        const mode = targetMode.value;
        bulkInputsRow.classList.toggle("hidden", mode !== "bulk");
        keywordsGroup.classList.toggle("hidden", mode !== "bulk");
        singleInputRow.classList.toggle("hidden", mode !== "single");
        csvUploadRow.classList.toggle("hidden", mode !== "csv");

        document.getElementById("category").required = (mode === "bulk");
        document.getElementById("location").required = (mode === "bulk");
        document.getElementById("target-url").required = (mode === "single");
    });

    agentForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const mode = targetMode.value;

        // ── CSV Bulk Mode ──────────────────────────────────────────────────────
        if (mode === "csv") {
            const fileInput = document.getElementById("csv-file-input");
            if (!fileInput.files || !fileInput.files[0]) {
                showToast("Please select a CSV file first.", "error");
                return;
            }
            const text = await fileInput.files[0].text();
            const companies = parseCSVText(text);
            if (companies.length === 0) {
                showToast("No valid companies found in CSV. Check the file format.", "error");
                return;
            }

            submitRunBtn.disabled = true;
            submitRunBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Starting ${companies.length} Jobs...`;
            terminalLogs.innerHTML = `<div class="terminal-line">&gt; CSV Bulk Mode — dispatching ${companies.length} company jobs...</div>`;

            try {
                const res = await fetchWithAuth(`${API_BASE}/leads/bulk-csv`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ companies })
                });

                if (res.ok) {
                    const data = await res.json();
                    showToast(`✅ ${data.total} company scrape jobs started!`, "success");
                    appendLogLine(`[CSV BATCH] ${data.message}`);
                    appendLogLine(`[CSV BATCH] Execution IDs: ${data.execution_ids.join(", ")}`);
                    appendLogLine(`[CSV BATCH] Check Dashboard → Execution History to track progress.`);
                    // Start streaming the last execution
                    if (data.execution_ids.length > 0) {
                        currentExecutionId = data.execution_ids[data.execution_ids.length - 1];
                        startStreamingLogs(currentExecutionId);
                    }
                } else {
                    const data = await res.json();
                    showToast(data.detail || "Bulk CSV start failed.", "error");
                }
            } catch (err) {
                showToast("Network error during CSV bulk launch.", "error");
            } finally {
                submitRunBtn.disabled = false;
                submitRunBtn.innerHTML = '<i class="fa-solid fa-play"></i> Launch Scraper Run';
            }
            return;
        }

        // ── Single / Bulk Mode ────────────────────────────────────────────────
        let categoryVal, locationVal, keywordsVal;
        if (mode === "single") {
            const rawUrl = document.getElementById("target-url").value.trim();
            const singleLoc = (document.getElementById("single-location")?.value || "").trim();
            const singleCat = (document.getElementById("single-category")?.value || "").trim();
            
            if (!rawUrl) {
                showToast("Please enter a Target Website URL or Company Name", "error");
                return;
            }

            categoryVal = singleCat || "Direct Enrichment";
            locationVal = rawUrl;
            
            const extraKw = document.getElementById("keywords")?.value.trim() || "";
            let combinedKw = [];
            if (singleLoc) combinedKw.push(`Location: ${singleLoc}`);
            if (extraKw) combinedKw.push(extraKw);
            keywordsVal = combinedKw.join(" | ");
        } else {
            categoryVal = document.getElementById("category").value.trim();
            locationVal = document.getElementById("location").value.trim();
            keywordsVal = document.getElementById("keywords").value.trim();
            
            if (!categoryVal || !locationVal) {
                showToast("Please provide both Business Category and Location", "error");
                return;
            }
        }

        const req = {
            category: categoryVal,
            location: locationVal,
            keywords: keywordsVal,
            email_subject: document.getElementById("email-subject").value.trim(),
            email_body: document.getElementById("email-body").value.trim()
        };
        
        // Lock button
        submitRunBtn.disabled = true;
        submitRunBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Initializing Agent...';
        
        // Reset terminal & progress
        terminalLogs.innerHTML = '<div class="terminal-line">&gt; Initiating pipeline thread, contacting agent API...</div>';
        runProgressBar.style.width = '0%';
        runProgressText.textContent = '0%';
        
        logFoundCount.textContent = "0";
        logValidCount.textContent = "0";
        logSentCount.textContent = "0";
        
        // Update sidebar indicator
        document.querySelector(".status-indicator").innerHTML = `
            <span class="pulse-dot orange"></span>
            <span class="status-label">Agent Engine Active</span>
        `;
        
        try {
            const response = await fetchWithAuth(`${API_BASE}/leads/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req)
            });
            
            if (response.ok) {
                const data = await response.json();
                currentExecutionId = data.execution_id;
                showToast(`Agent Run #${currentExecutionId} started successfully`, "success");
                
                // Begin logs streaming
                startStreamingLogs(currentExecutionId);
            } else {
                const data = await response.json();
                showToast(data.detail || "Failed to start agent execution", "error");
                resetRunUIState();
            }
        } catch (error) {
            showToast("Network error starting Agent execution", "error");
            resetRunUIState();
        }
    });

    clearConsoleBtn.addEventListener("click", () => {
        terminalLogs.innerHTML = '<div class="terminal-line placeholder-line">&gt; Ready for instructions.</div>';
    });

}

// ── CSV Helper Functions ───────────────────────────────────────────────────────

function parseCSVText(text) {
    const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
    if (lines.length < 2) return [];
    const headers = lines[0].split(",").map(h => h.trim().toLowerCase());
    const nameIdx = headers.findIndex(h => h.includes("company") || h.includes("name"));
    const webIdx = headers.findIndex(h => h.includes("website") || h.includes("url") || h.includes("domain"));
    const catIdx = headers.findIndex(h => h.includes("category") || h.includes("industry"));
    const locIdx = headers.findIndex(h => h.includes("location") || h.includes("city") || h.includes("region"));
    const kwIdx = headers.findIndex(h => h.includes("keyword"));

    if (nameIdx === -1) return [];

    return lines.slice(1).map(line => {
        const cols = line.split(",").map(c => c.trim().replace(/^"|"$/g, ""));
        return {
            name: cols[nameIdx] || "",
            website: webIdx >= 0 ? (cols[webIdx] || "") : "",
            category: catIdx >= 0 ? (cols[catIdx] || "General") : "General",
            location: locIdx >= 0 ? (cols[locIdx] || "United States") : "United States",
            keywords: kwIdx >= 0 ? (cols[kwIdx] || "") : ""
        };
    }).filter(c => c.name.length > 1);
}

function handleCsvFileSelect(input) {
    const file = input.files[0];
    if (!file) return;
    document.getElementById("csv-file-name").textContent = `📄 ${file.name} selected`;
    const reader = new FileReader();
    reader.onload = (e) => {
        const companies = parseCSVText(e.target.result);
        const preview = document.getElementById("csv-preview");
        if (companies.length > 0) {
            preview.style.display = "block";
            preview.innerHTML = companies.slice(0, 5).map((c, i) =>
                `${i+1}. ${c.name} ${c.website ? '→ ' + c.website : ''} ${c.category ? '['+c.category+']' : ''}`
            ).join("<br>") + (companies.length > 5 ? `<br><em>...and ${companies.length - 5} more</em>` : "");
            document.getElementById("csv-dropzone").style.borderColor = "rgba(16,185,129,0.5)";
            showToast(`✅ ${companies.length} companies loaded from CSV`, "success");
        } else {
            preview.style.display = "block";
            preview.innerHTML = "⚠️ No valid rows found. Check that first column is 'Company Name'.";
            showToast("CSV parse error — no valid companies found.", "error");
        }
    };
    reader.readAsText(file);
}

function handleCsvDrop(e) {
    e.preventDefault();
    document.getElementById("csv-dropzone").style.borderColor = "rgba(139,92,246,0.4)";
    const file = e.dataTransfer.files[0];
    if (!file || !file.name.endsWith(".csv")) {
        showToast("Please drop a .csv file.", "error");
        return;
    }
    const input = document.getElementById("csv-file-input");
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    handleCsvFileSelect(input);
}

async function exportLeadsCSV() {
    const token = localStorage.getItem("token");
    if (!token) { showToast("Please log in first.", "error"); return; }
    try {
        const res = await fetchWithAuth(`${API_BASE}/leads/download-csv`);
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "leads_export.csv";
            a.click();
            URL.revokeObjectURL(url);
            showToast("Leads exported to CSV successfully!", "success");
        } else {
            showToast("Export failed.", "error");
        }
    } catch (err) {
        showToast("Network error during export.", "error");
    }
}

function startStreamingLogs(executionId) {
    if (logEventSource) {
        logEventSource.close();
    }
    
    logEventSource = new EventSource(`${API_BASE}/stream-logs/${executionId}?token=${encodeURIComponent(localStorage.getItem("token") || "")}`);
    
    logEventSource.onmessage = (event) => {
        const line = event.data;
        appendLogLine(line);
    };
    
    logEventSource.onerror = (err) => {
        if (logEventSource && logEventSource.readyState === EventSource.CLOSED) {
            return;
        }
        if (logEventSource) {
            logEventSource.close();
        }
        checkExecutionFinalStatus(executionId);
    };

    // Set polling task to query metrics status update periodically
    const metricsPoller = setInterval(async () => {
        if (!logEventSource || logEventSource.readyState === EventSource.CLOSED) {
            clearInterval(metricsPoller);
            return;
        }
        
        try {
            const res = await fetchWithAuth(`${API_BASE}/leads/status/${executionId}`);
            if (res.ok) {
                const status = await res.json();
                
                logFoundCount.textContent = status.total_found;
                logValidCount.textContent = status.valid_leads;
                logSentCount.textContent = status.sent_count;
                
                // Calculate progress indicator
                // Let's assume MaxSearchSettings * 2 steps (search + email) is completion
                const maxSetting = parseInt(settingMaxResults.value) || 10;
                const totalTargetSteps = status.sent_count > 0 ? maxSetting * 2 : maxSetting;
                
                let progressPercent = 0;
                if (status.status === "Completed") {
                    progressPercent = 100;
                } else if (status.status === "Failed") {
                    progressPercent = 100;
                } else {
                    const currentStep = status.total_found + status.sent_count;
                    progressPercent = Math.min(Math.round((currentStep / totalTargetSteps) * 90), 95);
                }
                
                runProgressBar.style.width = `${progressPercent}%`;
                runProgressText.textContent = `${progressPercent}%`;
                
                if (status.status !== "Running") {
                    clearInterval(metricsPoller);
                    logEventSource.close();
                    finalizeAgentRun(status);
                }
            }
        } catch (e) {
            console.error("Error polling metrics", e);
        }
    }, 1500);
}

function appendLogLine(message) {
    // Remove placeholder line if exists
    const placeholder = terminalLogs.querySelector(".placeholder-line");
    if (placeholder) placeholder.remove();
    
    const div = document.createElement("div");
    div.className = "terminal-line";
    
    let text = message;
    // Format colors based on log prefixes
    if (message.includes("[SUCCESS]")) {
        div.classList.add("log-success");
    } else if (message.includes("[WARNING]")) {
        div.classList.add("log-warning");
    } else if (message.includes("[ERROR]")) {
        div.classList.add("log-error");
    } else if (message.includes("[OUTREACH]")) {
        div.classList.add("log-outreach");
    } else if (message.includes("[SIMULATION]") || message.includes("[LIVE SCRAPING]")) {
        div.classList.add("log-info");
    }
    
    div.textContent = text;
    terminalLogs.appendChild(div);
    
    // Auto scroll terminal
    terminalLogs.scrollTop = terminalLogs.scrollHeight;
}

async function checkExecutionFinalStatus(executionId) {
    try {
        const res = await fetchWithAuth(`${API_BASE}/leads/status/${executionId}`);
        if (res.ok) {
            const status = await res.json();
            finalizeAgentRun(status);
        }
    } catch (e) {
        resetRunUIState();
    }
}

function finalizeAgentRun(execution) {
    runProgressBar.style.width = '100%';
    runProgressText.textContent = '100%';
    
    logFoundCount.textContent = execution.total_found;
    logValidCount.textContent = execution.valid_leads;
    logSentCount.textContent = execution.sent_count;
    
    if (execution.status === "Completed") {
        showToast(`Run #${execution.id} completed successfully! Found ${execution.valid_leads} leads.`, "success");
        appendLogLine(`[SYSTEM] Pipeline complete. Generated ${execution.valid_leads} outreach targets.`);
    } else {
        showToast(`Run #${execution.id} failed. Check console output.`, "error");
        appendLogLine(`[SYSTEM] Pipeline terminated due to failures.`);
    }
    
    resetRunUIState();
}

function resetRunUIState() {
    submitRunBtn.disabled = false;
    submitRunBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Launch Agent Run';
    
    // Reset sidebar indicator
    document.querySelector(".status-indicator").innerHTML = `
        <span class="pulse-dot green"></span>
        <span class="status-label">Agent Engine Idle</span>
    `;
}

// 5. LEADS MANAGEMENT
let loadedLeads = [];

function calculateQualityScore(lead) {
    const checks = [
        { key: 'name', label: 'Contact Name Identified', passed: false, weight: 20 },
        { key: 'role', label: 'Job Designation Identified', passed: false, weight: 20 },
        { key: 'email', label: 'Email Format Validated', passed: false, weight: 20 },
        { key: 'phone', label: 'Office/Direct Phone Available', passed: false, weight: 20 },
        { key: 'linkedin', label: 'LinkedIn Profile Available', passed: false, weight: 20 }
    ];

    if (lead.name && lead.name !== "Office Manager" && lead.name.trim().length > 0) {
        checks[0].passed = true;
    }
    if (lead.designation && lead.designation !== "Operations" && lead.designation.trim().length > 0) {
        checks[1].passed = true;
    }
    if (lead.email && lead.email.includes("@") && lead.email.includes(".")) {
        checks[2].passed = true;
    }
    if (lead.phone && lead.phone !== "Not Available" && lead.phone.trim().length > 0) {
        checks[3].passed = true;
    }
    if (lead.linkedin_url && !lead.linkedin_url.includes("company/") && lead.linkedin_url.trim().length > 0) {
        checks[4].passed = true;
    }

    const score = checks.reduce((acc, curr) => acc + (curr.passed ? curr.weight : 0), 0);
    return { score, checks };
}


function initLeadsManager() {
    refreshLeadsBtn.addEventListener("click", () => fetchAndRenderLeads());
    
    leadSearch.addEventListener("input", () => filterAndRenderLeadsTable());
    filterStatus.addEventListener("change", () => filterAndRenderLeadsTable());
    
    exportLeadsBtn.addEventListener("click", () => exportLeadsCSV());
    
    // Close modal triggers
    closeModalBtn.addEventListener("click", () => leadModal.classList.remove("active"));
    leadModal.addEventListener("click", (e) => {
        if (e.target === leadModal) {
            leadModal.classList.remove("active");
        }
    });

    // Outreach Composer Modal triggers
    const composerModal = document.getElementById("email-composer-modal");
    const closeComposerBtn = document.getElementById("close-composer-btn");
    const composerForm = document.getElementById("composer-form");

    closeComposerBtn.addEventListener("click", () => composerModal.classList.remove("active"));
    composerModal.addEventListener("click", (e) => {
        if (e.target === composerModal) {
            composerModal.classList.remove("active");
        }
    });

    composerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const contactId = parseInt(document.getElementById("composer-contact-id").value);
        const subject = document.getElementById("composer-subject").value.trim();
        const body = document.getElementById("composer-body").value.trim();
        
        const sendBtn = document.getElementById("composer-send-btn");
        const originalText = sendBtn.innerHTML;
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Dispatched email...';
        
        try {
            const res = await fetchWithAuth(`${API_BASE}/leads/send-email`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ contact_id: contactId, subject, body })
            });
            
            if (res.ok) {
                const data = await res.json();
                const simTxt = data.simulated ? " (Simulated Mode)" : "";
                showToast(`Email sent successfully!${simTxt}`, "success");
                composerModal.classList.remove("active");
                fetchAndRenderLeads();
            } else {
                const data = await res.json();
                showToast(data.detail || "Failed to send email outreach.", "error");
            }
        } catch (err) {
            showToast("Network error trying to send email.", "error");
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalText;
        }
    });
}

async function fetchAndRenderLeads() {
    leadsTableBody.innerHTML = `
        <tr>
            <td colspan="8" class="text-center text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Refreshing lead data...</td>
        </tr>
    `;
    
    try {
        const response = await fetchWithAuth(`${API_BASE}/leads`);
        if (response.ok) {
            loadedLeads = await response.json();
            filterAndRenderLeadsTable();
        } else {
            showToast("Failed to fetch leads list", "error");
        }
    } catch (error) {
        showToast("Error connecting to leads service", "error");
    }
}

function filterAndRenderLeadsTable() {
    const query = leadSearch.value.trim().toLowerCase();
    const statusFilter = filterStatus.value;
    
    const filtered = loadedLeads.filter(lead => {
        // Query match
        const matchesQuery = !query || 
            (lead.name && lead.name.toLowerCase().includes(query)) ||
            (lead.email && lead.email.toLowerCase().includes(query)) ||
            (lead.designation && lead.designation.toLowerCase().includes(query)) ||
            (lead.company && lead.company.name.toLowerCase().includes(query)) ||
            (lead.company && lead.company.industry.toLowerCase().includes(query));
            
        // Status match
        const matchesStatus = !statusFilter || lead.status === statusFilter;
        
        return matchesQuery && matchesStatus;
    });

    renderLeadsTable(filtered);
}

function renderLeadsTable(leads) {
    leadsTableBody.innerHTML = "";
    
    if (leads.length === 0) {
        leadsTableBody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted">No matching leads found in directory.</td>
            </tr>
        `;
        return;
    }
    
    leads.forEach(lead => {
        const tr = document.createElement("tr");
        
        let statusBadgeClass = "badge-new";
        if (lead.status === "Sent") statusBadgeClass = "badge-sent";
        if (lead.status === "Replied") statusBadgeClass = "badge-replied";
        if (lead.status === "Failed") statusBadgeClass = "badge-failed";
        
        const timestamp = new Date(lead.created_at).toLocaleDateString();
        
        // Calculate Quality score
        const { score } = calculateQualityScore(lead);
        let qualityClass = "quality-low";
        if (score >= 80) qualityClass = "quality-high";
        else if (score >= 40) qualityClass = "quality-medium";
        
        // Actions buttons:
        // Details, Email, LinkedIn, Simulate Reply (only if status is Sent), Delete
        let linkedinAction = "";
        const compLinkedin = lead.company?.linkedin_url;
        const execLinkedin = lead.linkedin_url;

        if (compLinkedin && compLinkedin.trim().length > 0 && compLinkedin !== "Not Available") {
            linkedinAction += `
                <a href="${compLinkedin}" target="_blank" class="btn btn-icon linkedin-btn" title="Company LinkedIn Page">
                    <i class="fa-solid fa-building-user"></i>
                </a>
            `;
        }
        if (execLinkedin && execLinkedin.trim().length > 0 && execLinkedin !== "Not Available") {
            linkedinAction += `
                <a href="${execLinkedin}" target="_blank" class="btn btn-icon linkedin-btn" title="Executive/CEO LinkedIn Profile" style="background: rgba(139, 92, 246, 0.25); color: #a78bfa; border-color: rgba(139, 92, 246, 0.4);">
                    <i class="fa-brands fa-linkedin"></i>
                </a>
            `;
        }

        let emailAction = `
            <button class="btn btn-icon email-btn" data-id="${lead.id}" title="Send Individual Outreach">
                <i class="fa-solid fa-envelope"></i>
            </button>
        `;

        let simulateReplyBtn = "";
        if (lead.status === "Sent") {
            simulateReplyBtn = `
                <button class="btn btn-icon reply-btn" data-id="${lead.id}" title="Simulate Client Reply">
                    <i class="fa-solid fa-reply"></i>
                </button>
            `;
        }
        
        tr.innerHTML = `
            <td>
                <div class="bold-txt">${escapeHtml(lead.name)}</div>
            </td>
            <td>${escapeHtml(lead.designation || 'Not specified')}</td>
            <td>
                <a href="${lead.company?.website}" target="_blank" class="cyber-link">${escapeHtml(lead.company?.name || 'N/A')}</a>
            </td>
            <td>${escapeHtml(lead.email)}</td>
            <td>${escapeHtml(lead.phone || 'N/A')}</td>
            <td><span class="badge ${statusBadgeClass}">${lead.status}</span></td>
            <td><span class="quality-table-badge ${qualityClass}">${score}%</span></td>
            <td>${timestamp}</td>
            <td class="actions-col">
                <div class="filter-actions">
                    <button class="btn btn-icon view-btn" data-id="${lead.id}" title="Deep Inspect Details">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                    ${emailAction}
                    ${linkedinAction}
                    ${simulateReplyBtn}
                    <button class="btn btn-icon delete-btn" data-id="${lead.id}" title="Remove Target">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </td>
        `;
        
        // View event
        tr.querySelector(".view-btn").addEventListener("click", () => openLeadModal(lead.id));

        // Email event
        tr.querySelector(".email-btn").addEventListener("click", (e) => {
            e.stopPropagation();
            openOutreachComposer(lead.id);
        });
        
        // Reply event
        const repBtn = tr.querySelector(".reply-btn");
        if (repBtn) {
            repBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                simulateInboundReply(lead.id);
            });
        }
        
        // Delete event
        tr.querySelector(".delete-btn").addEventListener("click", (e) => {
            e.stopPropagation();
            if (confirm(`Are you sure you want to delete lead ${lead.name}?`)) {
                deleteLeadTarget(lead.id);
            }
        });
        
        leadsTableBody.appendChild(tr);
    });
}

// Modal View Details
function openLeadModal(leadId) {
    const lead = loadedLeads.find(l => l.id === leadId);
    if (!lead) return;
    
    modalLeadName.textContent = lead.name;
    modalLeadRole.textContent = lead.designation || "Not Specified";
    modalLeadEmail.textContent = lead.email;
    modalLeadPhone.textContent = lead.phone || "Not Available";
    
    const verBadge = document.getElementById("modal-lead-verification");
    if (verBadge) {
        const verStatus = lead.verification_status || "Unverified";
        verBadge.textContent = verStatus;
        if (verStatus === "Valid") verBadge.className = "badge badge-sent";
        else if (verStatus === "Risky") verBadge.className = "badge badge-purple";
        else verBadge.className = "badge badge-failed";
    }

    if (lead.linkedin_url && lead.linkedin_url !== "Not Available") {
        modalLeadLinkedin.textContent = lead.linkedin_url;
        modalLeadLinkedin.href = lead.linkedin_url;
        modalLeadLinkedin.style.display = "inline";
    } else {
        modalLeadLinkedin.textContent = "Not Available";
        modalLeadLinkedin.removeAttribute("href");
    }

    if (lead.company) {
        modalCompName.textContent = lead.company.name;
        modalCompWeb.textContent = lead.company.website || "N/A";
        modalCompWeb.href = lead.company.website || "#";
        modalCompIndustry.textContent = lead.company.industry || "N/A";
        modalCompPhone.textContent = lead.company.phone || "N/A";
        modalCompAddress.textContent = lead.company.address || "N/A";
        
        if (modalCompLinkedin) {
            if (lead.company.linkedin_url && lead.company.linkedin_url !== "Not Available") {
                modalCompLinkedin.textContent = lead.company.linkedin_url;
                modalCompLinkedin.href = lead.company.linkedin_url;
                modalCompLinkedin.style.display = "inline";
            } else {
                modalCompLinkedin.textContent = "Not Available";
                modalCompLinkedin.removeAttribute("href");
            }
        }

        const socialsContainer = document.getElementById("modal-comp-socials");
        if (socialsContainer) {
            socialsContainer.innerHTML = "";
            const sMap = lead.company.social_links || {};
            let found = false;

            const iconMap = {
                "facebook": { icon: "fa-brands fa-facebook", name: "Facebook" },
                "twitter": { icon: "fa-brands fa-x-twitter", name: "Twitter / X" },
                "instagram": { icon: "fa-brands fa-instagram", name: "Instagram" },
                "youtube": { icon: "fa-brands fa-youtube", name: "YouTube" },
                "company_linkedin": { icon: "fa-brands fa-linkedin", name: "LinkedIn" }
            };

            for (const [key, url] of Object.entries(sMap)) {
                if (url && url !== "Not Available" && typeof url === 'string') {
                    found = true;
                    const meta = iconMap[key] || { icon: "fa-solid fa-globe", name: key };
                    const btn = document.createElement("a");
                    btn.href = url;
                    btn.target = "_blank";
                    btn.className = "cyber-link text-xs";
                    btn.style.padding = "4px 8px";
                    btn.style.borderRadius = "6px";
                    btn.style.background = "rgba(255,255,255,0.05)";
                    btn.style.border = "1px solid rgba(255,255,255,0.1)";
                    btn.style.marginRight = "6px";
                    btn.innerHTML = `<i class="${meta.icon}"></i> ${meta.name}`;
                    socialsContainer.appendChild(btn);
                }
            }
            if (!found) {
                socialsContainer.textContent = "No extra social channels extracted.";
            }
        }
    }

    const attrEmail = document.getElementById("attr-email");
    const attrEmailVal = document.getElementById("attr-email-val");
    const attrPhone = document.getElementById("attr-phone");
    const attrLinkedin = document.getElementById("attr-linkedin");
    const attrDiscovery = document.getElementById("attr-discovery");

    const sourceMap = lead.source_attribution || {};
    if (attrEmail) attrEmail.textContent = sourceMap.email || "Website / Contact Subpage";
    if (attrEmailVal) attrEmailVal.textContent = sourceMap.email_validation || "Pattern & Syntax Validation";
    if (attrPhone) attrPhone.textContent = sourceMap.phone || "Website Footer";
    if (attrLinkedin) attrLinkedin.textContent = sourceMap.person_linkedin || sourceMap.company_linkedin || "Search Engine";
    if (attrDiscovery) attrDiscovery.textContent = sourceMap.discovery_provider || "DuckDuckGo Search Engine";

    // Outreach logs details
    if (lead.outreach) {
        modalOutreachSection.style.display = "block";
        modalOutreachSubject.textContent = lead.outreach.subject;
        modalOutreachDate.textContent = new Date(lead.outreach.sent_at).toLocaleString();
        modalOutreachBody.textContent = lead.outreach.body;
        
        let statusBadgeClass = "badge-new";
        if (lead.outreach.status.includes("Success")) statusBadgeClass = "badge-replied";
        if (lead.outreach.status.includes("Failed")) statusBadgeClass = "badge-failed";
        
        modalOutreachStatus.innerHTML = `Outreach Status: <span class="badge ${statusBadgeClass}">${lead.outreach.status}</span>`;
        
        if (lead.outreach.response) {
            modalOutreachResponseContainer.style.display = "block";
            modalOutreachResponse.textContent = lead.outreach.response;
        } else {
            modalOutreachResponseContainer.style.display = "none";
        }
    } else {
        modalOutreachSection.style.display = "none";
    }

    // Quality evaluation display
    const { score, checks } = calculateQualityScore(lead);
    const scoreCircle = document.getElementById("modal-score-circle");
    const scorePercent = document.getElementById("modal-score-percent");
    const scoreChecksContainer = document.getElementById("modal-score-checks");

    if (scoreCircle && scorePercent && scoreChecksContainer) {
        const circumference = 251.2;
        const offset = circumference - (score / 100) * circumference;
        scoreCircle.style.strokeDashoffset = offset;
        
        // Select color based on score
        let scoreColor = "#ef4444";
        if (score >= 80) scoreColor = "#10b981";
        else if (score >= 40) scoreColor = "#8b5cf6";
        scoreCircle.style.stroke = scoreColor;
        
        scorePercent.textContent = `${score}%`;
        scorePercent.style.color = scoreColor;

        // Render checks list
        scoreChecksContainer.innerHTML = "";
        checks.forEach(check => {
            const checkDiv = document.createElement("div");
            checkDiv.className = "score-check-item";
            
            const iconClass = check.passed ? "fa-solid fa-circle-check score-check-icon passed" : "fa-regular fa-circle score-check-icon failed";
            const badgeClass = check.passed ? "score-check-badge passed" : "score-check-badge failed";
            const badgeText = check.passed ? "PASS" : "MISSING";
            
            checkDiv.innerHTML = `
                <div class="score-check-label">
                    <i class="${iconClass}"></i>
                    <span>${check.label}</span>
                </div>
                <span class="${badgeClass}">${badgeText}</span>
            `;
            scoreChecksContainer.appendChild(checkDiv);
        });
    }

    leadModal.classList.add("active");
}

function openOutreachComposer(leadId) {
    const lead = loadedLeads.find(l => l.id === leadId);
    if (!lead) return;
    
    document.getElementById("composer-contact-id").value = lead.id;
    document.getElementById("composer-to").value = `${lead.name} <${lead.email}>`;
    
    // Set default personalized template
    const compName = lead.company?.name || "your company";
    const contactName = lead.name || "Valued Partner";
    const compWeb = lead.company?.website || "";
    
    document.getElementById("composer-subject").value = `Partnership Opportunity - ${compName}`;
    document.getElementById("composer-body").value = 
        `Hi ${contactName},\n\n` +
        `I visited your website at ${compWeb} and was very impressed with your work.\n\n` +
        `I wanted to reach out to discuss potential partnership opportunities and how we can support your business goals.\n\n` +
        `Let me know if you have a few minutes next week to connect.\n\n` +
        `Best regards,\n` +
        `My Sales Team`;
        
    document.getElementById("email-composer-modal").classList.add("active");
}

async function simulateInboundReply(leadId) {
    try {
        const res = await fetchWithAuth(`${API_BASE}/leads/${leadId}/simulate-reply`, {
            method: "POST"
        });
        
        if (res.ok) {
            showToast("Client response simulated successfully", "success");
            fetchAndRenderLeads();
        } else {
            const data = await res.json();
            showToast(data.detail || "Error simulating client reply", "error");
        }
    } catch (e) {
        showToast("Network error simulating reply", "error");
    }
}

async function deleteLeadTarget(leadId) {
    try {
        const res = await fetchWithAuth(`${API_BASE}/leads/${leadId}`, {
            method: "DELETE"
        });
        
        if (res.ok) {
            showToast("Lead removed from database", "info");
            fetchAndRenderLeads();
        } else {
            showToast("Error deleting lead target", "error");
        }
    } catch (e) {
        showToast("Network error deleting lead", "error");
    }
}

function exportLeadsCSV() {
    if (loadedLeads.length === 0) {
        showToast("No leads to export", "warning");
        return;
    }
    
    // Construct CSV header
    const headers = [
        "Lead ID", "Contact Name", "Designation", "Email", "Phone", "LinkedIn", "Status",
        "Company Name", "Website", "Industry", "Office Phone", "Address", "Discovered At"
    ];
    
    const rows = loadedLeads.map(l => [
        l.id,
        `"${l.name || ''}"`,
        `"${l.designation || ''}"`,
        l.email || '',
        l.phone || '',
        l.linkedin_url || '',
        l.status || '',
        `"${l.company?.name || ''}"`,
        l.company?.website || '',
        `"${l.company?.industry || ''}"`,
        l.company?.phone || '',
        `"${l.company?.address || ''}"`,
        l.created_at || ''
    ]);
    
    let csvContent = "data:text/csv;charset=utf-8," 
        + headers.join(",") + "\n"
        + rows.map(e => e.join(",")).join("\n");
        
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `lead_generation_targets_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    
    link.click();
    document.body.removeChild(link);
    showToast("Leads directory exported as CSV", "success");
}

// Utility Helpers
function escapeHtml(unsafe) {
    if (!unsafe) return "";
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

let campaignEventSource = null;

function initCampaignsManager() {
    const campaignLaunchForm = document.getElementById("campaign-launch-form");
    const clearCampaignLogsBtn = document.getElementById("clear-campaign-logs-btn");
    
    if (campaignLaunchForm) {
        campaignLaunchForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            launchCampaign();
        });
    }
    
    if (clearCampaignLogsBtn) {
        clearCampaignLogsBtn.addEventListener("click", () => {
            document.getElementById("campaign-terminal-logs").innerHTML = `
                <div class="terminal-placeholder">Console logs cleared. Ready for next campaign.</div>
            `;
        });
    }
}

async function populateCampaignSourceDropdown() {
    const campaignSource = document.getElementById("campaign-source");
    if (!campaignSource) return;
    
    // Save current selection
    const currentVal = campaignSource.value;
    
    // Reset to defaults
    campaignSource.innerHTML = `
        <option value="">-- Select Target Leads List --</option>
        <option value="all">All Uncontacted Leads (All Runs)</option>
    `;
    
    try {
        const res = await fetchWithAuth(`${API_BASE}/executions`);
        if (res.ok) {
            const executions = await res.json();
            // Filter completed ones
            const completed = executions.filter(e => e.status === "Completed");
            completed.forEach(exec => {
                const opt = document.createElement("option");
                opt.value = exec.id;
                opt.textContent = `Run #${exec.id}: ${exec.category} in ${exec.location} (${exec.valid_leads} leads)`;
                campaignSource.appendChild(opt);
            });
            
            // Restore selection if still exists
            campaignSource.value = currentVal;
        }
    } catch (err) {
        console.error("Failed to populate campaign lead sources:", err);
    }
}

async function launchCampaign() {
    const sourceVal = document.getElementById("campaign-source").value;
    const subjectVal = document.getElementById("campaign-subject").value.trim();
    const bodyVal = document.getElementById("campaign-body").value.trim();
    const submitBtn = document.getElementById("submit-campaign-btn");
    
    if (!sourceVal || !subjectVal || !bodyVal) {
        showToast("Please fill in all campaign fields", "error");
        return;
    }
    
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Launching Campaign...';
    
    // Reset stats
    document.getElementById("campaign-stat-sent").textContent = "0";
    document.getElementById("campaign-stat-failed").textContent = "0";
    
    const payload = {
        execution_id: sourceVal === "all" ? null : parseInt(sourceVal),
        subject: subjectVal,
        body: bodyVal
    };
    
    try {
        const res = await fetchWithAuth(`${API_BASE}/campaigns/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast("Campaign started successfully!", "success");
            
            // Stream campaign logs
            streamCampaignLogs(data.campaign_id);
            fetchCampaignsHistory();
        } else {
            const data = await res.json();
            showToast(data.detail || "Failed to start campaign.", "error");
        }
    } catch (err) {
        showToast("Network error trying to start campaign.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

function streamCampaignLogs(campaignId) {
    const logsConsole = document.getElementById("campaign-terminal-logs");
    logsConsole.innerHTML = ""; // Clear placeholders
    
    if (campaignEventSource) {
        campaignEventSource.close();
    }
    
    const token = localStorage.getItem("token");
    campaignEventSource = new EventSource(`${API_BASE}/stream-logs/campaign/${campaignId}?token=${encodeURIComponent(token)}`);
    
    campaignEventSource.onmessage = (event) => {
        const message = event.data;
        const lineDiv = document.createElement("div");
        lineDiv.className = "terminal-line";
        
        // Style messages
        if (message.includes("[SUCCESS]")) {
            lineDiv.classList.add("line-success");
        } else if (message.includes("[ERROR]") || message.includes("CRITICAL")) {
            lineDiv.classList.add("line-error");
        } else if (message.includes("[WARNING]")) {
            lineDiv.classList.add("line-warning");
        }
        
        lineDiv.textContent = message;
        logsConsole.appendChild(lineDiv);
        logsConsole.scrollTop = logsConsole.scrollHeight;
        
        // Parse metrics live from logs to update UI stats
        if (message.includes("[SUCCESS]")) {
            const sentSpan = document.getElementById("campaign-stat-sent");
            sentSpan.textContent = parseInt(sentSpan.textContent) + 1;
        } else if (message.includes("[ERROR] Failed to send")) {
            const failedSpan = document.getElementById("campaign-stat-failed");
            failedSpan.textContent = parseInt(failedSpan.textContent) + 1;
        }
        
        if (message.includes("Campaign complete") || message.includes("Ending campaign")) {
            campaignEventSource.close();
            fetchCampaignsHistory();
            fetchAndRenderLeads(); // Refresh leads table to update status
        }
    };
    
    campaignEventSource.onerror = () => {
        campaignEventSource.close();
        const errDiv = document.createElement("div");
        errDiv.className = "terminal-line line-error";
        errDiv.textContent = "[SYSTEM] Log channel disconnected.";
        logsConsole.appendChild(errDiv);
    };
}

async function fetchCampaignsHistory() {
    const tableBody = document.getElementById("campaigns-table-body");
    if (!tableBody) return;
    
    try {
        const res = await fetchWithAuth(`${API_BASE}/campaigns`);
        if (res.ok) {
            const campaigns = await res.json();
            if (campaigns.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-muted">No campaigns launched yet.</td>
                    </tr>
                `;
                return;
            }
            
            tableBody.innerHTML = "";
            campaigns.forEach(c => {
                const tr = document.createElement("tr");
                
                let badgeClass = "badge-new";
                if (c.status === "Running") badgeClass = "badge-running";
                if (c.status === "Completed") badgeClass = "badge-completed";
                if (c.status === "Failed") badgeClass = "badge-failed";
                
                const timestamp = c.created_at ? new Date(c.created_at).toLocaleString() : "-";
                
                tr.innerHTML = `
                    <td><strong>#${c.id}</strong></td>
                    <td class="bold-txt">${escapeHtml(c.subject)}</td>
                    <td>${escapeHtml(c.target)}</td>
                    <td>
                        <span class="green-txt">${c.sent_count} Sent</span> / 
                        <span style="color:#ef4444">${c.failed_count} Failed</span>
                    </td>
                    <td><span class="badge ${badgeClass}">${c.status}</span></td>
                    <td>${timestamp}</td>
                `;
                tableBody.appendChild(tr);
            });
        }
    } catch (err) {
        console.error("Failed to load campaigns history:", err);
    }
}
