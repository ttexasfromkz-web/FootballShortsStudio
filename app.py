import os
import sys
import threading
import cv2
import numpy as np
import librosa
import yt_dlp
import requests
import urllib.parse
from bs4 import BeautifulSoup
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont
from faster_whisper import WhisperModel
from ultralytics import YOLO
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
)
import moviepy.video.fx.all as vfx
from moviepy.audio.AudioClip import AudioArrayClip

# --- 🔄 АВТО-ЖАҢАРТУ БАПТАУЛАРЫ ---
CURRENT_VERSION = "1.0"
GITHUB_USERNAME = "ttexasfromkz-web"
GITHUB_REPO = "FootballShortsStudio"

UPDATE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/version.txt"
APP_CODE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/app.py"

ctk.set_appearance_mode("dark")
ctk.set_default_color_scheme("blue")

KEYWORDS = [
    "гол", "гоо", "соққы", "қауіпті", "тамаша", "міне", "қараңыз",
    "удар", "опасно", "опасный", "момент", "штанга", "пенальти", "девятка", "красота",
    "goal", "shot", "what a", "incredible", "score", "scores", "chance", "save", "penalty"
]

def load_font(size):
    font_candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except Exception: pass
    return ImageFont.load_default()

def fetch_logo_from_web(team_name):
    try:
        query = f"{team_name} football club logo png transparent site:wikipedia.org OR site:wikimedia.org"
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for a in soup.find_all('a', class_='result__snippet'):
            if 'wikipedia.org' in str(a) or 'wikimedia.org' in str(a):
                page_url = a.get('href')
                if page_url.startswith('//'): page_url = 'https:' + page_url
                
                wiki_res = requests.get(page_url, headers=headers, timeout=5)
                wiki_soup = BeautifulSoup(wiki_res.text, 'html.parser')
                img_tag = wiki_soup.find('table', class_='infobox').find('img') if wiki_soup.find('table', class_='infobox') else None
                if img_tag and img_tag.get('src'):
                    img_url = 'https:' + img_tag.get('src')
                    img_data = requests.get(img_url).content
                    temp_path = f"temp_logo_{team_name}.png"
                    with open(temp_path, 'wb') as f: f.write(img_data)
                    return temp_path
    except Exception as e: print(f"Лого іздеу қатесі ({team_name}): {e}")
    return ""

