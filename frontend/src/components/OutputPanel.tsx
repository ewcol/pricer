import { useState } from 'react';
import styles from './OutputPanel.module.css';

interface Props {
  label: string;
  value: string;
  variant?: 'default' | 'price' | 'copyable' | 'textarea';
  animDelay?: number;
}

export default function OutputPanel({ label, value, variant = 'default', animDelay = 0 }: Props) {
  const [copied, setCopied] = useState(false);
  const isEmpty = !value;
  const display = value || '—';

  const handleCopy = () => {
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  if (variant === 'textarea') {
    return (
      <div className={styles.wrapper}>
        <span className={styles.label}>{label}</span>
        <div className={styles.copyable}>
          <textarea
            className={styles.textarea}
            style={{ animationDelay: `${animDelay}ms` }}
            value={display}
            readOnly
            rows={4}
          />
          {value && (
            <button
              className={`${styles.copyBtn} ${copied ? styles.copyBtnDone : ''}`}
              onClick={handleCopy}
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}
        </div>
      </div>
    );
  }

  if (variant === 'copyable') {
    return (
      <div className={styles.wrapper}>
        <span className={styles.label}>{label}</span>
        <div className={styles.copyable}>
          <div
            className={`${styles.panel} ${isEmpty ? styles.panelEmpty : ''}`}
            style={{ animationDelay: `${animDelay}ms` }}
          >
            {display}
          </div>
          {value && (
            <button
              className={`${styles.copyBtn} ${copied ? styles.copyBtnDone : ''}`}
              onClick={handleCopy}
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <span className={styles.label}>{label}</span>
      <div
        className={`${styles.panel} ${isEmpty ? styles.panelEmpty : ''} ${variant === 'price' ? styles.panelPrice : ''}`}
        style={{ animationDelay: `${animDelay}ms` }}
      >
        {display}
      </div>
    </div>
  );
}
