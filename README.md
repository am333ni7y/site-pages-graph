# 🕸️ Site Pages Graph & SEO Architecture Visualizer

> **An advanced, interactive Technical SEO architecture crawler and internal link visualizer. Forked and heavily upgraded by [AMEEEN SEO](https://ameeen.ir) to bridge the gap between raw graph mathematics, click-depth audits, and actionable data visualization.**

[![Latest Release](https://img.shields.io/github/v/release/am333ni7y/site-pages-graph?color=teal&label=Release)](https://github.com/am333ni7y/site-pages-graph/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Author: AMEEEN SEO](https://img.shields.io/badge/Maintained%20by-AMEEEN.IR-orange.svg)](https://ameeen.ir)

---

## 🇬🇧 English Documentation

### 🚀 What is this tool & How does it differ from upstream?
The original repository was a CLI script that constructed internal link graphs using `networkx` and exported raw numeric data to SQLite and CSV.

**This upgraded fork by [AMEEEN SEO](https://ameeen.ir) turns it into a complete visual SEO intelligence platform:**
- **Interactive 3D-like HTML Graph**: Employs `Vis.js` with auto-freezing `forceAtlas2Based` physics layout, hierarchical tree mode, real-time node search, and deep-link inspection drawers.
- **Sitemap-First Auto-Discovery**: Automatically inspects `robots.txt` and locates standard/nested XML sitemaps before crawling.
- **Strict Media & Loop Filtering**: Rejects images, media, CSS/JS, and infinite WooCommerce parameter loops (`?add-to-cart=...`, filters).
- **Anti-Bot & WAF Resilience**: Includes realistic User-Agent presets (Screaming Frog, Googlebot-Mobile, Googlebot-Desktop, Chrome) and system proxy bypass to prevent 403 Forbidden errors.
- **Interactive TUI**: A sleek terminal UI with ASCII branding and live diagnostic checks.

---

### 📥 Installation & Setup

#### Option A: Clone with Git (Recommended for Developers)
```bash
git clone https://github.com/am333ni7y/site-pages-graph.git
cd site-pages-graph
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Option B: Download Standalone Release ZIP
1. Go to the [Releases Page](https://github.com/am333ni7y/site-pages-graph/releases).
2. Download the latest source code (`.zip` or `.tar.gz`).
3. Extract the folder, open your terminal inside it, and run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### ⚡ Quick Start & Usage

#### 1. Interactive Terminal Mode (TUI)
Simply launch `main.py` without arguments:
```bash
python main.py
```
Follow the interactive prompt to enter your target URL, select your User-Agent preset, set concurrency, and run.

#### 2. Direct CLI Execution
```bash
# Basic run with Chrome User-Agent
python main.py https://example.com

# Advanced crawl with Screaming Frog User-Agent and concurrency of 5
python main.py https://example.com --ua screaming-frog --threads 5
```

---

### 📊 Real-World SEO Use Case & Practical Example

**Scenario: Auditing a 200-page E-Commerce / Tech Site (`example.com`)**

1. **Click-Depth Audit (`clicks_from_root`)**:
   - The CSV report and HTML visualizer classify nodes by click distance from the homepage.
   - Any money-page or high-intent category with `clicks_from_root > 3` indicates severe link equity decay.
2. **Reverse Engineering Competitor Silos**:
   - Run the tool against competitor websites without purchasing expensive crawler licenses.
   - Switch the HTML view to `Layout: Tree (Hierarchical)` to instantly reveal their exact content hub and silo hierarchy.
3. **Internal Redirect Waste Cleanup**:
   - The `redirect_to` column flags internal links pointing to 301/302 redirects, allowing you to update internal anchors directly to the 200 OK target URL.

---

### 🐛 Issue Reporting & Bugs
Encountered an issue or have a feature request? Please open an issue on GitHub:
👉 [Report an Issue / Suggest a Feature](https://github.com/am333ni7y/site-pages-graph/issues)

---

## 🇮🇷 راهنمای جامع فارسی (Persian Documentation)

### 🎯 معرفی ابزار و تفاوت آن با نسخه اولیه
پروژه اصلی تنها یک اسکریپت ساده برای استخراج پیوندها و ذخیره آن‌ها در قالب دیتابیس SQLite بود و هیچ خروجی بصری ارائه نمی‌داد.

در این نسخه بازنویسی‌شده توسط [امین زاهد (AMEEEN SEO)](https://ameeen.ir)، قابلیت‌های تخصصی سئو و مصورسازی به پروژه اضافه شده است:
- **گراف بصری تعاملی (HTML Visualizer)**: ترسیم ساختار لینک‌های داخلی با موتور پایدار Vis.js، چیدمان درختی (Hierarchical)، سرچ‌باکس و کشوی اطلاعات صفحه.
- **سیستم کشف خودکار سایتمپ**: بررسی خودکار `robots.txt` و الگوهای متداول سایتمپ پیش از کرال.
- **حذف نویزها و لوپ‌های پارامتریک**: فیلتر هوشمند تمام فایل‌های تصویری (`.jpg`, `.webp`)، اسناد، فایل‌های استاتیک و آدرس‌های سبد خرید ووکامرس (`add-to-cart`).
- **پشتیبانی از یوزر ایجنت‌های اختصاصی سئو**: امکان انتخاب یوزر ایجنت اسکریمینگ فراگ، گوگل‌بات موبایل و دسکتاپ برای دور زدن فایروال‌ها.
- **رابط کاربری تعاملی در ترمینال (TUI)**: منوی کاربری با بنر متنی و راهنمای خط به خط.

---

### 💻 نحوه نصب و راه‌اندازی

#### روش اول: کلون با گیت
```bash
git clone https://github.com/am333ni7y/site-pages-graph.git
cd site-pages-graph
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### روش دوم: دانلود مستقیم فایل ریلیز (ZIP)
1. به بخش [Releases در گیت‌هاب](https://github.com/am333ni7y/site-pages-graph/releases) بروید.
2. آخرین نسخه را با فرمت `.zip` دانلود و اکسترکت کنید.
3. ترمینال را در همان پوشه باز کرده و وابستگی‌ها را نصب کنید:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 🛠️ نحوه اجرا و استفاده
کافی است فایل اصلی را اجرا کنید تا وارد منوی انتخاب شوید:
```bash
python main.py
```
سپس آدرس وب‌سایت هدف را وارد کرده و یوزر ایجنت دلخواه را انتخاب کنید. پس از پایان فرایند، فایل گراف در آدرس `output/<domain>.html` ساخته خواهد شد:
```bash
open output/yourdomain.com.html
```

---

### 📈 نمونه کاربرد عملی در سئو تکنیکال

1. **تحلیل عمق کلیک صفحات کلیدی**: صفحاتی که ارزش تجاری بالایی دارند اما عمق کلیک آن‌ها از صفحه اصلی بیشتر از ۳ است شناسایی شده و در گراف به عنوان گره‌های دورافتاده مشخص می‌شوند.
2. **مهندسی معکوس کلاسترهای رقبا**: استخراج ساختار سیلو (Silo) و هاب‌های مقالات سایت‌های رقیب در کسری از ثانیه و بدون نیاز به لایسنس ابزارهای خارجی.
3. **پاکسازی ریدایرکت‌های داخلی**: شناسایی پیوندهای داخلی سایت که به آدرس‌های تغییریافته (301/302) لینک داده‌اند و اصلاح آن‌ها به منظور حفظ بودجه خزش و اعتبار لینک.

---

### 🐛 ثبت باگ‌ها و پیشنهادات (Issues)
در صورت مشاهده هرگونه باگ یا خطای شبکه در کرال دامنه‌های مختلف، لطفاً از طریق لینک زیر یک Issue جدید ثبت کنید:
👉 [ثبت مشکل یا باگ در گیت‌هاب](https://github.com/am333ni7y/site-pages-graph/issues)

---

## 👨‍💻 Author & Credits
- Upgraded & Maintained by **AMEEEN SEO** ([https://ameeen.ir](https://ameeen.ir))
- Original graph topology concept based on `site-pages-graph` by *kilgoretrout1985*.
- Licensed under the [MIT License](LICENSE).
