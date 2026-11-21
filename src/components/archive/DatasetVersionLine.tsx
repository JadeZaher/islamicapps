import { versionText } from '@/lib/citation/cite';
import { loadDatasetVersion } from './report-data';
import './archive.css';

/** Unobtrusive line naming the dataset version a page was built from. */
export async function DatasetVersionLine({ className }: { className?: string }) {
  const version = await loadDatasetVersion();
  const text = versionText(version ? { label: version.label, shortId: version.shortId } : null);
  return (
    <p data-dataset-version={version?.id ?? ''} className={`text-xs text-[color:var(--archive-faint)] ${className ?? ''}`}>
      Built from {text}
      {version && version.releaseClass !== 'release' ? ', a preview (non-release) version' : ''}.
    </p>
  );
}
