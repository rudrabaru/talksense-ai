// API service for TalkSense AI backend integration

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Analyze audio file with backend
 * @param {File} file - Audio file to analyze
 * @param {string} mode - Analysis mode ('meeting' or 'sales')
 * @returns {Promise<Object>} Analysis results
 */
export async function analyzeAudio(file, mode = 'meeting') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);

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
                    time: '00:15',
                    text: mode === 'sales'
                        ? "Thanks for taking the time today. I'd love to understand your current workflow challenges."
                        : "Let's start with the Q4 roadmap discussion. I want to make sure we're all aligned on priorities.",
                    sentiment: 0.7,
                    sentiment_label: 'positive'
                },
                {
                    time: '01:23',
                    text: mode === 'sales'
                        ? "We're struggling with manual data entry. It's taking up 30% of our team's time."
                        : "I think we need to be realistic about the timeline. December is really tight for a full mobile release.",
                    sentiment: 0.3,
                    sentiment_label: 'negative'
                },
                {
                    time: '02:45',
                    text: mode === 'sales'
                        ? "Your automation features look promising. How does pricing work for teams of 50+?"
                        : "Agreed on mobile-first. The customer feedback has been clear on this point.",
                    sentiment: 0.8,
                    sentiment_label: 'positive'
                },
                {
                    time: '04:12',
                    text: mode === 'sales'
                        ? "We'd need to see ROI within 6 months to justify the investment to our CFO."
                        : "We'll need budget approval before we can commit resources to this timeline.",
                    sentiment: 0.5,
                    sentiment_label: 'neutral'
                },
                {
                    time: '05:30',
                    text: mode === 'sales'
                        ? "I'm confident this could work. Let me schedule a follow-up with our technical team."
                        : "I'm confident we can deliver if we scope it properly and get the right support.",
                    sentiment: 0.75,
                    sentiment_label: 'positive'
                }
            ]
        },
        insights: mode === 'sales' ? {
            summary: "Productive sales call with strong engagement. Client has clear pain points around manual processes and is evaluating ROI. Technical validation meeting needed as next step.",
            sentiment_score: 0.65,
            sentiment_label: "Positive / Engaged",
            quality: { label: "High", score: 0.87 },
            duration: "28:15",
            key_insights: [
                { text: "Client spending 30% of team time on manual data entry - strong pain point", type: "positive" },
                { text: "ROI requirement: must show value within 6 months", type: "blocker" },
                { text: "Pricing discussion for 50+ user enterprise plan", type: "decision" },
                { text: "Technical validation meeting scheduled as next step", type: "positive" }
            ],
            action_plan: [
                "Action: Prepare ROI calculator showing 6-month payback (@Sales)",
                "Action: Send enterprise pricing proposal for 50+ users (@Sales)",
                "Decision: Schedule technical validation call with client's engineering team",
                "Action: Follow up with case studies from similar-sized companies (@Marketing)"
            ]
        } : {
            summary: "Discussion focused on Q4 product roadmap priorities. Team aligned on mobile-first approach with concerns about timeline feasibility. Three key decisions made regarding feature prioritization.",
            sentiment_score: 0.65,
            sentiment_label: "Positive / Engaged",
            quality: { label: "High", score: 0.87 },
            duration: "32:45",
            key_insights: [
                { text: "Team unanimously agreed on mobile-first strategy for Q4", type: "decision" },
                { text: "Timeline concerns raised by engineering regarding December delivery", type: "risk" },
                { text: "Budget approval needed from finance before final commitment", type: "blocker" },
                { text: "Strong alignment on customer feedback integration approach", type: "positive" }
            ],
            action_plan: [
                "Decision: Prioritize mobile app development for Q4 launch",
                "Action: Sarah to prepare detailed timeline analysis (@Sarah)",
                "Action: Mike to schedule budget review meeting with finance (@Mike)",
                "Decision: Weekly sync meetings every Thursday at 2pm"
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
    } catch (error) {
        throw new Error('Backend is not available');
    }
}
