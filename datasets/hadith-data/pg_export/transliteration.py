"""Latin transliteration of an Arabic name as written (pure, standard library). See pg_export/AGENTS.md §Latin names.

One scheme, the glossary's (`TRANSLITERATION_NOTE` in src/lib/glossary/terms.ts): no long-vowel or dot marks; ʿ for
ʿayn and ʾ for hamza (not at the start of a word); th, dh, kh, sh, gh; doubled letters written twice; the article always
al-; ta marbuta -a. Case endings are dropped (pausal form), as names are cited. Two entry points:

- `transliterate_vocalized`: reads the short vowels the text itself carries. A word without a full set of vowel marks is
  read from the curated table instead, and a word in neither is a refusal (None), never a guess.
- `transliterate_by_table`: unvocalized text, only when every word is in the curated table.
"""

from __future__ import annotations

import re
import unicodedata

FATHA, DAMMA, KASRA, SUKUN, SHADDA = "َ", "ُ", "ِ", "ْ", "ّ"
FATHATAN, DAMMATAN, KASRATAN = "ً", "ٌ", "ٍ"
DAGGER_ALIF = "ٰ"
VOWELS = {FATHA: "a", DAMMA: "u", KASRA: "i"}
TANWIN = {FATHATAN, DAMMATAN, KASRATAN}
# Every combining mark the corpus uses on Arabic letters (harakat, Qur'anic annotation signs) and tatweel.
MARK = re.compile(r"[ً-ٰٟۖ-ۭـ]")
ARABIC_LETTER = re.compile(r"[ء-يٱ-ۓ]")

CONSONANTS = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z",
    "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "ʿ", "غ": "gh", "ف": "f", "ق": "q",
    "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y", "ء": "ʾ", "أ": "ʾ", "إ": "ʾ",
    "ؤ": "ʾ", "ئ": "ʾ", "ک": "k", "ی": "y",
}
ALIFS = {"ا", "أ", "إ", "آ", "ٱ"}
HONORIFIC_TOKENS = {"ع", "(ع)", "ص", "(ص)"}
# Reader state: the letter just read had no vowel mark because the long-vowel letter after it supplies one.
PENDING_LONG = "long"

# Words whose reading the letter rules cannot give (silent letters, fixed forms). Keyed by `table_key`.
FIXED = {
    "بن": "ibn", "ابن": "ibn", "بنت": "bint", "ابنه": "ibna", "الله": "Allah", "عمرو": "ʿAmr", "داود": "Dawud",
    "عبدالله": "ʿAbd Allah", "طاوس": "Tawus", "اسحاق": "Ishaq", "اسماعيل": "Ismaʿil", "ابراهيم": "Ibrahim",
}

