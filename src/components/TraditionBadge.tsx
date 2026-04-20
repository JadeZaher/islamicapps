interface TraditionBadgeProps {
    tradition: string;
    size?: 'sm' | 'md';
}

type StyleEntry = { bg: string; text: string; border: string; label: string };

// ─── Known tradition styles (keyed by UPPERCASE name) ───────────────────────
// Organized by cultural/geographic cluster for visual grouping.
// Any tradition not listed falls through to dynamicStyle().
const TRADITION_STYLES: Record<string, StyleEntry> = {
    // Abrahamic & Near Eastern
    JUDAISM: { bg: 'bg-amber-500/20', text: 'text-amber-300', border: 'border-amber-500/30', label: 'Judaism' },
    CHRISTIANITY: { bg: 'bg-sky-500/20', text: 'text-sky-300', border: 'border-sky-500/30', label: 'Christianity' },
    ZOROASTRIANISM: { bg: 'bg-orange-500/20', text: 'text-orange-300', border: 'border-orange-500/30', label: 'Zoroastrianism' },
    MANDAEISM: { bg: 'bg-teal-500/20', text: 'text-teal-300', border: 'border-teal-500/30', label: 'Mandaeism' },
    SABIANISM: { bg: 'bg-teal-500/20', text: 'text-teal-300', border: 'border-teal-500/30', label: 'Sabianism' },
    MANICHAEISM: { bg: 'bg-indigo-500/20', text: 'text-indigo-300', border: 'border-indigo-500/30', label: 'Manichaeism' },
    YAZIDISM: { bg: 'bg-indigo-500/20', text: 'text-indigo-300', border: 'border-indigo-500/30', label: 'Yazidism' },

    // Abrahamic derivative / modern
    SIKHISM: { bg: 'bg-yellow-500/20', text: 'text-yellow-300', border: 'border-yellow-500/30', label: 'Sikhism' },
    BAHAI: { bg: 'bg-rose-500/20', text: 'text-rose-300', border: 'border-rose-500/30', label: 'Baháʼí Faith' },
    'BAHAI FAITH': { bg: 'bg-rose-500/20', text: 'text-rose-300', border: 'border-rose-500/30', label: 'Baháʼí Faith' },

    // African traditional (monotheistic / henotheistic supreme creator)
    'AKAN RELIGION': { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/30', label: 'Akan (Onyame)' },
    AKAN: { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/30', label: 'Akan (Onyame)' },
    YORUBA: { bg: 'bg-lime-500/20', text: 'text-lime-300', border: 'border-lime-500/30', label: 'Yoruba (Olodumare)' },
    IGBO: { bg: 'bg-green-500/20', text: 'text-green-300', border: 'border-green-500/30', label: 'Igbo (Chukwu)' },
    DINKA: { bg: 'bg-cyan-500/20', text: 'text-cyan-300', border: 'border-cyan-500/30', label: 'Dinka (Nhialic)' },
    ZULU: { bg: 'bg-green-600/20', text: 'text-green-400', border: 'border-green-600/30', label: 'Zulu (uNkulunkulu)' },
    ATENISM: { bg: 'bg-yellow-600/20', text: 'text-yellow-400', border: 'border-yellow-600/30', label: 'Atenism (Ancient Egypt)' },
    'ANCIENT EGYPTIAN': { bg: 'bg-yellow-600/20', text: 'text-yellow-400', border: 'border-yellow-600/30', label: 'Ancient Egyptian' },

    // Central Asian / Eurasian steppe
    TENGRISM: { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/30', label: 'Tengrism' },
    TENGRIISM: { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/30', label: 'Tengrism' },

    // Ancient Near East / Semitic
    CANAANITE: { bg: 'bg-stone-500/20', text: 'text-stone-300', border: 'border-stone-500/30', label: 'Canaanite' },
    MESOPOTAMIAN: { bg: 'bg-amber-700/20', text: 'text-amber-400', border: 'border-amber-700/30', label: 'Mesopotamian' },
    SUMERIAN: { bg: 'bg-amber-700/20', text: 'text-amber-400', border: 'border-amber-700/30', label: 'Sumerian' },

    // Indigenous / Traditional — Americas
    'NATIVE AMERICAN': { bg: 'bg-red-700/20', text: 'text-red-400', border: 'border-red-700/30', label: 'Native American' },
    LAKOTA: { bg: 'bg-red-700/20', text: 'text-red-400', border: 'border-red-700/30', label: 'Lakota (Wakan Tanka)' },
    AZTEC: { bg: 'bg-red-600/20', text: 'text-red-300', border: 'border-red-600/30', label: 'Aztec' },
    MAYA: { bg: 'bg-red-600/20', text: 'text-red-300', border: 'border-red-600/30', label: 'Maya' },
    INCA: { bg: 'bg-orange-700/20', text: 'text-orange-400', border: 'border-orange-700/30', label: 'Inca (Inti)' },

    // Indigenous — Pacific & Oceania
    'INDIGENOUS AUSTRALIAN': { bg: 'bg-amber-800/20', text: 'text-amber-500', border: 'border-amber-800/30', label: 'Indigenous Australian' },
    MAORI: { bg: 'bg-emerald-700/20', text: 'text-emerald-400', border: 'border-emerald-700/30', label: 'Māori' },

    // South / East Asian
    'VEDIC RELIGION': { bg: 'bg-fuchsia-500/20', text: 'text-fuchsia-300', border: 'border-fuchsia-500/30', label: 'Vedic Religion' },
    BRAHMO: { bg: 'bg-fuchsia-500/20', text: 'text-fuchsia-300', border: 'border-fuchsia-500/30', label: 'Brahmo Samaj' },
};

// ─── Fallback palette — cycles through distinct hues for unknown traditions ──
// Deterministic: same tradition name always maps to the same color.
const FALLBACK_PALETTE: Array<{ bg: string; text: string; border: string }> = [
    { bg: 'bg-pink-500/20', text: 'text-pink-300', border: 'border-pink-500/30' },
    { bg: 'bg-cyan-600/20', text: 'text-cyan-400', border: 'border-cyan-600/30' },
    { bg: 'bg-lime-600/20', text: 'text-lime-400', border: 'border-lime-600/30' },
    { bg: 'bg-indigo-600/20', text: 'text-indigo-400', border: 'border-indigo-600/30' },
    { bg: 'bg-rose-600/20', text: 'text-rose-400', border: 'border-rose-600/30' },
    { bg: 'bg-teal-600/20', text: 'text-teal-400', border: 'border-teal-600/30' },
    { bg: 'bg-indigo-600/20', text: 'text-indigo-400', border: 'border-indigo-600/30' },
    { bg: 'bg-orange-600/20', text: 'text-orange-400', border: 'border-orange-600/30' },
];

function hashString(s: string): number {
    let hash = 0;
    for (let i = 0; i < s.length; i++) {
        hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
    }
    return hash;
}

function dynamicStyle(tradition: string): StyleEntry {
    const palette = FALLBACK_PALETTE[hashString(tradition) % FALLBACK_PALETTE.length];
    return { ...palette, label: tradition };
}

// ─── Badge primitives ────────────────────────────────────────────────────────

const PARALLEL_TYPE_STYLES: Record<string, StyleEntry> = {
    CONDEMNATION: { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/30', label: 'Condemnation' },
    CULTURAL_BLEED: { bg: 'bg-teal-500/20', text: 'text-teal-300', border: 'border-teal-500/30', label: 'Cultural Crossover' },
    SHARED_SOURCE: { bg: 'bg-green-500/20', text: 'text-green-300', border: 'border-green-500/30', label: 'Shared Source' },
    DIRECT_BORROWING: { bg: 'bg-yellow-500/20', text: 'text-yellow-300', border: 'border-yellow-500/30', label: 'Direct Borrowing' },
    APOLOGETIC: { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/30', label: 'Apologetic' },
    DISPUTED: { bg: 'bg-gray-500/20', text: 'text-gray-300', border: 'border-gray-500/30', label: 'Disputed' },
};

const ISRA_STATUS_STYLES: Record<string, StyleEntry> = {
    MUWAFIQ: { bg: 'bg-green-500/20', text: 'text-green-300', border: 'border-green-500/30', label: 'Muwafiq (Consistent)' },
    MUKHALIF: { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/30', label: 'Mukhalif (Contrary)' },
    MASKUT_ANHU: { bg: 'bg-gray-500/20', text: 'text-gray-300', border: 'border-gray-500/30', label: 'Maskut Anhu (Unknown)' },
    NONE: { bg: 'bg-slate-700/40', text: 'text-slate-400', border: 'border-slate-600/30', label: 'Not Classified' },
};

function Badge({ style, size = 'sm' }: { style: StyleEntry; size?: 'sm' | 'md' }) {
    return (
        <span
            className={`inline-block px-2 py-0.5 rounded border ${style.bg} ${style.text} ${style.border} ${
                size === 'sm' ? 'text-xs' : 'text-sm'
            } font-medium`}
        >
            {style.label}
        </span>
    );
}

// ─── Exports ─────────────────────────────────────────────────────────────────

export function TraditionBadge({ tradition, size = 'sm' }: TraditionBadgeProps) {
    const key = tradition.toUpperCase();
    const style = TRADITION_STYLES[key] ?? dynamicStyle(tradition);
    return <Badge style={style} size={size} />;
}

export function ParallelTypeBadge({ type, size = 'sm' }: { type: string; size?: 'sm' | 'md' }) {
    const style = PARALLEL_TYPE_STYLES[type] ?? dynamicStyle(type);
    return <Badge style={style} size={size} />;
}

export function IsraIliyyatBadge({ status, size = 'sm' }: { status: string; size?: 'sm' | 'md' }) {
    const style = ISRA_STATUS_STYLES[status] ?? ISRA_STATUS_STYLES['NONE'];
    return <Badge style={style} size={size} />;
}
