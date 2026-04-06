
import os
import requests
import feedparser
import xml.etree.ElementTree as ET
from groq import Groq
from email.mime.text import MIMEText #structured emails 
from email.mime.multipart import MIMEMultipart
import smtplib
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import re


load_dotenv(dotenv_path=Path(__file__).parent/".env")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

#Sources
ARXIV_URL = (
    "https://export.arxiv.org/api/query"
    "?search_query=cat:cs.AI+OR+cat:cs.LG"
    "&start=0&max_results=20"
    "&sortBy=submittedDate&sortOrder=descending"
)

HACKERNEWS_URL =  "https://hacker-news.firebaseio.com/v0/topstories.json"


RSS_FEEDS = [
    "https://feeds.feedburner.com/oreilly/radar",
    "https://machinelearningmastery.com/feed/",
]


#How many times to whow per category in final digest
TOP_N = 3


def fetch_arxiv():
    #fetches latest cs.AI papers from Arxiv
    #Returns: list of {title, summary, link} dicts

    print("Fetching Arxiv papers...")
    try:
        response = requests.get(ARXIV_URL, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print(" x Arxiv timeout")
        return []
    except requests.exceptions.ConnectionError:
        print("  x Arxiv connection error")
        return[]
    except requests.exceptions.HTTPError as e:
        print(f" x Arxiv HTTP error : {e}")
        return[]

    
    namespace = {"atom": "http://www.w3.org/2005/Atom"}

    try: 
        root = ET.fromstring(response.text)
    except ET.ParseError:
        print(" x Arxiv XML parse error ")
        return []

    entries = root.findall("atom:entry", namespace) 
    items = []

    for entry in entries[:10]:
        title = entry.find("atom:title", namespace).text.strip()
        summary = entry.find("atom:summary", namespace).text.strip()
        link = entry.find("atom:id", namespace).text.strip()
        items.append({
            "source": "Arxiv",
            "title": title,
            "summary": summary[:200],
            "link": link
        
        })
    print(f" Fetched {len(items)} papers")
    return items


def fetch_feeds(feed_urls):
    #fetches RSS feeds - Anthropic blog, DeepLearning.AI
    #Uses feedparser library
    #Returns: list of {title, summary, link} dicts

    print("Fetching RSS feeds...")
    items = []
    

    for url in feed_urls:
        try:
            feed = feedparser.parse(url)

            if feed.bozo:
                print(f" x feed parse warning: {url}")
                continue

            for entry in feed.entries[:5]:
                title = entry.get("title", "No title")
                link = entry.get("link", url)  # ← must come before summary
                summary = entry.get("summary", "") or entry.get("description", "") or "No summary available"
                summary = re.sub(r'<[^>]+>', '', summary)[:200]

                items.append({
                    "source": feed.feed.get("title", url),
                    "title": title,
                    "summary": summary,
                    "link": link
                })    


            print(f"Fetched {len(feed.entries[:5])} items from {feed.feed.get('title', url)}")
        except Exception as e:
            print(f" x feed error {url}: {e}")
            continue


    return items




def fetch_hackernews():
    #hits hacker news api for top AI stories
    #returns: list of {title, summary, url} dicts
    print("Fetching Hacker News stories...")

    try:
        response = requests.get(HACKERNEWS_URL, timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:30]
    
    except Exception as e:
        print(f" x HackerNews error: {e}")
        return []

    items = []
    ai_keywords = [
        "ai", "llm","gpt","claude","machine learning",
        "neural","openai","anthropic","agent","model"
    ]

    for story_id in story_ids:
        if len(items) >= 10:
            break
        try:
            story_url =  f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story = requests.get(story_url, timeout=5).json()

            if not story or story.get("type")!= "story":
                continue

            title = story.get("title", "").lower()
            if not any(keyword in title for keyword in ai_keywords):
                continue


            items.append({
                "source": "Hacker News",
                "title": story.get("title", ""),
                "summary": f"HN Score: {story.get('score', 0)} points| {story.get('descendants', 0)} comments",
                "link": story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
            })
        except Exception:
            continue
        
    print(f" Fetched {len(items)} AI stories")
    return items
    


    #takes combined list from all sources 
    #sends to AI with structured ranking prompt
    #returns : formatted digest string
def analyze_and_rank(all_items):
    
    print(f" Sending {len(all_items)} items to Groq for analysis...")

    items_text = ""
    for i, item in enumerate(all_items, 1):
        items_text += f"\n[{i}] SOURCE: {item['source']}\n"
        items_text += f"TITLE: {item['title']}\n"
        items_text += f"SUMMARY: {item['summary']}\n"
        items_text += f"LINK: {item['link']}\n"

    prompt = f""" You are a signal filter for an AI engineering student. 
    Today's date: {datetime.now().strftime('%B %d, %Y')}

    From the items below, select and rank the most relevant ones.
    Return EXACTLY this structure:

    TOP 3 PAPERS:
    1. [Title] - [One sentence why this matters to an AI builder] - [Link]
    2. ....
    3. ....

    TOP 3 INDUSTRY MOVES:
    1. [TITLE] - [One sentence why this matters]- [Link]
    2. ...
    3. ...

    TOP 3 TOOLS & LAUNCHES:
    1. [Title]- [One sentence why this matters] - [Link]
    2. ... 
    3. ...


"TOP JOB TO KNOW: If no actual job listing is available, skip this section entirely rather than filling it with an article."
    1. [Title]- [One sentence why this matters] - [Link]

    SELECTION RULES:
    - Every item must pass this test: would an AI engineering student act on this today?
    - if a category has fewer than 3 relevant items, include fewer never pad
    - No sports, no celebrity, no politics, no AI in cooking Strories 
    - if an item has no clear relevance to AI builders, cut it

Here are today's items:
{items_text}"""

    try:
        response = client.chat.completions.create(
             model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content": prompt}],
            max_tokens=1500
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f" x Groq error: {e}")
        return None



def format_email(digest_content):
    today = datetime.now().strftime("%B %d, %Y")

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px;
                 margin: 0 auto; padding: 20px; color: #111;">

        <h1 style="color: #1a1a2e; border-bottom: 2px solid #6366f1;
                   padding-bottom: 10px;">
            🧠 AI Signal Feed
        </h1>
        <p style="color: #666; font-size: 14px;">{today}</p>

        <div style="background: #f5f3ff; padding: 15px;
                    border-left: 4px solid #6366f1; margin: 20px 0;">
            <pre style="white-space: pre-wrap; font-family: Arial;
                        font-size: 14px; line-height: 1.6;">
{digest_content}
            </pre>
        </div>

        <p style="color: #999; font-size: 12px; margin-top: 30px;">
            Generated by Signal Feed · Your daily AI intelligence briefing
        </p>
    </body>
    </html>
    """
    return html

def send_email(content):
    #returns: True on successs, false on failure
    email_address = os.environ.get("EMAIL_ADDRESS")
    email_password = os.environ.get("EMAIL_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    if not email_address or not email_password or not recipient:
        print("x Missing email credentials in .env")
        return False

    subject = f"AI Signal Feed - {datetime.now().strftime('%B %d, %Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_address
    msg["To"] = recipient

    plain = MIMEText(content, "plain", "utf-8")
    html = MIMEText(format_email(content), "html", "utf-8")

    msg.attach(plain)
    msg.attach(html)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.sendmail(email_address, recipient, msg.as_string())

        print(f" Email sent to {recipient}")
        return True

    except smtplib.SMTPAuthenticationError:
        print(" x Gmail rejected login - check app Password")
        return False
    except smtplib.SMTPException as e:
        print(f" x Email failed: {e}")
        return False



    #Orchestrator - calls all functions in order 
    #Entry point 
def run_signal_feed():
    print(f"\n{'='*50}")
    print(f"  AI SIGNAL FEED")
    print(f"  {datetime.now().strftime('%B %d, %Y %H:%M')}")
    print(f"{'='*50}\n")

    # Step 1: Fetch from all sources
    all_items = []

    arxiv_items = fetch_arxiv()
    all_items.extend(arxiv_items)

    hn_items = fetch_hackernews()
    all_items.extend(hn_items)

    feed_items = fetch_feeds(RSS_FEEDS)
    all_items.extend(feed_items)

    print(f"\nTotal items collected: {len(all_items)}")

    # Step 2: Check we have enough to work with
    if len(all_items) < 5:
        print(" Not enough items fetched. Aborting: no email sent.")
        return

    # Step 3: Analyze and rank
    digest = analyze_and_rank(all_items)

    if digest is None:
        print(" AI analysis failed. Aborting — no email sent.")
        return

    # Step 4: Send email
    print("\nSending email...")
    success = send_email(digest)

    if success:
        print("\n Signal Feed delivered successfully.")
    else:
        print("\n Signal Feed failed.")


if __name__ == "__main__":
    run_signal_feed()
    
