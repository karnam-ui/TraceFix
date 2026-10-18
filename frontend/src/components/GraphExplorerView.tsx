import React, { useEffect, useState } from 'react'
import { GitBranch, Info, RefreshCw, ZoomIn } from 'lucide-react'
import { api } from '../api/client'
import type { GraphSummary, NeighborhoodResponse, NodeDetail } from '../types'

export const GraphExplorerView: React.FC = () => {
  const [graphs, setGraphs] = useState<GraphSummary[]>([])
  const [selectedGraph, setSelectedGraph] = useState<string>('requests_22623bd8')
  const [neighborhood, setNeighborhood] = useState<NeighborhoodResponse | null>(null)
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getGraphs()
      .then((gList) => {
        setGraphs(gList)
        if (gList.length > 0) {
          setSelectedGraph((prev) => prev || gList[0].graph_name)
        }
      })
      .catch((err) => setError(err.message))
  }, [])

  const loadGraphData = React.useCallback(async (graphName: string, entityId?: string) => {
    if (!graphName) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.getNeighborhood(graphName, entityId)
      setNeighborhood(data)
      setSelectedNode((prev) => prev || (data.nodes.length > 0 ? data.nodes[0] : null))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to query live FalkorDB graph')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedGraph) {
      loadGraphData(selectedGraph)
    }
  }, [selectedGraph, loadGraphData])

  const getNodeColor = (kind: string) => {
    switch (kind.toLowerCase()) {
      case 'function':
        return '#388bfd'
      case 'class':
        return '#bc8cff'
      case 'module':
        return '#39c5cf'
      case 'file':
        return '#8b949e'
      case 'test':
        return '#e3b341'
      default:
        return '#58a6ff'
    }
  }

  // Generate deterministic circular layout for visualization
  const width = 640
  const height = 400
  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(centerX, centerY) - 50

  const nodes = neighborhood?.nodes || []
  const edges = neighborhood?.edges || []

  const nodePositions = new Map<string, { x: number; y: number }>()
  nodes.forEach((n, idx) => {
    const angle = (idx / Math.max(1, nodes.length)) * 2 * Math.PI
    nodePositions.set(n.entity_id, {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    })
  })

  return (
    <div>
      {/* Controls & Graph Selector */}
      <div className="panel-card">
        <div className="panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <GitBranch size={15} color="#388bfd" />
            <span className="panel-title">FalkorDB Historical Revision Graph Explorer</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <label className="form-label" style={{ margin: 0, fontSize: 10 }} htmlFor="graph-select">
              Select Revision:
            </label>
            <select
              id="graph-select"
              className="form-select mono"
              style={{ width: 'auto', padding: '3px 8px', fontSize: 11 }}
              value={selectedGraph}
              onChange={(e) => setSelectedGraph(e.target.value)}
              disabled={isLoading}
            >
              {graphs.map((g) => (
                <option key={g.graph_name} value={g.graph_name}>
                  {g.graph_name} ({g.node_count} nodes, {g.edge_count} edges)
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => loadGraphData(selectedGraph)}
              disabled={isLoading}
            >
              <RefreshCw size={11} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: 10, color: 'var(--status-danger-text)', fontSize: 11 }}>
            {error}
          </div>
        )}
      </div>

      {/* Main visualization grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
        {/* SVG Graph View */}
        <div className="panel-card" style={{ marginBottom: 0 }}>
          <div className="panel-header">
            <span className="panel-title" style={{ fontSize: 11 }}>
              <ZoomIn size={12} /> Interactive Graph Subgraph ({nodes.length} nodes, {edges.length} edges)
            </span>
            <div style={{ display: 'flex', gap: 10, fontSize: 10 }}>
              <span style={{ color: '#388bfd' }}>● Function</span>
              <span style={{ color: '#bc8cff' }}>● Class</span>
              <span style={{ color: '#39c5cf' }}>● Module</span>
              <span style={{ color: '#e3b341' }}>● Test</span>
            </div>
          </div>

          <div style={{ padding: 10, display: 'flex', justifyContent: 'center', backgroundColor: '#090d13' }}>
            <svg width={width} height={height} style={{ overflow: 'visible' }}>
              {/* Edges */}
              {edges.map((e, idx) => {
                const srcPos = nodePositions.get(e.source_id)
                const tgtPos = nodePositions.get(e.target_id)
                if (!srcPos || !tgtPos) return null
                return (
                  <line
                    key={idx}
                    x1={srcPos.x}
                    y1={srcPos.y}
                    x2={tgtPos.x}
                    y2={tgtPos.y}
                    stroke="#30363d"
                    strokeWidth={1}
                    strokeDasharray={e.edge_type === 'CALLS' ? 'none' : '3,3'}
                  />
                )
              })}

              {/* Nodes */}
              {nodes.map((n) => {
                const pos = nodePositions.get(n.entity_id)
                if (!pos) return null
                const isSelected = selectedNode?.entity_id === n.entity_id
                const color = getNodeColor(n.kind)

                return (
                  <g
                    key={n.entity_id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onClick={() => {
                      setSelectedNode(n)
                      loadGraphData(selectedGraph, n.entity_id)
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle
                      r={isSelected ? 10 : 7}
                      fill={color}
                      stroke={isSelected ? '#ffffff' : '#0d1117'}
                      strokeWidth={isSelected ? 2 : 1}
                    />
                    <text
                      y={-10}
                      fontSize={9}
                      fill={isSelected ? '#ffffff' : '#8b949e'}
                      textAnchor="middle"
                      className="mono"
                    >
                      {n.qualified_name.split('.').slice(-1)[0] || n.entity_id.slice(0, 10)}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        </div>

        {/* Selected Node Inspector */}
        <div className="panel-card" style={{ marginBottom: 0 }}>
          <div className="panel-header">
            <span className="panel-title" style={{ fontSize: 11 }}>
              <Info size={12} /> Node Inspector
            </span>
          </div>
          <div className="panel-body">
            {selectedNode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <span className="form-label">Entity ID</span>
                  <div className="mono" style={{ fontSize: 11, wordBreak: 'break-all', color: 'var(--text-primary)' }}>
                    {selectedNode.entity_id}
                  </div>
                </div>

                <div>
                  <span className="form-label">Kind / Type</span>
                  <span
                    className="badge"
                    style={{
                      backgroundColor: `${getNodeColor(selectedNode.kind)}25`,
                      color: getNodeColor(selectedNode.kind),
                      border: `1px solid ${getNodeColor(selectedNode.kind)}50`,
                    }}
                  >
                    {selectedNode.kind}
                  </span>
                </div>

                <div>
                  <span className="form-label">Qualified Name</span>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {selectedNode.qualified_name}
                  </div>
                </div>

                <div>
                  <span className="form-label">File Path</span>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {selectedNode.path || '—'}
                  </div>
                </div>

                <div>
                  <span className="form-label">Source Lines</span>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {selectedNode.start_line && selectedNode.end_line
                      ? `L${selectedNode.start_line} - L${selectedNode.end_line}`
                      : '—'}
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-placeholder">Select a node to inspect metadata.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
