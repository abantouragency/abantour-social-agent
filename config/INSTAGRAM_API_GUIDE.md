# راهنمای راه‌اندازی API اینستاگرام (AbanTour Social Agent)

این ایجنت برای انتشار خودکار پست/ریلز از **Instagram Graph API** (رسمی) استفاده
می‌کنه. این مسیر ایمنه و باعث بن‌شدن نمی‌شه — اما نیاز به یک حساب **Business یا
Creator** داره که به یک **صفحه فیسبوک** وصل باشه. مراحل:

## ۱. آماده‌سازی حساب
- اینستاگرامتون رو به نوع **Professional / Business** یا **Creator** تغییر بدید
  (Settings → Account → Switch to Professional Account).
- یک **صفحه فیسبوک** بسازید (facebook.com/pages) و ایجنت آبان تور رو ادمینش کنید.
- در اینستاگرام: Settings → Accounts Center → Linked Accounts → Facebook،
  حساب IG رو به اون صفحه فیسبوک لینک کنید.

## ۲. ساخت اپلیکیشن متا و گرفتن توکن
- برید به developers.facebook.com → «My Apps» → «Create App» (نوع Business).
- محصول **Instagram Graph API** رو اضافه کنید.
- در بخش Instagram → Basic Display، حساب IG رو به اپلیکیشن متصل کنید
  (با نام‌کاربری/رمز عبور IG تستی).
- توکن کوتاه‌مدت بگیرید، بعد با ابزار **Access Token Debugger**
  (developers.facebook.com/tools/debug/accesstoken) تبدیلش کنید به
  **Long-Lived Token** (۶۰ روزه؛ قبل از انقضا باید باز تمدید شه).

## ۳. مقداردهی در .env
- `IG_USER_ID`: شناسه عددی IG (از Graph API: GET /me?fields=id با توکن).
- `IG_ACCESS_TOKEN`: همون توکن بلندمدت.
- (اختیاری) `IG_USERNAME`/`IG_PASSWORD` فقط اگر بخواید از مسیر غیررسمی
  (instagrapi) استفاده کنید — که پیشنهاد نمی‌شه چون ریسک بن داره.

## ۴. تست
روی PC:
    python modules\instagram_pub.py
سپس یک ریلز نمونه رو با:
    python -c "import instagram_pub,os; print(instagram_pub.create_container('https://your-public-url/reel.mp4','تست',is_reel=True))"
بررسی کنید (فایل باید روی یک URL عمومی باشه — مثل هاست یا CDN خودتون).

## نکته مهم
- انتشار ریلز از طریق Graph API نیاز داره ویدئو روی یک **URL عمومی** باشه.
  برای محتوای محلی، یا فایل رو آپلود کنید به هاستتون یا از همین ایجنت بخش
  «میزبانی موقت» اضافه بشه (در نسخه بعد).
- الگوریتم اینستاگرام پست‌های تکراری/اسپم رو جریمه می‌کنه؛ ایجنت کپشن‌ها رو
  متنوع نگه می‌داره.
