export function formatTrackedDate(iso) {
  try {
    const parsed = new Date(iso);
    if (Number.isNaN(parsed.getTime())) return iso;
    return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return iso;
  }
}

export function driftLabel(drift) {
  if (drift === 0) return '—';
  return drift > 0 ? `+${drift.toFixed(1)}%` : `${drift.toFixed(1)}%`;
}

export function thumbnailAlt(title) {
  return title ? `Thumbnail for ${title}` : 'Tracked item thumbnail';
}