# Curated common name elements (unvocalized key -> one standard reading). Only elements with a single customary reading
# are listed: ambiguous spellings (عبيدة ʿUbayda or ʿAbida, المكتب, حرب/حرث-style pairs) are left out on purpose, so an
# unvocalized name with such a word shows in Arabic alone.
NAME_TABLE = {
    **FIXED,
    "ابو": "Abu", "ابي": "Abi", "ابا": "Aba", "ام": "Umm", "اخيه": "akhihi", "ابيه": "abihi", "جده": "jaddihi",
    "عبد": "ʿAbd", "الرحمن": "al-Rahman", "الرحيم": "al-Rahim", "العزيز": "al-ʿAziz", "الملك": "al-Malik",
    "الواحد": "al-Wahid", "الحميد": "al-Hamid", "الجبار": "al-Jabbar", "الاعلي": "al-Aʿla", "الصمد": "al-Samad",
    "الحسن": "al-Hasan", "الحسين": "al-Husayn", "حسن": "Hasan", "حسين": "Husayn",
    "محمد": "Muhammad", "احمد": "Ahmad", "علي": "ʿAli", "جعفر": "Jaʿfar", "موسي": "Musa", "عيسي": "ʿIsa",
    "يحيي": "Yahya", "زكريا": "Zakariyya", "يعقوب": "Yaʿqub", "يوسف": "Yusuf", "سليمان": "Sulayman", "يونس": "Yunus",
    "هارون": "Harun", "ايوب": "Ayyub", "صالح": "Salih", "نوح": "Nuh", "ادريس": "Idris", "عمر": "ʿUmar",
    "عثمان": "ʿUthman", "سعيد": "Saʿid", "سعد": "Saʿd", "زيد": "Zayd", "يزيد": "Yazid", "زياد": "Ziyad",
    "خالد": "Khalid", "مالك": "Malik", "انس": "Anas", "عائشه": "ʿAʾisha", "فاطمه": "Fatima", "هشام": "Hisham",
    "حماد": "Hammad", "زراره": "Zurara", "سفيان": "Sufyan", "شعبه": "Shuʿba", "عباس": "ʿAbbas", "العباس": "al-ʿAbbas",
    "عبيد": "ʿUbayd", "القاسم": "al-Qasim", "قاسم": "Qasim", "حمزه": "Hamza", "عقبه": "ʿUqba", "عمار": "ʿAmmar",
    "نافع": "Nafiʿ", "مسلم": "Muslim", "بكر": "Bakr", "بكير": "Bukayr", "ابان": "Aban", "حريز": "Hariz",
    "جميل": "Jamil", "محبوب": "Mahbub", "صفوان": "Safwan", "فضال": "Faddal", "عمير": "ʿUmayr", "سماعه": "Samaʿa",
    "مهران": "Mihran", "سالم": "Salim", "سهل": "Sahl", "حبيب": "Habib", "تميم": "Tamim", "بهلول": "Buhlul",
    "غراب": "Ghurab", "الهيثم": "al-Haytham", "الوليد": "al-Walid", "الريان": "al-Rayyan", "الحكم": "al-Hakam",
    "المغيره": "al-Mughira", "الفضل": "al-Fadl", "الفضيل": "al-Fudayl", "النعمان": "al-Nuʿman", "مسعود": "Masʿud",
    "عامر": "ʿAmir", "جابر": "Jabir", "معاويه": "Muʿawiya", "شريك": "Sharik", "منصور": "Mansur", "حمران": "Humran",
    "بريد": "Burayd", "حنان": "Hannan", "سدير": "Sudayr", "اسباط": "Asbat", "عاصم": "ʿAsim", "قتاده": "Qatada",
    "الزهري": "al-Zuhri", "الاعمش": "al-Aʿmash", "عطاء": "ʿAtaʾ", "مجاهد": "Mujahid", "عكرمه": "ʿIkrima",
    "سلمه": "Salama", "مسلمه": "Maslama", "شهاب": "Shihab", "حازم": "Hazim", "ربيعه": "Rabiʿa",
    "المفضل": "al-Mufaddal", "عمران": "ʿImran", "مروان": "Marwan", "ثابت": "Thabit", "حميد": "Humayd",
    "رجاء": "Rajaʾ", "اسامه": "Usama", "هلال": "Hilal", "بلال": "Bilal", "سنان": "Sinan", "الربيع": "al-Rabiʿ",
    # nisbas and laqabs with one customary reading
    "الحلبي": "al-Halabi", "الاشعري": "al-Ashʿari", "البرقي": "al-Barqi", "القمي": "al-Qummi", "الكوفي": "al-Kufi",
    "البصري": "al-Basri", "النوفلي": "al-Nawfali", "السكوني": "al-Sakuni", "الثمالي": "al-Thumali",
    "الحسني": "al-Hasani", "العلوي": "al-ʿAlawi", "الهاشمي": "al-Hashimi", "الانصاري": "al-Ansari",
    "الازدي": "al-Azdi", "الخزاز": "al-Khazzaz", "الحذاء": "al-Hadhdhaʾ", "الكناني": "al-Kinani", "الجعفي": "al-Juʿfi",
    "العجلي": "al-ʿIjli", "القطان": "al-Qattan", "الصفار": "al-Saffar", "الصادق": "al-Sadiq", "الباقر": "al-Baqir",
    "الرضا": "al-Rida", "الكاظم": "al-Kazim", "الجواد": "al-Jawad", "الهادي": "al-Hadi", "العسكري": "al-ʿAskari",
    "الاول": "al-Awwal", "الثاني": "al-Thani", "الثالث": "al-Thalith", "المدني": "al-Madani", "المكي": "al-Makki",
    "البغدادي": "al-Baghdadi", "الخراساني": "al-Khurasani", "الواسطي": "al-Wasiti", "الشامي": "al-Shami",
    "الكرخي": "al-Karkhi", "الثقفي": "al-Thaqafi", "التميمي": "al-Tamimi", "الاسدي": "al-Asadi", "الضبي": "al-Dabbi",
    "الحضرمي": "al-Hadrami", "المروزي": "al-Marwazi", "الرازي": "al-Razi", "الهمداني": "al-Hamdani",
    "الطالقاني": "al-Taliqani", "العطار": "al-ʿAttar", "الجوهري": "al-Jawhari", "الحميري": "al-Himyari",
    "المدائني": "al-Madaʾini", "الدقاق": "al-Daqqaq", "المؤدب": "al-Muʾaddib", "الوراق": "al-Warraq",
    "السندي": "al-Sindi", "البزنطي": "al-Bazanti", "الحجال": "al-Hajjal", "الاحول": "al-Ahwal", "الجهني": "al-Juhani",
    "النخعي": "al-Nakhaʿi", "الخثعمي": "al-Khathʿami", "السعدابادي": "al-Saʿdabadi", "الطيالسي": "al-Tayalisi",
    # Frequent elements of Sunni and Imami chains (2026-11-21 census of names the table could not read). Left out on
    # purpose: معمر (Maʿmar or Muʿammar), عبيدة, حصين, حجر, حبان, سلام, عقيل, عمه, امه, and non-name words (يعني, قال, او, ح).
    "هريره": "Hurayra", "وكيع": "Wakiʿ", "شيبه": "Shayba", "قتيبه": "Qutayba", "الرزاق": "al-Razzaq", "عروه": "ʿUrwa",
    "وهب": "Wahb", "عفان": "ʿAffan", "جريج": "Jurayj", "بشار": "Bashshar", "الزبير": "al-Zubayr", "الليث": "al-Layth",
    "المثني": "al-Muthanna", "عيينه": "ʿUyayna", "كثير": "Kathir", "نمير": "Numayr", "شعيب": "Shuʿayb", "جبير": "Jubayr",
    "جرير": "Jarir", "دينار": "Dinar", "الخدري": "al-Khudri", "المسيب": "al-Musayyab", "الحارث": "al-Harith",
    "مسدد": "Musaddad", "همام": "Hammam", "بشر": "Bishr", "حجاج": "Hajjaj", "هاشم": "Hashim", "الاسود": "al-Aswad",
    "الاعرج": "al-Aʿraj", "كريب": "Kurayb", "لهيعه": "Lahiʿa", "هشيم": "Hushaym", "مره": "Murra", "اسرائيل": "Israʾil",
    "عوانه": "ʿAwana", "يسار": "Yasar", "الزناد": "al-Zinad", "عدي": "ʿAdi", "رافع": "Rafiʿ", "الشعبي": "al-Shaʿbi",
    "مهدي": "Mahdi", "ليث": "Layth", "العلاء": "al-ʿAlaʾ", "روح": "Rawh", "قيس": "Qays", "المبارك": "al-Mubarak",
    "الاوزاعي": "al-Awzaʿi", "ادم": "Adam", "زهير": "Zuhayr", "معاذ": "Muʿadh", "النضر": "al-Nadr", "وائل": "Waʾil",
    "زائده": "Zaʾida", "طلحه": "Talha", "نعيم": "Nuʿaym", "ليلي": "Layla", "حفص": "Hafs", "مسروق": "Masruq",
    "عياش": "ʿAyyash", "عون": "ʿAwn", "الاحوص": "al-Ahwas", "عبده": "ʿAbda", "اسلم": "Aslam", "سهيل": "Suhayl",
    "سيرين": "Sirin", "ذئب": "Dhiʾb", "قلابه": "Qilaba", "بهز": "Bahz", "برده": "Burda", "حرب": "Harb",
    "الوهاب": "al-Wahhab", "سماك": "Simak", "اليمان": "al-Yaman", "شقيق": "Shaqiq", "الخطاب": "al-Khattab",
    "حاتم": "Hatim", "وهيب": "Wuhayb", "علقمه": "ʿAlqama", "عجلان": "ʿAjlan", "الوارث": "al-Warith", "يعلي": "Yaʿla",
    "فضيل": "Fudayl", "ذر": "Dharr", "المقبري": "al-Maqburi", "السائب": "al-Saʾib", "عوف": "ʿAwf", "عتبه": "ʿUtba",
    "سمره": "Samura", "شيبان": "Shayban", "التيمي": "al-Taymi", "المتوكل": "al-Mutawakkil", "عباد": "ʿAbbad",
    "نضره": "Nadra", "نصر": "Nasr", "زريع": "Zurayʿ", "حرمله": "Harmala", "اسود": "Aswad", "منيع": "Maniʿ",
    "مليكه": "Mulayka", "الناقد": "al-Naqid", "كعب": "Kaʿb", "حسان": "Hassan", "سويد": "Suwayd", "عمره": "ʿAmra",
    "هناد": "Hannad", "المنكدر": "al-Munkadir", "رباح": "Rabah", "طالب": "Talib", "كامل": "Kamil", "حنبل": "Hanbal",
    "ميمون": "Maymun", "خلف": "Khalaf", "الشيباني": "al-Shaybani", "الصباح": "al-Sabbah", "سريج": "Surayj",
    "الجعد": "al-Jaʿd", "مسعر": "Misʿar", "مسهر": "Mushir", "الجريري": "al-Jurayri", "بكره": "Bakra", "عماره": "ʿUmara",
    "غندر": "Ghundar", "مريم": "Maryam", "الاشج": "al-Ashajj", "ماجيلويه": "Majiluwayh", "القعنبي": "al-Qaʿnabi",
    "فليح": "Fulayh", "امامه": "Umama", "البناني": "al-Bunani", "الحجاج": "al-Hajjaj", "عروبه": "ʿAruba",
    "معتمر": "Muʿtamir", "مطرف": "Mutarrif", "كهيل": "Kuhayl", "بقيه": "Baqiyya", "الثوري": "al-Thawri",
    "الطاهر": "al-Tahir", "المنذر": "al-Mundhir", "سليم": "Sulaym", "حذيفه": "Hudhayfa", "مصعب": "Musʿab",
    "المعتمر": "al-Muʿtamir", "مخلد": "Makhlad", "حكيم": "Hakim", "معن": "Maʿn", "رمح": "Rumh", "معروف": "Maʿruf",
    "ثوبان": "Thawban", "زرعه": "Zurʿa", "الحباب": "al-Hubab", "ميسره": "Maysara", "مولي": "mawla", "هند": "Hind",
    "صهيب": "Suhayb", "ثور": "Thawr", "الضحاك": "al-Dahhak", "مغيره": "Mughira", "مسعده": "Masʿada", "مؤمل": "Muʾammal",
    "واقد": "Waqid", "بشير": "Bashir", "اميه": "Umayya", "بسر": "Busr", "الهاد": "al-Had", "اوفي": "Awfa",
    "الدرداء": "al-Dardaʾ", "معدان": "Maʿdan", "قره": "Qurra", "عياض": "ʿIyad", "مقسم": "Miqsam", "كيسان": "Kaysan",
    "السرح": "al-Sarh", "الدمشقي": "al-Dimashqi", "حريث": "Hurayth", "الاحمر": "al-Ahmar", "ضمره": "Damra",
    "نجيح": "Najih", "اعين": "Aʿyan", "البراء": "al-Baraʾ", "مكحول": "Makhul", "محمود": "Mahmud", "خيثمه": "Khaythama",
    "عطيه": "ʿAtiyya", "حيوه": "Haywa", "راشد": "Rashid", "المسعودي": "al-Masʿudi", "زكرياء": "Zakariyyaʾ",
    "الحلواني": "al-Hulwani", "العاص": "al-ʿAs", "فديك": "Fudayk", "ذكوان": "Dhakwan", "النفيلي": "al-Nufayli",
    "اسماء": "Asmaʾ", "الطويل": "al-Tawil", "التياح": "al-Tayyah", "مجالد": "Mujalid", "خثيم": "Khuthaym",
    "الايلي": "al-Ayli", "الليثي": "al-Laythi", "طاووس": "Tawus", "السلمي": "al-Sulami", "المنهال": "al-Minhal",
    "اشعث": "Ashʿath", "النهدي": "al-Nahdi", "الفزاري": "al-Fazari", "عبدان": "ʿAbdan", "وقاص": "Waqqas",
    "العاليه": "al-ʿAliya", "حفصه": "Hafsa", "حزم": "Hazm", "اوس": "Aws", "الدستوائي": "al-Dastuwaʾi",
    "المعلم": "al-Muʿallim", "الضحي": "al-Duha", "واصل": "Wasil", "الزبيري": "al-Zubayri", "الخليل": "al-Khalil",
    "كليب": "Kulayb", "الكريم": "al-Karim", "معبد": "Maʿbad", "حيان": "Hayyan", "الدارمي": "al-Darimi", "يساف": "Yisaf",
    "الحصين": "al-Husayn", "سيار": "Sayyar", "ربه": "Rabbih", "صدقه": "Sadaqa", "الجوني": "al-Jawni", "هانئ": "Haniʾ",
    "ميمونه": "Maymuna", "بحير": "Buhayr", "الاشجعي": "al-Ashjaʿi", "قبيصه": "Qabisa", "زر": "Zirr",
    "المقرئ": "al-Muqriʾ", "الصامت": "al-Samit", "حنظله": "Hanzala", "الخولاني": "al-Khawlani", "شداد": "Shaddad",
    "عتاب": "ʿAttab", "الزبيدي": "al-Zubaydi", "المقدمي": "al-Muqaddami", "بهدله": "Bahdala", "الاصم": "al-Asamm",
    "الخلال": "al-Khallal", "المخزومي": "al-Makhzumi", "ورقاء": "Warqaʾ", "الحنفي": "al-Hanafi", "طارق": "Tariq",
    "الحبلي": "al-Hubuli", "سلمان": "Salman", "خشرم": "Khashram", "الخزاعي": "al-Khuzaʿi", "المحاربي": "al-Muharibi",
    "ربعي": "Ribʿi", "القرشي": "al-Qurashi", "شبيب": "Shabib", "فضاله": "Fadala", "شريح": "Shurayh", "مبارك": "Mubarak",
    "الحميدي": "al-Humaydi", "خبيب": "Khubayb", "يعمر": "Yaʿmar", "اويس": "Uways", "الحنظلي": "al-Hanzali",
    "زبيد": "Zubayd", "هرمز": "Hurmuz", "غالب": "Ghalib", "الصلت": "al-Salt", "سمي": "Sumayy", "شبابه": "Shababa",
    "الازرق": "al-Azraq", "غيلان": "Ghaylan", "قدامه": "Qudama", "شمر": "Shimr", "العبدي": "al-ʿAbdi", "السدي": "al-Suddi",
    "علاقه": "ʿIlaqa", "العقدي": "al-ʿAqadi", "عراك": "ʿIrak", "فراس": "Firas", "مهاجر": "Muhajir", "سيف": "Sayf",
    "الدورقي": "al-Dawraqi", "القواريري": "al-Qawariri", "معشر": "Maʿshar", "مقاتل": "Muqatil", "مخرمه": "Makhrama",
    "مطر": "Matar", "زاذان": "Zadhan", "الاشعث": "al-Ashʿath", "ابزي": "Abza", "عنبسه": "ʿAnbasa", "مجلز": "Mijlaz",
    "مسرور": "Masrur", "الزهراني": "al-Zahrani", "خلاد": "Khallad", "المطلب": "al-Muttalib", "رشدين": "Rishdin",
    "عزره": "ʿAzra", "الرقي": "al-Raqqi", "بحر": "Bahr", "شرحبيل": "Shurahbil", "الاغر": "al-Agharr", "ازهر": "Azhar",
    "ثمامه": "Thumama", "الجارود": "al-Jarud", "بكار": "Bakkar", "خارجه": "Kharija", "طهمان": "Tahman", "موهب": "Mawhab",
    "خباب": "Khabbab", "خصيف": "Khusayf", "بزيع": "Baziʿ", "فارس": "Faris", "النيسابوري": "al-Naysaburi", "اياس": "Iyas",
    "هبيره": "Hubayra", "كهمس": "Kahmas", "العتكي": "al-ʿAtaki", "البختري": "al-Bakhtari", "البرمكي": "al-Barmaki",
    "قعنب": "Qaʿnab", "الاموي": "al-Umawi", "جويريه": "Juwayriya", "ميناء": "Minaʾ", "المليح": "al-Malih",
    "معقل": "Maʿqil", "طريف": "Tarif", "السمان": "al-Samman", "مغول": "Mighwal", "كاسب": "Kasib", "الكليني": "al-Kulayni",
    "توبه": "Tawba", "شجاع": "Shujaʿ", "المهلب": "al-Muhallab", "العمري": "al-ʿUmari", "زينب": "Zaynab", "ارقم": "Arqam",
    "الجعابي": "al-Jiʿabi", "ابائه": "abaʾihi", "ابيهما": "abihima", "جدي": "jaddi", "اخي": "akhi",
}


