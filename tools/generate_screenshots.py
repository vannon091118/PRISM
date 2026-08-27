#!/usr/bin/env python3
"""Generate dashboard preview PNG images using Pillow."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

# Output directory
output_dir = Path(__file__).parent.parent / "docs" / "screenshots"
output_dir.mkdir(parents=True, exist_ok=True)

# Colors
BG = "#09090b"
BG2 = "#18181b"
BG3 = "#27272a"
BORDER = "#3f3f46"
TEXT = "#fafafa"
TEXT2 = "#a1a1aa"
TEXT3 = "#71717a"
ACCENT = "#3b82f6"
ACCENT2 = "#10b981"
ACCENT3 = "#8b5cf6"
WARN = "#f59e0b"
ERR = "#ef4444"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def draw_rounded_rect(draw, xy, fill, radius=8):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)

def draw_bar(draw, x, y, w, h, fill, bg=BG3):
    draw_rounded_rect(draw, (x, y, x+w, y+h), fill=hex_to_rgb(bg), radius=h//2)
    draw_rounded_rect(draw, (x, y, x+w, y+h), fill=hex_to_rgb(fill), radius=h//2)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Canvas Dashboard Preview
# ═══════════════════════════════════════════════════════════════════════════
def generate_canvas_preview():
    W, H = 1200, 675
    img = Image.new("RGB", (W, H), hex_to_rgb(BG))
    draw = ImageDraw.Draw(img)
    
    # Header bar
    draw.rectangle((0, 0, W, 50), fill=hex_to_rgb(BG2))
    draw.line((0, 50, W, 50), fill=hex_to_rgb(BORDER), width=1)
    
    # Header text
    try:
        font_title = ImageFont.truetype("arial.ttf", 16)
        font_stat_val = ImageFont.truetype("arial.ttf", 18)
        font_stat_lbl = ImageFont.truetype("arial.ttf", 9)
        font_label = ImageFont.truetype("arial.ttf", 11)
        font_small = ImageFont.truetype("arial.ttf", 10)
        font_medium = ImageFont.truetype("arial.ttf", 13)
    except:
        font_title = ImageFont.load_default()
        font_stat_val = font_title
        font_stat_lbl = font_title
        font_label = font_title
        font_small = font_title
        font_medium = font_title
    
    # Header: ◈ PRISM
    draw.text((20, 16), "◈ PRISM", fill=hex_to_rgb(TEXT), font=font_title)
    draw.text((120, 20), "Multi-Plattform Scan · 2026-08-27 04:56", fill=hex_to_rgb(TEXT3), font=font_small)
    
    # Stats in header
    stats = [
        ("341", "THREADS", ACCENT),
        ("207", "BEANTWORTET", ACCENT2),
        ("6", "OFFEN", ERR),
        ("10", "INTERRUPTS", WARN),
        ("60.7%", "RATE", ACCENT3),
    ]
    sx = 550
    for val, lbl, color in stats:
        draw_rounded_rect(draw, (sx, 8, sx+80, 42), fill=hex_to_rgb(BG3), radius=6)
        draw.text((sx+40-len(val*5), 10), val, fill=hex_to_rgb(color), font=font_stat_val)
        draw.text((sx+40-len(lbl*3), 32), lbl, fill=hex_to_rgb(TEXT3), font=font_stat_lbl)
        sx += 86
    
    # Canvas area (left side ~55%)
    canvas_w = int(W * 0.55)
    
    # Project bubbles
    projects = [
        ("snip-war", 180, 220, 95, ACCENT2, "109"),
        ("PRISM", 380, 320, 78, ACCENT, "84"),
        ("freebuff-desktop", 280, 470, 65, ACCENT3, "67"),
        ("hermes-ai", 500, 190, 50, WARN, "38"),
        ("mcp-server", 140, 430, 40, ERR, "22"),
        ("cli-tools", 560, 410, 35, "#06b6d4", "18"),
        ("docs", 450, 500, 28, "#ec4899", "12"),
    ]
    
    # Connection lines
    connections = [(0,1), (1,2), (0,3), (2,4), (3,5), (5,6)]
    for a, b in connections:
        pa, pb = projects[a], projects[b]
        draw.line((pa[1], pa[2], pb[1], pb[2]), fill=hex_to_rgb("#3f3f4630"), width=1)
    
    for name, x, y, r, color, threads in projects:
        # Glow
        for i in range(3):
            alpha = 15 - i * 5
            draw.ellipse((x-r-i*8, y-r-i*8, x+r+i*8, y+r+i*8), 
                        fill=(*hex_to_rgb(color), alpha) if alpha > 0 else None,
                        outline=None)
        
        # Main circle
        draw.ellipse((x-r, y-r, x+r, y+r), fill=None, outline=hex_to_rgb(color), width=2)
        
        # Inner pie slice
        draw.pieslice((x-int(r*0.7), y-int(r*0.7), x+int(r*0.7), y+int(r*0.7)), 
                     start=-30, end=120, fill=(*hex_to_rgb(color), 40), outline=None)
        
        # Labels
        tw = len(name) * 5
        draw.text((x-tw//2, y-12), name, fill=hex_to_rgb(TEXT), font=font_small)
        tw2 = len(threads) * 4
        draw.text((x-tw2//2, y+4), f"{threads} Threads", fill=hex_to_rgb(TEXT3), font=font_small)
    
    # Legend
    draw_rounded_rect(draw, (10, H-40, 400, H-10), fill=(*hex_to_rgb(BG), 230), radius=6)
    legend = [("Vollständig", ACCENT2), ("Teilweise", WARN), ("Unvollständig", ERR), ("Plattform", ACCENT)]
    lx = 20
    for lbl, color in legend:
        draw.ellipse((lx, H-32, lx+8, H-24), fill=hex_to_rgb(color))
        draw.text((lx+12, H-34), lbl, fill=hex_to_rgb(TEXT2), font=font_small)
        lx += len(lbl) * 7 + 25
    
    # ── Side Panel ──
    sp_x = canvas_w
    draw.rectangle((sp_x, 50, W, 50), fill=hex_to_rgb(BG2))
    draw.line((sp_x, 50, sp_x, H), fill=hex_to_rgb(BORDER), width=1)
    draw.rectangle((sp_x, 50, W, 75), fill=hex_to_rgb(BG2))
    
    # Tab bar
    tabs = ["Übersicht", "Projekte", "Zeitstrahl", "Integrität", "Flow"]
    tab_w = (W - sp_x) // len(tabs)
    for i, tab in enumerate(tabs):
        tx = sp_x + i * tab_w
        if i == 0:
            draw.rectangle((tx, 50, tx+tab_w, 75), fill=hex_to_rgb(BG2))
            draw.text((tx+10, 57), tab, fill=hex_to_rgb(TEXT), font=font_small)
            draw.line((tx, 74, tx+tab_w, 74), fill=hex_to_rgb(ACCENT), width=2)
        else:
            draw.text((tx+10, 57), tab, fill=hex_to_rgb(TEXT3), font=font_small)
    
    # Overview cards
    cards = [
        ("341", "GESAMT THREADS", ACCENT),
        ("207", "VOLLSTÄNDIG", ACCENT2),
        ("6", "OHNE AGENT", ERR),
        ("10", "INTERRUPTS", WARN),
        ("27", "PROJEKTE", ACCENT3),
        ("8", "PLATTFORMEN", ACCENT),
    ]
    card_w = (W - sp_x - 40) // 2
    for i, (val, lbl, color) in enumerate(cards):
        cx = sp_x + 12 + (i % 2) * (card_w + 8)
        cy = 85 + (i // 2) * 65
        draw_rounded_rect(draw, (cx, cy, cx+card_w, cy+55), fill=hex_to_rgb(BG3), radius=6)
        draw.line((cx, cy, cx+card_w, cy), fill=hex_to_rgb(BORDER), width=1)
        
        # Value
        tw = len(val) * 12
        draw.text((cx + card_w//2 - tw//2, cy+8), val, fill=hex_to_rgb(color), font=font_stat_val)
        # Label
        tw = len(lbl) * 5
        draw.text((cx + card_w//2 - tw//2, cy+35), lbl, fill=hex_to_rgb(TEXT3), font=font_stat_lbl)
    
    # Integrity bar
    iy = 290
    draw.text((sp_x+12, iy), "Integrität", fill=hex_to_rgb(TEXT), font=font_label)
    iy += 20
    draw_rounded_rect(draw, (sp_x+12, iy, W-12, iy+8), fill=hex_to_rgb(BG3), radius=4)
    # Segments
    total_w = W - sp_x - 24
    draw_rounded_rect(draw, (sp_x+12, iy, sp_x+12+int(total_w*0.607), iy+8), fill=hex_to_rgb(ACCENT2), radius=4)
    draw_rounded_rect(draw, (sp_x+12+int(total_w*0.607), iy, sp_x+12+int(total_w*0.857), iy+8), fill=hex_to_rgb(WARN), radius=0)
    draw.rectangle((sp_x+12+int(total_w*0.857), iy, W-12, iy+8), fill=hex_to_rgb(ERR))
    
    # Projects
    py = iy + 25
    draw.text((sp_x+12, py), "Projekte", fill=hex_to_rgb(TEXT), font=font_label)
    py += 20
    
    proj_data = [
        ("snip-war", "85%", ACCENT2, "109 Threads · Freebuff · ◇ PR MERGED"),
        ("PRISM", "72%", ACCENT, "84 Threads · Codebuff · ◇ COMMIT"),
        ("freebuff-desktop", "91%", ACCENT3, "67 Threads · Claude Code · ◇ BRANCH"),
    ]
    
    for name, pct, color, meta in proj_data:
        card_h = 80
        draw_rounded_rect(draw, (sp_x+12, py, W-12, py+card_h), fill=hex_to_rgb(BG3), radius=6)
        draw.line((sp_x+12, py, W-12, py), fill=hex_to_rgb(BORDER), width=1)
        
        draw.text((sp_x+20, py+10), name, fill=hex_to_rgb(TEXT), font=font_medium)
        draw.text((W-80, py+10), pct, fill=hex_to_rgb(color), font=font_medium)
        
        # Progress bar
        bar_y = py + 35
        draw_rounded_rect(draw, (sp_x+20, bar_y, W-20, bar_y+4), fill=hex_to_rgb(BG), radius=2)
        pct_val = int(pct.replace('%', ''))
        draw_rounded_rect(draw, (sp_x+20, bar_y, sp_x+20+int((W-sp_x-40)*pct_val/100), bar_y+4), 
                         fill=hex_to_rgb(color), radius=2)
        
        # Meta tags
        draw.text((sp_x+20, py+50), meta, fill=hex_to_rgb(TEXT3), font=font_small)
        
        py += card_h + 8
    
    # Save
    output = output_dir / "canvas-preview.png"
    img.save(str(output), "PNG")
    print(f"✓ Saved: {output}")


# ═══════════════════════════════════════════════════════════════════════════
# 2. Threads Dashboard Preview
# ═══════════════════════════════════════════════════════════════════════════
def generate_threads_preview():
    W, H = 1200, 675
    img = Image.new("RGB", (W, H), hex_to_rgb(BG))
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 22)
        font_heading = ImageFont.truetype("arial.ttf", 14)
        font_medium = ImageFont.truetype("arial.ttf", 13)
        font_small = ImageFont.truetype("arial.ttf", 11)
        font_tiny = ImageFont.truetype("arial.ttf", 9)
        font_stat = ImageFont.truetype("arial.ttf", 24)
        font_stat_lbl = ImageFont.truetype("arial.ttf", 10)
    except:
        font_title = ImageFont.load_default()
        font_heading = font_title
        font_medium = font_title
        font_small = font_title
        font_tiny = font_title
        font_stat = font_title
        font_stat_lbl = font_title
    
    # Header gradient (simulated)
    for y in range(80):
        r = int(13 + (22-13) * y/80)
        g = int(17 + (27-17) * y/80)
        b = int(23 + (34-23) * y/80)
        draw.line((0, y, W, y), fill=(r, g, b))
    
    draw.text((48, 24), "⚒ Agent Threads Dashboard", fill=hex_to_rgb(TEXT), font=font_title)
    draw.text((48, 55), "Projekt: Multi-Plattform Scan · 278 Threads · 7391 Messages · 6 Plattformen", 
              fill=hex_to_rgb(TEXT2), font=font_small)
    
    # Stats row
    stats = [
        ("Gesamt Threads", "278", ACCENT),
        ("User Inputs", "1,021", ACCENT2),
        ("Messages", "7,391", ACCENT3),
        ("Plattformen", "6", WARN),
        ("Projekte", "27", ACCENT),
    ]
    sx = 48
    for lbl, val, color in stats:
        draw_rounded_rect(draw, (sx, 100, sx+195, 155), fill=hex_to_rgb(BG2), radius=10)
        draw.line((sx, 100, sx+195, 100), fill=hex_to_rgb(BORDER), width=1)
        draw.text((sx+16, 108), lbl, fill=hex_to_rgb(TEXT2), font=font_stat_lbl)
        draw.text((sx+16, 122), val, fill=hex_to_rgb(color), font=font_stat)
        sx += 210
    
    # Charts section
    cy = 175
    draw.text((48, cy), "📊 Plattformen & Kategorien", fill=hex_to_rgb(TEXT), font=font_heading)
    cy += 25
    
    # Platform bar chart (left)
    chart_x = 48
    chart_w = 530
    draw_rounded_rect(draw, (chart_x, cy, chart_x+chart_w, cy+200), fill=hex_to_rgb(BG2), radius=10)
    draw.line((chart_x, cy, chart_x+chart_w, cy), fill=hex_to_rgb(BORDER), width=1)
    
    platforms = [
        ("Freebuff", 109, ACCENT3),
        ("Claude Code", 67, WARN),
        ("Hermes", 45, ACCENT),
        ("Codex", 32, ACCENT2),
        ("Cursor", 18, ERR),
        ("Gemini", 7, "#79c0ff"),
    ]
    bar_w = 55
    bar_gap = 18
    max_val = max(p[1] for p in platforms)
    for i, (name, count, color) in enumerate(platforms):
        bx = chart_x + 30 + i * (bar_w + bar_gap)
        bh = int((count / max_val) * 130)
        by = cy + 170 - bh
        
        # Bar
        draw_rounded_rect(draw, (bx, by, bx+bar_w, cy+170), fill=(*hex_to_rgb(color), 50), radius=4)
        draw.rectangle((bx, by, bx+bar_w, by+3), fill=hex_to_rgb(color))
        
        # Value
        draw.text((bx+bar_w//2-8, by-16), str(count), fill=hex_to_rgb(color), font=font_small)
        # Label
        draw.text((bx+bar_w//2-len(name)*3, cy+176), name, fill=hex_to_rgb(TEXT2), font=font_tiny)
    
    # Category pie chart (right)
    pie_x = chart_x + chart_w + 20
    pie_w = W - pie_x - 48
    draw_rounded_rect(draw, (pie_x, cy, pie_x+pie_w, cy+200), fill=hex_to_rgb(BG2), radius=10)
    draw.line((pie_x, cy, pie_x+pie_w, cy), fill=hex_to_rgb(BORDER), width=1)
    
    cats = [
        ("Feature", 89, ACCENT2),
        ("Bug", 67, ERR),
        ("Refactor", 45, ACCENT),
        ("Docs", 32, ACCENT3),
        ("Test", 28, WARN),
        ("Other", 17, TEXT3),
    ]
    total = sum(c[1] for c in cats)
    cx, cy_pie = pie_x + 80, cy + 100
    r = 65
    angle = -90
    for name, count, color in cats:
        sweep = int(360 * count / total)
        draw.pieslice((cx-r, cy_pie-r, cx+r, cy_pie+r), start=angle, end=angle+sweep, 
                      fill=hex_to_rgb(color), outline=hex_to_rgb(BG2), width=2)
        angle += sweep
    
    # Legend
    ly = cy + 15
    for name, count, color in cats:
        draw.rectangle((pie_x+pie_w-130, ly, pie_x+pie_w-120, ly+10), fill=hex_to_rgb(color))
        draw.text((pie_x+pie_w-115, ly-1), f"{name} ({count})", fill=hex_to_rgb(TEXT2), font=font_tiny)
        ly += 16
    
    # Thread cards
    ty = cy + 220
    draw.text((48, ty), "🧵 Threads", fill=hex_to_rgb(TEXT), font=font_heading)
    ty += 25
    
    thread_data = [
        ("PRISM Canvas Dashboard implementieren", "Freebuff", ACCENT3, "bug · feature · ui",
         "User", "Erstelle ein Canvas-Dashboard für PRISM mit Pie-Charts als Bubbles",
         "Agent", "Ich implementiere ein interaktives Canvas-Dashboard mit Partikel-System...", "✓ Committed", ACCENT2),
        ("Hermes state.db parser für multi-table JOIN", "Hermes", ACCENT, "backend · database",
         "User", "Parse die Hermes state.db mit dem 3-Table-JOIN",
         "Agent", "Ich analysiere die Tabellenstruktur und implementiere den JOIN...", "✓ Committed", ACCENT2),
        ("snip-war Featurebranch merge", "Freebuff", ACCENT3, "git · pr",
         "User", "Merge die Character-Dialogue Featurebranch in main",
         "Agent", "Ich führe den Merge durch und resolve die Konflikte...", "◇ PR #4 Merged", WARN),
    ]
    
    for title, platform, plat_color, tags, user_role, user_text, agent_role, agent_text, status, status_color in thread_data:
        card_h = 110
        draw_rounded_rect(draw, (48, ty, W-48, ty+card_h), fill=hex_to_rgb(BG2), radius=10)
        draw.line((48, ty, W-48, ty), fill=hex_to_rgb(BORDER), width=1)
        
        # Header
        draw.text((60, ty+12), title, fill=hex_to_rgb(TEXT), font=font_medium)
        # Platform badge
        draw_rounded_rect(draw, (W-250, ty+10, W-170, ty+28), fill=hex_to_rgb(BG3), radius=8)
        draw.text((W-245, ty+12), platform, fill=hex_to_rgb(plat_color), font=font_tiny)
        # Date
        draw.text((W-160, ty+12), "2026-08-27", fill=hex_to_rgb(TEXT2), font=font_tiny)
        
        # Tags
        tag_x = 60
        for tag in tags.split(" · "):
            tw = len(tag) * 6 + 12
            draw_rounded_rect(draw, (tag_x, ty+32, tag_x+tw, ty+46), fill=hex_to_rgb(BG3), radius=8)
            draw.text((tag_x+6, ty+33), tag, fill=hex_to_rgb(ACCENT3), font=font_tiny)
            tag_x += tw + 4
        
        # Messages
        draw.rectangle((60, ty+52, W-60, ty+card_h-15), fill=(*hex_to_rgb(BG), 0))
        draw.text((60, ty+55), f"▸ {user_role}: {user_text[:60]}...", fill=hex_to_rgb(ACCENT), font=font_small)
        draw.text((60, ty+72), f"▸ {agent_role}: {agent_text[:60]}...", fill=hex_to_rgb(ACCENT3), font=font_small)
        
        # Status
        draw.text((W-180, ty+card_h-22), status, fill=hex_to_rgb(status_color), font=font_small)
        
        ty += card_h + 10
    
    output = output_dir / "threads-preview.png"
    img.save(str(output), "PNG")
    print(f"✓ Saved: {output}")


# ═══════════════════════════════════════════════════════════════════════════
# 3. User Inputs Dashboard Preview
# ═══════════════════════════════════════════════════════════════════════════
def generate_user_inputs_preview():
    W, H = 1200, 675
    img = Image.new("RGB", (W, H), hex_to_rgb(BG))
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 22)
        font_heading = ImageFont.truetype("arial.ttf", 14)
        font_medium = ImageFont.truetype("arial.ttf", 13)
        font_small = ImageFont.truetype("arial.ttf", 11)
        font_tiny = ImageFont.truetype("arial.ttf", 9)
        font_stat = ImageFont.truetype("arial.ttf", 24)
        font_stat_lbl = ImageFont.truetype("arial.ttf", 10)
        font_code = ImageFont.truetype("consola.ttf", 10)
    except:
        try:
            font_code = ImageFont.truetype("cour.ttf", 10)
        except:
            font_code = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_heading = font_title
        font_medium = font_title
        font_small = font_title
        font_tiny = font_title
        font_stat = font_title
        font_stat_lbl = font_title
    
    # Header
    for y in range(80):
        r = int(13 + (22-13) * y/80)
        g = int(17 + (27-17) * y/80)
        b = int(23 + (34-23) * y/80)
        draw.line((0, y, W, y), fill=(r, g, b))
    
    draw.text((48, 24), "⚒ User-Inputs Dashboard V4", fill=hex_to_rgb(TEXT), font=font_title)
    draw.text((48, 55), "4 Plattformen · 1,021 User-Inputs · 12.4 MB Memory", fill=hex_to_rgb(TEXT2), font=font_small)
    
    # Stats
    stats = [
        ("User Inputs", "1,021", ACCENT),
        ("Memory", "12.4 MB", ACCENT2),
        ("Plattformen", "4", ACCENT3),
        ("Projekte", "27", WARN),
        ("Git Commits", "156", ACCENT),
    ]
    sx = 48
    for lbl, val, color in stats:
        draw_rounded_rect(draw, (sx, 100, sx+195, 150), fill=hex_to_rgb(BG2), radius=10)
        draw.text((sx+16, 108), lbl, fill=hex_to_rgb(TEXT2), font=font_stat_lbl)
        draw.text((sx+16, 122), val, fill=hex_to_rgb(color), font=font_stat)
        sx += 210
    
    # Memory bar
    my = 165
    draw.text((48, my), "📈 Memory-Volumen-Analyse", fill=hex_to_rgb(TEXT), font=font_heading)
    my += 22
    draw_rounded_rect(draw, (48, my, W-48, my+28), fill=hex_to_rgb(BG2), radius=6)
    mem_segments = [("4.2 MB User", 0.34, ACCENT), ("3.8 MB Assistant", 0.31, ACCENT3), ("4.4 MB Tool", 0.35, WARN)]
    mx = 48
    total_w = W - 96
    for lbl, pct, color in mem_segments:
        sw = int(total_w * pct)
        draw.rectangle((mx, my, mx+sw, my+28), fill=hex_to_rgb(color))
        draw.text((mx+10, my+8), lbl, fill=hex_to_rgb(BG), font=font_small)
        mx += sw
    
    # Charts
    cy = my + 45
    
    # Left chart: Categories (horizontal bars)
    chart_l_w = (W - 96 - 20) // 2
    draw_rounded_rect(draw, (48, cy, 48+chart_l_w, cy+190), fill=hex_to_rgb(BG2), radius=10)
    draw.text((60, cy+10), "📊 User-Intentionen nach Kategorie", fill=hex_to_rgb(TEXT), font=font_heading)
    
    cats = [
        ("Bug Fix", 312, ERR),
        ("Feature", 287, ACCENT2),
        ("Refactor", 198, ACCENT),
        ("Dokumentation", 124, ACCENT3),
        ("Testing", 67, WARN),
        ("Other", 33, TEXT3),
    ]
    max_cat = max(c[1] for c in cats)
    bar_start = 48 + 130
    for i, (name, count, color) in enumerate(cats):
        by = cy + 30 + i * 26
        draw.text((60, by), name, fill=hex_to_rgb(TEXT2), font=font_small)
        bw = int((count / max_cat) * (chart_l_w - 200))
        draw_rounded_rect(draw, (bar_start, by+2, bar_start+bw, by+16), fill=hex_to_rgb(color), radius=4)
        draw.text((bar_start+bw+8, by), str(count), fill=hex_to_rgb(TEXT2), font=font_small)
    
    # Right chart: Activity (bar chart)
    chart_r_x = 48 + chart_l_w + 20
    chart_r_w = W - chart_r_x - 48
    draw_rounded_rect(draw, (chart_r_x, cy, chart_r_x+chart_r_w, cy+190), fill=hex_to_rgb(BG2), radius=10)
    draw.text((chart_r_x+12, cy+10), "📅 Aktivität pro Tag", fill=hex_to_rgb(TEXT), font=font_heading)
    
    activity = [
        ("Mo", 45, 8), ("Di", 67, 12), ("Mi", 89, 15),
        ("Do", 123, 22), ("Fr", 156, 28), ("Sa", 89, 14), ("So", 34, 5),
    ]
    max_act = max(a[1] for a in activity)
    bw = 28
    bgap = 20
    for i, (day, inputs, commits) in enumerate(activity):
        bx = chart_r_x + 25 + i * (bw * 2 + bgap)
        h1 = int((inputs / max_act) * 110)
        h2 = int((commits / max_act) * 110)
        by = cy + 170
        
        draw_rounded_rect(draw, (bx, by-h1, bx+bw, by), fill=ACCENT, radius=3)
        draw_rounded_rect(draw, (bx+bw+3, by-h2, bx+bw*2+3, by), fill=ACCENT2, radius=3)
        draw.text((bx+bw//2, by+5), day, fill=hex_to_rgb(TEXT2), font=font_tiny)
    
    # Legend
    draw.rectangle((chart_r_x+25, cy+175, chart_r_x+33, cy+183), fill=hex_to_rgb(ACCENT))
    draw.text((chart_r_x+37, cy+174), "Inputs", fill=hex_to_rgb(TEXT2), font=font_tiny)
    draw.rectangle((chart_r_x+100, cy+175, chart_r_x+108, cy+183), fill=hex_to_rgb(ACCENT2))
    draw.text((chart_r_x+112, cy+174), "Commits", fill=hex_to_rgb(TEXT2), font=font_tiny)
    
    # Bottom section: Reasoning + Timeline
    by = cy + 210
    
    # Left: Reasoning
    draw_rounded_rect(draw, (48, by, 48+chart_l_w, by+155), fill=hex_to_rgb(BG2), radius=10)
    draw.text((60, by+10), "🧠 Top Reasoning-Snippets", fill=hex_to_rgb(TEXT), font=font_heading)
    
    reasoning = [
        ("Claude Sonnet 4", "12.4 KB", "Ich implementiere ein interaktives Canvas-Dashboard mit Partikel-System..."),
        ("Gemini 2.5 Pro", "8.7 KB", "Die state.db Struktur enthält 3 Tabellen: sessions, messages, parts..."),
    ]
    ry = by + 30
    for model, size, snippet in reasoning:
        draw_rounded_rect(draw, (60, ry, 48+chart_l_w-12, ry+50), fill=hex_to_rgb(BG3), radius=6)
        draw.text((70, ry+5), model, fill=hex_to_rgb(ACCENT3), font=font_tiny)
        draw.text((200, ry+5), size, fill=hex_to_rgb(TEXT2), font=font_tiny)
        draw.text((70, ry+22), snippet[:70], fill=hex_to_rgb(TEXT2), font=font_code)
        ry += 58
    
    # Right: Timeline
    draw_rounded_rect(draw, (chart_r_x, by, chart_r_x+chart_r_w, by+155), fill=hex_to_rgb(BG2), radius=10)
    draw.text((chart_r_x+12, by+10), "📅 Commit-Timeline", fill=hex_to_rgb(TEXT), font=font_heading)
    
    timeline = [
        ("2026-08-27", "12 Commits", [
            "feat: add canvas dashboard with particle system",
            "fix: resolve hermes state.db JOIN issue",
            "refactor: modularize platform readers",
            "feat: add SimHash deduplication",
        ]),
        ("2026-08-26", "8 Commits", [
            "feat: initial PRISM scaffold",
            "feat: add Claude Code reader",
            "feat: add categorizer with 18 categories",
        ]),
    ]
    ty = by + 30
    for date, badge, commits in timeline:
        draw.text((chart_r_x+12, ty), date, fill=hex_to_rgb(ACCENT), font=font_small)
        draw_rounded_rect(draw, (chart_r_x+120, ty+1, chart_r_x+120+len(badge)*6+12, ty+15), 
                         fill=hex_to_rgb(BG3), radius=8)
        draw.text((chart_r_x+126, ty+1), badge, fill=hex_to_rgb(TEXT2), font=font_tiny)
        ty += 18
        
        for commit in commits:
            draw.text((chart_r_x+25, ty), f"→ {commit[:55]}", fill=hex_to_rgb(TEXT2), font=font_tiny)
            ty += 14
        ty += 8
    
    output = output_dir / "user-inputs-preview.png"
    img.save(str(output), "PNG")
    print(f"✓ Saved: {output}")


if __name__ == "__main__":
    print("Generating dashboard preview screenshots...")
    generate_canvas_preview()
    generate_threads_preview()
    generate_user_inputs_preview()
    print("\n✅ All screenshots generated!")
