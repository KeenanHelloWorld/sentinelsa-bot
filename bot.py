import os
import re
import feedparser
import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
SAST = timezone(timedelta(hours=2))
VERSION = "v2.0"

KEYWORDS = [
    "riot", "protest", "looting", "shooting", "violence", "strike",
    "burning", "roadblock", "unrest", "attack", "mob", "marching",
    "arrested", "injured", "killed",
]

GAUTENG_TERMS = [
    # Province-level
    "gauteng",

    # City of Johannesburg
    "johannesburg", "joburg", "jozi",
    "soweto", "alexandra", "alex", "sandton", "randburg", "roodepoort",
    "diepsloot", "midrand", "orange farm", "eldorado park", "westbury",
    "hillbrow", "berea", "yeoville", "newtown", "fordsburg", "mayfair",
    "lenasia", "ennerdale", "turffontein", "booysens", "cyrildene",
    "norwood", "rosebank", "parktown", "braamfontein", "auckland park",
    "melville", "brixton", "sophiatown", "weltevreden park", "honeydew",
    "northriding", "fourways", "sunninghill", "rivonia", "bryanston",
    "greenside", "linden", "emmarentia", "houghton", "saxonwold",
    "kyalami", "waterfall", "jeppestown", "florida", "naturena",
    "devland", "stretford", "poortjie", "protea glen", "meadowlands",
    "dobsonville", "tladi", "moletsane", "naledi", "jabulani", "orlando",
    "dube", "kliptown", "zola", "zondi", "mapetla",

    # City of Tshwane
    "pretoria", "tshwane",
    "mamelodi", "soshanguve", "atteridgeville", "centurion",
    "mabopane", "ga-rankuwa", "hammanskraal", "temba",
    "silverton", "arcadia", "hatfield", "brooklyn", "menlyn",
    "garsfontein", "moreleta park", "faerie glen", "wonderboom",
    "akasia", "pretoria north", "pretoria west", "silverlakes",
    "muckleneuk", "lynnwood", "waterkloof", "wierda park",
    "olievenhoutbosch", "erasmia", "laudium", "eersterust",
    "mamelodi east", "nellmapius",

    # Ekurhuleni
    "ekurhuleni",
    "germiston", "benoni", "boksburg", "brakpan", "springs", "edenvale",
    "kempton park", "alberton", "vosloorus", "katlehong", "tembisa",
    "daveyton", "duduza", "tsakane", "wattville", "etwatwa",
    "actonville", "thokoza", "reiger park", "geldenhuys", "bedfordview",
    "dawn park", "likole", "langaville", "kwathema", "zonkizizwe",

    # West Rand
    "krugersdorp", "kagiso", "bekkersdal", "westonaria", "carletonville",
    "randfontein", "mohlakeng", "fochville", "kokosi", "wedela",
    "azaadville", "chamdor", "munsieville",

    # Sedibeng
    "vereeniging", "vanderbijlpark", "sebokeng", "evaton", "meyerton",
    "sharpeville", "boipatong", "bophelong", "tshepiso", "rust ter vaal",
    "walker lake", "oranjeville", "heidelberg", "ratanda",

    # Other Gauteng areas
    "bronkhorstspruit", "cullinan", "rayton", "bapsfontein",
    "nigel", "devon", "delmas", "balfour",
]

FEEDS = {
    "GNews: Police & SAPS":     "https://news.google.com/rss/search?q=SAPS+OR+police+gauteng&hl=en-ZA&gl=ZA&ceid=ZA:en",
    "GNews: Unrest & Protest":  "https://news.google.com/rss/search?q=unrest+OR+riot+OR+protest+gauteng&hl=en-ZA&gl=ZA&ceid=ZA:en",
    "GNews: Shooting & Attack": "https://news.google.com/rss/search?q=shooting+OR+attack+johannesburg+OR+gauteng&hl=en-ZA&gl=ZA&ceid=ZA:en",
    "GNews: Looting & Burning": "https://news.google.com/rss/search?q=looting+OR+burning+OR+arson+gauteng&hl=en-ZA&gl=ZA&ceid=ZA:en",
    "GNews: Strike & Roadblock":"https://news.google.com/rss/search?q=strike+OR+roadblock+OR+shutdown+gauteng&hl=en-ZA&gl=ZA&ceid=ZA:en",
    "News24 SA":                "https://feeds.news24.com/articles/news24/SouthAfrica/rss",
    "News24 Breaking":          "https://feeds.news24.com/articles/news24/TopStories/rss",
    "IOL":                      "https://www.iol.co.za/rss",
    "SABC News":                "https://www.sabcnews.com/sabcnews/feed/",
}

