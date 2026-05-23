import { useEffect, useState } from 'react';
import { formatWalletAddress, useWallet } from '../wallet/WalletContext';
import styles from './WalletStatus.module.css';

export default function WalletStatus() {
  const {
    configured,
    projectId,
    useMock,
    signedIn,
    address,
    signingIn,
    signingOut,
    signIn,
    signOut,
    configureWallet,
    clearWalletConfig,
  } = useWallet();
  const [error, setError] = useState<string | null>(null);
  const [setupOpen, setSetupOpen] = useState(false);
  const [draftProjectId, setDraftProjectId] = useState(projectId ?? '');
  const [draftUseMock, setDraftUseMock] = useState(useMock);

  useEffect(() => {
    if (!setupOpen) return;
    setDraftProjectId(projectId ?? '');
    setDraftUseMock(useMock);
  }, [projectId, setupOpen, useMock]);

  const openSetup = () => {
    setError(null);
    setSetupOpen(true);
  };

  const closeSetup = () => {
    setSetupOpen(false);
  };

  const saveSetup = () => {
    const trimmed = draftProjectId.trim();
    if (!trimmed && !draftUseMock) {
      setError('Enter a CDP project ID.');
      return;
    }

    setError(null);
    configureWallet({ projectId: trimmed, useMock: draftUseMock });
    setSetupOpen(false);
  };

  const handleSignIn = async () => {
    setError(null);
    try {
      await signIn('google');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in.');
    }
  };

  const handleSignOut = async () => {
    setError(null);
    try {
      await signOut();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign out.');
    }
  };

  return (
    <div className={styles.wallet}>
      <div className={styles.meta}>
        <span className={styles.label}>Wallet</span>
        <span className={styles.value}>
          {useMock
            ? 'Local test wallet active'
            : signedIn
            ? formatWalletAddress(address)
            : configured
              ? `Ready ${projectId ? `(${projectId.slice(0, 6)}…)` : ''}`
              : 'Not configured'}
        </span>
      </div>
      {useMock ? (
        <button
          className={styles.button}
          onClick={openSetup}
        >
          Change setup
        </button>
      ) : signedIn ? (
        <button
          className={styles.button}
          onClick={handleSignOut}
          disabled={signingOut}
        >
          {signingOut ? 'Signing out' : 'Sign out'}
        </button>
      ) : (
        <>
          <button
            className={styles.button}
            onClick={configured ? handleSignIn : openSetup}
            disabled={signingIn}
          >
            {signingIn ? 'Signing in' : configured ? 'Sign in with wallet' : 'Set up wallet'}
          </button>
          {configured && (
            <button
              className={styles.button}
              onClick={openSetup}
            >
              Change setup
            </button>
          )}
        </>
      )}
      {error && <span className={styles.error}>{error}</span>}

      {setupOpen && (
        <div className={styles.backdrop} role="presentation" onClick={closeSetup}>
          <div className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="wallet-setup-title" onClick={(e) => e.stopPropagation()}>
            <div className={styles.dialogHeader}>
              <div>
                <div className={styles.dialogLabel}>Wallet setup</div>
                <h2 id="wallet-setup-title" className={styles.dialogTitle}>Connect CDP from the UI</h2>
              </div>
              <button className={styles.closeBtn} onClick={closeSetup} aria-label="Close wallet setup">
                ×
              </button>
            </div>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>CDP Project ID</span>
              <input
                className={styles.input}
                value={draftProjectId}
                onChange={(e) => setDraftProjectId(e.target.value)}
                placeholder="Paste your CDP project ID"
                autoComplete="off"
                spellCheck="false"
              />
            </label>

            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={draftUseMock}
                onChange={(e) => setDraftUseMock(e.target.checked)}
              />
              <span>Use mock wallet mode for local testing</span>
            </label>

            <p className={styles.helperText}>
              This saves in your browser and unlocks wallet sign-in without editing app code.
            </p>

            <div className={styles.actions}>
              <button className={styles.secondaryButton} onClick={closeSetup}>Cancel</button>
              {configured && (
                <button className={styles.secondaryButton} onClick={clearWalletConfig}>
                  Clear
                </button>
              )}
              <button className={styles.primaryButton} onClick={saveSetup}>
                Save setup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
