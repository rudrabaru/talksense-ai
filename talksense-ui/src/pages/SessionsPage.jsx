import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { listSessions } from "../services/api";
import logoImage from "../assets/logo/logo.png";


// Helper to format duration seconds to MM:SS or HH:MM:SS
function formatDuration(seconds) {
    if (seconds === undefined || seconds === null) return "--:--";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.round(seconds % 60);
    if (hrs > 0) {
        return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Helper to format timezone-aware ISO date string into Indian local format
function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
        const date = new Date(dateStr);
        return date.toLocaleString("en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "numeric",
            minute: "2-digit",
            hour12: true,
        });
    } catch {
        return dateStr;
    }
}

export default function SessionsPage() {
    const navigate = useNavigate();

    // --- State ---------------------------------------------------------------
    const [sessions, setSessions] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // --- Compare selection state ---------------------------------------------
    const [compareSelected, setCompareSelected] = useState([]); // max 2 session_ids

    const toggleCompareSelect = useCallback((sessionId) => {
        setCompareSelected(prev => {
            if (prev.includes(sessionId)) return prev.filter(id => id !== sessionId);
            if (prev.length >= 2) return prev; // max 2
            return [...prev, sessionId];
        });
    }, []);

    const handleCompareNavigate = useCallback(() => {
        if (compareSelected.length === 2) {
            navigate(`/compare?id1=${compareSelected[0]}&id2=${compareSelected[1]}`);
        }
    }, [compareSelected, navigate]);

    // --- Query Params State --------------------------------------------------
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState("");
    const [mode, setMode] = useState("");
    const [sortBy, setSortBy] = useState("started_at");
    const [sortOrder, setSortOrder] = useState("desc");
    const [page, setPage] = useState(1);
    const limit = 10;

    // --- Fetch Data ----------------------------------------------------------
    const fetchSessions = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await listSessions({
                page,
                limit,
                search,
                status,
                mode,
                sort_by: sortBy,
                sort_order: sortOrder,
            });
            setSessions(data.items || []);
            setTotal(data.total || 0);
        } catch (err) {
            console.error("Failed to load sessions:", err);
            setError(err.message || "Failed to load historical sessions.");
        } finally {
            setLoading(false);
        }
    }, [page, search, status, mode, sortBy, sortOrder]);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        fetchSessions();
    }, [fetchSessions]);

    // Reset to page 1 on filter or search change
    const handleSearchChange = (e) => {
        setSearch(e.target.value);
        setPage(1);
    };

    const handleStatusChange = (e) => {
        setStatus(e.target.value);
        setPage(1);
    };

    const handleModeChange = (e) => {
        setMode(e.target.value);
        setPage(1);
    };

    const toggleSortOrder = () => {
        setSortOrder(prev => (prev === "desc" ? "asc" : "desc"));
        setPage(1);
    };

    const handleSortByChange = (e) => {
        setSortBy(e.target.value);
        setPage(1);
    };

    // --- Render Helpers ------------------------------------------------------
    const getStatusBadgeClass = (status) => {
        switch (status) {
            case "completed":
                return "bg-teal-50 text-teal-700 border-teal-100";
            case "active":
            case "processing":
                return "bg-indigo-50 text-indigo-700 border-indigo-100 animate-pulse";
            case "failed":
                return "bg-rose-50 text-rose-700 border-rose-100";
            case "interrupted":
                return "bg-amber-50 text-amber-700 border-amber-100";
            case "expired":
                return "bg-gray-100 text-gray-700 border-gray-200";
            default:
                return "bg-gray-50 text-gray-600 border-gray-100";
        }
    };

    const getSentimentBadgeClass = (sentiment) => {
        if (!sentiment) return "bg-gray-100 text-gray-500";
        const clean = sentiment.toLowerCase();
        if (clean.includes("pos")) return "bg-emerald-50 text-emerald-700 border-emerald-100";
        if (clean.includes("neg")) return "bg-rose-50 text-rose-700 border-rose-100";
        return "bg-gray-50 text-gray-700 border-gray-100";
    };

    const getModeBadgeClass = (mode) => {
        switch (mode) {
            case "sales":
                return "bg-purple-50 text-purple-700 border-purple-100";
            case "interview":
                return "bg-sky-50 text-sky-700 border-sky-100";
            default:
                return "bg-blue-50 text-blue-700 border-blue-100";
        }
    };

    const totalPages = Math.max(1, Math.ceil(total / limit));

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-indigo-50/20 text-gray-900 flex flex-col">
            {/* Navbar */}
            <nav className="border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
                <div className="mx-auto px-6 lg:px-12 xl:px-16 h-16 flex items-center justify-between">
                    <button
                        onClick={() => navigate('/')}
                        className="flex items-center gap-3 hover:opacity-85 transition-all"
                    >
                        <div className="relative w-9 h-9">
                            <img src={logoImage} alt="TalkSense AI Logo" className="w-full h-full object-contain" />
                        </div>
                        <span className="font-bold text-xl tracking-tight">
                            <span style={{ color: '#4F46E5' }}>TalkSense</span>
                            <span style={{ color: '#14B8A6' }}> AI</span>
                        </span>
                    </button>
                    <div className="flex gap-6 items-center text-sm font-medium">
                        <button
                            onClick={() => navigate('/')}
                            className="text-gray-500 hover:text-indigo-600 transition-colors"
                        >
                            Home
                        </button>
                        <button
                            onClick={() => navigate('/upload')}
                            className="text-gray-500 hover:text-indigo-600 transition-colors"
                        >
                            Analyze
                        </button>
                        <button
                            onClick={() => navigate('/sessions')}
                            className="text-indigo-600 font-semibold border-b-2 border-indigo-600 px-1 py-4"
                        >
                            History
                        </button>
                    </div>
                </div>
            </nav>

            {/* Main Content container */}
            <div className="flex-1 mx-auto w-full max-w-7xl px-6 lg:px-12 xl:px-16 py-10">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
                            Historical Sessions
                        </h1>
                        <p className="text-gray-500 mt-1">
                            Browse, filter, and review previously processed conversation intelligence reports.
                        </p>
                    </div>
                    <button
                        onClick={() => navigate('/compare')}
                        className="inline-flex items-center gap-2 px-4 py-2 border border-indigo-200 hover:border-indigo-600 text-indigo-600 hover:text-white hover:bg-indigo-600 rounded-lg text-sm font-semibold transition-all shadow-sm"
                    >
                        ⚖ Compare Sessions
                    </button>
                </div>

                {/* Compare CTA banner — shown when 2 sessions selected */}
                {compareSelected.length > 0 && (
                    <div className="mb-4 px-5 py-3 bg-indigo-50 border border-indigo-200 rounded-xl flex items-center justify-between gap-4">
                        <span className="text-sm text-indigo-700 font-medium">
                            {compareSelected.length === 1
                                ? "Select one more session to compare."
                                : "2 sessions selected — ready to compare."}
                        </span>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setCompareSelected([])}
                                className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg bg-white"
                            >
                                Clear
                            </button>
                            <button
                                id="btn-compare-selected"
                                onClick={handleCompareNavigate}
                                disabled={compareSelected.length < 2}
                                className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                Compare Selected
                            </button>
                        </div>
                    </div>
                )}

                {/* Filter and Search Panel */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    {/* Search Input */}
                    <div className="relative flex-1 max-w-md">
                        <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <input
                            type="text"
                            value={search}
                            onChange={handleSearchChange}
                            placeholder="Search by title, mode, client name..."
                            className="w-full pl-11 pr-4 py-2.5 bg-gray-50/50 hover:bg-gray-50 focus:bg-white text-gray-900 placeholder-gray-400 border border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 rounded-xl transition-all outline-none text-sm"
                        />
                    </div>

                    {/* Filters & Sorting */}
                    <div className="flex flex-wrap items-center gap-3">
                        {/* Mode Filter */}
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Mode:</span>
                            <select
                                value={mode}
                                onChange={handleModeChange}
                                className="bg-gray-50 hover:bg-gray-100 text-gray-700 py-2 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500"
                            >
                                <option value="">All Modes</option>
                                <option value="meeting">Meeting</option>
                                <option value="sales">Sales</option>
                                <option value="interview">Interview</option>
                            </select>
                        </div>

                        {/* Status Filter */}
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Status:</span>
                            <select
                                value={status}
                                onChange={handleStatusChange}
                                className="bg-gray-50 hover:bg-gray-100 text-gray-700 py-2 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500"
                            >
                                <option value="">All Statuses</option>
                                <option value="created">Created</option>
                                <option value="connecting">Connecting</option>
                                <option value="active">Active</option>
                                <option value="completed">Completed</option>
                                <option value="failed">Failed</option>
                                <option value="interrupted">Interrupted</option>
                                <option value="expired">Expired</option>
                            </select>
                        </div>

                        {/* Sort Field */}
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Sort:</span>
                            <select
                                value={sortBy}
                                onChange={handleSortByChange}
                                className="bg-gray-50 hover:bg-gray-100 text-gray-700 py-2 px-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500"
                            >
                                <option value="started_at">Date</option>
                                <option value="duration">Duration</option>
                                <option value="title">Title</option>
                                <option value="status">Status</option>
                                <option value="mode">Mode</option>
                            </select>
                            
                            {/* Asc/Desc toggle button */}
                            <button
                                onClick={toggleSortOrder}
                                className="p-2 border border-gray-200 rounded-lg bg-gray-50 hover:bg-gray-100 hover:text-indigo-600 transition-colors focus:ring-2 focus:ring-indigo-100 focus:outline-none"
                                title={sortOrder === "desc" ? "Descending" : "Ascending"}
                            >
                                <svg className={`w-5 h-5 transition-transform duration-200 ${sortOrder === "asc" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="p-4 mb-6 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-3">
                        <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <span>{error}</span>
                    </div>
                )}

                {/* Main Table Card */}
                <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                    {loading ? (
                        /* Skeletons Loading */
                        <div className="p-6 space-y-4">
                            {[1, 2, 3, 4, 5].map((idx) => (
                                <div key={idx} className="flex items-center justify-between border-b border-gray-100 pb-4 last:border-0 last:pb-0 animate-pulse">
                                    <div className="space-y-2 flex-1 pr-6">
                                        <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                                        <div className="h-3 bg-gray-100 rounded w-1/4"></div>
                                    </div>
                                    <div className="flex gap-4 items-center">
                                        <div className="h-6 bg-gray-100 rounded-full w-16"></div>
                                        <div className="h-6 bg-gray-100 rounded-full w-20"></div>
                                        <div className="h-9 bg-gray-200 rounded-lg w-24"></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : sessions.length === 0 ? (
                        /* Empty State */
                        <div className="py-20 text-center">
                            <div className="w-16 h-16 mx-auto mb-4 bg-indigo-50 flex items-center justify-center rounded-2xl text-indigo-500">
                                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>
                            </div>
                            <h3 className="text-gray-900 font-semibold text-lg mb-1">No sessions found</h3>
                            <p className="text-gray-500 text-sm max-w-sm mx-auto">
                                We couldn't find any historical sessions matching your criteria. Try adjusting your search query or filters.
                            </p>
                        </div>
                    ) : (
                        /* Table Content */
                        <div className="overflow-x-auto">
                            <table className="w-full border-collapse text-left text-sm text-gray-500">
                                <thead className="bg-gray-50/50 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-200">
                                    <tr>
                                        <th scope="col" className="px-4 py-4 w-10" title="Select to compare">⚖</th>
                                        <th scope="col" className="px-6 py-4">Title / Mode</th>
                                        <th scope="col" className="px-6 py-4">Status</th>
                                        <th scope="col" className="px-6 py-4">Client</th>
                                        <th scope="col" className="px-6 py-4">Date & Time</th>
                                        <th scope="col" className="px-6 py-4">Duration</th>
                                        <th scope="col" className="px-6 py-4">Health / Sentiment</th>
                                        <th scope="col" className="px-6 py-4 text-right">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {sessions.map((session) => {
                                        const isSelected = compareSelected.includes(session.session_id);
                                        const isDisabled = !isSelected && compareSelected.length >= 2;
                                        return (
                                        <tr key={session.session_id} className={`hover:bg-gray-50/40 transition-colors ${isSelected ? 'bg-indigo-50/60' : ''}`}>
                                            {/* Compare checkbox */}
                                            <td className="px-4 py-4">
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    disabled={isDisabled}
                                                    onChange={() => toggleCompareSelect(session.session_id)}
                                                    title={isDisabled ? "Deselect another session first" : "Select to compare"}
                                                    className="w-4 h-4 rounded accent-indigo-600 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
                                                />
                                            </td>

                                            {/* Title & Mode */}
                                            <td className="px-6 py-4">
                                                <div className="font-semibold text-gray-900 hover:text-indigo-600 transition-colors">
                                                    {session.title || `Session ${session.session_id.substring(0, 8)}`}
                                                </div>
                                                <div className="mt-1">
                                                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getModeBadgeClass(session.mode)}`}>
                                                        {session.mode}
                                                    </span>
                                                </div>
                                            </td>

                                            {/* Status */}
                                            <td className="px-6 py-4">
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getStatusBadgeClass(session.status)}`}>
                                                    {session.status}
                                                </span>
                                            </td>

                                            {/* Client */}
                                            <td className="px-6 py-4 text-gray-900 font-medium">
                                                {session.client_name || <span className="text-gray-300">—</span>}
                                            </td>

                                            {/* Date & Time */}
                                            <td className="px-6 py-4 text-gray-500 whitespace-nowrap">
                                                {formatDate(session.started_at)}
                                            </td>

                                            {/* Duration */}
                                            <td className="px-6 py-4 text-gray-900 whitespace-nowrap font-mono text-xs">
                                                {formatDuration(session.duration)}
                                            </td>

                                            {/* Health & Sentiment */}
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    {session.health_score !== null && session.health_score !== undefined ? (
                                                        <div className="flex items-center gap-1.5" title="Conversation Health Score">
                                                            <div className={`w-2 h-2 rounded-full ${session.health_score >= 80 ? 'bg-emerald-500' : session.health_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`} />
                                                            <span className="font-semibold text-gray-900">{session.health_score}</span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-gray-300 text-xs">—</span>
                                                    )}
                                                    {session.health_score !== null && session.sentiment && <span className="text-gray-200">|</span>}
                                                    {session.sentiment ? (
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border capitalize ${getSentimentBadgeClass(session.sentiment)}`}>
                                                            {session.sentiment}
                                                        </span>
                                                    ) : null}
                                                </div>
                                            </td>

                                            {/* Action Buttons */}
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button
                                                        onClick={() => navigate(`/dashboard/${session.session_id}`)}
                                                        className="inline-flex items-center justify-center px-3.5 py-1.5 border border-indigo-200 hover:border-indigo-600 text-indigo-600 hover:text-white hover:bg-indigo-600 rounded-lg text-xs font-semibold transition-all shadow-sm active:scale-95"
                                                    >
                                                        View Details
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* Pagination Controls */}
                {!loading && total > 0 && (
                    <div className="mt-6 flex items-center justify-between border-t border-gray-200 pt-6">
                        <div className="text-sm text-gray-500">
                            Showing <span className="font-semibold text-gray-900">{Math.min(total, (page - 1) * limit + 1)}</span> to{" "}
                            <span className="font-semibold text-gray-900">{Math.min(total, page * limit)}</span> of{" "}
                            <span className="font-semibold text-gray-900">{total}</span> sessions
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="inline-flex items-center justify-center px-3.5 py-2 border border-gray-200 rounded-lg text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:hover:bg-white transition-colors"
                            >
                                Previous
                            </button>
                            <div className="text-sm text-gray-500 px-2">
                                Page <span className="font-semibold text-gray-900">{page}</span> of{" "}
                                <span className="font-semibold text-gray-900">{totalPages}</span>
                            </div>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="inline-flex items-center justify-center px-3.5 py-2 border border-gray-200 rounded-lg text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:hover:bg-white transition-colors"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
