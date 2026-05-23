import { useRef, useState } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import styles from './ImageDropZone.module.css';

interface Props {
  onFile: (file: File, base64: string) => void;
  preview: string | null;
  disabled?: boolean;
}

export default function ImageDropZone({ onFile, preview, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const processFile = (file: File) => {
    if (!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const raw = e.target?.result as string;
      // Strip data URL prefix to get bare base64
      const base64 = raw.split(',')[1];
      onFile(file, base64);
    };
    reader.readAsDataURL(file);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const classes = [
    styles.zone,
    dragOver ? styles.zoneDragOver : '',
    preview ? styles.zoneHasImage : '',
  ].join(' ');

  return (
    <div
      className={classes}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
    >
      {preview ? (
        <>
          <img src={preview} alt="Item to price" className={styles.preview} />
          {!disabled && (
            <>
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                className={styles.input}
                onChange={onChange}
                aria-label="Replace image"
              />
              <button
                className={styles.changeBtn}
                onClick={() => inputRef.current?.click()}
                type="button"
              >
                Change
              </button>
            </>
          )}
        </>
      ) : (
        <>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className={styles.input}
            onChange={onChange}
            aria-label="Upload item photo"
          />
          <div className={styles.prompt}>
            <svg className={styles.icon} width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
              <rect x="4" y="6" width="24" height="20" rx="2" stroke="currentColor" strokeWidth="1.5"/>
              <circle cx="11" cy="13" r="2.5" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M4 22l7-6 5 4 4-3 8 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span className={styles.promptText}>Drop photo here</span>
            <span className={styles.promptSub}>or click to browse</span>
          </div>
        </>
      )}
    </div>
  );
}
