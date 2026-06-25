import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { compareSessions, listSessions } from "../services/api";
import logoImage from "../assets/logo/logo.png";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatDuration(seconds) {
    if (seconds == null) return "--:--";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.round(seconds % 60);
    if (hrs > 0) {
        return `${hrs}h ${mins}m ${secs}s`;
    }
    return `${mins}m ${secs}s`;
}

function formatDate(iso) {
    if (!iso) return "—";
    try {
        return new Date(iso).toLocaleString("en-IN", {
            day: "numeric", month: "short", year: "numeric",
            hour: "numeric", minute: "2-digit", hour12: true,
        });
    } catch { return iso; }
}

function DeltaPill({ value, unit = "", inverted = false }) {
    if (value == null) return <span style={{ color: "#6b7280", fontSize: 12 }}>—</span>;
    const positive = inverted ? value < 0 : value > 0;
    const color = value === 0 ? "#6b7280" : positive ? "#10b981" : "#ef4444";
    const arrow = value === 0 ? "=" : positive ? "▲" : "▼";
    const display = value > 0 ? `+${value}${unit}` : `${value}${unit}`;
    return (
        <span style={{
            display: "inline-flex", alignItems: "center", gap: 3,
            padding: "2px 8px", borderRadius: 9999,
            background: `${color}22`, color, fontWeight: 700, fontSize: 12,
        }}>
            {arrow} {display}
        </span>
    );
}

function ModeBadge({ mode }) {
    const colors = {
        meeting: { bg: "#3b82f622", color: "#60a5fa" },
        sales: { bg: "#a855f722", color: "#c084fc" },
        interview: { bg: "#f59e0b22", color: "#fbbf24" },
    };
    const s = colors[mode] || colors.meeting;
    return (
        <span style={{
            padding: "2px 10px", borderRadius: 9999,
            background: s.bg, color: s.color, fontSize: 12, fontWeight: 600,
            textTransform: "capitalize",
        }}>{mode}</span>
    );
}

function SessionSelector({ label, sessions, selectedId, onSelect, excluded }) {
    return (
        <div style={{ flex: 1 }}>
            <label style={{ display: "block", color: "#9ca3af", fontSize: 12, marginBottom: 6 }}>
                {label}
            </label>
            <select
                value={selectedId || ""}
                onChange={e => onSelect(e.target.value)}
                style={{
                    width: "100%", padding: "10px 14px", borderRadius: 10,
                    background: "#1e2535", border: "1px solid #334155",
                    color: "#e2e8f0", fontSize: 14, cursor: "pointer",
                }}
            >
                <option value="">— Select a session —</option>
                {sessions
                    .filter(s => s.session_id !== excluded)
                    .map(s => (
                        <option key={s.session_id} value={s.session_id}>
                            {s.title || `Session ${s.session_id.slice(0, 8)}`}
                            {" · "}
                            {s.mode}
                            {s.started_at ? ` · ${formatDate(s.started_at)}` : ""}
                        </option>
                    ))}
            </select>
        </div>
    );
}

function MetricCard({ label, valA, valB, delta, unit = "", invertDelta = false, format }) {
    const fmt = format || (v => v == null ? "—" : v);
    return (
        <div style={{
            background: "#1e2535", borderRadius: 14, padding: "18px 20px",
            border: "1px solid #334155",
        }}>
            <div style={{ color: "#9ca3af", fontSize: 12, marginBottom: 10, fontWeight: 600 }}>
                {label}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                <div style={{ textAlign: "center", flex: 1 }}>
                    <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 22 }}>
                        {fmt(valA)}{unit}
                    </div>
                    <div style={{ color: "#6b7280", fontSize: 11, marginTop: 4 }}>Session A</div>
                </div>
                <div style={{ textAlign: "center", padding: "0 10px" }}>
                    <DeltaPill value={delta} unit={unit} inverted={invertDelta} />
                </div>
                <div style={{ textAlign: "center", flex: 1 }}>
                    <div style={{ color: "#a78bfa", fontWeight: 700, fontSize: 22 }}>
                        {fmt(valB)}{unit}
                    </div>
                    <div style={{ color: "#6b7280", fontSize: 11, marginTop: 4 }}>Session B</div>
                </div>
            </div>
        </div>
    );
}

