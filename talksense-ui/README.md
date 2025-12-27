# TalkSense AI 🎙️

> **Turn your conversations into actionable insights.**

**TalkSense AI** is a cutting-edge web application designed to analyze audio calls—whether they are sales pitches or team meetings—and provide deep, actionable intelligence. By leveraging advanced AI, TalkSense transforms raw audio into structured summaries, sentiment analysis, and key insights, helping you make better decisions faster.

---

## 🚀 Features

- **Multi-Mode Analysis**: Specialized analysis for **Sales Calls** and **Meetings**.
- **Smart Summarization**: Get concise summaries of long conversations instantly.
- **Sentiment Tracking**: Visualize the emotional tone of the conversation with sentiment scores.
- **Key Insights**: Automatically extract critical points like "Budget Confirmed", "Action Items", and "Key Decision Makers".
- **Interactive Transcript**: Navigate through the call with time-stamped, sentiment-tagged transcripts.
- **Modern UI**: A sleek, responsive interface built for a premium user experience.

---

## 🛠️ Tech Stack

This project is built with a modern frontend stack ensuring performance and scalability:

- **Frontend Framework**: [React](https://react.dev/) (v19)
- **Build Tool**: [Vite](https://vitejs.dev/) - Super fast development server.
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework.
- **Routing**: [React Router](https://reactrouter.com/) (v7)

---

## 📦 Getting Started

Follow these steps to set up the project locally on your machine.

### Prerequisites

Ensure you have the following installed:
- **Node.js** (v18 or higher recommended)
- **npm** (comes with Node.js)

### Installation

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <repository-url>
   cd talksense-ui
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

### Running the App

Start the development server:
```bash
npm run dev
```

Open your browser and navigate to `http://localhost:5173` (or the URL shown in your terminal) to view the application.

---

## 📂 Project Structure

```
talksense-ui/
├── src/
│   ├── components/    # Reusable UI components
│   ├── mock/          # Mock data for analysis (e.g., analysis.json)
│   ├── pages/         # Application pages (UploadPage, ResultsPage)
│   ├── App.jsx        # Main application component with routing
│   └── main.jsx       # Entry point
├── public/            # Static assets
├── index.html         # HTML entry point
├── package.json       # Project dependencies and scripts
└── tailwind.config.js # Tailwind CSS configuration
```

---