def strip_marks(text: str) -> str:
    """The letters as written, without harakat or tatweel (the extractor's surface form)."""
    return MARK.sub("", text or "")


def table_key(word: str) -> str:
    """Lookup key of a word: no marks, alef forms as ا, final ى as ي, ة as ه."""
    key = strip_marks(unicodedata.normalize("NFC", word))
    key = re.sub("[أإآٱ]", "ا", key).replace("ى", "ي").replace("ة", "ه").replace("ی", "ي").replace("ک", "ك")
    return key.strip("()[]،,.:؛;-")


# Words kept lowercase inside a name: connectors, prepositions, kinship pronouns.
LOWERCASE = {"ibn", "bint", "wa", "min", "fi", "ʿan", "ʿala", "ila", "abihi", "akhihi", "jaddihi", "ghayruhu",
             "abaʾihi", "abihima", "jaddi", "akhi", "mawla"}


def _capitalize(word: str) -> str:
    if word in LOWERCASE or not word:
        return word
    prefix = "al-" if word.startswith("al-") else ""
    rest = word[len(prefix):]
    lead = ""
    while rest and rest[0] in "ʿʾ":
        lead, rest = lead + rest[0], rest[1:]
    return prefix + lead + rest[:1].upper() + rest[1:]


def _units(word: str) -> list[tuple[str, set[str]]]:
    """(letter, marks) pairs; a mark before any letter is ignored. Persian ی and ک read as Arabic ي and ك; a final
    Persian ی after fatha is the alif maqsura it stands for."""
    units: list[tuple[str, set[str]]] = []
    for char in unicodedata.normalize("NFC", word):
        if MARK.match(char):
            if units and char != "ـ":
                units[-1][1].add(char)
        elif ARABIC_LETTER.match(char):
            units.append(({"ی": "ي", "ک": "ك"}.get(char, char), set()))
            if char == "ی":
                units[-1][1].add("persian_ya")
    if units and "persian_ya" in units[-1][1] and len(units) > 1 and FATHA in units[-2][1]:
        units[-1] = ("ى", units[-1][1])
    return units


