import discord
import pandas as pd
import os

# ── Configuration ──────────────────────────────────────────────────────────────
TOKEN       = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
PREFIX      = "?"
HEADER_ROW  = 3   # 0-indexed row that contains column names

# CSV is expected to sit in the same folder as this script
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SPREADSHEET = os.path.join(BASE_DIR, "Embers Adrift Info - Weapons.csv")
# ───────────────────────────────────────────────────────────────────────────────


def load_items() -> pd.DataFrame:
    ext = os.path.splitext(SPREADSHEET)[1].lower()
    if ext == ".csv":
        return pd.read_csv(SPREADSHEET, header=HEADER_ROW)
    return pd.read_excel(SPREADSHEET, header=HEADER_ROW)


def is_blank(val) -> bool:
    """True if a value should be treated as absent."""
    if val is None:
        return True
    s = str(val).strip()
    return s in ("", "nan", "NaN", "–", "-", "0", "0.0", "None")


def fmt(val) -> str:
    """Format a numeric value cleanly (drop trailing .0)."""
    try:
        f = float(val)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(val).strip()


def build_stat_block(row: pd.Series) -> str:
    """Render one weapon as a D&D-style stat block inside a code fence."""
    name  = row.get("Weapon Name", "Unknown")
    lvl   = fmt(row.get("Lvl",  "?"))
    tier  = str(row.get("Tier", "?")).strip()
    role  = str(row.get("Role", "?")).strip()
    hand  = str(row.get("HH",   "?")).strip()
    dmin  = fmt(row.get("Dmg Min", "?"))
    dmax  = fmt(row.get("Dmg Max", "?"))
    delay = fmt(row.get("Delay",   "?"))

    lines = []
    W = 44   # width of the box interior (wider to fit pct values)

    def divider(char="─"):
        return char * W

    def center(text):
        return text.center(W)

    def kv(label, value, width=W):
        gap = width - len(label) - len(str(value))
        return f"{label}{'.' * max(1, gap)}{value}"

    lines.append("```")
    lines.append("┌" + "─" * W + "┐")
    lines.append("│" + center(name)                          + "│")
    lines.append("│" + center(f"Lvl {lvl}  ·  {tier}")      + "│")
    lines.append("│" + center(f"{role}  ·  {hand}")         + "│")
    lines.append("├" + divider()                             + "┤")

    # ── Core Combat ──────────────────────────────────────────────────
    lines.append("│" + center("── COMBAT ──")                + "│")
    lines.append("│" + kv("  Damage", f"{dmin}–{dmax}")     + "│")
    lines.append("│" + kv("  Delay",  delay)                 + "│")

    # ── Optional Stats (only if present) ─────────────────────────────
    opt_stats = []
    for col, label in [
        ("Haste",       "Haste"),
        ("Hit",         "Hit"),
        ("Pen",         "Pen"),
        ("Pos",         "Pos"),
        ("Dmg",         "Dmg Bonus"),
        ("Combat Mov.", "Combat Mov"),
        ("Block",       "Block"),
        ("Block Value", "Block Value"),
        ("Parry",       "Parry"),
        ("Riposte",     "Riposte"),
    ]:
        val = row.get(col)
        if not is_blank(val):
            opt_stats.append((label, fmt(val)))

    if opt_stats:
        lines.append("├" + divider()                         + "┤")
        lines.append("│" + center("── STATS ──")             + "│")
        for label, val in opt_stats:
            lines.append("│" + kv(f"  {label}", val)         + "│")

    # ── Positional ───────────────────────────────────────────────────
    pos_order = str(row.get("Pos Order", "")).strip()
    pos_lines = []

    front_stat = row.get("Front Stat")
    front_amt  = row.get("Front Amt")
    front_pct  = row.get("Front %")
    if not is_blank(front_stat) and not is_blank(front_amt):
        pct = f" ({fmt(front_pct)}%)" if not is_blank(front_pct) else ""
        pos_lines.append(("Front", f"{front_stat} +{fmt(front_amt)}{pct}"))

    side_stat = row.get("Side Stat")
    side_amt  = row.get("Side Amt")
    side_pct  = row.get("Side %")
    if not is_blank(side_stat) and not is_blank(side_amt):
        pct = f" ({fmt(side_pct)}%)" if not is_blank(side_pct) else ""
        pos_lines.append(("Side", f"{side_stat} +{fmt(side_amt)}{pct}"))

    rear_stat = row.get("Rear Stat")
    rear_amt  = row.get("Rear Amt")
    rear_pct  = row.get("Rear %")
    if not is_blank(rear_stat) and not is_blank(rear_amt):
        pct = f" ({fmt(rear_pct)}%)" if not is_blank(rear_pct) else ""
        pos_lines.append(("Rear", f"{rear_stat} +{fmt(rear_amt)}{pct}"))

    if pos_lines:
        lines.append("├" + divider()                                 + "┤")
        header = f"── POSITIONAL ({pos_order}) ──" if pos_order else "── POSITIONAL ──"
        lines.append("│" + center(header)                            + "│")
        for pos, bonus in pos_lines:
            lines.append("│" + kv(f"  {pos}", bonus)                + "│")

    # ── Other Stats & Source ──────────────────────────────────────────
    other  = str(row.get("Other Stats", "")).strip()
    source = str(row.get("Source",      "")).strip()

    if not is_blank(other) or not is_blank(source):
        lines.append("├" + divider()                                 + "┤")
        if not is_blank(other):
            words, cur = other.split(), ""
            wrapped = []
            for w in words:
                if len(cur) + len(w) + 1 > W - 4:
                    wrapped.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                wrapped.append(cur)
            lines.append("│" + center("── OTHER ──")                + "│")
            for chunk in wrapped:
                lines.append("│  " + chunk.ljust(W - 2)             + "│")
        if not is_blank(source):
            words, cur = source.split(), ""
            wrapped_src = []
            for w in words:
                if len(cur) + len(w) + 1 > W - 4:
                    wrapped_src.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                wrapped_src.append(cur)
            lines.append("│" + center("── SOURCE ──")               + "│")
            for chunk in wrapped_src:
                lines.append("│  " + chunk.ljust(W - 2)             + "│")

    lines.append("└" + "─" * W + "┘")
    lines.append("```")
    return "\n".join(lines)