FEED_CATEGORIES = {
    "GNews: Police & SAPS":     "🚔 Police / SAPS",
    "GNews: Unrest & Protest":  "✊ Unrest / Protest",
    "GNews: Shooting & Attack": "🔫 Shooting / Attack",
    "GNews: Looting & Burning": "🔥 Looting / Burning",
    "GNews: Strike & Roadblock":"🚧 Strike / Roadblock",
    "News24 SA":                "📰 News",
    "News24 Breaking":          "📰 Breaking News",
    "IOL":                      "📰 News",
    "SABC News":                "📰 News",
}

THREAT_LEVELS = ["LOW", "MEDIUM", "HIGH"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_threat_level(source_count: int) -> str:
    if source_count >= 4:
        return "HIGH"
    elif source_count >= 2:
        return "MEDIUM"
    return "LOW"

def threat_emoji(level: str) -> str:
    return {"LOW": "🟡", "MEDIUM": "🟠", "HIGH": "🔴"}.get(level, "⚪")

def threat_bar(level: str) -> str:
    bars = {"LOW": "▰▱▱▱▱", "MEDIUM": "▰▰▰▱▱", "HIGH": "▰▰▰▰▰"}.get(level, "▱▱▱▱▱")
    return f"{bars} {level}"

def threat_description(level: str) -> str:
    return {
        "LOW":    "1 source — unconfirmed report",
        "MEDIUM": "2–3 sources — likely confirmed",
        "HIGH":   "4+ sources — major incident confirmed",
    }.get(level, "")

def sast_now() -> datetime:
    return datetime.now(SAST)

def to_sast(dt: datetime) -> datetime:
    return dt.astimezone(SAST)

def fmt_time(dt: datetime) -> str:
    return to_sast(dt).strftime("%H:%M SAST")

def fmt_datetime(dt: datetime) -> str:
    return to_sast(dt).strftime("%d %b %Y, %H:%M SAST")

def time_ago(dt: datetime) -> str:
    diff = datetime.now(timezone.utc) - dt
    mins = int(diff.total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    rem = mins % 60
    return f"{hours}h {rem}m ago" if rem else f"{hours}h ago"

def extract_casualties(texts: list[str]) -> dict:
    killed = injured = arrested = 0
    for text in texts:
        t = text.lower()
        for m in re.findall(r'(\d+)\s+(?:people\s+)?killed', t):
            killed = max(killed, int(m))
        for m in re.findall(r'(\d+)\s+(?:people\s+)?(?:injured|wounded|hospitalised|hospitalized)', t):
            injured = max(injured, int(m))
        for m in re.findall(r'(\d+)\s+(?:people\s+)?arrested', t):
            arrested = max(arrested, int(m))
    return {"killed": killed, "injured": injured, "arrested": arrested}

def extract_locations(texts: list[str]) -> list[str]:
    found = set()
    for text in texts:
        t = text.lower()
        for area in GAUTENG_TERMS:
            if area in t:
                found.add(area.title())
    return sorted(found)

def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()

def short_title(t: str, n: int = 72) -> str:
    return t[:n] + "…" if len(t) > n else t

def header(title: str) -> str:
    return f"🛡 *SentinelSA*  ·  {title}"

def footer() -> str:
    return f"_Gauteng Intelligence Monitor  ·  {VERSION}_"

def divider() -> str:
    return "─────────────────────"

# ── State ─────────────────────────────────────────────────────────────────────

STATE_FILE = "state.json"

incident_clusters: dict = {}
incident_index: list = []
seen_urls: set = set()
subscribed_chats: set = set()
last_scan_summary: dict = {
    "time": None, "feeds_checked": 0, "entries_scanned": 0, "matches": 0,
}


def save_state():
    try:
        clusters_serial = {}
        for k, c in incident_clusters.items():
            key_str = f"{k[0]}|{k[1]}"
            clusters_serial[key_str] = {
                **c,
                "sources": list(c["sources"]),
                "created_at": c["created_at"].isoformat(),
                "updated_at": c.get("updated_at", c["created_at"]).isoformat(),
            }
        index_serial = [f"{k[0]}|{k[1]}" for k in incident_index]
        data = {
            "seen_urls": list(seen_urls),
            "subscribed_chats": list(subscribed_chats),
            "incident_clusters": clusters_serial,
            "incident_index": index_serial,
        }
        with open(STATE_FILE, "w") as f:
            import json
            json.dump(data, f)
        log.info(f"State saved: {len(seen_urls)} URLs, {len(incident_clusters)} clusters")
    except Exception as e:
        log.error(f"Failed to save state: {e}")


def load_state():
    global seen_urls, subscribed_chats, incident_clusters, incident_index
    import json
    if not os.path.exists(STATE_FILE):
        log.info("No saved state found — starting fresh")
        return
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        seen_urls = set(data.get("seen_urls", []))
        subscribed_chats = set(data.get("subscribed_chats", []))
        incident_index.clear()
        for key_str in data.get("incident_index", []):
            parts = key_str.split("|", 1)
            if len(parts) == 2:
                incident_index.append((parts[0], parts[1]))
        incident_clusters.clear()
        for key_str, c in data.get("incident_clusters", {}).items():
            parts = key_str.split("|", 1)
            if len(parts) != 2:
                continue
            key = (parts[0], parts[1])
            incident_clusters[key] = {
                **c,
                "sources": set(c["sources"]),
                "created_at": datetime.fromisoformat(c["created_at"]),
                "updated_at": datetime.fromisoformat(c["updated_at"]),
            }
        log.info(f"State loaded: {len(seen_urls)} URLs, {len(incident_clusters)} clusters, {len(subscribed_chats)} subscribers")
    except Exception as e:
        log.error(f"Failed to load state: {e}")

def get_incident_id(key) -> int:
    if key not in incident_index:
        incident_index.append(key)
    return incident_index.index(key) + 1

def extract_match(title: str, summary: str) -> tuple[str, str]:
    text = (title + " " + summary).lower()
    matched_kw = next((kw for kw in KEYWORDS if kw in text), "")
    matched_area = next((area for area in GAUTENG_TERMS if area in text), "")
    return matched_kw, matched_area

# ── Message builders ──────────────────────────────────────────────────────────

def build_alert_message(cluster: dict, level: str, key) -> tuple[str, InlineKeyboardMarkup]:
    inc_id = get_incident_id(key)
    emoji = threat_emoji(level)
    category = cluster.get("category", "📰 News")
    casualties = extract_casualties(cluster["titles"] + cluster["summaries"])
    locations = extract_locations(cluster["titles"] + cluster["summaries"])
    loc_str = ", ".join(locations[:3]) if locations else cluster["area"].title()

    cas_parts = []
    if casualties["killed"]:   cas_parts.append(f"💀 {casualties['killed']} killed")
    if casualties["injured"]:  cas_parts.append(f"🤕 {casualties['injured']} injured")
    if casualties["arrested"]: cas_parts.append(f"🔒 {casualties['arrested']} arrested")
    cas_line = "   ".join(cas_parts) if cas_parts else "No figures reported yet"

    headlines = list(zip(cluster["titles"], cluster["urls"]))[:3]
    headline_lines = "\n".join(
        f"  `{i+1}.` [{short_title(t)}]({u})" for i, (t, u) in enumerate(headlines)
    )

    text = (
        f"{header(f'NEW ALERT  ·  #{inc_id}')}\n"
        f"{divider()}\n"
        f"{emoji} *{threat_bar(level)}*\n"
        f"_{threat_description(level)}_\n\n"
        f"*{category}*\n"
        f"📍 {loc_str}\n"
        f"🔑 `{cluster['keyword']}`   ·   🕐 {fmt_time(cluster['created_at'])}\n"
        f"📡 {len(cluster['sources'])} source(s) reporting\n\n"
        f"*Casualties:*\n{cas_line}\n\n"
        f"*Latest headlines:*\n{headline_lines}\n\n"
        f"{divider()}\n"
        f"{footer()}"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"🔍 Full Report  ·  #{inc_id}", callback_data=f"incident:{inc_id}"),
        InlineKeyboardButton("📊 Dashboard", callback_data="status"),
    ]])
    return text, keyboard