def _vowel(marks: set[str]) -> str | None:
    for mark, latin in VOWELS.items():
        if mark in marks:
            return latin
    if DAGGER_ALIF in marks:
        return "a"
    return None


def _read_vocalized_word(word: str) -> str | None:
    """One fully vocalized word, or None when a letter's vowel cannot be read from the marks."""
    units = _units(word)
    if not units:
        return None
    out: list[str] = []
    index = 0
    article = len(units) > 2 and units[0][0] in ("ا", "ٱ") and units[1][0] == "ل" and SHADDA not in units[1][1]
    if article:
        out.append("al-")
        index = 2
    last = len(units) - 1
    previous_vowel: str | None = None
    while index <= last:
        letter, marks = units[index]
        final = index == last
        following = units[index + 1][0] if index < last else None
        vowel = None if final else _vowel(marks)
        if final and DAGGER_ALIF in marks:
            vowel = "a"
        if letter in ALIFS and (index == 0 or (article and index == 2)):
            # Word-initial hamza is not written; its vowel is.
            initial = _vowel(marks) or ("i" if letter == "إ" else "a" if letter == "آ" else None)
            if initial is None and letter == "ا" and following is not None and SUKUN in units[1][1]:
                initial = "i"
            if initial is None:
                return None
            out.append(initial)
            previous_vowel = initial
        elif letter in ALIFS and letter != "أ" and letter != "إ":
            if previous_vowel != "a":
                out.append("a")
            previous_vowel = "a"
        elif letter == "ى":
            if previous_vowel != "a":
                out.append("a")
            previous_vowel = "a"
        elif letter == "ة":
            if final:
                if previous_vowel != "a":
                    out.append("a")
            else:
                out.append("t" + (vowel or ""))
            previous_vowel = "a"
        elif letter in ("و", "ي") and not (marks & {FATHA, DAMMA, KASRA, SHADDA}) and index > 0:
            # Long vowel (after the matching short vowel, or after an unmarked letter that leans on it) or the second
            # half of a diphthong (after fatha). After sukun it is unreadable.
            long_vowel = "u" if letter == "و" else "i"
            if previous_vowel == long_vowel:
                pass
            elif previous_vowel == "a":
                out.append(CONSONANTS[letter])
            elif previous_vowel == PENDING_LONG:
                out.append(long_vowel)
            else:
                return None
            previous_vowel = None if previous_vowel == "a" else long_vowel
        elif letter == "آ":
            out.append("ʾa")
            previous_vowel = "a"
        else:
            latin = CONSONANTS.get(letter)
            if latin is None:
                return None
            doubled = SHADDA in marks and not (article and index == 2)
            out.append(latin * 2 if doubled else latin)
            if final:
                previous_vowel = None
            elif vowel is not None:
                out.append(vowel)
                previous_vowel = vowel
            elif SUKUN in marks:
                previous_vowel = None
            elif following in ALIFS or following == "ى":
                previous_vowel = PENDING_LONG   # a long a follows: the alif supplies the vowel
            elif following in ("و", "ي") and not (units[index + 1][1] & {FATHA, DAMMA, KASRA, SHADDA, SUKUN}):
                previous_vowel = PENDING_LONG   # the long vowel letter supplies it
            else:
                return None
        index += 1
    last_letter, last_marks = units[last]
    if last_letter == "ه" and last > 1 and (KASRA in last_marks or DAMMA in last_marks):
        out.append("i" if KASRA in last_marks else "u")   # the pronoun suffix -hi / -hu keeps its vowel in pausal form
    text = "".join(out)
    text = re.sub(r"iyy$", "i", text)
    text = re.sub(r"uww$", "u", text)
    return text


