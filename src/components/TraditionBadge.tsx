import { HADITH_TRADITIONS, TraditionMark, type HadithTradition } from '@/components/marks';
import { cn } from '@/lib/utils';

interface TraditionBadgeProps {
    tradition: string;
    size?: 'sm' | 'md';
}

/**
 * Tradition, parallel-type and isra'iliyyat labels (DESIGN.md §Tradition marks, §Badges). The four hadith traditions
 * show their mark before the name; every other value is muted text. No colour distinguishes any of them.
 */

// Display names for comparative-religion entries whose stored key differs from how they are written.
const TRADITION_LABELS: Record<string, string> = {
    JUDAISM: 'Judaism',
    CHRISTIANITY: 'Christianity',
    ZOROASTRIANISM: 'Zoroastrianism',
    MANDAEISM: 'Mandaeism',
    SABIANISM: 'Sabianism',
    MANICHAEISM: 'Manichaeism',
    YAZIDISM: 'Yazidism',
    SIKHISM: 'Sikhism',
    CANAANITE: 'Canaanite',
    MESOPOTAMIAN: 'Mesopotamian',
    SUMERIAN: 'Sumerian',
    AZTEC: 'Aztec',
    MAYA: 'Maya',
    BAHAI: 'Baháʼí Faith',
    'BAHAI FAITH': 'Baháʼí Faith',
    'AKAN RELIGION': 'Akan (Onyame)',
    AKAN: 'Akan (Onyame)',
    YORUBA: 'Yoruba (Olodumare)',
    IGBO: 'Igbo (Chukwu)',
    DINKA: 'Dinka (Nhialic)',
    ZULU: 'Zulu (uNkulunkulu)',
    ATENISM: 'Atenism (Ancient Egypt)',
    'ANCIENT EGYPTIAN': 'Ancient Egyptian',
    TENGRISM: 'Tengrism',
    TENGRIISM: 'Tengrism',
    LAKOTA: 'Lakota (Wakan Tanka)',
    INCA: 'Inca (Inti)',
    MAORI: 'Māori',
    'VEDIC RELIGION': 'Vedic Religion',
    BRAHMO: 'Brahmo Samaj',
    'NATIVE AMERICAN': 'Native American',
    'INDIGENOUS AUSTRALIAN': 'Indigenous Australian',
};

const PARALLEL_TYPE_LABELS: Record<string, string> = {
    CONDEMNATION: 'Condemnation',
    CULTURAL_BLEED: 'Cultural Crossover',
    SHARED_SOURCE: 'Shared Source',
    DIRECT_BORROWING: 'Direct Borrowing',
    APOLOGETIC: 'Apologetic',
    DISPUTED: 'Disputed',
};

const ISRA_STATUS_LABELS: Record<string, string> = {
    MUWAFIQ: 'Muwafiq (Consistent)',
    MUKHALIF: 'Mukhalif (Contrary)',
    MASKUT_ANHU: 'Maskut Anhu (neither affirmed nor denied)',
    NONE: 'Not Classified',
};

function hadithTradition(value: string): HadithTradition | undefined {
    return HADITH_TRADITIONS.find((name) => name.toUpperCase() === value.toUpperCase());
}

export function TraditionBadge({ tradition, size = 'sm' }: TraditionBadgeProps) {
    const known = hadithTradition(tradition);
    const textSize = size === 'sm' ? 'text-sm leading-5' : 'text-base';
    if (known) {
        return (
            <span className={cn('inline-flex items-center gap-2 whitespace-nowrap font-medium text-ink', textSize)}>
                <TraditionMark tradition={known} decorative />
                {known}
            </span>
        );
    }
    const key = tradition.toUpperCase();
    const label = TRADITION_LABELS[key] ?? tradition;
    return <span className={cn('inline-block text-ink-muted', textSize)}>{label}</span>;
}

export function ParallelTypeBadge({ type }: { type: string; size?: 'sm' | 'md' }) {
    return <span className="type-label inline-block">{PARALLEL_TYPE_LABELS[type] ?? type}</span>;
}

export function IsraIliyyatBadge({ status }: { status: string; size?: 'sm' | 'md' }) {
    return <span className="type-label inline-block">{ISRA_STATUS_LABELS[status] ?? ISRA_STATUS_LABELS.NONE}</span>;
}
