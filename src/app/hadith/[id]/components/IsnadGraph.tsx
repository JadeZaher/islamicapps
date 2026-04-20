'use client';

import dynamic from 'next/dynamic';
import { useRef, useEffect, useCallback, useMemo } from 'react';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface Node {
    id: string;
    name_arabic: string;
    name_english: string;
    reliability: string;
    tabaqah?: string;
    death_year_hijri?: number;
    is_prophet?: boolean;
}

interface Edge {
    source: string;
    target: string;
    status: string;
}

interface IsnadGraphProps {
    nodes: Node[];
    edges: Edge[];
    hadithTextArabic?: string | null;
    hadithTextEnglish?: string | null;
}

const RELIABILITY_COLORS: Record<string, string> = {
    THIQA: '#10b981',
    SADUQ: '#eab308',
    DAIF: '#ef4444',
    KADHAB: '#ef4444',
    MAJHUL: '#9ca3af',
};

const RELIABILITY_LABELS: Record<string, string> = {
    THIQA: 'Trustworthy',
    SADUQ: 'Truthful',
    DAIF: 'Weak',
    KADHAB: 'Fabricator',
    MAJHUL: 'Unknown',
};

const HADITH_NODE_ID = '__hadith_matn__';

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
    const words = text.split(/\s+/);
    const lines: string[] = [];
    let cur = '';
    for (const w of words) {
        const test = cur ? `${cur} ${w}` : w;
        if (ctx.measureText(test).width > maxWidth && cur) {
            lines.push(cur);
            cur = w;
        } else {
            cur = test;
        }
    }
    if (cur) lines.push(cur);
    return lines;
}