def is_fully_vocalized(word: str) -> bool:
    """True when every letter's vowel can be read from the marks the word carries (and it carries some)."""
    if not any(mark in word for mark in (FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN)):
        return False
    return _read_vocalized_word(word) is not None


def _words(text: str) -> list[str]:
    return [word for word in re.split(r"[\s‌‏‎]+", (text or "").strip()) if word]


def _render(parts: list[str]) -> str:
    rendered = [_capitalize(part) for part in parts]
    if rendered and rendered[0] in LOWERCASE:
        rendered[0] = rendered[0][:1].upper() + rendered[0][1:]
    return " ".join(rendered)


def _table_word(word: str) -> str | None:
    return NAME_TABLE.get(table_key(word))


def transliterate_vocalized(text: str) -> str | None:
    """Latin form of a vocalized name. Each word is read from its own marks, or from the table when it carries none
    (or too few); None when some word is in neither, or when no word was read from marks (use the table entry point)."""
    parts: list[str] = []
    read_from_marks = False
    for word in _words(text):
        if word in HONORIFIC_TOKENS or table_key(word) in HONORIFIC_TOKENS:
            continue
        key = table_key(word)
        if key in FIXED:
            parts.append(FIXED[key])
            continue
        if key == "و":
            parts.append("wa")
            continue
        reading = _read_vocalized_word(word) if is_fully_vocalized(word) else None
        if reading is not None:
            parts.append(reading)
            read_from_marks = True
            continue
        fallback = _table_word(word)
        if fallback is None:
            return None
        parts.append(fallback)
    if not parts or not read_from_marks:
        return None
    return _render(parts)


def transliterate_by_table(text: str) -> str | None:
    """Latin form from the curated table, only when every word is covered; None otherwise (Arabic alone is shown)."""
    parts: list[str] = []
    for word in _words(text):
        if word in HONORIFIC_TOKENS or table_key(word) in HONORIFIC_TOKENS:
            continue
        if table_key(word) == "و":
            parts.append("wa")
            continue
        reading = _table_word(word)
        if reading is None:
            return None
        parts.append(reading)
    return _render(parts) if parts else None


def latin_name(text: str) -> tuple[str, str] | None:
    """(latin, basis) for a name as written: `transliteration_vocalized` or `transliteration_table`, else None."""
    vocalized = transliterate_vocalized(text)
    if vocalized:
        return vocalized, "transliteration_vocalized"
    table = transliterate_by_table(text)
    if table:
        return table, "transliteration_table"
    return None