def search_and_format(query: str) -> list[str]:
    """Search the spreadsheet and return Discord messages with stat blocks."""
    df      = load_items()
    mask    = df["Weapon Name"].astype(str).str.contains(query, case=False, na=False)
    results = df[mask]

    # Exclude crafted items (anything with a Skill entry)
    results = results[results["Skill"].isna() | (results["Skill"].astype(str).str.strip() == "")]

    if results.empty:
        return [f"❌  No weapons found matching **{query}**."]

    # More than 3 results -- just list names so the user can narrow the search
    if len(results) > 3:
        names = results["Weapon Name"].astype(str).tolist()
        lines = [f"🔍  **{len(results)}** results for `{query}` — please narrow your search:\n"]
        for name in names:
            lines.append(f"• {name}")
        messages = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > 1950:
                messages.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            messages.append(current)
        return messages

    header  = f"🔍  **{len(results)}** result(s) for `{query}`\n"
    current = header
    messages = []

    for _, row in results.iterrows():
        block = build_stat_block(row) + "\n"
        if len(current) + len(block) > 1950:
            messages.append(current)
            current = block
        else:
            current += block

    if current:
        messages.append(current)

    return messages


# ── Discord client ────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
client  = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    content = message.content.strip()
    if not content.startswith(PREFIX):
        return

    query = content[len(PREFIX):].strip()
    if not query:
        return

    messages = search_and_format(query)
    for msg in messages:
        await message.channel.send(msg)


client.run(TOKEN)