function ListCompare({ title, shared, uniqueA, uniqueB }) {
    const hasAny = shared.length || uniqueA.length || uniqueB.length;
    if (!hasAny) {
        return (
            <div style={{ background: "#1e2535", borderRadius: 14, padding: "18px 20px", border: "1px solid #334155" }}>
                <div style={{ color: "#9ca3af", fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{title}</div>
                <div style={{ color: "#4b5563", fontSize: 13 }}>No data recorded for either session.</div>
            </div>
        );
    }
    return (
        <div style={{ background: "#1e2535", borderRadius: 14, padding: "18px 20px", border: "1px solid #334155" }}>
            <div style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 700, marginBottom: 14 }}>{title}</div>
            {shared.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                    <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: 700, marginBottom: 6 }}>
                        SHARED ({shared.length})
                    </div>
                    {shared.map((t, i) => (
                        <div key={i} style={{
                            padding: "6px 10px", marginBottom: 4, borderRadius: 8,
                            background: "#10b98122", color: "#6ee7b7", fontSize: 13,
                            borderLeft: "3px solid #10b981",
                        }}>
                            {t}
                        </div>
                    ))}
                </div>
            )}
            <div style={{ display: "flex", gap: 12 }}>
                <div style={{ flex: 1 }}>
                    {uniqueA.length > 0 && (
                        <>
                            <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: 700, marginBottom: 6 }}>
                                ONLY IN A ({uniqueA.length})
                            </div>
                            {uniqueA.map((t, i) => (
                                <div key={i} style={{
                                    padding: "6px 10px", marginBottom: 4, borderRadius: 8,
                                    background: "#3b82f622", color: "#93c5fd", fontSize: 13,
                                    borderLeft: "3px solid #3b82f6",
                                }}>
                                    {t}
                                </div>
                            ))}
                        </>
                    )}
                </div>
                <div style={{ flex: 1 }}>
                    {uniqueB.length > 0 && (
                        <>
                            <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: 700, marginBottom: 6 }}>
                                ONLY IN B ({uniqueB.length})
                            </div>
                            {uniqueB.map((t, i) => (
                                <div key={i} style={{
                                    padding: "6px 10px", marginBottom: 4, borderRadius: 8,
                                    background: "#a855f722", color: "#c084fc", fontSize: 13,
                                    borderLeft: "3px solid #a855f7",
                                }}>
                                    {t}
                                </div>
                            ))}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

