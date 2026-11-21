
MODEL_SIZE = "small"              
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
MODEL_DIR = None  
# auto = Whisper يخمّن | ar = عربي | en = إنجليزي | best_of_two = يجرّب الاتنين ويختار الأوثق
LANGUAGE_MODE = "best_of_two"

# كلمات بتساعد Whisper يتعرف على أسماء التطبيقات. لو طلعت أسوأ خليها ""
#اخد اسامي الاوامر اللي هيدعمها بجد سواء من موديول 3 و 6 واسامي التطبيقات كمان وده بيحسن الاسماء الانجليزي الموجوده جوه العربي
INITIAL_PROMPT = "Chrome,Spotify,Firefox,YouTube" 
CONFIDENCE_THRESHOLD = 0.7

BEAM_SIZE = 5
VAD_FILTER = False   # True يشيل الصمت تلقائيًا، لكن ممكن يقص أوامر قصيرة

# فحص الـ WAV (بيشتغل على ملفات .wav بس)
CHECK_WAV = True #not used yet
EXPECTED_RATE = 16000
EXPECTED_CHANNELS = 1

# كلمة التنشيط لو اتسجلت في أول الملف (هنشيلها)
WAKE_WORDS = []

#ده بيشيل الهلوسه اللي ويسبر هيهلوسها وقت الصمت ومع التجارب كل ما يحصل هلوسه معايا اكتبها عشان متحصلش تاني
# جمل وهمية بيألفها Whisper على الصمت
HALLUCINATIONS = [
    "شكرا على المشاهدة", "شكرًا على المشاهدة", "شكرا لمشاهدتكم",
    "اشتركوا في القناة", "thank you", "thanks for watching",
    "thank you for watching", "you", "bye",
]
#اضيف الحاجات اللي ممكن تتكتب بطريقتين بعد ما اخد الاوامر
# توحيد أسماء التطبيقات لحساب الدقة (بتتحط بالشكل المبسّط)
APP_SYNONYMS = {
    "كروم": "chrome",
    "كروميوم": "chromium",
    "سبوتيفاي": "spotify",
    "سبوتفاي": "spotify",
    "فايرفوكس": "firefox",
    "يوتيوب": "youtube",
    "جوجل": "google",
    "الاله الحاسبه":"calculator",
    "الحاسبه":"calculator",
    "الاعدادات":"settings",
    "الترمينال":"terminal",
    "ترمينال":"terminal"
      
     }
    