export function IsnadGraph({
    nodes,
    edges,
    hadithTextArabic,
    hadithTextEnglish,
}: IsnadGraphProps) {
    const fgRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const hasZoomed = useRef(false);

    const getNodeColor = (r: string) => RELIABILITY_COLORS[r] || '#6b7280';

    const graphData = useMemo(() => {
        const gNodes: any[] = nodes.map((n) => ({
            id: n.id,
            name: n.name_english || '',
            nameArabic: n.name_arabic || '',
            reliability: n.reliability,
            tabaqah: n.tabaqah,
            deathYear: n.death_year_hijri,
            isProphet: n.is_prophet || n.tabaqah === 'PROPHET',
            isHadithNode: false,
            color: getNodeColor(n.reliability),
        }));

        const gLinks: any[] = edges.map((e) => ({
            source: e.source,
            target: e.target,
            status: e.status,
        }));

        if (hadithTextArabic || hadithTextEnglish) {
            gNodes.push({
                id: HADITH_NODE_ID,
                name: hadithTextEnglish || '',
                nameArabic: hadithTextArabic || '',
                reliability: '',
                tabaqah: '',
                deathYear: null,
                isProphet: false,
                isHadithNode: true,
                color: '#f59e0b',
            });

            const prophet = nodes.find((n) => n.is_prophet || n.tabaqah === 'PROPHET');
            if (prophet) {
                gLinks.push({ source: prophet.id, target: HADITH_NODE_ID, status: 'connected' });
            } else {
                const srcSet = new Set(edges.map((e) => e.source));
                const tgtSet = new Set(edges.map((e) => e.target));
                const root = nodes.find((n) => tgtSet.has(n.id) && !srcSet.has(n.id)) || nodes[0];
                if (root) {
                    gLinks.push({ source: root.id, target: HADITH_NODE_ID, status: 'connected' });
                }
            }
        }

        return { nodes: gNodes, links: gLinks };
    }, [nodes, edges, hadithTextArabic, hadithTextEnglish]);

    /** Simple zoom-to-fit with a max zoom cap to prevent over-zooming on narrow chains. */
    const doFit = useCallback(() => {
        const fg = fgRef.current;
        if (!fg) return;
        fg.zoomToFit(300, 30);
        // After the fit animation, cap the zoom
        setTimeout(() => {
            const z = fg.zoom();
            if (z > 1.8) {
                fg.zoom(1.8, 200);
            }
        }, 350);
    }, []);

    // Initial fit after simulation has had time to compute positions
    useEffect(() => {
        hasZoomed.current = false;
        const t = setTimeout(() => {
            doFit();
            hasZoomed.current = true;
        }, 1500);
        return () => clearTimeout(t);
    }, [nodes, edges, doFit]);

    const handleEngineStop = useCallback(() => {
        // Only auto-fit once; after that the user may have panned/zoomed manually
        if (!hasZoomed.current) {
            doFit();
            hasZoomed.current = true;
        }
    }, [doFit]);

    const handleNodeClick = useCallback((node: any) => {
        if (node.isHadithNode) return;
        window.open(`/narrator/${node.id}`, '_blank');
    }, []);

    const handleNodeHover = useCallback((node: any) => {
        const canvas = containerRef.current?.querySelector('canvas');
        if (canvas) canvas.style.cursor = node && !node.isHadithNode ? 'pointer' : 'default';
    }, []);

    // ── Link renderer ──
    const linkCanvasObject = useCallback(
        (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const s = link.source;
            const t = link.target;
            if (!s || !t || typeof s.x !== 'number') return;

            const isOk = link.status === 'connected';
            const lw = Math.max(1.5, 2.5 / globalScale);

            // Line
            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(t.x, t.y);
            if (!isOk) ctx.setLineDash([6 / globalScale, 4 / globalScale]);
            ctx.strokeStyle = isOk ? '#94a3b8' : '#dc2626';
            ctx.lineWidth = lw;
            ctx.stroke();
            ctx.setLineDash([]);

            // Arrow head
            const dx = t.x - s.x;
            const dy = t.y - s.y;
            const len = Math.sqrt(dx * dx + dy * dy);
            if (len < 1) return;
            const ax = s.x + dx * 0.78;
            const ay = s.y + dy * 0.78;
            const ang = Math.atan2(dy, dx);
            const aLen = Math.max(5, 8 / globalScale);
            const sp = Math.PI / 6;
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(ax - aLen * Math.cos(ang - sp), ay - aLen * Math.sin(ang - sp));
            ctx.moveTo(ax, ay);
            ctx.lineTo(ax - aLen * Math.cos(ang + sp), ay - aLen * Math.sin(ang + sp));
            ctx.strokeStyle = isOk ? '#cbd5e1' : '#ef4444';
            ctx.lineWidth = Math.max(1.2, 2 / globalScale);
            ctx.stroke();
        },
        [],
    );

    // ── Node renderer ──
    const nodeCanvasObject = useCallback(
        (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const px = (sp: number) => sp / globalScale;

            // ── Hadith matn box ──
            if (node.isHadithNode) {
                const bw = px(320);
                const pad = px(10);
                const aFs = px(13);
                const eFs = px(10);
                const lh = 1.45;

                ctx.font = `600 ${aFs}px "Amiri", serif`;
                const aLines = node.nameArabic ? wrapText(ctx, node.nameArabic, bw - pad * 2).slice(0, 3) : [];
                ctx.font = `400 ${eFs}px Inter, system-ui, sans-serif`;
                const eLines = node.name ? wrapText(ctx, node.name, bw - pad * 2).slice(0, 2) : [];

                if (aLines.length === 3) aLines[2] += '...';
                if (eLines.length === 2) eLines[1] += '...';

                const gap = aLines.length && eLines.length ? px(8) : 0;
                const th = pad * 2 + aLines.length * aFs * lh + gap + eLines.length * eFs * lh;
                const bx = node.x - bw / 2;
                const by = node.y - th / 2;
                const cr = px(6);

                // Rounded rect
                ctx.beginPath();
                ctx.moveTo(bx + cr, by);
                ctx.lineTo(bx + bw - cr, by);
                ctx.quadraticCurveTo(bx + bw, by, bx + bw, by + cr);
                ctx.lineTo(bx + bw, by + th - cr);
                ctx.quadraticCurveTo(bx + bw, by + th, bx + bw - cr, by + th);
                ctx.lineTo(bx + cr, by + th);
                ctx.quadraticCurveTo(bx, by + th, bx, by + th - cr);
                ctx.lineTo(bx, by + cr);
                ctx.quadraticCurveTo(bx, by, bx + cr, by);
                ctx.closePath();
                ctx.fillStyle = 'rgba(30,41,59,0.95)';
                ctx.fill();
                ctx.strokeStyle = '#f59e0b';
                ctx.lineWidth = px(1.5);
                ctx.stroke();

                let cy = by + pad + aFs;
                ctx.font = `600 ${aFs}px "Amiri", serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'alphabetic';
                ctx.fillStyle = '#fef3c7';
                for (const l of aLines) { ctx.fillText(l, node.x, cy); cy += aFs * lh; }

                if (aLines.length && eLines.length) {
                    cy += px(2);
                    ctx.beginPath();
                    ctx.moveTo(bx + pad, cy);
                    ctx.lineTo(bx + bw - pad, cy);
                    ctx.strokeStyle = '#475569';
                    ctx.lineWidth = px(0.5);
                    ctx.stroke();
                    cy += px(4);
                }

                cy += eFs;
                ctx.font = `400 ${eFs}px Inter, system-ui, sans-serif`;
                ctx.fillStyle = '#cbd5e1';
                for (const l of eLines) { ctx.fillText(l, node.x, cy); cy += eFs * lh; }
                return;
            }

            // ── Narrator node ──
            const isProphet = node.isProphet;
            const nr = isProphet ? px(7) : px(5);

            ctx.beginPath();
            ctx.arc(node.x, node.y, nr, 0, 2 * Math.PI);
            ctx.fillStyle = node.color;
            ctx.fill();
            if (isProphet) {
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = px(2);
                ctx.stroke();
            }

            // Arabic (above)
            if (node.nameArabic) {
                ctx.font = `600 ${px(12)}px "Amiri", serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillStyle = '#e2e8f0';
                ctx.fillText(node.nameArabic, node.x, node.y - nr - px(3));
            }

            // English (below)
            if (node.name) {
                ctx.font = `500 ${px(10)}px Inter, system-ui, sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillStyle = '#94a3b8';
                ctx.fillText(node.name, node.x, node.y + nr + px(2));
            }

            // Death year
            if (node.deathYear) {
                ctx.font = `${px(8)}px Inter, system-ui, sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillStyle = '#64748b';
                ctx.fillText(`d. ${node.deathYear} AH`, node.x, node.y + nr + (node.name ? px(15) : px(2)));
            }
        },
        [],
    );

    const nodePointerAreaPaint = useCallback(
        (node: any, color: string, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const px = (s: number) => s / globalScale;
            ctx.fillStyle = color;
            if (node.isHadithNode) {
                ctx.fillRect(node.x - px(160), node.y - px(60), px(320), px(120));
            } else {
                ctx.beginPath();
                ctx.arc(node.x, node.y, px(12), 0, 2 * Math.PI);
                ctx.fill();
            }
        },
        [],
    );

    const legendItems = useMemo(() => {
        const seen = new Set<string>();
        return nodes.map((n) => n.reliability).filter((r) => {
            if (!r || seen.has(r)) return false;
            seen.add(r);
            return true;
        }).map((r) => ({ reliability: r, color: getNodeColor(r), label: RELIABILITY_LABELS[r] || r }));
    }, [nodes]);

    return (
        <div ref={containerRef} className="w-full h-full bg-slate-950 rounded-lg border border-slate-800 relative">
            <ForceGraph2D
                ref={fgRef}
                graphData={graphData}
                dagMode="bu"
                dagLevelDistance={60}
                nodeLabel={(node: any) => {
                    if (node.isHadithNode) return '';
                    return `<div style="background:rgba(15,23,42,.95);padding:8px 14px;border-radius:8px;color:#fff;font-family:system-ui;border:1px solid rgba(100,116,139,.3);max-width:260px">
                        <div style="font-weight:600;margin-bottom:2px">${node.name || 'Unknown'}</div>
                        <div style="font-size:14px;color:#e2e8f0;font-family:'Amiri',serif;direction:rtl">${node.nameArabic || ''}</div>
                        <div style="font-size:11px;color:${node.color};margin-top:4px">${RELIABILITY_LABELS[node.reliability] || ''}</div>
                        ${node.deathYear ? `<div style="font-size:11px;color:#94a3b8;margin-top:2px">d. ${node.deathYear} AH</div>` : ''}
                    </div>`;
                }}
                nodeCanvasObject={nodeCanvasObject}
                nodePointerAreaPaint={nodePointerAreaPaint}
                linkCanvasObject={linkCanvasObject}
                linkCanvasObjectMode={() => 'replace'}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
                cooldownTicks={100}
                onEngineStop={handleEngineStop}
                d3VelocityDecay={0.3}
                minZoom={0.3}
                maxZoom={10}
            />
            {legendItems.length > 0 && (
                <div className="absolute bottom-3 left-3 bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2 flex gap-4 text-xs">
                    {legendItems.map((item) => (
                        <div key={item.reliability} className="flex items-center gap-1.5">
                            <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                            <span className="text-slate-300">{item.label}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
