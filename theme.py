# =====================================================================
# LINEXA - Module 7: Interface & User Interaction (واجهة المستخدم)
# =====================================================================
# الملف ده هو الواجهة بس. مفيهوش صوت ولا AI ولا تنفيذ أوامر.
# شغلته: يعرض الشاشات (مايك -> تسجيل -> انتظار -> نتيجة أو تأكيد أمني)
# ويستنى الباك يبعتله النتيجة.
#
# ---------------------------------------------------------------------
# دليل الربط (للي هيربط الباك بالواجهة)
# ---------------------------------------------------------------------
# 1) اللي يتبدّل بس هو الـ 4 دوال اللي اسمهم mock_... في قسم "MOCK FUNCTIONS":
#       mock_start_recording  -> هنا نادي بداية التسجيل (Module 1)
#       mock_stop_recording   -> هنا نادي إيقاف التسجيل وابدأ المعالجة
#       mock_confirm_action   -> اليوزر وافق على أمر خطير (ابعت الموافقة لـ Module 5/6)
#       mock_cancel_action    -> اليوزر رفض (ابعت الإلغاء)
#    وامسح الدالتين _mock_backend_processing و _mock_finish_confirmed بعد ما
#    تربط، لأنهم بس بيمثلوا الباك.
#
# 2) الباك يرجّع أي نتيجة عن طريق دالة واحدة بس:
#       app.show_backend_result(result_dict)
#    ومتنادوش على resultframe / confirmationframe مباشرة.
#
# 3) شكل الـ dict المقبول:
#    أ) نتيجة عادية:
#       {
#         "success": True أو False,          # لازم bool حقيقي، مش نص "true"/"false"
#         "transcription": "Open Chrome",    # اللي الباك سمعه
#         "command": "open_browser(...)",    # الأمر اللي اتفهم
#         "status": "Successfully completed",
#         "error": None أو "رسالة الخطأ",    # بتظهر بس لو success=False
#       }
#    ب) طلب تأكيد أمني (أمر خطير):
#       { "needs_confirmation": True, "message": "نص السؤال لليوزر" }
#
# 4) ملاحظات مهمة:
#    - لو مفتاح ناقص مش هيحصل كراش، هيتعرض نص افتراضي ("..." أو "Unknown").
#      بس لو "success" ناقص الواجهة هتعتبرها فشل وتعرض شاشة الخطأ.
#    - الـ success لازم True/False حقيقي. النص "false" بيتحسب True في بايثون
#      (يعني هتظهر "All Done" على أمر فاشل).
#    - النصوص بتتقص: transcription و command لـ 160 حرف، status لـ 100، error لـ 200.
#    - ممنوع تنادي أي دالة باك تقيلة (تسجيل/نموذج/تنفيذ) على الـ main thread،
#      الواجهة هتهنج وكل الأنيميشن هيقف. شغّلها في threading.Thread
#      زي ما عملت في الـ mock، وبعدين نادي show_backend_result من الثريد.
#    - لو الباك فيه Exception جوه الثريد، لازم يتمسك (try/except) ويتبعت
#      كنتيجة فشل. لو لأ الثريد هيموت بصمت والواجهة هتفضل على "wait a minute"
#      لحد ما يخلص الـ timeout (120 ثانية).
#    - لو النتيجة جت بعد ما الـ timeout يعرض شاشة الخطأ، هتظهر فوقها عادي.
# =====================================================================

import customtkinter as ctk
import tkinter as tk
import threading
import random
import time
import math
import os

# Pillow بيجي مع customtkinter أصلاً، بنستخدمه هنا عشان نرسم الخلفية المتدرجة.
from PIL import Image, ImageDraw, ImageFont, ImageTk