def build_status_message(active_pairs: list) -> str:
    scan_time = last_scan_summary.get("time")
    time_str = fmt_time(scan_time) if scan_time else "Not yet run"

    grouped: dict[str, list] = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for key, cluster in active_pairs:
        grouped[cluster["alerted_level"]].append((key, cluster))

    counts = {lvl: len(grouped[lvl]) for lvl in THREAT_LEVELS}
    total = sum(counts.values())

    lines = [
        header("INCIDENT DASHBOARD"),
        divider(),
        f"🔴 HIGH  {counts['HIGH']}   "
        f"🟠 MEDIUM  {counts['MEDIUM']}   "
        f"🟡 LOW  {counts['LOW']}",
        f"📡 {len(FEEDS)} feeds   ·   📰 {last_scan_summary.get('entries_scanned', 0)} articles   ·   🕐 {time_str}",
        f"*{total} active incident(s)*",
        "",
    ]

    for level in ["HIGH", "MEDIUM", "LOW"]:
        pairs = grouped[level]
        if not pairs:
            continue
        emoji = threat_emoji(level)
        lines.append(f"{emoji} *{threat_bar(level)}*")
        lines.append(divider())
        for key, c in sorted(pairs, key=lambda x: len(x[1]["sources"]), reverse=True):
            inc_id = get_incident_id(key)
            casualties = extract_casualties(c["titles"] + c["summaries"])
            cas_parts = []
            if casualties["killed"]:   cas_parts.append(f"💀{casualties['killed']}")
            if casualties["injured"]:  cas_parts.append(f"🤕{casualties['injured']}")
            if casualties["arrested"]: cas_parts.append(f"🔒{casualties['arrested']}")
            cas_str = "  ".join(cas_parts)

            locations = extract_locations(c["titles"] + c["summaries"])
            loc_str = ", ".join(locations[:2]) if locations else c["area"].title()

            lines.append(
                f"*#{inc_id}*  {c.get('category','📰')}  ·  `{c['keyword']}`\n"
                f"  📍 {loc_str}\n"
                f"  📡 {len(c['sources'])} source(s)  ·  🕐 {time_ago(c['created_at'])}"
                + (f"  ·  {cas_str}" if cas_str else "") +
                f"\n  _/incident {inc_id}_"
            )
        lines.append("")

    lines += [divider(), footer()]
    return "\n".join(lines)


