/**
 * AgroFast — Field Operations Offline Synchronisation Engine
 * Provides resilient client-side offline queueing, conflict detection,
 * idempotency tracking, tenant/user binding, exponential backoff, and network recovery sync.
 * Restyled with authentic AgroFast slate glassmorphism & emerald green visual identity.
 */

(function () {
  const STORAGE_KEY = "agrotrack_offline_activities_queue";
  let isSyncing = false;
  let lastSyncTimestamp = localStorage.getItem("agrotrack_last_sync") || null;
  let lastManualClick = 0;
  const MAX_RETRIES = 5;
  const BACKOFF_DELAYS = [2000, 4000, 8000, 16000, 32000]; // Exponential backoff in ms

  function getQueue() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error("Error reading offline queue from localStorage:", e);
      return [];
    }
  }

  function saveQueue(queue) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
      updateUI();
    } catch (e) {
      console.error("Error saving offline queue to localStorage:", e);
    }
  }

  function generateMutationId() {
    if (window.crypto && window.crypto.randomUUID) {
      return "mut_" + window.crypto.randomUUID();
    }
    return "mut_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
  }

  function getCurrentUserContext() {
    const roleObj = (window.AgroTrack && window.AgroTrack.getActiveRole)
      ? window.AgroTrack.getActiveRole()
      : null;
    const token = (window.AgroTrack && window.AgroTrack.getAuthToken)
      ? window.AgroTrack.getAuthToken()
      : localStorage.getItem("agrotrack-auth-token") || "mock-token-field";
    const userId = (roleObj && roleObj.id) ? `usr_${roleObj.id}` : localStorage.getItem("agrotrack-user-id") || "usr_field_003";
    const orgId = localStorage.getItem("agrotrack-org-id") || "org_greenvalley_01";
    return { token, userId, orgId };
  }

  /**
   * Enqueues an activity record bound to current authenticated user and organisation.
   */
  function queueActivity(activityData) {
    const queue = getQueue();
    const ctx = getCurrentUserContext();

    const item = {
      clientMutationId: generateMutationId(),
      farmId: activityData.farmId,
      farmerId: activityData.farmerId || null,
      activityType: activityData.activityType || "farm_visit",
      activityDate: activityData.activityDate || new Date().toISOString().split("T")[0],
      notes: activityData.notes || "",
      metrics: activityData.metrics || {},
      observations: activityData.observations || [],
      clientCreatedAt: new Date().toISOString(),
      authorUserId: ctx.userId,
      orgId: ctx.orgId,
      status: "pending", // "pending" | "conflict" | "retry" | "validation_error" | "failed_max_retries"
      retryCount: 0,
      nextRetryAt: 0,
      conflictReason: null,
      validationError: null
    };

    queue.push(item);
    saveQueue(queue);
    return item;
  }

  /**
   * Performs safe batch synchronization with backend idempotency and conflict detection.
   * Gated by user/tenant matching, session validation, retry caps, and exponential backoff.
   */
  async function syncQueue() {
    if (isSyncing) return;
    if (!navigator.onLine) {
      updateUI();
      return;
    }

    const ctx = getCurrentUserContext();
    const queue = getQueue();
    const now = Date.now();

    // Only sync items belonging to current user and tenant that are ready
    const pendingItems = queue.filter(item => {
      const belongsToCurrentSession = (!item.authorUserId || item.authorUserId === ctx.userId) &&
                                     (!item.orgId || item.orgId === ctx.orgId);
      const isPendingStatus = (item.status === "pending" || item.status === "retry");
      const readyForRetry = !item.nextRetryAt || now >= item.nextRetryAt;
      return belongsToCurrentSession && isPendingStatus && readyForRetry;
    });

    if (pendingItems.length === 0) {
      updateUI();
      return;
    }

    isSyncing = true;
    updateUI();

    try {
      const payload = {
        batch: pendingItems.map(item => ({
          clientMutationId: item.clientMutationId,
          farmId: item.farmId,
          farmerId: item.farmerId,
          activityType: item.activityType,
          activityDate: item.activityDate,
          notes: item.notes,
          metrics: item.metrics,
          observations: item.observations,
          clientCreatedAt: item.clientCreatedAt,
          authorUserId: item.authorUserId,
          orgId: item.orgId
        }))
      };

      const response = await fetch("/api/v1/agrotrack/activities/sync", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${ctx.token}`
        },
        body: JSON.stringify(payload)
      });

      // ── Handle Session Expiry (401) ──
      if (response.status === 401) {
        showSyncToast("Session expired. Please re-authenticate to sync your offline field activities.", true);
        isSyncing = false;
        updateUI();
        return;
      }

      // ── Handle Validation Errors (400, 422) ──
      if (response.status === 400 || response.status === 422) {
        let errDetail = "Validation error from server";
        try {
          const errJson = await response.json();
          errDetail = errJson.detail || errJson.error || JSON.stringify(errJson);
        } catch (_) {}

        // Mark items with validation error so they stop endless loop
        const currentQueue = getQueue();
        const pendingIds = new Set(pendingItems.map(p => p.clientMutationId));
        currentQueue.forEach(item => {
          if (pendingIds.has(item.clientMutationId)) {
            item.status = "validation_error";
            item.validationError = errDetail;
          }
        });
        saveQueue(currentQueue);
        showSyncToast(`Sync rejected: ${errDetail}`, true);
        isSyncing = false;
        updateUI();
        return;
      }

      if (!response.ok) {
        throw new Error(`Sync server responded with status: ${response.status}`);
      }

      const result = await response.json();
      const currentQueue = getQueue();

      // Collect IDs of successfully synced and duplicated records
      const resolvedMutationIds = new Set();
      (result.synced || []).forEach(s => resolvedMutationIds.add(s.clientMutationId));
      (result.duplicates || []).forEach(d => resolvedMutationIds.add(d.clientMutationId));

      // Map conflicts
      const conflictMap = new Map();
      (result.conflicts || []).forEach(c => conflictMap.set(c.clientMutationId, c.message));

      const updatedQueue = [];
      currentQueue.forEach(item => {
        if (resolvedMutationIds.has(item.clientMutationId)) {
          // Successfully synchronized or already recorded: safely remove from queue
          return;
        }
        if (conflictMap.has(item.clientMutationId)) {
          // Flagged conflict: keep in queue for user inspection
          item.status = "conflict";
          item.conflictReason = conflictMap.get(item.clientMutationId);
          updatedQueue.push(item);
        } else {
          updatedQueue.push(item);
        }
      });

      saveQueue(updatedQueue);
      lastSyncTimestamp = new Date().toISOString();
      localStorage.setItem("agrotrack_last_sync", lastSyncTimestamp);

      // Dispatch event for UI views to refresh
      document.dispatchEvent(new CustomEvent("agrotrack:sync-complete", { detail: result }));

      if (result.syncedCount > 0) {
        showSyncToast(`Synchronized ${result.syncedCount} offline field ${result.syncedCount === 1 ? 'activity' : 'activities'} successfully.`);
      }
      if (result.conflictCount > 0) {
        showSyncToast(`${result.conflictCount} activity conflict${result.conflictCount > 1 ? 's' : ''} detected. Check sync queue.`, true);
      }
    } catch (err) {
      console.warn("AgroTrack offline sync retry deferred with exponential backoff:", err.message);

      // Apply exponential backoff and retry cap
      const currentQueue = getQueue();
      const pendingIds = new Set(pendingItems.map(p => p.clientMutationId));

      currentQueue.forEach(item => {
        if (pendingIds.has(item.clientMutationId)) {
          const retries = (item.retryCount || 0) + 1;
          item.retryCount = retries;
          if (retries >= MAX_RETRIES) {
            item.status = "failed_max_retries";
            item.conflictReason = `Failed after ${MAX_RETRIES} attempts. Network or server unreachable: ${err.message}`;
          } else {
            item.status = "retry";
            const delayMs = BACKOFF_DELAYS[Math.min(retries - 1, BACKOFF_DELAYS.length - 1)];
            item.nextRetryAt = Date.now() + delayMs;
          }
        }
      });
      saveQueue(currentQueue);
    } finally {
      isSyncing = false;
      updateUI();
    }
  }

  function showSyncToast(message, isWarning = false) {
    let toast = document.getElementById("agrotrackSyncToast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "agrotrackSyncToast";
      toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 99999;
        padding: 12px 18px;
        border-radius: 10px;
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 0.88rem;
        font-weight: 500;
        box-shadow: 0 12px 30px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        gap: 10px;
        backdrop-filter: blur(12px);
        transition: opacity 0.3s ease, transform 0.3s ease;
      `;
      document.body.appendChild(toast);
    }

    if (isWarning) {
      toast.style.background = "rgba(127, 29, 29, 0.95)";
      toast.style.color = "#fecaca";
      toast.style.border = "1px solid rgba(239, 68, 68, 0.4)";
      toast.innerHTML = `<i class="fas fa-triangle-exclamation" style="color: #ef4444;"></i> <span>${message}</span>`;
    } else {
      toast.style.background = "rgba(15, 23, 42, 0.95)";
      toast.style.color = "#f1f5f9";
      toast.style.border = "1px solid rgba(34, 197, 94, 0.4)";
      toast.innerHTML = `<i class="fas fa-circle-check" style="color: #22c55e;"></i> <span>${message}</span>`;
    }

    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
    }, 4500);
  }

  /**
   * Updates the sync status badge in the topbar.
   */
  function updateUI() {
    const pill = document.getElementById("shellSyncPill");
    if (!pill) return;

    const queue = getQueue();
    const ctx = getCurrentUserContext();

    // Filter items relevant to active user/session
    const userQueue = queue.filter(item => !item.authorUserId || item.authorUserId === ctx.userId);
    const pendingCount = userQueue.filter(x => x.status === "pending" || x.status === "retry").length;
    const conflictCount = userQueue.filter(x => x.status === "conflict" || x.status === "validation_error" || x.status === "failed_max_retries").length;
    const isOnline = navigator.onLine;

    if (isSyncing) {
      pill.className = "sync-pill syncing";
      pill.innerHTML = `<i class="fas fa-rotate fa-spin"></i> <span>Syncing...</span>`;
      pill.title = "Synchronizing offline records with server...";
    } else if (conflictCount > 0) {
      pill.className = "sync-pill conflict";
      pill.innerHTML = `<i class="fas fa-triangle-exclamation"></i> <span>${conflictCount} Conflict${conflictCount > 1 ? 's' : ''}</span>`;
      pill.title = "Click to inspect synchronization conflicts / validation errors";
    } else if (!isOnline) {
      pill.className = "sync-pill offline";
      pill.innerHTML = `<i class="fas fa-cloud-arrow-up"></i> <span>Offline (${pendingCount})</span>`;
      pill.title = `Working offline. ${pendingCount} change${pendingCount === 1 ? '' : 's'} queued locally.`;
    } else if (pendingCount > 0) {
      pill.className = "sync-pill pending";
      pill.innerHTML = `<i class="fas fa-cloud-arrow-up"></i> <span>${pendingCount} Pending</span>`;
      pill.title = `${pendingCount} record${pendingCount === 1 ? '' : 's'} awaiting sync. Click to sync now.`;
    } else {
      pill.className = "sync-pill online";
      pill.innerHTML = `<i class="fas fa-circle-check"></i> <span>Online</span>`;
      pill.title = "Connected to AgroFast server. All data synchronized.";
    }
  }

  /**
   * Modal dialog to inspect pending sync items and resolve conflicts.
   * Restyled to match AgroFast deep slate `#020617` / `#0f172a` glassmorphism.
   */
  function openSyncQueueModal() {
    let modal = document.getElementById("agrotrackSyncModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "agrotrackSyncModal";
      modal.className = "modal-backdrop";
      modal.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(2, 6, 23, 0.75);
        backdrop-filter: blur(8px);
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
      `;
      modal.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; width: 100%; max-width: 640px; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7);">
          <div style="padding: 18px 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.5);">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 34px; height: 34px; border-radius: 8px; background: rgba(34, 197, 94, 0.15); display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-cloud-arrow-up" style="color: #22c55e; font-size: 1rem;"></i>
              </div>
              <div>
                <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #f1f5f9; letter-spacing: -0.01em;">Offline Synchronisation Queue</h3>
                <span style="font-size: 0.75rem; color: #94a3b8;">Field Officer local storage manager</span>
              </div>
            </div>
            <button id="closeSyncModalBtn" style="background: none; border: none; color: #94a3b8; font-size: 1.3rem; cursor: pointer; transition: color 0.15s;" onmouseover="this.style.color='#f1f5f9'" onmouseout="this.style.color='#94a3b8'">&times;</button>
          </div>
          <div id="syncModalBody" style="padding: 20px 24px; overflow-y: auto; flex: 1;"></div>
          <div style="padding: 16px 24px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center; background: rgba(2, 6, 23, 0.85);">
            <div id="syncModalSummary" style="font-size: 0.8rem; color: #94a3b8;"></div>
            <div style="display: flex; gap: 12px;">
              <button id="clearSyncQueueBtn" style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); color: #cbd5e1; padding: 8px 14px; border-radius: 8px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.15s;" onmouseover="this.style.background='rgba(30, 41, 59, 0.9)'" onmouseout="this.style.background='rgba(30, 41, 59, 0.6)'">Dismiss Synced</button>
              <button id="manualSyncBtn" style="background: #22c55e; border: none; color: #020617; font-weight: 700; padding: 8px 18px; border-radius: 8px; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 8px; box-shadow: 0 0 16px rgba(34, 197, 94, 0.35); transition: all 0.2s ease;">
                <i class="fas fa-rotate"></i> <span>Sync Now</span>
              </button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      document.getElementById("closeSyncModalBtn").onclick = () => {
        modal.style.display = "none";
      };
      modal.onclick = (e) => {
        if (e.target === modal) modal.style.display = "none";
      };

      // Debounced manual sync trigger
      document.getElementById("manualSyncBtn").onclick = async () => {
        const now = Date.now();
        if (now - lastManualClick < 2000) {
          return; // Debounce double clicks
        }
        lastManualClick = now;

        const btn = document.getElementById("manualSyncBtn");
        btn.innerHTML = `<i class="fas fa-rotate fa-spin"></i> <span>Syncing...</span>`;
        btn.disabled = true;
        btn.style.opacity = "0.7";

        await syncQueue();

        btn.innerHTML = `<i class="fas fa-rotate"></i> <span>Sync Now</span>`;
        btn.disabled = false;
        btn.style.opacity = "1";
        renderModalContent();
      };

      document.getElementById("clearSyncQueueBtn").onclick = () => {
        const queue = getQueue().filter(item => item.status === "conflict" || item.status === "pending" || item.status === "retry");
        saveQueue(queue);
        renderModalContent();
      };
    }

    renderModalContent();
    modal.style.display = "flex";
  }

  function renderModalContent() {
    const body = document.getElementById("syncModalBody");
    const summary = document.getElementById("syncModalSummary");
    if (!body) return;

    const queue = getQueue();
    const ctx = getCurrentUserContext();
    const userQueue = queue.filter(item => !item.authorUserId || item.authorUserId === ctx.userId);
    const isOnline = navigator.onLine;

    summary.textContent = `Network: ${isOnline ? 'Online' : 'Offline'} • ${userQueue.length} queued item${userQueue.length === 1 ? '' : 's'}`;

    if (userQueue.length === 0) {
      body.innerHTML = `
        <div style="text-align: center; padding: 48px 20px; color: #94a3b8;">
          <div style="width: 56px; height: 56px; border-radius: 50%; background: rgba(34, 197, 94, 0.12); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto;">
            <i class="fas fa-check" style="font-size: 1.5rem; color: #22c55e;"></i>
          </div>
          <p style="margin: 0 0 6px 0; font-size: 1.05rem; font-weight: 600; color: #f1f5f9;">All changes are synchronized!</p>
          <span style="font-size: 0.82rem; color: #64748b;">No pending field activities or data conflicts in this browser session.</span>
        </div>
      `;
      return;
    }

    let html = `<div style="display: flex; flex-direction: column; gap: 12px;">`;
    userQueue.forEach((item, idx) => {
      const isConflict = item.status === "conflict" || item.status === "validation_error" || item.status === "failed_max_retries";
      const statusColor = isConflict ? "#ef4444" : (item.status === "retry" ? "#38bdf8" : "#f59e0b");
      const statusBg = isConflict ? "rgba(239, 68, 68, 0.15)" : (item.status === "retry" ? "rgba(56, 189, 248, 0.15)" : "rgba(245, 158, 11, 0.15)");
      const statusLabel = item.status === "conflict" ? "Conflict" :
                          item.status === "validation_error" ? "Validation Error" :
                          item.status === "failed_max_retries" ? "Exceeded Retries" :
                          item.status === "retry" ? `Retry #${item.retryCount || 1}` : "Queued Offline";

      html += `
        <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid ${isConflict ? 'rgba(239, 68, 68, 0.4)' : 'rgba(255, 255, 255, 0.08)'}; border-radius: 10px; padding: 14px 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span style="background: ${statusBg}; color: ${statusColor}; font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">${statusLabel}</span>
              <strong style="color: #f1f5f9; font-size: 0.9rem;">${(item.activityType || 'Activity').replace('_', ' ').toUpperCase()}</strong>
            </div>
            <span style="font-size: 0.74rem; color: #94a3b8;">${new Date(item.clientCreatedAt).toLocaleTimeString()}</span>
          </div>
          <div style="font-size: 0.82rem; color: #cbd5e1; margin-bottom: 6px;">
            <strong>Farm Plot:</strong> <code>${item.farmId}</code> • <strong>Date:</strong> ${item.activityDate}
          </div>
          <div style="font-size: 0.8rem; color: #94a3b8; background: rgba(2, 6, 23, 0.6); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.04);">
            "${item.notes || 'No observation notes'}"
          </div>
          ${isConflict ? `
            <div style="margin-top: 10px; font-size: 0.78rem; color: #fca5a5; display: flex; align-items: flex-start; gap: 8px; background: rgba(127, 29, 29, 0.2); padding: 6px 10px; border-radius: 6px;">
              <i class="fas fa-circle-exclamation" style="margin-top: 2px;"></i>
              <div><strong>Reason:</strong> ${item.conflictReason || item.validationError || 'Rejected by server.'}</div>
            </div>
          ` : ''}
        </div>
      `;
    });
    html += `</div>`;
    body.innerHTML = html;
  }

  // Network event listeners
  window.addEventListener("online", () => {
    updateUI();
    showSyncToast("Network restored. Initiating automatic sync...");
    syncQueue();
  });

  window.addEventListener("offline", () => {
    updateUI();
    showSyncToast("Network disconnected. AgroFast is now working offline.", true);
  });

  document.addEventListener("DOMContentLoaded", () => {
    updateUI();
    // If pending items exist on page load and we are online, trigger sync
    if (navigator.onLine && getQueue().some(x => x.status === "pending" || x.status === "retry")) {
      syncQueue();
    }
  });

  // Expose global interface
  window.agrotrackOfflineSync = {
    getQueue,
    queueActivity,
    syncQueue,
    updateUI,
    openSyncQueueModal
  };
})();
