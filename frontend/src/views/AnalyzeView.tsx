import { useState } from 'react';
import ImageDropZone from '../components/ImageDropZone';
import OutputPanel from '../components/OutputPanel';
import SkeletonPanel from '../components/SkeletonPanel';
import ConfidenceBadge from '../components/ConfidenceBadge';
import ProgressTracker from '../components/ProgressTracker';
import type { StepState } from '../components/ProgressTracker';
import { useWallet } from '../wallet/WalletContext';
import { createAnalyzeStreamParser, type AnalyzeStreamEvent } from './AnalyzeView.stream.js';
import styles from './AnalyzeView.module.css';

interface ListingResult {
  item_name: string;
  brand: string;
  condition_guess: string;
  title: string;
  description: string;
  category_suggestion: string;
  recommended_price: number;
  price_rationale: string;
  low: number | null;
  high: number | null;
  confidence: number | null;
  signals_agree: boolean | null;
  identification_reasoning: string;
  image_url: string;
  search_keywords: string[];
  sources_used: string[];
  source_breakdown: SourceBreakdownEntry[];
  error?: string;
}

interface SourceBreakdownEntry {
  source: string;
  label: string;
  count: number;
  priority: number;
  note: string;
}

const INITIAL_STEPS: StepState[] = [
  { id: 'vision',       label: 'Gemini vision identification',   status: 'idle' },
  { id: 'image_search', label: 'Reverse image search',           status: 'idle' },
  { id: 'reconcile',    label: 'Cross-referencing signals',      status: 'idle' },
  { id: 'prices',       label: 'Researching eBay sold prices',   status: 'idle' },
  { id: 'listing',      label: 'Generating eBay listing',        status: 'idle' },
];