def build_incident_detail(cluster: dict, level: str, inc_id: int) -> str:
    emoji = threat_emoji(level)
    category = cluster.get("category", "📰 News")
    casualties = extract_casualties(cluster["titles"] + cluster["summaries"])
    locations = extract_locations(cluster["titles"] + cluster["summaries"])
    loc_str = ", ".join(locations) if locations else cluster["area"].title()

    cas_parts = []
    if casualties["killed"]:   cas_parts.append(f"  💀 Killed:    *{casualties['killed']}*")
    if casualties["injured"]:  cas_parts.append(f"  🤕 Injured:   *{casualties['injured']}*")
    if casualties["arrested"]: cas_parts.append(f"  🔒 Arrested:  *{casualties['arrested']}*")
    cas_block = "\n".join(cas_parts) if cas_parts else "  No casualty figures reported"

    all_headlines = [
        f"  `{i+1}.` [{short_title(t, 80)}]({u})"
        for i, (t, u) in enumerate(zip(cluster["titles"], cluster["urls"]))
    ]

    snippet_lines = []
    for s in cluster["summaries"][:3]:
        clean = strip_html(s)
        if clean:
            snippet_lines.append(f'  _"{clean[:130]}…"_')

    source_list = "\n".join(f"  • {s}" for s in sorted(cluster["sources"]))
    updated = cluster.get("updated_at", cluster["created_at"])

    parts = [
        header(f"INCIDENT REPORT  ·  #{inc_id}"),
        divider(),
        f"{emoji} *{threat_bar(level)}*",
        f"_{threat_description(level)}_",
        "",
        f"*Category:*  {category}",
        f"*Keyword:*   `{cluster['keyword']}`",
        "",
        f"📍 *Locations:*",
        f"  {loc_str}",
        "",
        f"⏱ *Timeline:*",
        f"  First detected:  {fmt_datetime(cluster['created_at'])}",
        f"  Last updated:    {fmt_time(updated)}",
        f"  Age:             {time_ago(cluster['created_at'])}",
        "",
        f"🩸 *Casualty Report:*",
        cas_block,
        "",
        f"📰 *Headlines  ({len(cluster['titles'])} articles):*",
        *all_headlines[:8],
    ]
    if len(cluster["titles"]) > 8:
        parts.append(f"  _+ {len(cluster['titles']) - 8} more articles_")
    if snippet_lines:
        parts += ["", "📝 *Snippets:*"] + snippet_lines
    parts += [
        "",
        f"📡 *Sources  ({len(cluster['sources'])}):*",
        source_list,
        "",
        divider(),
        footer(),
    ]
    return "\n".join(parts)