function TalkRatioBar({ ratio, colorA, colorB }) {
    if (!ratio || Object.keys(ratio).length === 0) {
        return <div style={{ color: "#4b5563", fontSize: 13 }}>No talk ratio data.</div>;
    }
    const total = Object.values(ratio).reduce((a, b) => a + b, 0) || 1;
    const speakers = Object.entries(ratio);
    const palette = ["#60a5fa", "#a78bfa", "#34d399", "#fb923c", "#f472b6"];
    return (
        <div>
            <div style={{
                display: "flex", borderRadius: 8, overflow: "hidden",
                height: 16, marginBottom: 10, background: "#0f1623",
            }}>
                {speakers.map(([spk, val], i) => (
                    <div
                        key={spk}
                        title={`${spk}: ${Math.round((val / total) * 100)}%`}
                        style={{ width: `${(val / total) * 100}%`, background: palette[i % palette.length] }}
                    />
                ))}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {speakers.map(([spk, val], i) => (
                    <div key={spk} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12 }}>
                        <div style={{ width: 10, height: 10, borderRadius: 2, background: palette[i % palette.length] }} />
                        <span style={{ color: "#9ca3af" }}>{spk}</span>
                        <span style={{ color: "#e2e8f0", fontWeight: 600 }}>
                            {Math.round((val / total) * 100)}%
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ActionItemsTable({ items }) {
    if (!items || items.length === 0) {
        return <div style={{ color: "#4b5563", fontSize: 13 }}>No action items recorded.</div>;
    }
    return (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
                <tr>
                    {["Source", "Action Item", "Owner", "Deadline"].map(h => (
                        <th key={h} style={{
                            textAlign: "left", color: "#6b7280", fontWeight: 700,
                            fontSize: 11, padding: "6px 10px", borderBottom: "1px solid #334155",
                        }}>{h}</th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {items.map((item, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #1e2535" }}>
                        <td style={{ padding: "8px 10px" }}>
                            <span style={{
                                padding: "2px 8px", borderRadius: 9999, fontSize: 11, fontWeight: 700,
                                background: item.source === "a" ? "#3b82f622" : "#a855f722",
                                color: item.source === "a" ? "#60a5fa" : "#c084fc",
                            }}>
                                {item.source === "a" ? "A" : "B"}
                            </span>
                        </td>
                        <td style={{ padding: "8px 10px", color: "#e2e8f0" }}>{item.text}</td>
                        <td style={{ padding: "8px 10px", color: "#9ca3af" }}>{item.owner || "—"}</td>
                        <td style={{ padding: "8px 10px", color: "#9ca3af" }}>{item.deadline || "—"}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function ComparisonPage() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    const [id1, setId1] = useState(searchParams.get("id1") || "");
    const [id2, setId2] = useState(searchParams.get("id2") || "");

    const [sessions, setSessions] = useState([]);
    const [loadingSessions, setLoadingSessions] = useState(true);

    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Load available sessions for the selectors
    useEffect(() => {
        (async () => {
            setLoadingSessions(true);
            try {
                const data = await listSessions({ status: "completed", limit: 100, sort_by: "started_at", sort_order: "desc" });
                setSessions(data.items || []);
            } catch {
                setSessions([]);
            } finally {
                setLoadingSessions(false);
            }
        })();
    }, []);

    // Auto-fetch if both IDs are present in URL
    useEffect(() => {
        if (id1 && id2) {
            runComparison(id1, id2);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const runComparison = useCallback(async (a, b) => {
        if (!a || !b) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await compareSessions(a, b);
            setResult(data);
            setSearchParams({ id1: a, id2: b }, { replace: true });
        } catch (e) {
            setError(e.message || "Comparison failed");
        } finally {
            setLoading(false);
        }
    }, [setSearchParams]);

    const handleCompare = () => {
        if (!id1 || !id2) { setError("Please select both sessions."); return; }
        if (id1 === id2) { setError("Please select two different sessions."); return; }
        runComparison(id1, id2);
    };

    const handleExport = () => {
        if (!result) return;
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `comparison_${result.session_a.session_id.slice(0, 8)}_vs_${result.session_b.session_id.slice(0, 8)}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const { session_a: sA, session_b: sB, delta } = result || {};

    return (
        <div style={{
            minHeight: "100vh", background: "#0f1623",
            color: "#e2e8f0", fontFamily: "'Inter', sans-serif",
        }}>
            {/* ── Nav ── */}
            <nav style={{
                background: "#13192a", borderBottom: "1px solid #1e2d45",
                padding: "0 32px", height: 64,
                display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <img src={logoImage} alt="TalkSense" style={{ height: 36 }} />
                    <span style={{ color: "#e2e8f0", fontWeight: 700, fontSize: 18 }}>TalkSense AI</span>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                    {[
                        { label: "Home", path: "/" },
                        { label: "Sessions", path: "/sessions" },
                    ].map(({ label, path }) => (
                        <button
                            key={path}
                            onClick={() => navigate(path)}
                            style={{
                                background: "none", border: "none", color: "#9ca3af",
                                fontSize: 14, cursor: "pointer", padding: "6px 12px", borderRadius: 8,
                            }}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </nav>

            {/* ── Main content ── */}
            <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>

                {/* Page header */}
                <div style={{ marginBottom: 28 }}>
                    <h1 style={{
                        fontSize: 28, fontWeight: 800, color: "#f1f5f9", margin: 0,
                        background: "linear-gradient(135deg, #60a5fa, #a78bfa)",
                        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                    }}>
                        Session Comparison
                    </h1>
                    <p style={{ color: "#6b7280", margin: "6px 0 0", fontSize: 14 }}>
                        Compare metrics, objections, and outcomes across two sessions.
                    </p>
                </div>

                {/* Session selectors */}
                <div style={{
                    background: "#13192a", borderRadius: 16, padding: "24px",
                    border: "1px solid #1e2d45", marginBottom: 28,
                }}>
                    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
                        <SessionSelector
                            label="Session A"
                            sessions={sessions}
                            selectedId={id1}
                            onSelect={v => setId1(v)}
                            excluded={id2}
                        />
                        <div style={{
                            color: "#6b7280", fontSize: 22, paddingBottom: 10, userSelect: "none",
                        }}>vs</div>
                        <SessionSelector
                            label="Session B"
                            sessions={sessions}
                            selectedId={id2}
                            onSelect={v => setId2(v)}
                            excluded={id1}
                        />
                        <button
                            id="btn-compare"
                            onClick={handleCompare}
                            disabled={loading || !id1 || !id2}
                            style={{
                                padding: "10px 28px", borderRadius: 10, border: "none",
                                background: loading ? "#334155" : "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                                color: "#fff", fontWeight: 700, fontSize: 14, cursor: loading ? "default" : "pointer",
                                whiteSpace: "nowrap",
                            }}
                        >
                            {loading ? "Comparing…" : "Compare"}
                        </button>
                    </div>

                    {error && (
                        <div style={{
                            marginTop: 14, padding: "10px 14px", borderRadius: 8,
                            background: "#ef444422", color: "#fca5a5", fontSize: 13,
                            border: "1px solid #ef444444",
                        }}>
                            {error}
                        </div>
                    )}
                </div>

                {/* ── Results ── */}
                {result && (
                    <>
                        {/* Session header cards */}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
                            {[
                                { snap: sA, label: "Session A", accent: "#60a5fa", bg: "#3b82f611" },
                                { snap: sB, label: "Session B", accent: "#a78bfa", bg: "#8b5cf611" },
                            ].map(({ snap, label, accent, bg }) => (
                                <div key={label} style={{
                                    background: bg, borderRadius: 14, padding: "20px 22px",
                                    border: `1px solid ${accent}44`,
                                }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                                        <span style={{ color: accent, fontWeight: 700, fontSize: 12 }}>{label}</span>
                                        <ModeBadge mode={snap.mode} />
                                    </div>
                                    <div style={{ color: "#f1f5f9", fontWeight: 700, fontSize: 16, marginBottom: 4 }}>
                                        {snap.title}
                                    </div>
                                    <div style={{ color: "#9ca3af", fontSize: 12 }}>
                                        {formatDate(snap.started_at)} · {formatDuration(snap.duration)}
                                    </div>
                                    {snap.summary && (
                                        <div style={{
                                            marginTop: 10, padding: "8px 12px", borderRadius: 8,
                                            background: "#0f162388", color: "#9ca3af", fontSize: 12,
                                            borderLeft: `3px solid ${accent}`,
                                        }}>
                                            {snap.summary}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Metric cards */}
                        <div style={{ marginBottom: 24 }}>
                            <h2 style={{ color: "#e2e8f0", fontSize: 16, fontWeight: 700, marginBottom: 14 }}>
                                Key Metrics
                            </h2>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
                                <MetricCard
                                    label="Health Score"
                                    valA={sA.health_score}
                                    valB={sB.health_score}
                                    delta={delta?.health_score}
                                    format={v => v == null ? "—" : v}
                                />
                                <MetricCard
                                    label="Sentiment Score"
                                    valA={sA.sentiment_score != null ? (sA.sentiment_score * 100).toFixed(0) : null}
                                    valB={sB.sentiment_score != null ? (sB.sentiment_score * 100).toFixed(0) : null}
                                    delta={delta?.sentiment_score != null ? +(delta.sentiment_score * 100).toFixed(1) : null}
                                    unit="%"
                                />
                                <MetricCard
                                    label="Duration"
                                    valA={sA.duration != null ? formatDuration(sA.duration) : null}
                                    valB={sB.duration != null ? formatDuration(sB.duration) : null}
                                    delta={delta?.duration != null ? Math.round(delta.duration) : null}
                                    unit="s"
                                    format={v => v || "—"}
                                />
                            </div>
                        </div>

                        {/* Talk ratio */}
                        <div style={{ marginBottom: 24 }}>
                            <h2 style={{ color: "#e2e8f0", fontSize: 16, fontWeight: 700, marginBottom: 14 }}>
                                Talk Ratio
                            </h2>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                                {[
                                    { snap: sA, label: "Session A", accent: "#60a5fa" },
                                    { snap: sB, label: "Session B", accent: "#a78bfa" },
                                ].map(({ snap, label, accent }) => (
                                    <div key={label} style={{
                                        background: "#1e2535", borderRadius: 14, padding: "18px 20px",
                                        border: "1px solid #334155",
                                    }}>
                                        <div style={{ color: accent, fontSize: 12, fontWeight: 700, marginBottom: 12 }}>
                                            {label}
                                        </div>
                                        <TalkRatioBar ratio={snap.talk_ratio} />
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Objections */}
                        <div style={{ marginBottom: 24 }}>
                            <h2 style={{ color: "#e2e8f0", fontSize: 16, fontWeight: 700, marginBottom: 14 }}>
                                Objections
                            </h2>
                            <ListCompare
                                title="Objections Raised"
                                shared={result.shared_objections}
                                uniqueA={result.unique_to_a_objections}
                                uniqueB={result.unique_to_b_objections}
                            />
                        </div>

                        {/* Buying signals */}
                        <div style={{ marginBottom: 24 }}>
                            <h2 style={{ color: "#e2e8f0", fontSize: 16, fontWeight: 700, marginBottom: 14 }}>
                                Buying Signals
                            </h2>
                            <ListCompare
                                title="Buying Signals Detected"
                                shared={result.shared_buying_signals}
                                uniqueA={result.unique_to_a_buying_signals}
                                uniqueB={result.unique_to_b_buying_signals}
                            />
                        </div>

                        {/* Action items */}
                        <div style={{ marginBottom: 24 }}>
                            <h2 style={{ color: "#e2e8f0", fontSize: 16, fontWeight: 700, marginBottom: 14 }}>
                                Action Items
                            </h2>
                            <div style={{
                                background: "#1e2535", borderRadius: 14, padding: "18px 20px",
                                border: "1px solid #334155", overflowX: "auto",
                            }}>
                                <ActionItemsTable items={result.all_action_items} />
                            </div>
                        </div>

                        {/* Export */}
                        <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: 8 }}>
                            <button
                                id="btn-export"
                                onClick={handleExport}
                                style={{
                                    padding: "10px 24px", borderRadius: 10, border: "1px solid #334155",
                                    background: "#1e2535", color: "#9ca3af", fontWeight: 600,
                                    fontSize: 14, cursor: "pointer",
                                    display: "flex", alignItems: "center", gap: 8,
                                }}
                            >
                                ⬇ Export JSON Report
                            </button>
                        </div>
                    </>
                )}

                {/* Empty state */}
                {!result && !loading && !error && (
                    <div style={{
                        textAlign: "center", padding: "80px 20px",
                        color: "#4b5563", fontSize: 15,
                    }}>
                        <div style={{ fontSize: 48, marginBottom: 16 }}>⚖️</div>
                        <div style={{ fontWeight: 700, color: "#6b7280", fontSize: 18 }}>
                            Select two completed sessions above and click Compare
                        </div>
                        <div style={{ marginTop: 8, fontSize: 13 }}>
                            Results will appear here with metrics, insights, and exportable report.
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
