# AI Signal Feed

Automated daily AI digest that fetches from multiple sources, 
filters with AI, and delivers a clean ranked briefing to your 
inbox every morning at 8am — no manual trigger required.


## What It Does

Fetches daily from 3 sources — Arxiv cs.AI/cs.LG, Hacker News, 
and AI newsletters. Sends all content to Groq AI which filters 
and ranks into a structured digest:

- Top 3 Papers — latest AI/ML research worth reading
- Top 3 Industry Moves — what's happening in the field
- Top 3 Tools & Launches — new things worth trying
- Top Job to Know — relevant opportunity if available

Each item has a one-line summary explaining why it matters 
to an AI builder, plus a clickable link. Delivered as an 
HTML email every morning automatically.

## Why I Built This

I was spending 2+ hours daily switching between Arxiv, 
Hacker News, newsletters, and blogs trying to stay current. 
This tool replaced that with a 5-minute morning email. 
Every item passes one test: would an AI engineering student 
act on this today? If not, it gets cut.

## Stack

- Python 3.13
- Arxiv API
- Hacker News API
- feedparser — RSS parsing
- Groq API (llama-3.3-70b) — filtering and ranking
- Gmail SMTP — HTML email delivery
- Windows Task Scheduler — automated daily runs

## Setup

1. Clone the repo
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\Activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file:
GROQ_API_KEY=your_groq_key
EMAIL_ADDRESS=yourgmail@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient@gmail.com

6. Run manually: `python main.py`
7. Automate: Schedule `run.bat` via Windows Task Scheduler at 8am

## Automation

The included `run.bat` activates the venv and runs the script.
Set it up in Windows Task Scheduler to run daily at 8am:

- Trigger: Daily at 8:00 AM
- Action: Start `run.bat`
- Settings: Run whether user is logged on or not

## Notes

- Free Groq API key at console.groq.com
- Gmail requires an App Password — not your regular password
- RSS feed URLs can break — replace with alternatives if needed

## Project Status

v1.0 — working and automated. Part of a 12-project 