def load_logo_rgba(path, size=(120, 120)):
    if path and os.path.exists(path):
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail(size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            ox = (size[0] - img.width) // 2
            oy = (size[1] - img.height) // 2
            canvas.paste(img, (ox, oy), img)
            return canvas
        except Exception: pass
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    pad = 8
    draw.ellipse([pad, pad, size[0] - pad, size[1] - pad], fill=(30, 45, 80, 230), outline=(255, 215, 0, 255), width=4)
    return canvas

def generate_youtube_metadata(team1, team2, score, output_dir):
    t1_clean = team1.replace(" ", "").replace("-", "")
    t2_clean = team2.replace(" ", "").replace("-", "")
    metadata_content = f"""==================================================
🎬 YOUTUBE SHORTS ҮШІН ДАЙЫН МӘТІНДЕР
==================================================

📌 [ВИДЕО АТАУЛАРЫ (ТИТУЛДАР)]:
1. 🔥 {team1} vs {team2} ({score}) - Ең қауіпті сәттер мен голдар! Shorts
2. ШОК! {team1} - {team2} ({score}) | Үздік сәттер ⚽
3. ⚡ {team1} мен {team2} матчындағы ЖЫНДЫ ГОЛДАР! ({score})
4. {team1} {score} {team2} - Обзор матча за 1 минуту! 🔥

--------------------------------------------------
📝 [ОПИСАНИЕ (DESCRIPTION)]:
⚽ Матч: {team1} қарсы {team2}
🏆 Қорытынды есеп: {score}

Ең керемет голдар мен қауіпті сәттерді бір минутта тамашалаңыз! 
Каналға жазылып, лайк басуды ұмытпаңыз! 👇

#футбол #спорт #{t1_clean} #{t2_clean} #гол #shorts #қазақшафутбол #football #highlights #обзорматча

--------------------------------------------------
🏷 [ТЕГТЕР (TAGS)]:
футбол, үздік сәттер, гол, {team1}, {team2}, футбол 2026, спорт, қазақша футбол, обзор матча, опасные моменты, highlights, football shorts, {team1} {team2} обзор, {score}
=================================================="""
    file_path = os.path.join(output_dir, "youtube_metadata.txt")
    with open(file_path, "w", encoding="utf-8") as f: f.write(metadata_content)
    return file_path


class FootballShortsMakerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"⚽ AI Football Shorts Studio PRO (v{CURRENT_VERSION})")
        self.geometry("820x860")
        self.resizable(False, False)

        self.check_for_updates()

        self.music_path = ""
        self.logo1_path = ""
        self.logo2_path = ""
        self.output_dir = os.path.join(os.getcwd(), "output_shorts")
        os.makedirs(self.output_dir, exist_ok=True)

        self._build_ui()

    def check_for_updates(self):
        try:
            res = requests.get(UPDATE_URL, timeout=3)
            if res.status_code == 200:
                latest_version = res.text.strip()
                if latest_version != CURRENT_VERSION:
                    ans = messagebox.askyesno("Жаңа нұсқа табылды!", f"Бағдарламаның жаңа v{latest_version} нұсқасы шықты!\nҚазір жаңартайық па?")
                    if ans:
                        code_res = requests.get(APP_CODE_URL)
                        if code_res.status_code == 200:
                            with open(os.path.abspath(__file__), "w", encoding="utf-8") as f:
                                f.write(code_res.text)
                            messagebox.showinfo("Сәтті", "Жаңарту жүктелді! Бағдарлама қайта іске қосылады.")
                            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            print("Жаңартуды тексеру мүмкін болмады:", e)

    def _build_ui(self):
        title_label = ctk.CTkLabel(self, text=f"⚽ AI Football Shorts Studio (v{CURRENT_VERSION})", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(12, 6))

        url_frame = ctk.CTkFrame(self)
        url_frame.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(url_frame, text="1. YouTube видео сілтемесі:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(6, 2))
        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text="https://www.youtube.com/watch?v=...", height=34)
        self.url_entry.pack(fill="x", padx=12, pady=(0, 8))

        match_frame = ctk.CTkFrame(self)
        match_frame.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(match_frame, text="2. Командалар және Логотиптер (Интернеттен авто-іздеу):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(6, 4))

        teams_grid = ctk.CTkFrame(match_frame, fg_color="transparent")
        teams_grid.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkLabel(teams_grid, text="1-команда:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.team1_entry = ctk.CTkEntry(teams_grid, width=140)
        self.team1_entry.insert(0, "БАРСЕЛОНА")
        self.team1_entry.grid(row=0, column=1, padx=4, pady=4)

        self.logo1_lbl = ctk.CTkLabel(teams_grid, text="❌ Жоқ", text_color="gray", width=40)
        self.logo1_lbl.grid(row=0, column=2, padx=2)
        
        btn_frame1 = ctk.CTkFrame(teams_grid, fg_color="transparent")
        btn_frame1.grid(row=0, column=3, padx=2)
        ctk.CTkButton(btn_frame1, text="🌐", width=35, command=lambda: self.auto_search_logo(1)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame1, text="📁", width=35, command=lambda: self.select_logo(1)).pack(side="left", padx=2)

        ctk.CTkLabel(teams_grid, text="2-команда:").grid(row=0, column=4, sticky="w", padx=(12, 4), pady=4)
        self.team2_entry = ctk.CTkEntry(teams_grid, width=140)
        self.team2_entry.insert(0, "РЕАЛ МАДРИД")
        self.team2_entry.grid(row=0, column=5, padx=4, pady=4)

        self.logo2_lbl = ctk.CTkLabel(teams_grid, text="❌ Жоқ", text_color="gray", width=40)
        self.logo2_lbl.grid(row=0, column=6, padx=2)
        
        btn_frame2 = ctk.CTkFrame(teams_grid, fg_color="transparent")
        btn_frame2.grid(row=0, column=7, padx=2)
        ctk.CTkButton(btn_frame2, text="🌐", width=35, command=lambda: self.auto_search_logo(2)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame2, text="📁", width=35, command=lambda: self.select_logo(2)).pack(side="left", padx=2)

        ctk.CTkLabel(teams_grid, text="Қорытынды:").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self.final_score_entry = ctk.CTkEntry(teams_grid, width=140)
        self.final_score_entry.insert(0, "3 : 2")
        self.final_score_entry.grid(row=1, column=1, padx=4, pady=6)

        ctk.CTkLabel(teams_grid, text="Табло есептері:").grid(row=1, column=4, sticky="w", padx=(12, 4), pady=6)
        self.live_scores_entry = ctk.CTkEntry(teams_grid, width=220)
        self.live_scores_entry.insert(0, "1:0, 1:1, 2:1, 3:2")
        self.live_scores_entry.grid(row=1, column=5, columnspan=3, sticky="w", padx=4, pady=6)

        music_frame = ctk.CTkFrame(self)
        music_frame.pack(fill="x", padx=25, pady=5)
        music_inner = ctk.CTkFrame(music_frame, fg_color="transparent")
        music_inner.pack(fill="x", padx=12, pady=8)
        self.music_label = ctk.CTkLabel(music_inner, text="🎵 Музыка таңдалмады...", text_color="#ff9900")
        self.music_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(music_inner, text="Музыка таңдау", width=160, command=self.select_music).pack(side="right")

        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(fill="x", padx=25, pady=5)
        grid_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(grid_frame, text="Үздік сәттер:").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.top_n_var = ctk.StringVar(value="3")
        ctk.CTkOptionMenu(grid_frame, values=["1", "2", "3", "4", "5"], variable=self.top_n_var, width=80).grid(row=0, column=1, padx=6, pady=4)

        ctk.CTkLabel(grid_frame, text="Ұзақтығы (сек):").grid(row=0, column=2, sticky="w", padx=10, pady=4)
        self.clip_dur_var = ctk.StringVar(value="12")
        ctk.CTkOptionMenu(grid_frame, values=["8", "10", "12", "15"], variable=self.clip_dur_var, width=80).grid(row=0, column=3, padx=6, pady=4)

        self.intro_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(grid_frame, text="Басында VS Интро", variable=self.intro_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=6)

        self.goal_fx_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(grid_frame, text="'ГОООЛ!' Эффекті", variable=self.goal_fx_var).grid(row=1, column=2, columnspan=2, sticky="w", padx=10, pady=6)

        self.slowmo_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(grid_frame, text="Голдан соң Slow-Mo (2 сек)", variable=self.slowmo_var, text_color="#ff9900").grid(row=1, column=4, sticky="w", padx=10, pady=6)

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(fill="x", padx=25, pady=(8, 4))
        self.progress_bar.set(0)

        self.log_box = ctk.CTkTextbox(self, height=130, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="x", padx=25, pady=4)
        self.log(f"Жүйе дайын (v{CURRENT_VERSION})! Жаңартулар GitHub арқылы автоматты түрде келеді.")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=10)

        self.start_btn = ctk.CTkButton(btn_frame, text="🚀 SHORTS ЖАСАУДЫ БАСТАУ", height=46, font=ctk.CTkFont(weight="bold"), fg_color="#1f8b4c", command=self.start_pipeline)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(btn_frame, text="📂 Папканы ашу", height=46, width=180, fg_color="#3b3b3b", command=lambda: os.startfile(self.output_dir)).pack(side="right")

    def log(self, message):
        self.log_box.insert("end", f"> {message}\n")
        self.log_box.see("end")
        self.update_idletasks()

    def select_music(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.m4a")])
        if path:
            self.music_path = path
            self.music_label.configure(text=f"✅ {os.path.basename(path)}", text_color="#2ecc71")

    def select_logo(self, team_num):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.webp")])
        if path:
            if team_num == 1:
                self.logo1_path = path
                self.logo1_lbl.configure(text="✅ Бар", text_color="#2ecc71")
            else:
                self.logo2_path = path
                self.logo2_lbl.configure(text="✅ Бар", text_color="#2ecc71")

    def auto_search_logo(self, team_num):
        name = self.team1_entry.get().strip() if team_num == 1 else self.team2_entry.get().strip()
        if not name: return
        self.log(f"🌐 Интернеттен '{name}' логотипі ізделуде...")
        def fetch():
            path = fetch_logo_from_web(name)
            if path:
                if team_num == 1:
                    self.logo1_path = path
                    self.logo1_lbl.configure(text="✅ Табылды", text_color="#2ecc71")
                else:
                    self.logo2_path = path
                    self.logo2_lbl.configure(text="✅ Табылды", text_color="#2ecc71")
                self.log(f"✅ '{name}' логотипі сәтті жүктелді!")
            else:
                self.log(f"❌ '{name}' логотипі табылмады. Қолмен жүктеңіз (📁).")
        threading.Thread(target=fetch, daemon=True).start()

    def start_pipeline(self):
        url = self.url_entry.get().strip()
        if not url: return
        self.start_btn.configure(state="disabled", text="⏳ ЖАСАЛУДА...")
        self.progress_bar.set(0.05)
        threading.Thread(target=self.run_process, args=(url,), daemon=True).start()

    def render_goal_celebration_frame(self, bg_rgb, dt):
        dur = 1.5
        if dt < 0.22: scale = 0.4 + 0.75 * (dt / 0.22)
        elif dt < 0.38: scale = 1.15 - 0.15 * ((dt - 0.22) / 0.16)
        else: scale = 1.0 + 0.04 * np.sin((dt - 0.38) * 14.0)

        fade = 1.0
        if dt > (dur - 0.3): fade = max(0.0, (dur - dt) / 0.3)

        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if dt < 0.25:
            flash_alpha = int(115 * (1.0 - dt / 0.25))
            draw.rectangle([0, 0, 1080, 1920], fill=(255, 215, 0, flash_alpha))

        cx, cy = 540, 960
        r_outer = int(380 * scale)
        glow_alpha = int(140 * fade * (0.7 + 0.3 * np.sin(dt * 20.0)))

        draw.ellipse([cx - r_outer, cy - r_outer // 2, cx + r_outer, cy + r_outer // 2], fill=(255, 140, 0, glow_alpha // 2), outline=(255, 215, 0, int(230 * fade)), width=6)

        bw, bh = int(460 * scale), int(155 * scale)
        draw.rounded_rectangle([cx - bw, cy - bh, cx + bw, cy + bh], radius=40, fill=(200, 20, 30, int(242 * fade)), outline=(255, 230, 0, int(255 * fade)), width=7)

        font_main = load_font(max(32, int(86 * scale)))
        font_sub = load_font(max(20, int(44 * scale)))

        main_text = "⚽ ГОООЛ! ⚽"
        bm = draw.textbbox((0, 0), main_text, font=font_main)
        draw.text((cx - (bm[2] - bm[0]) / 2 + 4, cy - (bm[3] - bm[1]) - 16 + 4), main_text, font=font_main, fill=(0, 0, 0, int(220 * fade)))
        draw.text((cx - (bm[2] - bm[0]) / 2, cy - (bm[3] - bm[1]) - 16), main_text, font=font_main, fill=(255, 255, 255, int(255 * fade)))

        sub_text = "🔥  G O A L !  🔥"
        bs = draw.textbbox((0, 0), sub_text, font=font_sub)
        draw.text((cx - (bs[2] - bs[0]) / 2, cy + 22), sub_text, font=font_sub, fill=(255, 230, 0, int(255 * fade)))

        return self.blend_rgba_onto_rgb(bg_rgb, np.array(overlay))

    def render_animated_intro_frame(self, bg_rgb, t, intro_dur, team1, team2, logo1_big, logo2_big):
        slide_p = min(1.0, t / 0.55)
        ease_out = 1.0 - (1.0 - slide_p) ** 3
        fade_out = max(0.0, (intro_dur - t) / 0.4) if t > (intro_dur - 0.4) else 1.0

        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, int(185 * fade_out)))
        draw = ImageDraw.Draw(overlay)
        font_title = load_font(44)
        font_team = load_font(42)
        font_vs = load_font(95)

        draw.rounded_rectangle([50, 560, 1030, 1340], radius=45, fill=(14, 20, 36, int(235 * fade_out)), outline=(255, 215, 0, int(255 * fade_out)), width=5)
        header = "⚡ MATCH HIGHLIGHTS ⚡"
        bh = draw.textbbox((0, 0), header, font=font_title)
        draw.text(((1080 - (bh[2] - bh[0])) / 2, 610), header, font=font_title, fill=(255, 215, 0, int(255 * fade_out)))

        x1 = int(-300 + (140 - (-300)) * ease_out)
        overlay.paste(logo1_big, (x1, 740), logo1_big)
        x2 = int(1120 - (1120 - 700) * ease_out)
        overlay.paste(logo2_big, (x2, 740), logo2_big)

        if t > 0.25:
            vs_text = "VS"
            bvs = draw.textbbox((0, 0), vs_text, font=font_vs)
            draw.ellipse([445, 785, 635, 975], fill=(220, 40, 40, int(240 * fade_out)), outline=(255, 255, 255, int(255 * fade_out)), width=5)
            draw.text(((1080 - (bvs[2] - bvs[0])) / 2, 830), vs_text, font=font_vs, fill=(255, 255, 255, int(255 * fade_out)))

        t1_str, t2_str = team1.upper(), team2.upper()
        draw.text((x1 + 120 - (draw.textbbox((0, 0), t1_str, font=font_team)[2] - draw.textbbox((0, 0), t1_str, font=font_team)[0]) / 2, 1030), t1_str, font=font_team, fill=(255, 255, 255, int(255 * fade_out)))
        draw.text((x2 + 120 - (draw.textbbox((0, 0), t2_str, font=font_team)[2] - draw.textbbox((0, 0), t2_str, font=font_team)[0]) / 2, 1030), t2_str, font=font_team, fill=(255, 255, 255, int(255 * fade_out)))

        lx1 = (1080 - int(760 * ease_out)) // 2
        draw.rounded_rectangle([lx1, 1170, lx1 + int(760 * ease_out), 1182], radius=6, fill=(46, 204, 113, int(255 * fade_out)))
        return self.blend_rgba_onto_rgb(bg_rgb, np.array(overlay))

    def create_top_hud_overlay(self, team1, team2, current_score, logo1_sm, logo2_sm):
        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font_teams = load_font(34)
        font_score = load_font(48)

        draw.rounded_rectangle([45, 50, 1035, 160], radius=28, fill=(12, 16, 28, 225), outline=(255, 215, 0, 195), width=3)
        overlay.paste(logo1_sm, (68, 63), logo1_sm)
        overlay.paste(logo2_sm, (928, 63), logo2_sm)

        match_title = f"{team1.upper()}   vs   {team2.upper()}"
        draw.text(((1080 - (draw.textbbox((0, 0), match_title, font=font_teams)[2] - draw.textbbox((0, 0), match_title, font=font_teams)[0])) / 2, 86), match_title, font=font_teams, fill=(255, 255, 255, 255))
        draw.rounded_rectangle([385, 172, 695, 250], radius=22, fill=(22, 135, 68, 240), outline=(255, 255, 255, 230), width=3)
        draw.text(((1080 - (draw.textbbox((0, 0), current_score.strip(), font=font_score)[2] - draw.textbbox((0, 0), current_score.strip(), font=font_score)[0])) / 2, 182), current_score.strip(), font=font_score, fill=(255, 255, 255, 255))
        return np.array(overlay)

    def create_final_score_overlay(self, team1, team2, final_score, logo1_big, logo2_big):
        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 195))
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle([60, 560, 1020, 1340], radius=42, fill=(16, 22, 36, 245), outline=(255, 215, 0, 255), width=5)
        
        header = "МАТЧ АЯҚТАЛДЫ • FULL TIME"
        draw.text(((1080 - (draw.textbbox((0, 0), header, font=load_font(52))[2] - draw.textbbox((0, 0), header, font=load_font(52))[0])) / 2, 620), header, font=load_font(52), fill=(255, 215, 0, 255))
        
        overlay.paste(logo1_big, (130, 760), logo1_big)
        overlay.paste(logo2_big, (710, 760), logo2_big)
        
        draw.text(((1080 - (draw.textbbox((0, 0), final_score.strip(), font=load_font(120))[2] - draw.textbbox((0, 0), final_score.strip(), font=load_font(120))[0])) / 2, 815), final_score.strip(), font=load_font(120), fill=(46, 204, 113, 255))
        
        teams_line = f"{team1.upper()}   —   {team2.upper()}"
        draw.text(((1080 - (draw.textbbox((0, 0), teams_line, font=load_font(38))[2] - draw.textbbox((0, 0), teams_line, font=load_font(38))[0])) / 2, 1110), teams_line, font=load_font(38), fill=(240, 240, 240, 255))
        return np.array(overlay)

    @staticmethod
    def blend_rgba_onto_rgb(rgb_frame, rgba_overlay):
        alpha = rgba_overlay[:, :, 3:4].astype(np.float32) / 255.0
        return (rgba_overlay[:, :, :3].astype(np.float32) * alpha + rgb_frame.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)

    def download_youtube_video(self, url):
        out_tmpl = os.path.join(self.output_dir, "source_video.%(ext)s")
        for f in os.listdir(self.output_dir):
            if f.startswith("source_video."):
                try: os.remove(os.path.join(self.output_dir, f))
                except: pass
        ydl_opts = {"format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best", "outtmpl": out_tmpl, "merge_output_format": "mp4", "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        return os.path.join(self.output_dir, "source_video.mp4")

    def run_process(self, url):
        try:
            top_n = int(self.top_n_var.get())
            clip_dur = int(self.clip_dur_var.get())
            team1 = self.team1_entry.get().strip() or "КОМАНДА 1"
            team2 = self.team2_entry.get().strip() or "КОМАНДА 2"
            final_score = self.final_score_entry.get().strip() or "0 : 0"

            raw_live_scores = [s.strip() for s in self.live_scores_entry.get().split(",") if s.strip()]
            if not raw_live_scores: raw_live_scores = [final_score]

            logo1_sm, logo2_sm = load_logo_rgba(self.logo1_path, size=(84, 84)), load_logo_rgba(self.logo2_path, size=(84, 84))
            logo1_big, logo2_big = load_logo_rgba(self.logo1_path, size=(240, 240)), load_logo_rgba(self.logo2_path, size=(240, 240))

            self.log("1/5: YouTube-тан видео жүктелуде (yt-dlp)...")
            video_path = self.download_youtube_video(url)
            self.progress_bar.set(0.20)

            y, sr = librosa.load(video_path, sr=16000, mono=True)
            rms = librosa.feature.rms(y=y, frame_length=32000, hop_length=16000)[0]
            rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)

            candidates = []
            for idx in np.argsort(rms_norm)[::-1]:
                t = float(idx)
                if 5 < t < (len(rms_norm) - 5) and all(abs(t - c) >= 15 for c in candidates):
                    candidates.append(t)
                if len(candidates) >= top_n * 2: break

            whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            scored_moments = []
            for t in candidates:
                segments, _ = whisper_model.transcribe(y[int(max(0, t - 5) * sr):int(min(len(y), (t + 5) * sr))], beam_size=1)
                text = " ".join([seg.text.lower() for seg in segments])
                score = float(rms_norm[int(t)])
                if any(w in text for w in KEYWORDS): score += 0.65
                scored_moments.append((score, t))

            highlights = sorted([t for _, t in sorted(scored_moments, key=lambda x: x[0], reverse=True)[:top_n]])
            self.log(f"2/5: Гол сәттері табылды: {[round(t, 1) for t in highlights]}")
            self.progress_bar.set(0.40)

            self.log("3/5: AI кесу және 9:16 форматқа айналдыру...")
            main_video = VideoFileClip(video_path)
            bg_music = AudioFileClip(self.music_path) if self.music_path else None
            yolo_model = YOLO("yolov8n.pt")
            processed_clips = []
            final_outro_rgba = self.create_final_score_overlay(team1, team2, final_score, logo1_big, logo2_big)

            for idx, peak_time in enumerate(highlights):
                start_t = max(0, peak_time - clip_dur * 0.65)
                end_t = min(main_video.duration, start_t + clip_dur)
                peak_offset = peak_time - start_t
                
                subclip = main_video.subclip(start_t, end_t)
                hud_rgba = self.create_top_hud_overlay(team1, team2, raw_live_scores[min(idx, len(raw_live_scores) - 1)], logo1_sm, logo2_sm)

                w, h = subclip.size
                target_w = int(h * 9 / 16)
                if target_w % 2 != 0: target_w -= 1
                sample_times = np.arange(0, subclip.duration, 0.25)
                raw_centers = []

                for t in sample_times:
                    results = yolo_model.predict(subclip.get_frame(t), classes=[0, 32], verbose=False, conf=0.25)
                    boxes = results[0].boxes
                    if boxes is not None and len(boxes) > 0:
                        cls, xyxy = boxes.cls.cpu().numpy(), boxes.xyxy.cpu().numpy()
                        raw_centers.append((xyxy[np.where(cls == 32)[0][0]][0] + xyxy[np.where(cls == 32)[0][0]][2]) / 2.0 if len(np.where(cls == 32)[0]) > 0 else float(np.median((xyxy[:, 0] + xyxy[:, 2]) / 2.0)))
                    else:
                        raw_centers.append(w / 2.0)

                smooth_centers = np.convolve(raw_centers, np.ones(min(7, len(raw_centers))) / min(7, len(raw_centers)), mode="same")

                def process_frame(get_frame, t):
                    x1 = int(np.clip(float(np.interp(t, sample_times, smooth_centers)) - target_w / 2, 0, w - target_w))
                    vertical = self.blend_rgba_onto_rgb(cv2.resize(get_frame(t)[:, x1 : x1 + target_w], (1080, 1920), interpolation=cv2.INTER_LINEAR), hud_rgba)
                    if (idx == 0) and self.intro_var.get() and t <= 2.4: vertical = self.render_animated_intro_frame(vertical, t, 2.4, team1, team2, logo1_big, logo2_big)
                    if self.goal_fx_var.get() and (peak_offset <= t <= peak_offset + 1.5): vertical = self.render_goal_celebration_frame(vertical, t - peak_offset)
                    if (idx == len(highlights) - 1) and t >= (subclip.duration - 2.8): vertical = self.blend_rgba_onto_rgb(vertical, final_outro_rgba)
                    return vertical

                vertical_clip = subclip.fl(process_frame, apply_to=[])

                if self.slowmo_var.get():
                    sm_start, sm_end = min(peak_offset, vertical_clip.duration - 2), min(min(peak_offset, vertical_clip.duration - 2) + 2, vertical_clip.duration)
                    if sm_end > sm_start + 0.5:
                        vertical_clip = concatenate_videoclips([vertical_clip, vertical_clip.subclip(sm_start, sm_end).fx(vfx.speedx, 0.5).without_audio()], method="compose")

                if bg_music:
                    sr_aud = 44100
                    orig_arr = vertical_clip.audio.to_soundarray(fps=sr_aud)
                    music_arr = bg_music.subclip(0, min(bg_music.duration, vertical_clip.duration)).to_soundarray(fps=sr_aud)
                    if len(music_arr) < len(orig_arr): music_arr = np.tile(music_arr, (int(np.ceil(len(orig_arr) / len(music_arr))), 1))
                    music_arr = music_arr[: len(orig_arr)]
                    highlight_curve = np.exp(-0.5 * ((np.linspace(0, vertical_clip.duration, len(orig_arr)) - peak_offset) / 1.8) ** 2)
                    mixed_arr = np.clip(orig_arr * (0.35 + 0.65 * highlight_curve)[:, np.newaxis] + music_arr * (0.65 - 0.50 * highlight_curve)[:, np.newaxis], -1.0, 1.0)
                    vertical_clip = vertical_clip.set_audio(AudioArrayClip(mixed_arr, fps=sr_aud))

                single_out = os.path.join(self.output_dir, f"short_moment_{idx+1}.mp4")
                vertical_clip.write_videofile(single_out, codec="libx264", audio_codec="aac", fps=30, logger=None)
                processed_clips.append(vertical_clip)
                self.log(f"✅ Сәт #{idx+1} дайын!")

            self.progress_bar.set(0.85)

            if len(processed_clips) > 1:
                self.log("4/5: Барлық сәттер біріктірілуде...")
                padded = [processed_clips[0]] + [c.crossfadein(0.3) for c in processed_clips[1:]]
                concatenate_videoclips(padded, padding=-0.3, method="compose").write_videofile(os.path.join(self.output_dir, "FINAL_COMPILATION_SHORTS.mp4"), codec="libx264", audio_codec="aac", fps=30, logger=None)

            self.log("5/5: YouTube-қа арналған мәтіндер мен хештегтер жасалуда...")
            generate_youtube_metadata(team1, team2, final_score, self.output_dir)

            main_video.close()
            if bg_music: bg_music.close()
            self.progress_bar.set(1.0)
            self.log(f"✅ ДАЙЫН! Видеолар мен YouTube мәтіндері сақталды: {self.output_dir}")
            messagebox.showinfo("Сәтті аяқталды!", f"Shorts видеолар және YouTube мәтіні дайын!\nПапка: {self.output_dir}")

        except Exception as e:
            self.log(f"❌ Қате: {str(e)}")
            messagebox.showerror("Қате", f"Қате орын алды:\n{str(e)}")
        finally:
            self.start_btn.configure(state="normal", text="🚀 SHORTS ЖАСАУДЫ БАСТАУ")

if __name__ == "__main__":
    app = FootballShortsMakerApp()
    app.mainloop()