export default function AnalyzeView() {
  const { configured, signedIn, address, useMock, fetchWithPayment } = useWallet();
  const [preview, setPreview] = useState<string | null>(null);
  const [base64, setBase64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ListingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<StepState[]>(INITIAL_STEPS);

  const [itemId, setItemId] = useState('');
  const [trackStatus, setTrackStatus] = useState<{ msg: string; ok: boolean } | null>(null);
  const [tracking, setTracking] = useState(false);

  const handleFile = (_file: File, b64: string) => {
    setBase64(b64);
    setPreview(URL.createObjectURL(_file));
    setResult(null);
    setError(null);
    setTrackStatus(null);
    setSteps(INITIAL_STEPS);
  };

  const updateStep = (id: string, patch: Partial<StepState>) => {
    setSteps(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));
  };

  const analyze = async () => {
    if (!base64) return;
    if (configured && !signedIn) {
      setError('Sign in with a wallet to pay for analysis.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setSteps(INITIAL_STEPS);

    try {
      const analyzeFetch = useMock ? fetch : fetchWithPayment;
      const resp = await analyzeFetch('/analyze-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(useMock ? { 'X-Pricer-Mock-Wallet': 'true' } : {}),
        },
        body: JSON.stringify({ image_base64: base64 }),
      });

      if (!resp.ok) {
        const msg = resp.status === 402
          ? 'Payment required. This endpoint requires x402 USDC payment.'
          : `Request failed (${resp.status})`;
        setError(msg);
        return;
      }

      if (!resp.body) {
        setError('Streaming response was empty.');
        return;
      }

      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      const eventQueue: AnalyzeStreamEvent[] = [];
      const parser = createAnalyzeStreamParser((event) => {
        eventQueue.push(event);
      });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        parser.push(decoder.decode(value, { stream: true }));
        await drainAnalyzeEvents(eventQueue, updateStep, setResult, setError);
      }
      parser.push(decoder.decode());
      parser.flush();
      await drainAnalyzeEvents(eventQueue, updateStep, setResult, setError);
    } catch {
      setError(configured ? 'Payment failed. Try signing in again.' : 'Network error. Is the server running?');
    } finally {
      setLoading(false);
    }
  };

  const trackItem = async () => {
    if (!result || !itemId.trim()) return;
    setTracking(true);
    try {
      const resp = await fetch('/track-item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_id: itemId.trim(),
          title: result.title || result.item_name,
          recommended_price: result.recommended_price,
          image_url: result.image_url || '',
          notes: result.price_rationale || '',
        }),
      });
      if (resp.ok) {
        setTrackStatus({ msg: `Item ${itemId.trim()} is now tracked.`, ok: true });
      } else {
        setTrackStatus({ msg: 'Failed to track item.', ok: false });
      }
    } catch {
      setTrackStatus({ msg: 'Network error.', ok: false });
    } finally {
      setTracking(false);
    }
  };

  const priceRange = result && result.low != null && result.high != null
    ? `$${result.low} – $${result.high}`
    : '';

  const showProgress = loading || (steps.some(s => s.status !== 'idle') && !result && !error);
  const walletReady = !configured || signedIn;

  return (
    <div className={styles.layout}>
      {/* Left column */}
      <div className={styles.leftCol}>
        <ImageDropZone onFile={handleFile} preview={preview} disabled={loading} />

        <button
          className={styles.analyzeBtn}
          onClick={analyze}
          disabled={!base64 || loading || !walletReady}
        >
          {loading ? (
            <span className={styles.analyzing} aria-live="polite">
              <span className={styles.dots} aria-hidden="true">
                <span className={styles.dot} />
                <span className={styles.dot} />
                <span className={styles.dot} />
              </span>
              <span className={styles.analyzingLabel}>Analyzing</span>
            </span>
          ) : 'Analyze Item'}
        </button>

        <p className={styles.walletNote}>
          {useMock
            ? 'Local test wallet mode is on. Analysis runs without auth or payment.'
            : configured
            ? signedIn
              ? `Wallet connected ${address ? `(${address.slice(0, 6)}…${address.slice(-4)})` : ''}. Paid analysis will retry automatically.`
              : 'Sign in with a wallet to unlock paid analysis.'
            : 'Wallet sign-in is not configured here, so analysis runs without x402 payment.'}
        </p>

        {result && (
          <div className={styles.trackSection}>
            <span className={styles.sectionLabel}>Track this listing</span>
            <div className={styles.fieldGroup}>
              <label htmlFor="item-id" className={styles.fieldLabel}>eBay Item ID</label>
              <input
                id="item-id"
                className={styles.input}
                type="text"
                placeholder="e.g. 123456789012"
                value={itemId}
                onChange={(e) => setItemId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && trackItem()}
              />
            </div>
            <button
              className={styles.trackBtn}
              onClick={trackItem}
              disabled={!itemId.trim() || tracking}
            >
              {tracking ? 'Tracking...' : 'Track This Item'}
            </button>
            {trackStatus && (
              <p className={`${styles.trackStatus} ${trackStatus.ok ? styles.trackStatusOk : styles.trackStatusError}`}>
                {trackStatus.msg}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Right column */}
      <div className={styles.rightCol}>
        {error && (
          <div className={styles.errorMsg}>{error}</div>
        )}

        {showProgress && !result && !error && (
          <ProgressTracker steps={steps} />
        )}

        {!loading && !result && !error && !showProgress && (
          <>
            <SkeletonPanel variant="price" />
            <SkeletonPanel lines={1} />
            <SkeletonPanel lines={2} />
            <SkeletonPanel lines={2} />
            <SkeletonPanel lines={3} />
          </>
        )}

        {result && !error && (
          <>
            {/* Item identity */}
            <div className={styles.itemHeader}>
              <h2 className={styles.itemName}>
                {result.brand && result.brand !== 'Unknown' ? `${result.brand} ` : ''}{result.item_name}
              </h2>
              {result.condition_guess && (
                <span className={styles.itemMeta}>{result.condition_guess} condition</span>
              )}
              {result.confidence != null && result.signals_agree != null && (
                <ConfidenceBadge
                  confidence={result.confidence}
                  signalsAgree={result.signals_agree}
                  reasoning={result.identification_reasoning}
                  animDelay={100}
                />
              )}
            </div>

            {/* Recommended price — the hero */}
            <OutputPanel
              label="Recommended Price"
              value={result.recommended_price ? `$${result.recommended_price}` : ''}
              variant="price"
              animDelay={150}
            />

            {/* Price range */}
            {priceRange && (
              <div className={styles.fieldGroup}>
                <span className={styles.fieldLabel}>Price Range Found</span>
                <span className={styles.priceRange}>{priceRange}</span>
              </div>
            )}

            {(result.sources_used.length > 0 || result.source_breakdown.length > 0) && (
              <div className={styles.evidenceBlock}>
                <div className={styles.fieldGroup}>
                  <span className={styles.fieldLabel}>Marketplaces Used</span>
                  <div className={styles.sourceChips}>
                    {result.source_breakdown.length > 0
                      ? result.source_breakdown.map((source) => (
                          <span key={source.source} className={styles.sourceChip}>
                            <span className={styles.sourceName}>{source.label}</span>
                            <span className={styles.sourceWeight}>w{source.priority}</span>
                          </span>
                        ))
                      : result.sources_used.map((source) => (
                          <span key={source} className={styles.sourceChip}>
                            <span className={styles.sourceName}>{source}</span>
                          </span>
                        ))}
                  </div>
                </div>

                {result.source_breakdown.length > 0 && (
                  <div className={styles.fieldGroup}>
                    <span className={styles.fieldLabel}>Marketplace Breakdown</span>
                    <div className={styles.breakdownList}>
                      {result.source_breakdown.map((source) => (
                        <div key={source.source} className={styles.breakdownItem}>
                          <div className={styles.breakdownTopRow}>
                            <span className={styles.breakdownLabel}>
                              {source.label}
                              <span className={styles.breakdownWeight}>w{source.priority}</span>
                            </span>
                            <span className={styles.breakdownCount}>{source.count} hits</span>
                          </div>
                          {source.note && (
                            <div className={styles.breakdownNote}>{source.note}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Listing fields */}
            <OutputPanel
              label="Suggested eBay Title"
              value={result.title}
              variant="copyable"
              animDelay={200}
            />
            <OutputPanel
              label="Description"
              value={result.description}
              variant="textarea"
              animDelay={250}
            />
            <OutputPanel
              label="Category"
              value={result.category_suggestion}
              animDelay={300}
            />

            {/* Published image URL */}
            {result.image_url && (
              <div className={styles.imageUrlRow}>
                <span className={styles.imageUrlLabel}>Image URL</span>
                <a
                  href={result.image_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.imageUrlLink}
                >
                  {result.image_url}
                </a>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function buildDetail(event: AnalyzeStreamEvent): string {
  if (!event.data || event.status !== 'done') return '';
  const d = event.data;
  if (event.step === 'vision') return `${d.brand ?? ''} ${d.item_name ?? ''}`.trim();
  if (event.step === 'image_search') return `${d.hits ?? 0} visual matches`;
  if (event.step === 'reconcile') {
    const pct = d.confidence != null ? `${Math.round(Number(d.confidence) * 100)}% confidence` : '';
    return pct;
  }
  if (event.step === 'prices') {
    const rec = d.recommended != null ? `$${d.recommended} recommended` : '';
    return rec;
  }
  return '';
}

function isStepStatus(status: unknown): status is StepState['status'] {
  return status === 'idle' || status === 'running' || status === 'done' || status === 'error';
}

async function drainAnalyzeEvents(
  eventQueue: AnalyzeStreamEvent[],
  updateStep: (id: string, patch: Partial<StepState>) => void,
  setResult: (result: ListingResult) => void,
  setError: (error: string) => void,
) {
  while (eventQueue.length > 0) {
    const event = eventQueue.shift()!;

    if (event.step === 'result') {
      const data = event.data as unknown as ListingResult;
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } else if (event.step && isStepStatus(event.status)) {
      const detail = buildDetail(event);
      updateStep(event.step, {
        status: event.status,
        ...(event.label ? { label: event.label } : {}),
        ...(detail ? { detail } : {}),
      });
    }

    await nextPaint();
  }
}

function nextPaint() {
  return new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve());
  });
}