# ── Scanner ───────────────────────────────────────────────────────────────────

async def send_to_all(context, text: str, keyboard: InlineKeyboardMarkup = None):
    for chat_id in list(subscribed_chats):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )
        except Exception as e:
            log.warning(f"Failed to send to {chat_id}: {e}")


async def scan_feeds(context, verbose_chat_id=None):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_entries = 0
    new_matches = 0
    escalations = []

    log.info("=== Starting feed scan ===")

    for source_name, feed_url in FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.entries
            total_entries += len(entries)
            log.info(f"  {source_name}: {len(entries)} entries")

            for entry in entries:
                url = entry.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title   = entry.get("title", "")
                summary = strip_html(entry.get("summary", ""))
                keyword, area = extract_match(title, summary)

                if not keyword or not area:
                    continue

                new_matches += 1
                log.info(f"  MATCH [{source_name}] kw={keyword} area={area} | {title[:70]}")

                cluster_key = (keyword, today)
                if cluster_key not in incident_clusters:
                    incident_clusters[cluster_key] = {
                        "keyword":       keyword,
                        "area":          area,
                        "category":      FEED_CATEGORIES.get(source_name, "📰 News"),
                        "sources":       set(),
                        "titles":        [],
                        "urls":          [],
                        "summaries":     [],
                        "alerted_level": None,
                        "created_at":    datetime.now(timezone.utc),
                        "updated_at":    datetime.now(timezone.utc),
                    }

                cluster = incident_clusters[cluster_key]
                cluster["sources"].add(source_name)
                cluster["updated_at"] = datetime.now(timezone.utc)
                if title not in cluster["titles"]:
                    cluster["titles"].append(title)
                    cluster["urls"].append(url)
                    cluster["summaries"].append(summary)

        except Exception as e:
            log.error(f"  {source_name}: ERROR — {e}")

    for key, cluster in incident_clusters.items():
        current_level = get_threat_level(len(cluster["sources"]))
        alerted_level = cluster["alerted_level"]
        alerted_idx   = THREAT_LEVELS.index(alerted_level) if alerted_level else -1
        current_idx   = THREAT_LEVELS.index(current_level)

        if current_idx > alerted_idx:
            cluster["alerted_level"] = current_level
            text, keyboard = build_alert_message(cluster, current_level, key)
            escalations.append((text, keyboard))
            log.info(f"  ⚠️ ESCALATION: {cluster['keyword']} in {cluster['area']} → {current_level} ({len(cluster['sources'])} sources)")

    for text, keyboard in escalations:
        await send_to_all(context, text, keyboard)

    last_scan_summary["time"]            = datetime.now(timezone.utc)
    last_scan_summary["feeds_checked"]   = len(FEEDS)
    last_scan_summary["entries_scanned"] = total_entries
    last_scan_summary["matches"]         = new_matches

    log.info(f"=== Scan done: {total_entries} entries, {new_matches} new matches, {len(escalations)} alerts ===")

    if verbose_chat_id:
        active = [c for c in incident_clusters.values() if c["alerted_level"]]
        msg = (
            f"{header('SCAN COMPLETE')}\n"
            f"{divider()}\n"
            f"📡 Feeds checked:      {len(FEEDS)}\n"
            f"📰 Articles scanned:   {total_entries}\n"
            f"🔍 New Gauteng matches: {new_matches}\n"
            f"🚨 Alerts sent:        {len(escalations)}\n"
            f"📊 Active incidents:   {len(active)}\n"
            f"{divider()}\n"
            f"{footer()}"
        )
        try:
            await context.bot.send_message(
                chat_id=verbose_chat_id, text=msg, parse_mode="Markdown",
            )
        except Exception:
            pass

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    expired = [k for k, v in incident_clusters.items() if v["created_at"] < cutoff]
    for k in expired:
        del incident_clusters[k]

    save_state()