# ---------- الثيمات (كل الألوان في مكان واحد) ----------
# فيه ثيمين: "light" (الألوان الجديدة اللي طلبوها) و "dark" (الألوان القديمة).
# كل ثيم عبارة عن قاموس بنفس أسماء الألوان. دالة apply_theme بتنسخ ألوان الثيم
# المختار على المتغيرات اللي تحت (BG_COLOR, CARD_COLOR, ...) فباقي الكود مبيتغيرش.
# لو عايز تغير لون: غيره هنا بس.
#
# ملاحظة: BG_COLOR هو لون "نص" الخلفية (المنطقة الهادية اللي في نص الشاشة).
# الألوان المتدرجة اللي في الأطراف متعرفة في BLOBS تحت.
THEMES = {
    "light": {
        "BG_COLOR": "#F1F4FD",        # لون نص الخلفية (فاتح جدًا)
        "CARD_COLOR": "#FFFFFF",      # كروت بيضا
        "CARD_BORDER": "#D6DDF2",     # حدود هادية
        "CARD_HOVER": "#E8EDFB",
        "ACCENT_COLOR": "#2F8CF6",    # أزرق (زي زرار المايك)
        "ACCENT_HOVER": "#1D6FD8",
        "RECORDING_COLOR": "#6A5CF5", # بنفسجي (زي حلقة المايك)
        "SUCCESS_COLOR": "#059669",   # أخضر أغمق شوية عشان يتقرا على الفاتح
        "ERROR_COLOR": "#F43F5E",
        "ERROR_HOVER": "#E11D48",
        "WARNING_COLOR": "#F59E0B",
        "WARNING_PULSE_END": "#FCE3B5",  # آخر لون في نبض شاشة التأكيد
        "TEXT_MAIN": "#1E2A55",       # كحلي غامق (زي "What can i do for you today")
        "TEXT_SUB": "#5B6485",        # رمادي مزرق (زي "Tap the mic and speak")
        "TITLE_A": "#2B8CF5",         # بداية تدرج العنوان (أزرق)
        "TITLE_B": "#6A5CF5",         # نهاية تدرج العنوان (بنفسجي)
    },
    "dark": {
        "BG_COLOR": "#0B0F19",
        "CARD_COLOR": "#131826",
        "CARD_BORDER": "#1E293B",
        "CARD_HOVER": "#1D2438",
        "ACCENT_COLOR": "#38BDF8",
        "ACCENT_HOVER": "#0EA5E9",
        "RECORDING_COLOR": "#818CF8",
        "SUCCESS_COLOR": "#10B981",
        "ERROR_COLOR": "#F43F5E",
        "ERROR_HOVER": "#E11D48",
        "WARNING_COLOR": "#F59E0B",
        "WARNING_PULSE_END": "#7A4F0A",
        "TEXT_MAIN": "#F8FAFC",
        "TEXT_SUB": "#94A3B8",
        "TITLE_A": "#38BDF8",
        "TITLE_B": "#818CF8",
    },
}

# ---------- بقع الألوان اللي بتعمل التدرج في الخلفية ----------
# كل بقعة = (مكان X, مكان Y, اتساع X, اتساع Y, اللون, القوة)
# الأماكن والاتساع كنسبة من عرض/طول النافذة (0 = الحافة الشمال/فوق، 1 = اليمين/تحت).
# اتساع أكبر = البقعة أوسع وأنعم. القوة من 0 لـ 1.
# البقع في الأطراف عشان نص الشاشة يفضل هادي وعناصر الواجهة متبانش عليها حدود.
BLOBS = {
    "light": [
        (0.06, 0.16, 0.20, 0.30, "#A5EAFB", 1.0),   # سماوي فوق شمال
        (0.96, 0.14, 0.16, 0.34, "#CDB8FC", 1.0),   # لافندر فوق يمين
        (0.97, 0.96, 0.17, 0.24, "#F9CDBA", 1.0),   # خوخي تحت يمين
        (0.20, 1.02, 0.20, 0.22, "#BFD0FD", 1.0),   # أزرق فاتح تحت شمال
    ],
    "dark": [
        (0.06, 0.16, 0.20, 0.30, "#0F4560", 0.9),
        (0.96, 0.14, 0.16, 0.34, "#2E2670", 0.9),
        (0.97, 0.96, 0.17, 0.24, "#4B2B3A", 0.8),
        (0.20, 1.02, 0.20, 0.22, "#142C5C", 0.9),
    ],
}

# الثيم اللي بيفتح بيه البرنامج: "light" أو "dark"
DEFAULT_THEME = "light"

# المتغيرات دي بتتملى من apply_theme (تحت). معرّفينها هنا عشان الكود يفضل مقروء.
BG_COLOR = CARD_COLOR = CARD_BORDER = CARD_HOVER = ""
ACCENT_COLOR = ACCENT_HOVER = RECORDING_COLOR = ""
SUCCESS_COLOR = ERROR_COLOR = ERROR_HOVER = WARNING_COLOR = ""
WARNING_PULSE_END = TEXT_MAIN = TEXT_SUB = TITLE_A = TITLE_B = ""


def apply_theme(name):
    """بينسخ ألوان الثيم المختار على المتغيرات العامة (BG_COLOR وباقيهم)."""
    globals().update(THEMES[name])


apply_theme(DEFAULT_THEME)

# أقصى وقت (بالثواني) نستنى فيه رد من الباك قبل ما نعرض شاشة خطأ
BACKEND_TIMEOUT_SECONDS = 120

# نص العنوان اللي بيترسم فوق في الخلفية
TITLE_TEXT = "LINUXA SOUND SYSTEM"


