'use client';

import ForceGraph2D from 'react-force-graph-2d';
import { useRef, useEffect } from 'react';


interface Node {
    id: string;
    name_arabic: string;
    name_english: string;
    reliability: string;
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
    onNodeClick: (node: Node) => void;
    onChainClick?: (edges: Edge[]) => void;
}

export function IsnadGraph({ nodes, edges, onNodeClick, onChainClick }: IsnadGraphProps) {
    const fgRef = useRef<any>();

    // Reliability color mapping
    const getNodeColor = (reliability: string) => {
        switch (reliability) {
            case 'THIQA':
                return '#10b981'; // Green
            case 'SADUQ':
                return '#fbbf24'; // Yellow
            case 'DAIF':
            case 'KADHAB':
                return '#ef4444'; // Red
            case 'MAJHUL':
                return '#9ca3af'; // Gray
            default:
                return '#6b7280';
        }
    };

    // Format graph data for react-force-graph-2d
    const graphData = {
        nodes: nodes.map((n) => ({
            id: n.id,
            name: n.name_english,
            nameArabic: n.name_arabic,
            reliability: n.reliability,
            deathYear: n.death_year_hijri,
            isProphet: n.is_prophet,
            color: getNodeColor(n.reliability),
        })),
        links: edges.map((e) => ({
            source: e.source,
            target: e.target,
            status: e.status,
        })),
    };

    useEffect(() => {
        if (fgRef.current) {
            // Center the graph
            fgRef.current.zoomToFit(400);
        }
    }, [nodes, edges]);

    return (
        <div className="w-full h-full bg-slate-950 rounded-lg border border-slate-800">
            <ForceGraph2D
                ref={fgRef}
                graphData={graphData}
                nodeLabel={(node: any) => `
          <div style="background: rgba(0,0,0,0.9); padding: 8px 12px; border-radius: 6px; color: white; font-family: sans-serif;">
            <div style="font-weight: 600; margin-bottom: 4px;">${node.name}</div>
            <div style="font-size: 12px; color: #cbd5e1;">${node.nameArabic}</div>
            ${node.deathYear ? `<div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">d. ${node.deathYear} AH</div>` : ''}
          </div>
        `}
                nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                    const label = node.name;
                    const fontSize = 12 / globalScale;
                    ctx.font = `${fontSize}px Inter, sans-serif`;

                    // Draw node circle
                    const nodeSize = node.isProphet ? 12 : 8;
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, nodeSize, 0, 2 * Math.PI);
                    ctx.fillStyle = node.color;
                    ctx.fill();

                    // Prophet gets gold border
                    if (node.isProphet) {
                        ctx.strokeStyle = '#fbbf24';
                        ctx.lineWidth = 2 / globalScale;
                        ctx.stroke();
                    }

                    // Draw label
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'top';
                    ctx.fillStyle = '#ffffff';
                    ctx.fillText(label, node.x, node.y + nodeSize + 4);
                }}
                linkColor={() => '#475569'}
                linkWidth={2}
                linkDirectionalArrowLength={6}
                linkDirectionalArrowRelPos={1}
                linkDirectionalArrowColor={() => '#64748b'}
                onNodeClick={(node: any) => {
                    const originalNode = nodes.find((n) => n.id === node.id);
                    if (originalNode) {
                        onNodeClick(originalNode);
                    }
                }}
                cooldownTicks={100}
                onEngineStop={() => {
                    if (fgRef.current) {
                        fgRef.current.zoomToFit(400);
                    }
                }}
            />
        </div>
    );
}
