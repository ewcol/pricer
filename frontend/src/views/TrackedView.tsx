import { useState, useEffect, useCallback } from 'react';
import TrackedTable from '../components/TrackedTable';
import type { TrackedItem } from '../components/TrackedTable';
import type { HistoryEntry } from '../components/PriceSparkline';
import styles from './TrackedView.module.css';

interface PortfolioSummary {
  total: number;
  avg_drift: number;
  flagged: number;
}

export default function TrackedView() {
  const [items, setItems] = useState<TrackedItem[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const [historyMap, setHistoryMap] = useState<Record<string, HistoryEntry[]>>({});

  const refreshDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [itemsResp, summaryResp] = await Promise.all([
        fetch('/tracked-items'),
        fetch('/portfolio-summary'),
      ]);

      if (itemsResp.ok) setItems(await itemsResp.json());
      if (summaryResp.ok) setSummary(await summaryResp.json());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refreshDashboard(); }, [refreshDashboard]);

  useEffect(() => {
    if (!selectedId) return;
    if (Object.prototype.hasOwnProperty.call(historyMap, selectedId)) return;

    let active = true;

    void (async () => {
      try {
        const resp = await fetch(`/price-history/${selectedId}`);
        if (!resp.ok) return;
        const history: HistoryEntry[] = await resp.json();
        if (active) {
          setHistoryMap((prev) => ({
            ...prev,
            [selectedId]: history,
          }));
        }
      } catch {
        // Leave the cache empty so the user can retry by reselecting the row.
      }
    })();

    return () => {
      active = false;
    };
  }, [historyMap, selectedId]);

  const schedule = async () => {
    if (!selectedId) return;
    setActionStatus(`Scheduling check for ${selectedId}…`);
    try {
      const resp = await fetch('/schedule-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: selectedId }),
      });
      if (resp.ok) {
        setActionStatus(`Check scheduled for ${selectedId}. Will refresh in ~5s.`);
        setTimeout(refreshDashboard, 7000);
      } else {
        setActionStatus('Failed to schedule check.');
      }
    } catch {
      setActionStatus('Network error.');
    }
  };

  const cancel = async () => {
    if (!selectedId) return;
    setActionStatus(`Canceling check for ${selectedId}…`);
    try {
      const resp = await fetch('/cancel-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: selectedId }),
      });
      setActionStatus(resp.ok ? `Check canceled for ${selectedId}.` : 'Nothing to cancel.');
    } catch {
      setActionStatus('Network error.');
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.toolbar}>
        <span className={styles.tableTitle}>Tracked Items</span>
        <button
          className={styles.refreshBtn}
          onClick={refreshDashboard}
          disabled={loading}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
            <path d="M10.5 6A4.5 4.5 0 1 1 6 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M10.5 1.5v3h-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {loading ? 'Refreshing' : 'Refresh'}
        </button>
      </div>

      {summary && summary.total > 0 && (
        <div className={styles.summary}>
          <div className={styles.summaryStat}>
            <div className={styles.summaryValue}>{summary.total}</div>
            <div className={styles.summaryLabel}>tracked</div>
          </div>
          <div className={styles.summaryStat}>
            <div className={styles.summaryValue}>
              {summary.avg_drift > 0 ? '+' : ''}
              {summary.avg_drift.toFixed(1)}%
            </div>
            <div className={styles.summaryLabel}>avg drift</div>
          </div>
          <div className={styles.summaryStat}>
            <div className={styles.summaryValue}>{summary.flagged}</div>
            <div className={styles.summaryLabel}>flagged</div>
          </div>
        </div>
      )}

      <TrackedTable
        items={items}
        selectedId={selectedId}
        historyMap={historyMap}
        onSelect={(id) => {
          setSelectedId(prev => prev === id ? null : id);
          setActionStatus(null);
        }}
      />

      {selectedId && (
        <div className={styles.rowActions}>
          <span className={styles.selectedLabel}>{selectedId}</span>
          <button className={styles.scheduleBtn} onClick={schedule}>
            Schedule 5s Check
          </button>
          <button className={styles.cancelBtn} onClick={cancel}>
            Cancel
          </button>
          {actionStatus && (
            <span className={styles.actionStatus}>{actionStatus}</span>
          )}
        </div>
      )}
    </div>
  );
}
