/**
 * AgroTrack AI — Field Operations Offline Synchronisation Engine
 * Provides resilient client-side offline queueing, conflict detection,
 * idempotency tracking, and network recovery synchronisation for Field Officers.
 */

(function () {
  const STORAGE_KEY = "agrotrack_offline_activities_queue";
  let isSyncing = false;
  let lastSyncTimestamp = localStorage.getItem("agrotrack_last_sync") || null;

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

  /**
   * Enqueues an activity record when field officer is offline or experiencing network drops.
   */
  function queueActivity(activityData) {
    const queue = getQueue();
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
      status: "pending", // "pending" | "conflict"
      conflictReason: null
    };

    queue.push(item);
    saveQueue(queue);
    return item;
  }

  /**
   * Performs safe batch synchronization with backend idempotency and conflict detection.
   */
  async function syncQueue() {
    if (isSyncing) return;
    if (!navigator.onLine) {
      updateUI();
      return;
    }

    const queue = getQueue();
    const pendingItems = queue.filter(item => item.status === "pending" || item.status === "retry");
    if (pendingItems.length === 0) {
      updateUI();
      return;
    }

    isSyncing = true;
    updateUI();

    const token = (window.AgroTrack && window.AgroTrack.getAuthToken)
      ? window.AgroTrack.getAuthToken()
      : localStorage.getItem("agrotrack-auth-token") || "mock-token-field";

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
          clientCreatedAt: item.clientCreatedAt
        }))
      };

      const response = await fetch("/api/v1/agrotrack/activities/sync", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Sync server responded with status: ${response.status}`);
      }

      const result = await response.json();
      const currentQueue = getQueue();

      // Collect IDs of successfully synced and duplicated records to remove from queue
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
          // Flagged conflict: keep in queue for user review
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

      // Optional user feedback toast
      if (result.syncedCount > 0) {
        showSyncToast(`Synchronized ${result.syncedCount} offline field ${result.syncedCount === 1 ? 'activity' : 'activities'} successfully.`);
      }
      if (result.conflictCount > 0) {
        showSyncToast(`${result.conflictCount} activity ${result.conflictCount === 1 ? 'conflict' : 'conflicts'} detected. Check sync queue.`, true);
      }
    } catch (err) {
      console.warn("AgroTrack offline sync retry deferred:", err.message);
      // Mark pending items for retry
      const currentQueue = getQueue();
      currentQueue.forEach(item => {
        if (item.status === "pending") item.status = "retry";
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
        border-radius: 8px;
        font-family: 'Outfit', sans-serif;
        font-size: 0.88rem;
        font-weight: 500;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 10px;
        transition: opacity 0.3s ease, transform 0.3s ease;
      `;
      document.body.appendChild(toast);
    }

    if (isWarning) {
      toast.style.background = "#7f1d1d";
      toast.style.color = "#fecaca";
      toast.style.border = "1px solid #b91c1c";
      toast.innerHTML = `<i class="fas fa-triangle-exclamation"></i> <span>${message}</span>`;
    } else {
      toast.style.background = "#064e3b";
      toast.style.color = "#a7f3d0";
      toast.style.border = "1px solid #059669";
      toast.innerHTML = `<i class="fas fa-circle-check"></i> <span>${message}</span>`;
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
    const pendingCount = queue.filter(x => x.status === "pending" || x.status === "retry").length;
    const conflictCount = queue.filter(x => x.status === "conflict").length;
    const isOnline = navigator.onLine;

    if (isSyncing) {
      pill.className = "sync-pill syncing";
      pill.innerHTML = `<i class="fas fa-rotate fa-spin"></i> <span>Syncing...</span>`;
      pill.title = "Synchronizing offline records with server...";
    } else if (conflictCount > 0) {
      pill.className = "sync-pill conflict";
      pill.innerHTML = `<i class="fas fa-triangle-exclamation"></i> <span>${conflictCount} Conflict${conflictCount > 1 ? 's' : ''}</span>`;
      pill.title = "Click to inspect synchronization conflicts";
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
      pill.title = "Connected to AgroTrack AI server. All data synchronized.";
    }
  }

  /**
   * Modal dialog to inspect pending sync items and resolve conflicts.
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
        background: rgba(0,0,0,0.65);
        backdrop-filter: blur(4px);
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
      `;
      modal.innerHTML = `
        <div style="background: #111e17; border: 1px solid #1e3a2b; border-radius: 12px; width: 100%; max-width: 600px; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
          <div style="padding: 16px 20px; border-bottom: 1px solid #1e3a2b; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <i class="fas fa-cloud-arrow-up" style="color: #22c55e;"></i>
              <h3 style="margin: 0; font-size: 1.05rem; font-weight: 600; color: #f8fafc;">Offline Synchronisation Queue</h3>
            </div>
            <button id="closeSyncModalBtn" style="background: none; border: none; color: #94a3b8; font-size: 1.1rem; cursor: pointer;">&times;</button>
          </div>
          <div id="syncModalBody" style="padding: 20px; overflow-y: auto; flex: 1;"></div>
          <div style="padding: 14px 20px; border-top: 1px solid #1e3a2b; display: flex; justify-content: space-between; align-items: center; background: #0c1510;">
            <div id="syncModalSummary" style="font-size: 0.82rem; color: #94a3b8;"></div>
            <div style="display: flex; gap: 10px;">
              <button id="clearSyncQueueBtn" style="background: transparent; border: 1px solid #334155; color: #94a3b8; padding: 7px 14px; border-radius: 6px; font-size: 0.85rem; cursor: pointer;">Dismiss Synced</button>
              <button id="manualSyncBtn" style="background: #22c55e; border: none; color: #022c22; font-weight: 600; padding: 7px 16px; border-radius: 6px; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                <i class="fas fa-rotate"></i> Sync Now
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

      document.getElementById("manualSyncBtn").onclick = async () => {
        const btn = document.getElementById("manualSyncBtn");
        btn.innerHTML = `<i class="fas fa-rotate fa-spin"></i> Syncing...`;
        btn.disabled = true;
        await syncQueue();
        btn.innerHTML = `<i class="fas fa-rotate"></i> Sync Now`;
        btn.disabled = false;
        renderModalContent();
      };

      document.getElementById("clearSyncQueueBtn").onclick = () => {
        const queue = getQueue().filter(item => item.status === "conflict" || item.status === "pending");
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
    const isOnline = navigator.onLine;

    summary.textContent = `Network: ${isOnline ? 'Connected' : 'Disconnected'} • ${queue.length} items in local store`;

    if (queue.length === 0) {
      body.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: #94a3b8;">
          <i class="fas fa-check-circle" style="font-size: 2.5rem; color: #22c55e; margin-bottom: 12px; display: block;"></i>
          <p style="margin: 0; font-size: 0.95rem; font-weight: 500; color: #e2e8f0;">All changes are synchronized!</p>
          <span style="font-size: 0.82rem; color: #64748b;">No pending field activities or data conflicts in this browser session.</span>
        </div>
      `;
      return;
    }

    let html = `<div style="display: flex; flex-direction: column; gap: 10px;">`;
    queue.forEach((item, idx) => {
      const isConflict = item.status === "conflict";
      const statusColor = isConflict ? "#ef4444" : "#f59e0b";
      const statusBg = isConflict ? "rgba(239, 68, 68, 0.12)" : "rgba(245, 158, 11, 0.12)";
      const statusLabel = isConflict ? "Conflict" : (item.status === "retry" ? "Retry Pending" : "Queued Offline");

      html += `
        <div style="background: #16261e; border: 1px solid ${isConflict ? '#991b1b' : '#1e3a2b'}; border-radius: 8px; padding: 12px 14px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="background: ${statusBg}; color: ${statusColor}; font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 4px;">${statusLabel}</span>
              <strong style="color: #f1f5f9; font-size: 0.88rem;">${(item.activityType || 'Activity').replace('_', ' ').toUpperCase()}</strong>
            </div>
            <span style="font-size: 0.75rem; color: #94a3b8;">${new Date(item.clientCreatedAt).toLocaleTimeString()}</span>
          </div>
          <div style="font-size: 0.82rem; color: #cbd5e1; margin-bottom: 4px;">
            <strong>Target Plot:</strong> <code>${item.farmId}</code> • <strong>Date:</strong> ${item.activityDate}
          </div>
          <div style="font-size: 0.8rem; color: #94a3b8; background: #0c1510; padding: 6px 10px; border-radius: 4px;">
            "${item.notes || 'No notes'}"
          </div>
          ${isConflict ? `
            <div style="margin-top: 8px; font-size: 0.78rem; color: #fca5a5; display: flex; align-items: center; gap: 6px;">
              <i class="fas fa-circle-exclamation"></i> <strong>Conflict Reason:</strong> ${item.conflictReason || 'Server rejected overwrite.'}
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
    showSyncToast("Network disconnected. AgroTrack is now working offline.", true);
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
