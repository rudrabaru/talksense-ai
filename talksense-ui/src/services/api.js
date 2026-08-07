// API service for TalkSense AI backend integration

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Analyze audio file with backend
 * @param {File} file - Audio file to analyze
 * @param {string} mode - Analysis mode ('meeting' or 'sales')
 * @returns {Promise<Object>} Analysis results
 */
export async function analyzeAudio(file, mode = 'meeting', clientId = null) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    if (clientId) {
        formData.append('client_id', clientId);
    }

    const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Analysis failed' }));
        throw new Error(error.detail || 'Failed to analyze audio');
    }

    return response.json();
}

/**
 * Load demo data (mock for now, can be replaced with backend endpoint)
 * NOTE: This provides offline demo data for testing when backend is unavailable.
 * Data structure mirrors actual /analyze response for consistency.
 * @param {string} mode - Analysis mode ('meeting' or 'sales')
 * @returns {Promise<Object>} Demo analysis results
 */
export async function loadDemoData(mode = 'meeting') {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));

    return {
        filename: 'demo_conversation.m4a',
        mode: mode,
        transcript: {
            text: mode === 'sales'
                ? "Discussion about Q4 product roadmap and pricing strategy. Client expressed interest in enterprise features."
                : "Team meeting discussing Q4 priorities, timeline concerns, and budget approval needs.",
            segments: [
                {
                    start: 15,
                    end: 45,
                    text: mode === 'sales'
                        ? "Thanks for taking the time today. I'd love to understand your current workflow challenges."
                        : "Let's start with the Q4 roadmap discussion. I want to make sure we're all aligned on priorities.",
                    sentiment: 0.7,
                    sentiment_label: 'Positive'
                },
                {
                    start: 83,
                    end: 120,
                    text: mode === 'sales'
                        ? "We're struggling with manual data entry. It's taking up 30% of our team's time."
                        : "I think we need to be realistic about the timeline. December is really tight for a full mobile release.",
                    sentiment: -0.3,
                    sentiment_label: 'Negative'
                },
                {
                    start: 165,
                    end: 200,
                    text: mode === 'sales'
                        ? "Your automation features look promising. How does pricing work for teams of 50+?"
                        : "Agreed on mobile-first. The customer feedback has been clear on this point.",
                    sentiment: 0.8,
                    sentiment_label: 'Positive'
                },
                {
                    start: 252,
                    end: 290,
                    text: mode === 'sales'
                        ? "We'd need to see ROI within 6 months to justify the investment to our CFO."
                        : "We'll need budget approval before we can commit resources to this timeline.",
                    sentiment: 0.0,
                    sentiment_label: 'Neutral'
                },
                {
                    start: 330,
                    end: 365,
                    text: mode === 'sales'
                        ? "I'm confident this could work. Let me schedule a follow-up with our technical team."
                        : "I'm confident we can deliver if we scope it properly and get the right support.",
                    sentiment: 0.75,
                    sentiment_label: 'Positive'
                }
            ]
        },
        insights: mode === 'sales' ? {
            summary: "Productive sales call with strong engagement. Client has clear pain points around manual processes and is evaluating ROI. Technical validation meeting needed as next step.",
            sentiment_score: 0.65,
            overall_call_sentiment: "positive",
            quality: { label: "High", score: 8, drivers: ["Hard commitment locked", "Value articulated"] },
            key_insights: [
                { text: "Client spending 30% of team time on manual data entry - strong pain point", type: "Positive Momentum" },
                { text: "ROI requirement: must show value within 6 months", type: "Execution Risk" },
                { text: "Pricing discussion for 50+ user enterprise plan", type: "Decision Ambiguity" },
                { text: "Technical validation meeting scheduled as next step", type: "Positive Momentum" }
            ],
            objections: [
                { type: "Pricing", text: "How does pricing work for teams of 50+?", time: 165 },
                { type: "Authority", text: "We'd need to see ROI within 6 months to justify the investment to our CFO", time: 252 }
            ],
            recommended_actions: [
                "Send pricing clarification",
                "Follow up after internal discussion"
            ]
        } : {
            summary: "Discussion focused on Q4 product roadmap priorities. Team aligned on mobile-first approach with concerns about timeline feasibility. Three key decisions made regarding feature prioritization.",
            sentiment_score: 0.65,
            overall_sentiment_label: "Neutral / Focused",
            quality: { label: "High", score: 8, drivers: ["Decisions finalized", "Ownership assigned"] },
            key_insights: [
                { text: "Team unanimously agreed on mobile-first strategy for Q4", type: "Positive Momentum" },
                { text: "Timeline concerns raised by engineering regarding December delivery", type: "Execution Risk" },
                { text: "Budget approval needed from finance before final commitment", type: "Ownership Gap" },
                { text: "Strong alignment on customer feedback integration approach", type: "Positive Momentum" }
            ],
            decisions: [
                { text: "Prioritize mobile app development for Q4 launch", time: 165 },
                { text: "Weekly sync meetings every Thursday at 2pm", time: 330 }
            ],
            action_items: [
                { task: "Prepare detailed timeline analysis", owner: "Sarah", deadline: "Friday", time: 200 },
                { task: "Schedule budget review meeting with finance", owner: "Mike", deadline: "Next week", time: 252 }
            ]
        }
    };
}

