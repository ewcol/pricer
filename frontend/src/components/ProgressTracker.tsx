import styles from './ProgressTracker.module.css';

export interface StepState {
  id: string;
  label: string;
  status: 'idle' | 'running' | 'done' | 'error';
  detail?: string;
}

interface Props {
  steps: StepState[];
}

export default function ProgressTracker({ steps }: Props) {
  return (
    <div className={styles.tracker}>
      {steps.map((step, i) => (
        <div key={step.id} className={`${styles.step} ${styles[step.status]}`}>
          <div className={styles.spine}>
            <div className={styles.dot}>
              {step.status === 'done' && (
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
                  <path d="M2 5l2.5 2.5L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              {step.status === 'running' && <span className={styles.pulse} aria-hidden="true" />}
            </div>
            {i < steps.length - 1 && <div className={styles.line} />}
          </div>
          <div className={styles.content}>
            <span className={styles.label}>{step.label}</span>
            {step.detail && <span className={styles.detail}>{step.detail}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
