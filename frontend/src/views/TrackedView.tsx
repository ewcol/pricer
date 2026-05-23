import { useState, useEffect, useCallback } from 'react';
import TrackedTable from '../components/TrackedTable';
import type { TrackedItem } from '../components/TrackedTable';
import styles from './TrackedView.module.css';

export default function TrackedView() {
  const [items, setItems] = useState<TrackedItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch('/tracked-items');
      if (resp.ok) setItems(await resp.json());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchItems(); }, [fetchItems]);

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
        setActionStatus(`Check scheduled for ${selectedId}. Will refresh in ~30s.`);
        setTimeout(fetchItems, 32000);
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
          onClick={fetchItems}
          disabled={loading}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
            <path d="M10.5 6A4.5 4.5 0 1 1 6 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M10.5 1.5v3h-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {loading ? 'Refreshing' : 'Refresh'}
        </button>
      </div>

      <TrackedTable
        items={items}
        selectedId={selectedId}
        onSelect={(id) => {
          setSelectedId(prev => prev === id ? null : id);
          setActionStatus(null);
        }}
      />

      {selectedId && (
        <div className={styles.rowActions}>
          <span className={styles.selectedLabel}>{selectedId}</span>
          <button className={styles.scheduleBtn} onClick={schedule}>
            Schedule 30s Check
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
