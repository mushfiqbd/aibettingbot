# 🤖 AI Integrated Betting Telegram Bot

একটি সম্পূর্ণ প্রোডাকশন-রেডি **এআই-চালিত বেটিং বট** যা Telegram-এ চলে এবং রিয়েল-টাইম ম্যাচ ডেটা, লাইভ অডস, এবং স্মার্ট বেট সাজেশন প্রদান করে।

## 🎯 মূল বৈশিষ্ট্য

✅ **লাইভ ম্যাচ ফেচিং** - The Odds API থেকে রিয়েল-টাইম ম্যাচ ডেটা এবং অডস  
✅ **ইউজার বেটিং সিস্টেম** - যেকোনো ম্যাচে সহজে বেট করুন  
✅ **ডিপোজিট/উইথড্র** - এডমিন অনুমোদনে নিরাপদ লেনদেন  
✅ **এআই ইন্টিগ্রেশন** - ChatGPT-চালিত বেট সাজেশন এবং কথোপকথন  
✅ **ভয়েস রেসপন্স** - gTTS ব্যবহার করে প্রতিটি কমান্ডে ভয়েস উত্তর  
✅ **অ্যাডমিন প্যানেল** - সম্পূর্ণ নিয়ন্ত্রণ এবং মনিটরিং  
✅ **ডেটাবেস** - SQLite/PostgreSQL সাপোর্ট  
✅ **অটো রেজাল্ট ট্র্যাকিং** - ম্যাচ শেষে স্বয়ংক্রিয় জয়/পরাজয় নির্ধারণ  

## 📋 প্রয়োজনীয় ক্রেডেনশিয়ালস

আপনাকে নিম্নলিখিত API কী এবং টোকেনগুলি প্রয়োজন:

### 1. **Telegram Bot Token**
- Telegram-এ `@BotFather` খুঁজুন
- `/start` → `/newbot` ব্যবহার করে নতুন বট তৈরি করুন
- Token কপি করুন

### 2. **The Odds API Key**
- https://the-odds-api.com/ এ যান
- ফ্রি অ্যাকাউন্ট তৈরি করুন
- API Key পান

### 3. **OpenAI API Key**
- https://platform.openai.com/ এ যান
- API keys সেকশনে যান
- নতুন key তৈরি করুন

## 🚀 ইনস্টলেশন এবং সেটআপ

### ধাপ 1: প্রয়োজনীয় প্যাকেজ ইনস্টল করুন

```bash
pip install -r requirements.txt
```

### ধাপ 2: পরিবেশ ভেরিয়েবল সেট করুন

```bash
# env_example.txt কপি করে .env তে রিনেম করুন
# .env ফাইল খুলুন এবং আপনার ক্রেডেনশিয়ালস যোগ করুন
```

**Windows এ:**
```bash
copy env_example.txt .env
```

**Linux/Mac এ:**
```bash
cp env_example.txt .env
```

### ধাপ 3: .env ফাইল এডিট করুন

```env
TELEGRAM_BOT_TOKEN=আপনার_বট_টোকেন
ADMIN_ID=আপনার_টেলিগ্রাম_আইডি
ODDS_API_KEY=আপনার_অডস_এপিআই_কী
OPENAI_API_KEY=আপনার_ওপেনএআই_কী
```

### ধাপ 4: বট চালু করুন

```bash
python main.py
```

## 📱 ব্যবহারকারী কমান্ডসমূহ

| কমান্ড | বর্ণনা |
|--------|--------|
| `/start` | বটকে স্বাগত জানান এবং রেজিস্টার করুন |
| `/live` | চলমান ম্যাচ দেখুন |
| `/upcoming` | আসন্ন ম্যাচ দেখুন |
| `/odds` | নির্দিষ্ট ম্যাচের অডস দেখুন |
| `/bet` | বেট করুন |
| `/mybets` | আপনার সমস্ত বেট দেখুন |
| `/balance` | ব্যালেন্স এবং পরিসংখ্যান দেখুন |
| `/deposit` | ডিপোজিট রিকোয়েস্ট করুন |
| `/withdraw` | উইথড্র রিকোয়েস্ট করুন |
| `/help` | সাহায্য পান |

## 🛡️ অ্যাডমিন কমান্ডসমূহ

| কমান্ড | বর্ণনা |
|--------|--------|
| `/approve_deposit <tx_id>` | ডিপোজিট অনুমোদন করুন |
| `/approve_withdraw <tx_id>` | উইথড্র অনুমোদন করুন |
| `/stats` | সিস্টেম পরিসংখ্যান দেখুন |
| `/users` | সমস্ত ব্যবহারকারী দেখুন |

## 🗄️ ডাটাবেস স্কিমা

