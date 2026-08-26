"""
데이터센터 산업 뉴스 자동 수집 & 이메일 발송 스크립트
- Claude/OpenAI 등 AI API를 전혀 사용하지 않습니다 (RSS + 키워드 필터링만 사용, 완전 무료)
- GitHub Actions에서 매일 자동 실행되도록 설계되었습니다

사용 방법:
    python fetch_datacenter_news.py

환경변수 (GitHub Actions Secrets 또는 로컬 .env):
    SMTP_HOST      예: smtp.gmail.com
    SMTP_PORT      예: 587
    SMTP_USER      보내는 사람 이메일 (예: your@gmail.com)
    SMTP_PASSWORD  이메일 앱 비밀번호 (Gmail은 일반 로그인 비밀번호 아님, 아래 README 참고)
    MAIL_TO        받는 사람 이메일 (여러 명이면 콤마로 구분)
"""

import os
import re
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
from deep_translator import GoogleTranslator

# ---------------------------------------------------------------------------
# 1. 설정: RSS 피드 목록 (자유롭게 추가/삭제 가능)
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    ("Data Center Knowledge", "https://www.datacenterknowledge.com/rss.xml"),
    ("Data Center Dynamics", "https://www.datacenterdynamics.com/en/rss/"),
    ("Data Center Frontier", "https://www.datacenterfrontier.com/rss.xml"),
    ("Utility Dive", "https://www.utilitydive.com/feeds/news/"),
    ("Reuters Technology", "https://www.reutersagency.com/feed/?best-topics=tech"),
]

# 이 키워드 중 하나라도 제목/요약에 포함되면 채택 (대소문자 무시)
KEYWORDS = [
    "data center", "datacenter", "hyperscale", "hyperscaler",
    "power grid", "grid interconnect", "interconnection queue",
    "AI infrastructure", "gigawatt", "megawatt", "nuclear power",
    "electricity demand", "utility", "cooling", "FERC", "PJM", "ERCOT",
    "server farm", "cloud infrastructure",
]

# 최근 며칠 이내 기사만 포함할지
LOOKBACK_DAYS = 2

# 뉴스레터에 최대 몇 개까지 포함할지
MAX_ITEMS = 10

# 한글로 번역할지 여부 (Claude/OpenAI API 아님, 무료 Google 번역 라이브러리 사용)
TRANSLATE_TO_KOREAN = True


def translate_ko(text: str) -> str:
    if not TRANSLATE_TO_KOREAN or not text:
        return text
    try:
        return GoogleTranslator(source="auto", target="ko").translate(text)
    except Exception as e:
        print(f"[경고] 번역 실패, 원문 그대로 사용: {e}")
        return text


def is_relevant(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)


def is_recent(entry) -> bool:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return True  # 날짜 정보 없으면 일단 포함
    published_dt = datetime(*published[:6], tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    return published_dt >= cutoff


def clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw or "")
    return re.sub(r"\s+", " ", text).strip()


def collect_news():
    items = []
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[경고] {source_name} 피드를 가져오지 못했습니다: {e}")
            continue

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")

            if not title or not link:
                continue
            if not is_recent(entry):
                continue
            if not is_relevant(title, summary):
                continue

            trimmed_summary = summary[:220] + ("…" if len(summary) > 220 else "")

            items.append({
                "source": source_name,
                "title": translate_ko(title),
                "summary": translate_ko(trimmed_summary),
                "link": link,
            })

    # 중복 제거 (제목 기준)
    seen = set()
    deduped = []
    for item in items:
        key = item["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped[:MAX_ITEMS]


def build_html_email(items):
    today = datetime.now().strftime("%Y년 %m월 %d일")

    if not items:
        body_html = "<p style='color:#666;'>오늘은 조건에 맞는 새 뉴스가 없었습니다.</p>"
    else:
        rows = []
        for item in items:
            rows.append(f"""
            <div style="margin-bottom:20px; padding-bottom:16px; border-bottom:1px solid #eee;">
                <div style="font-size:12px; color:#888; margin-bottom:4px;">{item['source']}</div>
                <a href="{item['link']}" style="font-size:16px; font-weight:600; color:#1a56db; text-decoration:underline;">
                    {item['title']}
                </a>
                <p style="font-size:14px; color:#555; margin:6px 0 8px; line-height:1.6;">{item['summary']}</p>
                <a href="{item['link']}" style="font-size:13px; color:#1a56db; text-decoration:underline;">
                    원문 보기 →
                </a>
            </div>
            """)
        body_html = "".join(rows)

    return f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width:640px; margin:0 auto;">
        <div style="background:#0b0f1a; color:#fff; padding:20px 24px; border-radius:8px 8px 0 0;">
            <div style="font-size:18px; font-weight:700;">DCNI · Data Center Industry News</div>
            <div style="font-size:13px; opacity:0.75; margin-top:6px;">{today}</div>
        </div>
        <div style="border:1px solid #eee; border-top:none; padding:20px 24px; border-radius:0 0 8px 8px;">
            {body_html}
        </div>
    </div>
    """


def send_email(html_body: str):
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    mail_to = os.environ["MAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[DCNI] 데이터센터 산업 뉴스 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = smtp_user
    msg["To"] = mail_to

    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, mail_to.split(","), msg.as_string())

    print(f"이메일 발송 완료: {mail_to}")


def main():
    print("뉴스 수집 시작...")
    items = collect_news()
    print(f"{len(items)}건의 관련 뉴스를 찾았습니다.")

    html_body = build_html_email(items)
    send_email(html_body)


if __name__ == "__main__":
    main()