# دالة مساعدة للألوان بس: بتاخد لونين وبتطلع لون في النص بينهم (t=0 اللون الأول، t=1 التاني).
# بستخدمها في أنيميشن النبض عشان لون الحدود يتغير بنعومة.
def mix_colors(c1, c2, t):
    """بيمزج لونين hex بنسبة t (من 0 لـ 1). بنستخدمه عشان نعمل نبض ناعم للحدود."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hex_to_rgb(c):
    """بيحوّل لون hex (#RRGGBB) لـ (r, g, b)."""
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


# ---------- رسم الخلفية المتدرجة ----------

# بتدوّر على خط Bold عريض (Arial على ويندوز) وتحمله. لو مفيش، بتجرب خطوط تانية،
# ولو مفيش خالص بتستخدم الخط الافتراضي بتاع Pillow عشان البرنامج ميقعش.
def _load_title_font(size):
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf",
                 "LiberationSans-Bold.ttf", "FreeSansBold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)
    except Exception:
        return ImageFont.load_default()


# بتعمل صورة الخلفية بحجم النافذة بالظبط: لون أساسي + بقع ألوان ناعمة في الأطراف
# + العنوان بتدرج (أزرق -> بنفسجي) مرسوم فوقها.
# الحيلة: بنحسب البقع على صورة صغيرة (120 بكسل عرض) وبعدين نكبّرها بنعومة،
# فالتدرج يطلع ناعم والحساب يفضل سريع.
def make_background(theme, w, h):
    colors = THEMES[theme]
    base = hex_to_rgb(colors["BG_COLOR"])
    blobs = [(cx, cy, sx, sy, hex_to_rgb(col), st) for cx, cy, sx, sy, col, st in BLOBS[theme]]

    sw = 120
    sh = max(2, int(sw * h / max(1, w)))
    small = Image.new("RGB", (sw, sh))
    pixels = []
    for j in range(sh):
        y = j / (sh - 1)
        for i in range(sw):
            x = i / (sw - 1)
            r, g, b = base
            for cx, cy, sx, sy, col, st in blobs:
                a = min(1.0, math.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2)) * st)
                r += (col[0] - r) * a
                g += (col[1] - g) * a
                b += (col[2] - b) * a
            pixels.append((int(r), int(g), int(b)))
    small.putdata(pixels)

    resample = getattr(Image, "Resampling", Image).BICUBIC
    img = small.resize((w, h), resample)

    # العنوان بتدرج: بنرسم النص كـ "قناع" وبنلصق فوقه صورة متدرجة
    try:
        font = _load_title_font(50)
        bbox = ImageDraw.Draw(img).textbbox((0, 0), TITLE_TEXT, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        mask = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(mask).text((-bbox[0], -bbox[1]), TITLE_TEXT, font=font, fill=255)
        grad = Image.new("RGB", (tw, th))
        gd = ImageDraw.Draw(grad)
        for x in range(tw):
            gd.line([(x, 0), (x, th)], fill=mix_colors(colors["TITLE_A"], colors["TITLE_B"], x / max(1, tw - 1)))
        img.paste(grad, ((w - tw) // 2, 30), mask)
    except Exception:
        pass  # لو رسم العنوان فشل لأي سبب، الخلفية تفضل شغالة من غير عنوان بدل ما البرنامج يقع

    return img


# الكلاس الرئيسي: هو النافذة كلها. كل شاشة هي دالة جواه (micframe, recordingframe...)
# وبننتقل بينهم بإننا نمسح اللي على الشاشة ونرسم الشاشة الجديدة.
class Linuxa(ctk.CTk):
    # بيتنادى مرة واحدة أول ما البرنامج يفتح: بيجهز النافذة والخلفية والمتغيرات
    # وبعدين بيفتح شاشة المايك.
    def __init__(self):
        super().__init__()

        self.title("LINUXA - sound os ")
        self.geometry("900x600")
        self.minsize(800, 600)
        self.configure(fg_color=BG_COLOR)

        # متغيرات الحالة
        self.is_recording = False
        self._timeout_id = None  # مؤقت الـ timeout
        self._pulse_id = None    # مؤقت أنيميشن النبض
        self.theme = DEFAULT_THEME      # الثيم الحالي
        self._current_screen = None     # (الدالة, الـ args) بتاعة الشاشة الظاهرة، عشان نعيد رسمها لما الثيم يتغير
        self._box = None                # صندوق الشاشة الحالية
        self._bg_photo = None           # لازم نحتفظ بالصورة عشان tkinter ميمسحهاش
        self._bg_size = None            # آخر حجم اترسمت بيه الخلفية
        self._resize_job = None         # مؤقت إعادة رسم الخلفية لما النافذة تتكبر/تتصغر

        # 🌟 الخلفية المتدرجة: Label بيغطي النافذة كلها وعليه الصورة.
        # بنعمله أول حاجة عشان يفضل تحت كل العناصر التانية.
        # (العنوان نفسه مرسوم جوه الصورة دي، فمفيش Label للعنوان.)
        self.bg_label = tk.Label(self, bd=0, highlightthickness=0, bg=BG_COLOR)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # زرار تبديل الثيم
        self.theme_btn = ctk.CTkButton(
            self,
            text="🌙" if self.theme == "light" else "☀️",
            width=44,
            height=44,
            corner_radius=22,
            fg_color=CARD_COLOR,
            hover_color=CARD_HOVER,
            text_color=TEXT_MAIN,
            border_width=1,
            border_color=CARD_BORDER,
            font=ctk.CTkFont(size=20),
            command=self.toggle_theme,
        )
        self.theme_btn.place(relx=1.0, x=-16, y=14, anchor="ne")

        # إعادة رسم الخلفية لما حجم النافذة يتغير (مع تأخير بسيط عشان متتعملش مليون مرة)
        self.bind("<Configure>", self._on_configure)
        self._render_background()

        self.micframe()

    # ---------- الخلفية ----------

    # بتتنادى مع كل تغيير في النافذة: بتتجاهل أحداث العناصر الصغيرة
    # وبتأجل إعادة الرسم 100 ملي ثانية لحد ما التكبير/التصغير يخلص.
    def _on_configure(self, event):
        if event.widget is not self:
            return
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(100, self._render_background)

    # بترسم الخلفية بحجم النافذة الحالي وتحطها. لو الحجم مغيرش مبتعملش حاجة (إلا لو force).
    def _render_background(self, force=False):
        self._resize_job = None
        w, h = self.winfo_width(), self.winfo_height()
        if w < 100 or h < 100:  # النافذة لسه معملتش رسم، نستخدم الحجم الافتراضي
            w, h = 900, 600
        if not force and self._bg_size == (w, h):
            return
        self._bg_size = (w, h)
        self._bg_photo = ImageTk.PhotoImage(make_background(self.theme, w, h))
        self.bg_label.configure(image=self._bg_photo, bg=BG_COLOR)

    # ---------- تبديل الثيم ----------

    # بتتنادى لما اليوزر يدوس على زرار الثيم: بتقلب بين light و dark.
    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self._refresh_theme()

    # بتطبق الثيم الحالي: بتحدّث الألوان الثابتة (الخلفية وزرار الثيم)
    # وبعدين تعيد رسم نفس الشاشة الظاهرة بالألوان الجديدة.
    # (كل شاشة بتترسم من الصفر كل مرة أصلاً، فإعادة الرسم بسيطة ومبتبوظش حاجة،
    # والـ timeout والباك مبيتأثروش.)
    def _refresh_theme(self):
        apply_theme(self.theme)
        self.configure(fg_color=BG_COLOR)
        self._render_background(force=True)
        self.theme_btn.configure(
            text="🌙" if self.theme == "light" else "☀️",
            fg_color=CARD_COLOR,
            hover_color=CARD_HOVER,
            text_color=TEXT_MAIN,
            border_color=CARD_BORDER,
        )
        if self._current_screen is not None:
            func, args = self._current_screen
            func(*args)

    # بتتنادى في أول كل شاشة: بتوقف الأنيميشن القديم وتمسح صندوق الشاشة القديمة.
    # لازم توقف الأنيميشن قبل المسح عشان ميحصلش إن مؤقت يحاول يعدّل على عنصر اتمسح.
    def clear_frame(self):
        """تنظيف محتويات الشاشة الحالية بسلاسة"""
        self._stop_pulse()
        for name in ("waveform_progress", "processing_progress"):
            bar = getattr(self, name, None)
            if bar is not None:
                try:
                    bar.stop()
                except Exception:
                    pass
        if self._box is not None:
            try:
                self._box.destroy()
            except Exception:
                pass
            self._box = None

    # بتعمل "صندوق" في نص الشاشة، وكل شاشة بتحط محتواها جواه عشان يفضل متنسق.
    def new_box(self):
        """بيعمل حاوية في نص الشاشة بالظبط عشان المحتوى يفضل متناسق ومنضبط."""
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.place(relx=0.5, rely=0.55, anchor="center")
        self._box = box
        return box

    # ---------- أنيميشن النبض (بيشد العين من غير ما يزعج) ----------

    # بتخلي حدود عنصر (widget) تتحرك رايح جاي بين لونين (color_a و color_b)
    # كأنها بتنبض. بتشتغل لوحدها كل 60 ملي ثانية لحد ما حد يوقفها.
    # period_ms = مدة النبضة الكاملة.
    def _start_pulse(self, widget, color_a, color_b, period_ms=1800):
        self._stop_pulse()
        t0 = time.time()

        def tick():
            try:
                k = (1 + math.sin((time.time() - t0) * 2 * math.pi / (period_ms / 1000))) / 2
                widget.configure(border_color=mix_colors(color_a, color_b, k))
            except Exception:
                # لو العنصر اتمسح (الشاشة اتغيرت) نوقف النبض بهدوء من غير خطأ
                self._pulse_id = None
                return
            self._pulse_id = self.after(60, tick)

        tick()

    # بتوقف أي نبض شغال. آمنة تتنادى حتى لو مفيش حاجة شغالة.
    def _stop_pulse(self):
        if self._pulse_id is not None:
            try:
                self.after_cancel(self._pulse_id)
            except Exception:
                pass
            self._pulse_id = None

    # أنيميشن شاشة التسجيل: الدايرة (halo) بتكبر وتصغر عشوائي وتنور كأنها بتتفاعل مع صوت اليوزر.
    # (مش بتقرأ الصوت الحقيقي، ده شكل بس.)
    # base = الحجم الأساسي، wobble = أقصى فرق في الحجم.
    def _start_blob(self, halo, base=140, wobble=24):
        """بيخلي الهالو يتغير حجمه وشكله بشكل عشوائي وناعم، كأنه بيتفاعل مع صوت اليوزر.
        مهم: بيستخدم نفس مؤقت النبض (_pulse_id)، فـ clear_frame بتوقفه لوحدها."""
        self._stop_pulse()
        st = {"w": base, "h": base, "tw": base, "th": base}

        def tick():
            try:
                # كل شوية بنختار حجم "هدف" عشوائي جديد للعرض والطول
                if random.random() < 0.3:
                    st["tw"] = base + random.randint(-wobble, wobble)
                    st["th"] = base + random.randint(-wobble, wobble)
                # بنقرّب الحجم الحالي من الهدف بالتدريج عشان الحركة تبقى ناعمة
                st["w"] += (st["tw"] - st["w"]) * 0.35
                st["h"] += (st["th"] - st["h"]) * 0.35
                w, h = int(st["w"]), int(st["h"])
                # كل ما الهالو يكبر، لونه ينور أكتر
                k = max(0.0, min(1.0, (w + h - 2 * (base - wobble)) / (4 * wobble)))
                halo.configure(
                    width=w, height=h,
                    corner_radius=min(w, h) // 2,
                    border_color=mix_colors(ACCENT_COLOR, RECORDING_COLOR, k),
                )
            except Exception:
                # نفس الفكرة: لو العنصر اتمسح نوقف من غير ما نعمل كراش
                self._pulse_id = None
                return
            self._pulse_id = self.after(70, tick)

        tick()

    # ==========================================
    # الشاشات (بنفس هيكل كودك الأصلي بالظبط)
    # ==========================================
    # كل دالة هنا بترسم شاشة واحدة بس. مفيهاش منطق باك، بس عرض.
    # ترتيب الشاشات: micframe -> recordingframe -> processingframe -> resultframe
    # وفي حالة أمر خطير: processingframe -> confirmationframe -> processingframe -> resultframe
    # (السطر اللي فيه _current_screen في أول كل شاشة بيحفظ الشاشة الحالية عشان تتعاد لما الثيم يتغير.)

    # الشاشة 1: شاشة البداية. فيها زرار المايك. لما اليوزر يدوس بتنادي start_recording_ui.
    def micframe(self):
        self.clear_frame()
        self._current_screen = (self.micframe, ())
        box = self.new_box()

        # العنوان الرئيسي مرسوم فوق في الخلفية، هنا بنحط النص الترحيبي والمايك بس
        sub_title = ctk.CTkLabel(box, text="What can i do for you today 😊", text_color=TEXT_MAIN, font=ctk.CTkFont(size=20, weight="bold"))
        sub_title.pack(pady=(0, 24))

        mic_halo = ctk.CTkFrame(box, width=160, height=160, corner_radius=80, fg_color=CARD_COLOR, border_width=3, border_color=CARD_BORDER)
        mic_halo.pack(pady=(0, 16))
        mic_halo.pack_propagate(False)

        self.mic_btn = ctk.CTkButton(
            mic_halo,
            text="🎙️",
            text_color="#FFFFFF",
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=48),
            width=120,
            height=120,
            corner_radius=60,
            fg_color=ACCENT_COLOR,
            command=self.start_recording_ui,
        )
        self.mic_btn.place(relx=0.5, rely=0.5, anchor="center")

        hint = ctk.CTkLabel(box, text="Tap the mic and speak", text_color=TEXT_SUB, font=ctk.CTkFont(size=14))
        hint.pack()

        # الحلقة بتنبض بين الأزرق والبنفسجي (زي تدرج الحلقة في التصميم)
        self._start_pulse(mic_halo, ACCENT_COLOR, RECORDING_COLOR)

    # الشاشة 2: شاشة "بسمعك". فيها دايرة بتتحرك وشريط تحميل وزرار Stop.
    # لما اليوزر يدوس Stop بتنادي stoprecordingui.
    def recordingframe(self):
        self.clear_frame()
        self._current_screen = (self.recordingframe, ())
        box = self.new_box()

        subtitle = ctk.CTkLabel(box, text="I am listening to you 🎧.....", text_color=RECORDING_COLOR, font=ctk.CTkFont(size=22, weight="bold"))
        subtitle.pack(pady=(0, 24))

        # holder: مربع ثابت الحجم، والهالو بيتحرك جواه من غير ما يزق باقي العناصر
        holder = ctk.CTkFrame(box, width=180, height=180, fg_color="transparent")
        holder.pack(pady=(0, 6))
        holder.pack_propagate(False)
        rec_halo = ctk.CTkFrame(holder, width=140, height=140, corner_radius=70, fg_color=CARD_COLOR, border_width=3, border_color=RECORDING_COLOR)
        rec_halo.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(rec_halo, text="🎙️",text_color=ACCENT_COLOR, font=ctk.CTkFont(size=46)).place(relx=0.5, rely=0.5, anchor="center")

        self.waveform_progress = ctk.CTkProgressBar(box, width=400, height=12, corner_radius=6, fg_color=CARD_BORDER, progress_color=RECORDING_COLOR, mode="indeterminate")
        self.waveform_progress.pack(pady=(0, 24))
        self.waveform_progress.start()

        stopbtn = ctk.CTkButton(
            box,
            width=200,
            height=46,
            corner_radius=23,
            text="stop recording",
            text_color="#FFFFFF",
            fg_color=ERROR_COLOR,
            hover_color=ERROR_HOVER,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.stoprecordingui,
        )
        stopbtn.pack()

        self._start_blob(rec_halo)

    # الشاشة 3: شاشة الانتظار "wait a minute". بتفضل ظاهرة لحد ما الباك يرد
    # (بنستدعي show_backend_result) أو يخلص الـ timeout.
    def processingframe(self):
        self.clear_frame()
        self._current_screen = (self.processingframe, ())
        box = self.new_box()

        textlabel = ctk.CTkLabel(box, text="wait a minute.... ", text_color=TEXT_SUB, font=ctk.CTkFont(size=24, weight="bold"))
        textlabel.pack(pady=(0, 24))

        think_halo = ctk.CTkFrame(box, width=140, height=140, corner_radius=70, fg_color=CARD_COLOR, border_width=3, border_color=ACCENT_COLOR)
        think_halo.pack(pady=(0, 20))
        think_halo.pack_propagate(False)
        ctk.CTkLabel(think_halo, text="🧠",text_color=ACCENT_COLOR, font=ctk.CTkFont(size=46)).place(relx=0.5, rely=0.5, anchor="center")

        self.processing_progress = ctk.CTkProgressBar(box, width=400, height=12, corner_radius=6, fg_color=CARD_BORDER, progress_color=ACCENT_COLOR, mode="indeterminate")
        self.processing_progress.pack()
        self.processing_progress.start()

        self._start_pulse(think_halo, ACCENT_COLOR, RECORDING_COLOR, period_ms=1400)

    # الشاشة 4: شاشة النتيجة. بتعرض: اللي اتسمع (transcription) والأمر (command) والحالة (status).
    # لو error مش فاضي بتعرض عنوان الخطأ الأحمر، لو فاضي بتعرض "All Done".
    # الزرار Start Over بيرجّع لشاشة المايك.
    def resultframe(self, transcription, command, status, error=None):
        self.clear_frame()
        self._current_screen = (self.resultframe, (transcription, command, status, error))
        box = self.new_box()

        # فريم فاضي عرضه ثابت عشان الشاشة متتغيرش في العرض حسب طول النص
        ctk.CTkFrame(box, width=580, height=1, fg_color="transparent").pack()

        if error:
            title = ctk.CTkLabel(box, text="something went wrong ! 🥺....", text_color=ERROR_COLOR, font=ctk.CTkFont(size=26, weight="bold"))
            title.pack(pady=(0, 6))
            sub = ctk.CTkLabel(box, text=error, text_color=TEXT_SUB, font=ctk.CTkFont(size=15, weight="bold"), wraplength=550)
            sub.pack(pady=(0, 12))
        else:
            title = ctk.CTkLabel(box, text="All Done 😁", text_color=SUCCESS_COLOR, font=ctk.CTkFont(size=30, weight="bold"))
            title.pack(pady=(0, 12))

        # الكارت الأنيق اللي بيجمع المعلومات
        card = ctk.CTkFrame(box, fg_color=CARD_COLOR, corner_radius=18, border_width=1, border_color=CARD_BORDER)
        card.pack(fill="x", pady=(0, 14))

        # Transcription
        ctk.CTkLabel(card, text="I heard : ", text_color=ACCENT_COLOR, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=24, pady=(16, 2))
        ctk.CTkLabel(card, text=f'"{transcription}"', text_color=TEXT_MAIN, font=ctk.CTkFont(size=16), wraplength=530, justify="left").pack(anchor="w", padx=24, pady=(0, 10))

        # Command
        ctk.CTkLabel(card, text="command:", text_color=ACCENT_COLOR, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=24, pady=2)
        ctk.CTkLabel(card, text=command, text_color=TEXT_MAIN, font=ctk.CTkFont(size=16), wraplength=530, justify="left").pack(anchor="w", padx=24, pady=(0, 10))

        # Status
        status_color = ERROR_COLOR if error or status == "Failed" else SUCCESS_COLOR
        ctk.CTkLabel(card, text="status:", text_color=ACCENT_COLOR, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=24, pady=2)
        ctk.CTkLabel(card, text=status, text_color=status_color, font=ctk.CTkFont(size=16, weight="bold"), wraplength=530, justify="left").pack(anchor="w", padx=24, pady=(0, 16))

        # زرار Start Over
        record_again_btn = ctk.CTkButton(
            box,
            text="Start Over",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            text_color="#FFFFFF",
            width=200,
            height=46,
            corner_radius=23,
            command=self.reset_to_recording,
        )
        record_again_btn.pack()

    # شاشة التأكيد الأمني: بتظهر لما الباك يقول إن الأمر خطير (needs_confirmation).
    # message = السؤال اللي هيتعرض لليوزر.
    # Nevermind -> mock_cancel_action | Yes, do it -> mock_confirm_action
    # ملاحظة: الشاشة دي مفيهاش timeout عن قصد، لأننا بنستنى اليوزر مش الباك.
    def confirmationframe(self, message):
        self.clear_frame()
        self._current_screen = (self.confirmationframe, (message,))
        box = self.new_box()

        # 🌟 فريم السيكيوريتي الأنيق بإطار أصفر هادئ ومتناسق
        card = ctk.CTkFrame(box, fg_color=CARD_COLOR, corner_radius=20, border_width=2, border_color=WARNING_COLOR)
        card.pack()
        ctk.CTkFrame(card, width=540, height=1, fg_color="transparent").pack()

        icon = ctk.CTkLabel(card, text="⚠️", font=ctk.CTkFont(size=52), text_color=WARNING_COLOR)
        icon.pack(pady=(24, 6))

        subtitle = ctk.CTkLabel(card, text="Security Confirmation Needed", text_color=WARNING_COLOR, font=ctk.CTkFont(size=26, weight="bold"))
        subtitle.pack(pady=(0, 10))

        msg_label = ctk.CTkLabel(card, text=message, text_color=TEXT_MAIN, font=ctk.CTkFont(size=16), wraplength=480)
        msg_label.pack(pady=(0, 24))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=(0, 28))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Nevermind",
            text_color=TEXT_MAIN,
            hover_color=CARD_HOVER,
            fg_color=BG_COLOR,
            border_width=1,
            border_color=CARD_BORDER,
            font=ctk.CTkFont(size=15, weight="bold"),
            width=150,
            height=44,
            corner_radius=22,
            command=self.mock_cancel_action,
        )
        cancel_btn.pack(side="left", padx=10)

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Yes, do it",
            text_color="#FFFFFF",
            hover_color=ERROR_HOVER,
            fg_color=ERROR_COLOR,
            font=ctk.CTkFont(size=15, weight="bold"),
            width=150,
            height=44,
            corner_radius=22,
            command=self.mock_confirm_action,
        )
        confirm_btn.pack(side="right", padx=10)

        self._start_pulse(card, WARNING_COLOR, WARNING_PULSE_END, period_ms=2000)

    # ==========================================
    # استقبال النتيجة من الباك
    # ==========================================

    # ⭐ دي النقطة الوحيدة اللي الباك ينادي عليها (من أي Thread) عشان يعرض أي نتيجة.
    # بتبعت النتيجة للـ main thread عن طريق self.after عشان tkinter ميتلخبطش.
    # لو النافذة اتقفلت قبل ما النتيجة توصل، الخطأ بيتمسك وبيتجاهل من غير كراش.
    def show_backend_result(self, result):
        """النقطة الوحيدة اللي الباك ينادي عليها لعرض أي نتيجة."""
        try:
            self.after(0, self._handle_result, result)
        except Exception:
            pass

    # بتشتغل على الـ main thread. بتوقف الـ timeout، وتتأكد إن النتيجة dict سليم،
    # وبعدين تقرر: تعرض شاشة تأكيد (needs_confirmation) ولا شاشة نتيجة عادية.
    # أي حاجة غريبة في الداتا بتتمسك وبتتعرض كشاشة خطأ بدل ما البرنامج يقع.
    def _handle_result(self, result):
        self._cancel_timeout()
        try:
            if not isinstance(result, dict):
                raise ValueError("Invalid response from backend")

            if result.get("needs_confirmation"):
                self.confirmationframe(str(result.get("message") or "Are you sure you want to continue?"))
                return

            success = bool(result.get("success", False))
            # [:160] معناها "خدي أول 160 حرف بس" عشان النص الطويل ميبوّظش شكل الشاشة
            transcription = str(result.get("transcription") or "...")[:160]
            command = str(result.get("command") or "Unknown")[:160]
            status = str(result.get("status") or ("Completed" if success else "Failed"))[:100]
            error = None if success else str(result.get("error") or "Something went wrong.")[:200]

            self.resultframe(transcription, command, status, error)
        except Exception as e:
            self.resultframe("...", "Unknown", "Failed", f"Unexpected error: {e}")

    # ---------- Timeout ----------
    # فكرته: لو الباك سكت أكتر من BACKEND_TIMEOUT_SECONDS، منفضلش على شاشة الانتظار للأبد
    # ونعرض شاشة خطأ.

    # بتشغّل عداد الـ timeout (وبتلغي أي عداد قديم الأول).
    def _start_timeout(self):
        self._cancel_timeout()
        self._timeout_id = self.after(BACKEND_TIMEOUT_SECONDS * 1000, self._on_timeout)

    # بتلغي العداد. بتتنادى أول ما النتيجة توصل.
    def _cancel_timeout(self):
        if self._timeout_id is not None:
            try:
                self.after_cancel(self._timeout_id)
            except Exception:
                pass
            self._timeout_id = None

    # بتشتغل لو الوقت خلص من غير رد: بتعرض شاشة خطأ.
    def _on_timeout(self):
        self._timeout_id = None
        self.resultframe("...", "Unknown", "Failed", "This is taking too long. Please try again.")

    # ==========================================
    # دوال الأزرار
    # ==========================================
    # دي اللي بتتنادى لما اليوزر يدوس على زرار. هي الجسر بين الواجهة والباك.

    # اليوزر داس على المايك: بنبلّغ الباك إن التسجيل يبدأ، ولو نجح نفتح شاشة التسجيل.
    # لو الباك رمى Exception نعرض شاشة خطأ ومنفتحش شاشة التسجيل.
    # (بتتنفذ على الـ main thread: لو بداية التسجيل بطيئة شغّلها في thread.)
    def start_recording_ui(self):
        try:
            self.mock_start_recording()
        except Exception as e:
            self.resultframe("...", "Unknown", "Failed", f"Couldn't start recording: {e}")
            return
        self.is_recording = True
        self.recordingframe()

    # اليوزر داس Stop: نفتح شاشة الانتظار ونشغل الـ timeout وبعدين نبلّغ الباك إن التسجيل وقف.
    # لو الباك رمى Exception نلغي الـ timeout ونعرض شاشة خطأ بدل ما نفضل مستنيين.
    def stoprecordingui(self):
        self.is_recording = False
        self.processingframe()
        self._start_timeout()
        # لو دالة الباك وقعت، نعرض شاشة خطأ بدل ما الشاشة تفضل مستنية للأبد
        try:
            self.mock_stop_recording()
        except Exception as e:
            self._cancel_timeout()
            self.resultframe("...", "Unknown", "Failed", f"Couldn't process recording: {e}")

    # زرار Start Over: بيرجّع لشاشة المايك.
    def reset_to_recording(self):
        self.micframe()

    # ==========================================
    # MOCK FUNCTIONS
    # ==========================================
    # ⚠️ كل اللي تحت ده تمثيل بس عشان أجرب الواجهة لوحدي.
    # اللي هيربط: بدّل جوه الدوال دي بالكود الحقيقي، وامسح الباقي.

    # [Module 1] امسح الـ print وحط مكانه نداء بداية التسجيل.
    def mock_start_recording(self):
        print("[Backend Mock] Recording started...")

    # [Module 1 ثم 2 ثم 3 ثم 4 ثم 5 ثم 6] امسح الـ print، وغيّر target=self._mock_backend_processing
    # بدالة الباك الحقيقية. سيب الـ Thread زي ما هو.
    def mock_stop_recording(self):
        print("[Backend Mock] Recording stopped. Processing...")
        threading.Thread(target=self._mock_backend_processing, daemon=True).start()

    # امسحها كلها. الباك الحقيقي يبعت النتيجة بنفس الشكل بـ show_backend_result.
    def _mock_backend_processing(self):
        time.sleep(2.5)
        scenario = random.choice(["success", "error", "confirmation"])

        if scenario == "success":
            self.show_backend_result({
                "success": True,
                "transcription": "Open Google Chrome",
                "command": "open_browser(target='Chrome')",
                "status": "Successfully completed",
                "error": None,
                "needs_confirmation": False,
            })
        elif scenario == "error":
            self.show_backend_result({
                "success": False,
                "transcription": "...",
                "command": "Unknown",
                "status": "Failed",
                "error": "I couldn't understand your voice clearly. Please try again.",
                "needs_confirmation": False,
            })
        else:
            self.show_backend_result({
                "needs_confirmation": True,
                "message": "This action might affect your system files. Are you sure you want to continue?",
            })

    # [Module 5 / 6] سيب processingframe والـ timeout، وغيّر target=self._mock_finish_confirmed
    # بدالة الباك اللي بتنفذ الأمر. النتيجة ترجع بـ show_backend_result.
    def mock_confirm_action(self):
        """اليوزر داس "Yes, do it": بنفتح شاشة الانتظار الأول (لأن التنفيذ بياخد وقت)،
        وبعدين النتيجة بتيجي من الباك وتظهر شاشة النتيجة."""
        print("[Backend Mock] Action Confirmed by user.")
        self.processingframe()
        self._start_timeout()
        try:
            threading.Thread(target=self._mock_finish_confirmed, daemon=True).start()
        except Exception as e:
            self._cancel_timeout()
            self.resultframe("...", "Unknown", "Failed", f"Couldn't send the confirmation: {e}")

    # امسحها بعد الربط.
    def _mock_finish_confirmed(self):
        # بيمثل وقت تنفيذ الأمر عند Module 6 (رزق)
        time.sleep(1.5)
        self.show_backend_result({
            "success": True,
            "transcription": "Delete system file",
            "command": "delete_file()",
            "status": "Executed successfully",
        })

    # [Module 5 / 8] ابلّغ الباك إن الأمر اتلغى (عشان ميتنفذش ويتسجل في الـ log).
    # سيب عرض شاشة النتيجة زي ما هو.
    def mock_cancel_action(self):
        """اليوزر داس "Nevermind": مفيش حاجة هتتنفذ، فبنروح للنتيجة على طول من غير شاشة انتظار."""
        print("[Backend Mock] Action Canceled by user.")
        self.show_backend_result({
            "success": True,
            "transcription": "Delete system file",
            "command": "delete_file()",
            "status": "Cancelled by you",
        })


# نقطة البداية: بيفتح النافذة ويفضل شغال لحد ما اليوزر يقفلها.
if __name__ == "__main__":
    app = Linuxa()
    app.mainloop()