/**
 * Health check for backend
 * @returns {Promise<Object>} Health status
 */
export async function healthCheck() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.json();
    } catch {
        throw new Error('Backend is not available');
    }
}

/**
 * Create a new session with the backend
 * @param {string} mode - Session mode ('meeting' or 'sales')
 * @param {string|null} clientId - Optional client ID to link
 * @returns {Promise<Object>} Session creation result containing session_id
 */
export async function createSession(mode = 'meeting', clientId = null) {
    let url = `${API_BASE_URL}/sessions?mode=${mode}`;
    if (clientId) {
        url += `&client_id=${clientId}`;
    }
    const response = await fetch(url, {
        method: 'POST',
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to create session' }));
        throw new Error(error.detail || 'Failed to create session');
    }

    const data = await response.json();
    if (data.ws_token) {
        localStorage.setItem(`ws_token_${data.session_id}`, data.ws_token);
    }
    return data;
}

/**
 * Get session details to validate existence
 * @param {string} sessionId - ID of the session to validate
 * @returns {Promise<Object>} Session details
 */
export async function getSession(sessionId) {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Session not found' }));
        throw new Error(error.detail || 'Session not found');
    }

    return response.json();
}

/**
 * Get paginated list of sessions with filters and search
 * @param {Object} params - Query parameters (page, limit, mode, status, client_id, search, sort_by, sort_order)
 * @returns {Promise<Object>} Paginated sessions response
 */
export async function listSessions(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== '') {
            query.append(key, val);
        }
    });

    const response = await fetch(`${API_BASE_URL}/sessions?${query.toString()}`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to fetch sessions' }));
        throw new Error(error.detail || 'Failed to fetch sessions');
    }

    return response.json();
}

/**
 * List all clients from backend
 * @returns {Promise<Array>} List of clients
 */
export async function listClients() {
    const response = await fetch(`${API_BASE_URL}/clients`);
    if (!response.ok) {
        throw new Error('Failed to fetch clients');
    }
    return response.json();
}

/**
 * Get client briefing card details by ID
 * @param {string} clientId - The ID of the client
 * @returns {Promise<Object>} Client briefing card data
 */
export async function getClientBriefing(clientId) {
    const response = await fetch(`${API_BASE_URL}/clients/${clientId}`);
    if (!response.ok) {
        throw new Error('Failed to fetch client briefing');
    }
    return response.json();
}

/**
 * Create a new client profile
 * @param {Object} clientData - Client data { name, industry }
 * @returns {Promise<Object>} Created client profile
 */
export async function createClient(clientData) {
    const response = await fetch(`${API_BASE_URL}/clients`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(clientData),
    });
    if (!response.ok) {
        throw new Error('Failed to create client');
    }
    return response.json();
}

/**
 * Compare two completed sessions and return a ComparisonResult.
 * @param {string} id1 - UUID of the first session
 * @param {string} id2 - UUID of the second session
 * @returns {Promise<Object>} ComparisonResult with delta, shared/unique lists, action items
 */
export async function compareSessions(id1, id2) {
    const response = await fetch(
        `${API_BASE_URL}/sessions/compare?id1=${encodeURIComponent(id1)}&id2=${encodeURIComponent(id2)}`
    );

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Comparison failed' }));
        throw new Error(error.detail || 'Failed to compare sessions');
    }

    return response.json();
}

/**
 * Get active diarization engine configuration from backend
 * @returns {Promise<Object>} { engine: string }
 */
export async function getDiarizationEngine() {
    try {
        const response = await fetch(`${API_BASE_URL}/engine`);
        if (!response.ok) {
            throw new Error('Failed to fetch engine');
        }
        return await response.json();
    } catch (err) {
        console.error('Error fetching diarization engine:', err);
        return { engine: 'error' };
    }
}