# ── Callback handler (inline buttons) ────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "status":
        active = [(k, c) for k, c in incident_clusters.items() if c["alerted_level"]]
        if not active:
            await query.message.reply_text(
                f"{header('DASHBOARD')}\n{divider()}\n"
                f"✅ No active incidents.\n{divider()}\n{footer()}",
                parse_mode="Markdown",
            )
        else:
            await query.message.reply_text(
                build_status_message(active),
                parse_mode="Markdown",
            )

    elif data.startswith("incident:"):
        inc_id = int(data.split(":")[1])
        idx = inc_id - 1
        if idx < 0 or idx >= len(incident_index):
            await query.message.reply_text(f"❌ Incident #{inc_id} not found.")
            return
        key = incident_index[idx]
        cluster = incident_clusters.get(key)
        if not cluster:
            await query.message.reply_text(f"❌ Incident #{inc_id} has expired.")
            return
        level = get_threat_level(len(cluster["sources"]))
        await query.message.reply_text(
            build_incident_detail(cluster, level, inc_id),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

# ── Commands ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribed_chats.add(chat_id)
    log.info(f"New subscriber: {chat_id}")
    await update.message.reply_text(
        f"{header('ONLINE')}\n"
        f"{divider()}\n"
        f"You are now subscribed to live Gauteng unrest alerts.\n\n"
        f"*What it monitors:*\n"
        f"  🔫 Shootings & attacks\n"
        f"  ✊ Protests & civil unrest\n"
        f"  🔥 Looting & arson\n"
        f"  🚧 Strikes & road blockages\n"
        f"  🚔 Police operations & arrests\n\n"
        f"*Threat levels:*\n"
        f"  🟡 `▰▱▱▱▱ LOW`     — 1 source, unconfirmed\n"
        f"  🟠 `▰▰▰▱▱ MEDIUM`  — 2–3 sources confirmed\n"
        f"  🔴 `▰▰▰▰▰ HIGH`    — 4+ sources, major incident\n\n"
        f"*Commands:*\n"
        f"  /status       — live incident dashboard\n"
        f"  /incident <id> — full report on one incident\n"
        f"  /scan         — trigger an immediate scan\n"
        f"  /sources      — view all monitored sources\n"
        f"  /keywords     — view all monitored keywords\n"
        f"  /stop         — unsubscribe from alerts\n\n"
        f"{divider()}\n"
        f"Scanning {len(FEEDS)} sources every 5 minutes across 120+ Gauteng areas.\n"
        f"{footer()}",
        parse_mode="Markdown",
    )


async def sources_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [f"  • {name}" for name in FEEDS]
    await update.message.reply_text(
        f"{header('MONITORED SOURCES')}\n"
        f"{divider()}\n"
        f"*{len(FEEDS)} active feeds:*\n"
        + "\n".join(lines) +
        f"\n\n_Google News feeds aggregate 100+ South African publications including "
        f"TimesLive, News24, EWN, SABC, Daily Maverick, eNCA, and SAPS press releases._\n"
        f"{divider()}\n"
        f"{footer()}",
        parse_mode="Markdown",
    )


async def keywords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kw_list = "  " + ",  ".join(f"`{kw}`" for kw in KEYWORDS)
    loc_list = ", ".join(t.title() for t in GAUTENG_TERMS)
    await update.message.reply_text(
        f"{header('MONITORED KEYWORDS')}\n"
        f"{divider()}\n"
        f"*{len(KEYWORDS)} keywords:*\n{kw_list}\n\n"
        f"*{len(GAUTENG_TERMS)} Gauteng locations:*\n_{loc_list}_\n"
        f"{divider()}\n"
        f"{footer()}",
        parse_mode="Markdown",
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active = [(k, c) for k, c in incident_clusters.items() if c["alerted_level"]]
    scan_time = last_scan_summary.get("time")
    time_str = fmt_time(scan_time) if scan_time else "Not yet run"

    if not active:
        await update.message.reply_text(
            f"{header('DASHBOARD')}\n"
            f"{divider()}\n"
            f"✅ *No active incidents detected.*\n\n"
            f"📡 Feeds monitored:    {len(FEEDS)}\n"
            f"📰 Articles checked:   {last_scan_summary.get('entries_scanned', 0)}\n"
            f"🕐 Last scan:          {time_str}\n\n"
            f"_Monitoring continuously — you'll be alerted the moment something is detected._\n"
            f"{divider()}\n"
            f"{footer()}",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        build_status_message(active),
        parse_mode="Markdown",
    )


async def incident_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            f"{header('INCIDENT LOOKUP')}\n"
            f"{divider()}\n"
            f"Usage: `/incident <id>`\n"
            f"Example: `/incident 3`\n\n"
            f"_Get incident IDs from /status_\n"
            f"{footer()}",
            parse_mode="Markdown",
        )
        return

    inc_id = int(args[0])
    idx = inc_id - 1
    if idx < 0 or idx >= len(incident_index):
        await update.message.reply_text(
            f"❌ Incident *#{inc_id}* not found.\n_Use /status to see current IDs._",
            parse_mode="Markdown",
        )
        return

    key = incident_index[idx]
    cluster = incident_clusters.get(key)
    if not cluster:
        await update.message.reply_text(
            f"❌ Incident *#{inc_id}* has expired (older than 48h).",
            parse_mode="Markdown",
        )
        return

    level = get_threat_level(len(cluster["sources"]))
    await update.message.reply_text(
        build_incident_detail(cluster, level, inc_id),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def scan_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{header('MANUAL SCAN TRIGGERED')}\n"
        f"{divider()}\n"
        f"🔄 Scanning {len(FEEDS)} sources now…\n{footer()}",
        parse_mode="Markdown",
    )
    await scan_feeds(context, verbose_chat_id=update.effective_chat.id)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribed_chats.discard(chat_id)
    await update.message.reply_text(
        f"{header('UNSUBSCRIBED')}\n"
        f"{divider()}\n"
        f"🔕 You have been removed from alerts.\n"
        f"Send /start at any time to re-subscribe.\n"
        f"{divider()}\n"
        f"{footer()}",
        parse_mode="Markdown",
    )


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    for word in KEYWORDS:
        if word in text:
            await update.message.reply_text(
                f"🚨 Keyword detected: `{word}`\n\nUse /status to view active incidents.",
                parse_mode="Markdown",
            )
            return

# ── App ───────────────────────────────────────────────────────────────────────

load_state()
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",    start))
app.add_handler(CommandHandler("sources",  sources_cmd))
app.add_handler(CommandHandler("keywords", keywords_cmd))
app.add_handler(CommandHandler("status",   status_cmd))
app.add_handler(CommandHandler("incident", incident_cmd))
app.add_handler(CommandHandler("scan",     scan_now))
app.add_handler(CommandHandler("stop",     stop))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, monitor))

app.job_queue.run_repeating(scan_feeds, interval=300, first=10)
app.run_polling(drop_pending_updates=True)