### Users Table
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    balance REAL DEFAULT 0,
    total_bet INTEGER DEFAULT 0,
    total_win INTEGER DEFAULT 0,
    total_loss INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    is_verified BOOLEAN DEFAULT 0
);
```

### Bets Table
```sql
CREATE TABLE bets (
    bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    match_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    odds REAL NOT NULL,
    amount REAL NOT NULL,
    potential_win REAL,
    status TEXT DEFAULT 'pending',
    result TEXT DEFAULT 'waiting',
    created_at TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### Transactions Table
```sql
CREATE TABLE transactions (
    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    admin_approved_by INTEGER,
    created_at TIMESTAMP,
    approved_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

## 📊 প্রজেক্ট স্ট্রাকচার

```
D:\AIBetingBot\
├── main.py                 # মূল বট ফাইল (সমস্ত কমান্ড)
├── config.py               # কনফিগারেশন সেটিংস
├── database.py             # ডেটাবেস অপারেশন
├── api_handler.py          # The Odds API ইন্টিগ্রেশন
├── ai_integration.py       # OpenAI/ChatGPT ইন্টিগ্রেশন
├── voice_handler.py        # gTTS ভয়েস জেনারেশন
├── requirements.txt        # পাইথন ডিপেন্ডেন্সি
├── env_example.txt         # এনভায়রনমেন্ট ভেরিয়েবল টেমপ্লেট
├── README.md               # এই ফাইল
└── betting_bot.db          # SQLite ডাটাবেস (অটো তৈরি)
```

## ⚙️ কনফিগারেশন

### Betting Limits
```python
MIN_BET_AMOUNT = 100      # ন্যূনতম বেট
MAX_BET_AMOUNT = 100000   # সর্বোচ্চ বেট
INITIAL_BALANCE = 1000    # নতুন ব্যবহারকারীর প্রাথমিক ব্যালেন্স
```

### Sports Available
- Soccer: EPL, La Liga, Serie A, Bundesliga, Ligue 1
- American Football: NFL
- Basketball: NBA
- Baseball: MLB
- Ice Hockey: NHL

## 🔐 নিরাপত্তা বৈশিষ্ট্য

- ✅ শক্তিশালী পাসওয়ার্ড সুরক্ষা
- ✅ এডমিন অনুমোদন সিস্টেম
- ✅ ট্রানজেকশন লগিং
- ✅ ইউজার ভেরিফিকেশন
- ✅ API রেট লিমিটিং

## 🐛 ট্রাবলশুটিং

### সমস্যা: "Invalid token" ত্রুটি
**সমাধান:** আপনার `TELEGRAM_BOT_TOKEN` সঠিক কিনা তা নিশ্চিত করুন `.env` ফাইলে।

### সমস্যা: API সংযোগ ব্যর্থ
**সমাধান:** আপনার ইন্টারনেট সংযোগ এবং API কী পরীক্ষা করুন।

### সমস্যা: ডাটাবেস লক
**সমাধান:** বটটি বন্ধ করুন এবং `betting_bot.db` ফাইল মুছুন, তারপর আবার চালু করুন।

## 📈 পারফরম্যান্স অপটিমাইজেশন

- ✅ এসিঙ্ক/আওয়েট ব্যবহার করে দ্রুত রেসপন্স
- ✅ কানেকশন পুলিং ডাটাবেসের জন্য
- ✅ ক্যাশিং ম্যাচ ডেটার জন্য
- ✅ ব্যাচ প্রসেসিং বড় অপারেশনের জন্য

## 🚀 ডিপ্লয়মেন্ট

### Render এ ডিপ্লয়মেন্ট

1. GitHub এ আপনার প্রজেক্ট পুশ করুন
2. Render.com এ যান এবং নতুন Web Service তৈরি করুন
3. আপনার GitHub রিপো সংযুক্ত করুন
4. পরিবেশ ভেরিয়েবল সেট করুন
5. ডিপ্লয় করুন

### Railway এ ডিপ্লয়মেন্ট

1. Railway.app এ যান
2. নতুন প্রজেক্ট তৈরি করুন
3. GitHub থেকে কানেক্ট করুন
4. পরিবেশ ভেরিয়েবল যোগ করুন
5. স্বয়ংক্রিয় ডিপ্লয়মেন্ট সক্ষম করুন

## 📞 সাপোর্ট এবং অবদান

এই প্রজেক্টে অবদান রাখতে স্বাগতম! যেকোনো বাগ রিপোর্ট বা ফিচার রিকোয়েস্টের জন্য একটি ইস্যু খুলুন।

## 📄 লাইসেন্স

এই প্রজেক্ট MIT লাইসেন্সের অধীন।

## ⚠️ সতর্কতা

এই বট শুধুমাত্র শিক্ষামূলক উদ্দেশ্যের জন্য। আপনার স্থানীয় আইন এবং নিয়ম অনুযায়ী বেটিং সেবা প্রদান করুন।

---

**স্থিতি:** ✅ প্রোডাকশন-রেডি  
**সংস্করণ:** 1.0.0  
**শেষ আপডেট:** 2024
