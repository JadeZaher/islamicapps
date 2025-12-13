'use client';

interface ReliabilityBadgeProps {
    reliability: 'THIQA' | 'SADUQ' | 'DAIF' | 'MAJHUL' | 'KADHAB';
    className?: string;
}

const RELIABILITY_CONFIG = {
    THIQA: {
        label: 'Thiqah (Trustworthy)',
        bgColor: 'bg-emerald-500/20',
        borderColor: 'border-emerald-500/40',
        textColor: 'text-emerald-300',
        icon: '✓',
    },
    SADUQ: {
        label: 'Saduq (Truthful)',
        bgColor: 'bg-blue-500/20',
        borderColor: 'border-blue-500/40',
        textColor: 'text-blue-300',
        icon: '◐',
    },
    DAIF: {
        label: 'Daif (Weak)',
        bgColor: 'bg-yellow-500/20',
        borderColor: 'border-yellow-500/40',
        textColor: 'text-yellow-300',
        icon: '⚠',
    },
    MAJHUL: {
        label: 'Majhul (Unknown)',
        bgColor: 'bg-gray-500/20',
        borderColor: 'border-gray-500/40',
        textColor: 'text-gray-300',
        icon: '?',
    },
    KADHAB: {
        label: 'Kadhab (Liar)',
        bgColor: 'bg-red-500/20',
        borderColor: 'border-red-500/40',
        textColor: 'text-red-300',
        icon: '✕',
    },
};

export function ReliabilityBadge({ reliability, className = '' }: ReliabilityBadgeProps) {
    const config = RELIABILITY_CONFIG[reliability];

    return (
        <div
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border backdrop-blur-sm 
                transition-all duration-300 hover:scale-105 ${config.bgColor} ${config.borderColor} ${className}`}
        >
            <span className={`text-lg ${config.textColor}`}>{config.icon}</span>
            <span className={`font-semibold ${config.textColor}`}>{config.label}</span>
        </div>
    );
}
