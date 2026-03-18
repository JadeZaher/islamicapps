import { runWrite, closeDriver } from '../lib/db/neo4j';
import { randomUUID } from 'crypto';

interface Location {
  id: string;
  name: string;
  name_arabic: string;
  latitude: number;
  longitude: number;
  modern_country: string;
  region: string;
  description: string;
}

interface HistoricalEvent {
  id: string;
  title: string;
  title_arabic: string;
  description: string;
  year_hijri: number;
  year_gregorian: number;
  end_year_hijri?: number;
  end_year_gregorian?: number;
  category: 'PROPHETIC_ERA' | 'RASHIDUN' | 'UMAYYAD' | 'ABBASID' | 'SCHOLARLY' | 'MILITARY' | 'POLITICAL' | 'SOCIAL';
  significance: string;
  location_name: string;
}

const LOCATIONS: Location[] = [
  {
    id: randomUUID(),
    name: 'Makkah',
    name_arabic: 'مكة المكرمة',
    latitude: 21.4225,
    longitude: 39.8265,
    modern_country: 'Saudi Arabia',
    region: 'Hejaz',
    description: 'The holiest city in Islam, birthplace of Prophet Muhammad and home to the Kaaba. Center of Islamic pilgrimage and spiritual significance.'
  },
  {
    id: randomUUID(),
    name: 'Medina',
    name_arabic: 'المدينة المنورة',
    latitude: 24.5247,
    longitude: 39.5692,
    modern_country: 'Saudi Arabia',
    region: 'Hejaz',
    description: 'City of the Prophet, destination of the Hijra, and capital of the early Islamic state. Contains the Masjid al-Nabawi.'
  },
  {
    id: randomUUID(),
    name: 'Jerusalem',
    name_arabic: 'القدس',
    latitude: 31.7683,
    longitude: 35.2137,
    modern_country: 'Palestine/Israel',
    region: 'Levant',
    description: 'Third holiest city in Islam, site of Al-Aqsa Mosque and the Dome of the Rock. Central to Islamic, Jewish, and Christian traditions.'
  },
  {
    id: randomUUID(),
    name: 'Damascus',
    name_arabic: 'دمشق',
    latitude: 33.5138,
    longitude: 36.2765,
    modern_country: 'Syria',
    region: 'Levant',
    description: 'Capital of the Umayyad Caliphate, major center of Islamic scholarship and Quran compilation. Home to the Umayyad Mosque.'
  },
  {
    id: randomUUID(),
    name: 'Baghdad',
    name_arabic: 'بغداد',
    latitude: 33.3128,
    longitude: 44.3615,
    modern_country: 'Iraq',
    region: 'Mesopotamia',
    description: 'Capital of the Abbasid Caliphate, center of Islamic learning and the House of Wisdom. One of the greatest cities of the medieval world.'
  },
  {
    id: randomUUID(),
    name: 'Kufa',
    name_arabic: 'الكوفة',
    latitude: 32.0106,
    longitude: 44.4008,
    modern_country: 'Iraq',
    region: 'Iraq',
    description: 'Major city founded during the Rashidun period, important center of Quranic studies and Islamic jurisprudence.'
  },
  {
    id: randomUUID(),
    name: 'Basra',
    name_arabic: 'البصرة',
    latitude: 30.5273,
    longitude: 47.8027,
    modern_country: 'Iraq',
    region: 'Iraq',
    description: 'Strategic port city founded during Rashidun era, major center of trade, Hadith scholarship, and Arabic linguistics.'
  },
  {
    id: randomUUID(),
    name: 'Fustat',
    name_arabic: 'الفسطاط',
    latitude: 30.0444,
    longitude: 31.2357,
    modern_country: 'Egypt',
    region: 'Egypt',
    description: 'Early Islamic capital of Egypt, predecessor to Cairo. Major center of Islamic administration and learning.'
  },
  {
    id: randomUUID(),
    name: 'Bukhara',
    name_arabic: 'بخارى',
    latitude: 39.7750,
    longitude: 64.4256,
    modern_country: 'Uzbekistan',
    region: 'Central Asia',
    description: 'Major center of Islamic learning and Hadith scholarship. Birthplace of Imam Bukhari and hub of the Silk Road.'
  },
  {
    id: randomUUID(),
    name: 'Nishapur',
    name_arabic: 'نيسابور',
    latitude: 36.2140,
    longitude: 58.7738,
    modern_country: 'Iran',
    region: 'Khorasan',
    description: 'Important center of Islamic scholarship and Hadith collection. Hometown of Imam Muslim and numerous scholars.'
  },
  {
    id: randomUUID(),
    name: 'Samarkand',
    name_arabic: 'سمرقند',
    latitude: 39.6548,
    longitude: 66.9597,
    modern_country: 'Uzbekistan',
    region: 'Central Asia',
    description: 'Major crossroads of the Silk Road and center of Islamic science, astronomy, and mathematics.'
  },
  {
    id: randomUUID(),
    name: 'Karbala',
    name_arabic: 'كربلاء',
    latitude: 32.5086,
    longitude: 44.0263,
    modern_country: 'Iraq',
    region: 'Iraq',
    description: 'Holy city in Shia Islam, site of the martyrdom of Husayn ibn Ali. Major pilgrimage destination.'
  },
  {
    id: randomUUID(),
    name: 'Abyssinia',
    name_arabic: 'الحبشة',
    latitude: 9.1450,
    longitude: 40.4897,
    modern_country: 'Ethiopia',
    region: 'East Africa',
    description: 'Christian kingdom that provided refuge for early Muslims fleeing Meccan persecution. Important in early Islamic history.'
  },
  {
    id: randomUUID(),
    name: 'Sana\'a',
    name_arabic: 'صنعاء',
    latitude: 15.3694,
    longitude: 48.2159,
    modern_country: 'Yemen',
    region: 'Arabia',
    description: 'Major Islamic city and cultural center in Yemen, important for trade and Islamic governance.'
  },
  {
    id: randomUUID(),
    name: 'Taif',
    name_arabic: 'الطائف',
    latitude: 21.2716,
    longitude: 40.4158,
    modern_country: 'Saudi Arabia',
    region: 'Arabia',
    description: 'Mountain city near Makkah, site of Prophet Muhammad\'s preaching mission and important in early Islam.'
  },
  {
    id: randomUUID(),
    name: 'Badr',
    name_arabic: 'بدر',
    latitude: 24.3544,
    longitude: 38.7472,
    modern_country: 'Saudi Arabia',
    region: 'Arabia',
    description: 'Site of the Battle of Badr, first major military victory of Muslims against the Quraysh.'
  },
  {
    id: randomUUID(),
    name: 'Uhud',
    name_arabic: 'أحد',
    latitude: 24.6067,
    longitude: 39.5928,
    modern_country: 'Saudi Arabia',
    region: 'Arabia',
    description: 'Mountain north of Medina, site of the Battle of Uhud where Muslims faced temporary defeat.'
  },
  {
    id: randomUUID(),
    name: 'Khaybar',
    name_arabic: 'خيبر',
    latitude: 25.1925,
    longitude: 39.4842,
    modern_country: 'Saudi Arabia',
    region: 'Arabia',
    description: 'Fortress and Jewish settlement conquered by Muslims, significant in establishing Islamic authority.'
  },
  {
    id: randomUUID(),
    name: 'Hudaybiyyah',
    name_arabic: 'الحديبية',
    latitude: 21.8694,
    longitude: 39.6125,
    modern_country: 'Saudi Arabia',
    region: 'Arabia',
    description: 'Coastal location where the Treaty of Hudaybiyyah was signed, peace accord between Muslims and Quraysh.'
  },
  {
    id: randomUUID(),
    name: 'Yarmouk',
    name_arabic: 'اليرموك',
    latitude: 32.7567,
    longitude: 35.7733,
    modern_country: 'Jordan/Syria border',
    region: 'Levant',
    description: 'Site of the decisive Battle of Yarmouk, victory that secured Muslim control of the Levant.'
  },
  {
    id: randomUUID(),
    name: 'Qadisiyyah',
    name_arabic: 'القادسية',
    latitude: 31.9500,
    longitude: 44.3667,
    modern_country: 'Iraq',
    region: 'Iraq',
    description: 'Site of the Battle of Qadisiyyah, major victory that led to the conquest of Persia.'
  },
  {
    id: randomUUID(),
    name: 'Siffin',
    name_arabic: 'صفين',
    latitude: 35.2389,
    longitude: 39.3278,
    modern_country: 'Syria',
    region: 'Levant',
    description: 'Site of the Battle of Siffin between Ali and Mu\'awiya, major conflict in early Islamic history.'
  },
  {
    id: randomUUID(),
    name: 'Termez',
    name_arabic: 'الترمذ',
    latitude: 37.2622,
    longitude: 68.7735,
    modern_country: 'Uzbekistan/Afghanistan',
    region: 'Central Asia',
    description: 'Ancient city on the Silk Road, birthplace of Imam Tirmidhi, major center of Islamic learning.'
  },
  {
    id: randomUUID(),
    name: 'Qazvin',
    name_arabic: 'قزوين',
    latitude: 36.2665,
    longitude: 50.0049,
    modern_country: 'Iran',
    region: 'Persia',
    description: 'Historic Persian city and center of Islamic learning, birthplace of Ibn Majah.'
  },
  {
    id: randomUUID(),
    name: 'Ray',
    name_arabic: 'الري',
    latitude: 35.6667,
    longitude: 51.4167,
    modern_country: 'Iran',
    region: 'Persia',
    description: 'Historic Persian city and major center of Islamic scholarship, near modern-day Tehran.'
  },
  {
    id: randomUUID(),
    name: 'Isfahan',
    name_arabic: 'أصفهان',
    latitude: 32.6769,
    longitude: 51.6694,
    modern_country: 'Iran',
    region: 'Persia',
    description: 'Major Persian city and center of Islamic arts, sciences, and architecture.'
  },
  {
    id: randomUUID(),
    name: 'Herat',
    name_arabic: 'هرات',
    latitude: 34.3425,
    longitude: 62.1986,
    modern_country: 'Afghanistan',
    region: 'Central Asia',
    description: 'Important center of Islamic learning and trade on the Silk Road.'
  },
  {
    id: randomUUID(),
    name: 'Cordoba',
    name_arabic: 'قرطبة',
    latitude: 37.8882,
    longitude: -4.7794,
    modern_country: 'Spain',
    region: 'Iberia',
    description: 'Capital of the Islamic Umayyad Caliphate in Spain, center of Islamic learning and culture in medieval Europe.'
  },
  {
    id: randomUUID(),
    name: 'Fez',
    name_arabic: 'فاس',
    latitude: 34.0333,
    longitude: -5.0033,
    modern_country: 'Morocco',
    region: 'North Africa',
    description: 'Major Islamic city in Morocco, center of learning and culture. Home to Al-Qarawiyyin University.'
  },
  {
    id: randomUUID(),
    name: 'Cairo',
    name_arabic: 'القاهرة',
    latitude: 30.0444,
    longitude: 31.2357,
    modern_country: 'Egypt',
    region: 'Egypt',
    description: 'Capital of Egypt built on the foundation of Fustat, major center of Islamic civilization and learning.'
  },
  {
    id: randomUUID(),
    name: 'Cave Hira',
    name_arabic: 'غار حراء',
    latitude: 21.5011,
    longitude: 39.8397,
    modern_country: 'Saudi Arabia',
    region: 'Arabia',
    description: 'Mountain cave near Makkah where the Prophet Muhammad received the first revelation.'
  },
  {
    id: randomUUID(),
    name: 'Tours',
    name_arabic: 'تور',
    latitude: 47.3915,
    longitude: 0.6848,
    modern_country: 'France',
    region: 'Europe',
    description: 'Site of the Battle of Tours, where Muslim expansion into Europe was halted.'
  }
];

const HISTORICAL_EVENTS: HistoricalEvent[] = [
  // Prophetic Era
  {
    id: randomUUID(),
    title: 'Birth of Prophet Muhammad',
    title_arabic: 'ميلاد الرسول محمد صلى الله عليه وسلم',
    description: 'Birth of Prophet Muhammad, founder of Islam. Born in Makkah on a Monday, year 53 BH (Before Hijra).',
    year_hijri: 0,
    year_gregorian: 570,
    category: 'PROPHETIC_ERA',
    significance: 'Beginning of Islamic history, birth of the final messenger.',
    location_name: 'Makkah'
  },
  {
    id: randomUUID(),
    title: 'First Revelation (Bi\'thah)',
    title_arabic: 'أول الوحي والبعثة الشريفة',
    description: 'The Prophet Muhammad received the first divine revelation in Cave Hira, beginning his prophetic mission.',
    year_hijri: -13,
    year_gregorian: 610,
    category: 'PROPHETIC_ERA',
    significance: 'Start of the Quran\'s revelation and the Islamic message.',
    location_name: 'Cave Hira'
  },
  {
    id: randomUUID(),
    title: 'Migration to Abyssinia',
    title_arabic: 'الهجرة الأولى إلى الحبشة',
    description: 'A group of Muslims migrated to Abyssinia (Ethiopia) seeking refuge from Meccan persecution under the protection of the Christian king Najashi.',
    year_hijri: -7,
    year_gregorian: 615,
    category: 'PROPHETIC_ERA',
    significance: 'First Islamic migration to establish religious freedom.',
    location_name: 'Abyssinia'
  },
  {
    id: randomUUID(),
    title: 'Isra and Mi\'raj',
    title_arabic: 'الإسراء والمعراج',
    description: 'The Night Journey where Prophet Muhammad traveled from Makkah to Jerusalem and then ascended to heaven, receiving the command of five daily prayers.',
    year_hijri: -1,
    year_gregorian: 621,
    category: 'PROPHETIC_ERA',
    significance: 'Spiritual journey reaffirming divine connection and establishing Islamic law.',
    location_name: 'Makkah'
  },
  {
    id: randomUUID(),
    title: 'The Hijra (Migration to Medina)',
    title_arabic: 'الهجرة النبوية الشريفة',
    description: 'Prophet Muhammad and Muslims migrated from Makkah to Medina, marking the start of the Islamic calendar and the establishment of the first Islamic state.',
    year_hijri: 1,
    year_gregorian: 622,
    category: 'PROPHETIC_ERA',
    significance: 'Foundation of Islamic community and calendar epoch.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Battle of Badr',
    title_arabic: 'معركة بدر الكبرى',
    description: 'First major military engagement where about 313 Muslims defeated a Meccan army of approximately 1000, establishing Islamic military authority.',
    year_hijri: 2,
    year_gregorian: 624,
    category: 'MILITARY',
    significance: 'First decisive Muslim victory, validates Islamic message.',
    location_name: 'Badr'
  },
  {
    id: randomUUID(),
    title: 'Battle of Uhud',
    title_arabic: 'معركة أحد',
    description: 'Muslims faced temporary defeat at Mount Uhud north of Medina, learning important lessons about military discipline.',
    year_hijri: 3,
    year_gregorian: 625,
    category: 'MILITARY',
    significance: 'Important military lesson in Islamic history.',
    location_name: 'Uhud'
  },
  {
    id: randomUUID(),
    title: 'Battle of the Trench (Khandaq)',
    title_arabic: 'معركة الخندق',
    description: 'Muslims defended Medina by digging a trench, successfully repelling a large Meccan siege force through tactical innovation.',
    year_hijri: 5,
    year_gregorian: 627,
    category: 'MILITARY',
    significance: 'Successful defense of Islamic state, demonstrates Muslim ingenuity.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Treaty of Hudaybiyyah',
    title_arabic: 'صلح الحديبية',
    description: 'Peace treaty between Muslims and Quraysh, establishing framework for coexistence and enabling Islamic expansion.',
    year_hijri: 6,
    year_gregorian: 628,
    category: 'POLITICAL',
    significance: 'Peace treaty facilitating Islamic growth.',
    location_name: 'Hudaybiyyah'
  },
  {
    id: randomUUID(),
    title: 'Conquest of Makkah',
    title_arabic: 'فتح مكة المكرمة',
    description: 'Muslims conquered Makkah and purified the Kaaba from idolatry, spreading Islam throughout Arabia.',
    year_hijri: 8,
    year_gregorian: 630,
    category: 'MILITARY',
    significance: 'Most important city falls to Islam, validating the faith.',
    location_name: 'Makkah'
  },
  {
    id: randomUUID(),
    title: 'Farewell Pilgrimage',
    title_arabic: 'حجة الوداع',
    description: 'Prophet Muhammad\'s final pilgrimage to Makkah, where he delivered the Farewell Sermon establishing Islamic principles of equality and unity.',
    year_hijri: 10,
    year_gregorian: 632,
    category: 'PROPHETIC_ERA',
    significance: 'Final guidance on Islamic principles and practices.',
    location_name: 'Makkah'
  },
  {
    id: randomUUID(),
    title: 'Death of Prophet Muhammad',
    title_arabic: 'وفاة رسول الله صلى الله عليه وسلم',
    description: 'Prophet Muhammad passed away in Medina after completing his divine mission and establishing Islamic civilization.',
    year_hijri: 11,
    year_gregorian: 632,
    category: 'PROPHETIC_ERA',
    significance: 'End of prophetic era, beginning of Islamic governance.',
    location_name: 'Medina'
  },

  // Rashidun Caliphate
  {
    id: randomUUID(),
    title: 'Abu Bakr becomes Caliph',
    title_arabic: 'خلافة أبي بكر الصديق',
    description: 'Abu Bakr al-Siddiq became the first Caliph, establishing the precedent for Islamic leadership succession.',
    year_hijri: 11,
    year_gregorian: 632,
    category: 'POLITICAL',
    significance: 'First organized Islamic government under a Caliph.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Wars of Apostasy (Ridda)',
    title_arabic: 'حروب الردة',
    description: 'Abu Bakr unified Arabia by defeating various apostate groups who rejected Islam after the Prophet\'s death.',
    year_hijri: 11,
    year_gregorian: 632,
    end_year_hijri: 12,
    end_year_gregorian: 633,
    category: 'MILITARY',
    significance: 'Consolidation of Islamic Arabia and prevention of religious schism.',
    location_name: 'Makkah'
  },
  {
    id: randomUUID(),
    title: 'Compilation of Quran (First)',
    title_arabic: 'جمع القرآن الكريم',
    description: 'Abu Bakr initiated the first official collection of the Quran into a single standardized manuscript.',
    year_hijri: 12,
    year_gregorian: 633,
    category: 'SCHOLARLY',
    significance: 'Preservation of the Quran in written form.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Umar becomes Caliph',
    title_arabic: 'خلافة عمر بن الخطاب',
    description: 'Umar ibn al-Khattab became the second Caliph, known for administrative genius and Islamic expansion.',
    year_hijri: 13,
    year_gregorian: 634,
    category: 'POLITICAL',
    significance: 'Period of rapid Islamic expansion and administrative reforms.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Battle of Yarmouk',
    title_arabic: 'معركة اليرموك',
    description: 'Decisive Muslim victory over Byzantine forces, securing control of the Levant and Syria for the Islamic caliphate.',
    year_hijri: 15,
    year_gregorian: 636,
    category: 'MILITARY',
    significance: 'Major territorial conquest establishing Islamic control.',
    location_name: 'Yarmouk'
  },
  {
    id: randomUUID(),
    title: 'Conquest of Jerusalem',
    title_arabic: 'فتح بيت المقدس',
    description: 'Muslim forces under Umar conquered Jerusalem, the third holiest city in Islam, establishing tolerance for Christian and Jewish populations.',
    year_hijri: 16,
    year_gregorian: 637,
    category: 'MILITARY',
    significance: 'Conquest of major religious center with policy of religious tolerance.',
    location_name: 'Jerusalem'
  },
  {
    id: randomUUID(),
    title: 'Conquest of Persia (Battle of Qadisiyyah)',
    title_arabic: 'معركة القادسية',
    description: 'Muslim forces defeated the Sassanid Persian army at Qadisiyyah, leading to the conquest of Persia and its integration into the Islamic empire.',
    year_hijri: 15,
    year_gregorian: 636,
    category: 'MILITARY',
    significance: 'Major territorial conquest and Sassanid empire defeat.',
    location_name: 'Qadisiyyah'
  },
  {
    id: randomUUID(),
    title: 'Foundation of Kufa',
    title_arabic: 'تأسيس مدينة الكوفة',
    description: 'Umar established the garrison city of Kufa as a military and administrative center in Iraq.',
    year_hijri: 17,
    year_gregorian: 638,
    category: 'POLITICAL',
    significance: 'Establishment of major Islamic city and learning center.',
    location_name: 'Kufa'
  },
  {
    id: randomUUID(),
    title: 'Foundation of Basra',
    title_arabic: 'تأسيس مدينة البصرة',
    description: 'Umar founded Basra as a strategic port city and garrison, becoming a major center of trade and Islamic learning.',
    year_hijri: 17,
    year_gregorian: 638,
    category: 'POLITICAL',
    significance: 'Establishment of major port city and Islamic center.',
    location_name: 'Basra'
  },
  {
    id: randomUUID(),
    title: 'Foundation of Fustat',
    title_arabic: 'تأسيس مدينة الفسطاط',
    description: 'Muslims established Fustat as the first Islamic capital of Egypt, serving as the administrative center for centuries.',
    year_hijri: 21,
    year_gregorian: 641,
    category: 'POLITICAL',
    significance: 'Establishment of Islamic Egypt\'s first capital.',
    location_name: 'Fustat'
  },
  {
    id: randomUUID(),
    title: 'Uthman becomes Caliph',
    title_arabic: 'خلافة عثمان بن عفان',
    description: 'Uthman ibn Affan became the third Caliph, expanding Islamic territory and standardizing the Quran.',
    year_hijri: 23,
    year_gregorian: 644,
    category: 'POLITICAL',
    significance: 'Period of Quranic standardization and further Islamic expansion.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Standardization of Quran (Uthmanic Codex)',
    title_arabic: 'جمع القرآن الكريم على مصحف واحد',
    description: 'Uthman standardized the Quranic text into an official canonical version distributed throughout the Islamic empire.',
    year_hijri: 25,
    year_gregorian: 645,
    category: 'SCHOLARLY',
    significance: 'Preservation of Quranic uniformity across Islamic world.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Assassination of Uthman',
    title_arabic: 'مقتل عثمان بن عفان',
    description: 'Third Caliph Uthman was assassinated by rebels, leading to civil conflict in the Islamic community.',
    year_hijri: 35,
    year_gregorian: 656,
    category: 'POLITICAL',
    significance: 'Major political crisis and beginning of Islamic civil strife.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Ali becomes Caliph',
    title_arabic: 'خلافة علي بن أبي طالب',
    description: 'Ali ibn Abi Talib became the fourth and final Rashidun Caliph, facing significant opposition and civil war.',
    year_hijri: 35,
    year_gregorian: 656,
    category: 'POLITICAL',
    significance: 'Fourth Caliph\'s rule amid civil strife.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Battle of the Camel',
    title_arabic: 'معركة الجمل',
    description: 'Civil war between Ali\'s supporters and those of Aisha, wife of the Prophet, fought near Basra.',
    year_hijri: 36,
    year_gregorian: 656,
    category: 'MILITARY',
    significance: 'Major internal Islamic conflict establishing precedents.',
    location_name: 'Basra'
  },
  {
    id: randomUUID(),
    title: 'Battle of Siffin',
    title_arabic: 'معركة صفين',
    description: 'Major conflict between Ali and Mu\'awiya, ending in arbitration that divided the Islamic community.',
    year_hijri: 37,
    year_gregorian: 657,
    category: 'MILITARY',
    significance: 'Significant Islamic civil war with lasting impacts.',
    location_name: 'Siffin'
  },
  {
    id: randomUUID(),
    title: 'Assassination of Ali',
    title_arabic: 'مقتل علي بن أبي طالب',
    description: 'Fourth Caliph Ali was assassinated, ending the Rashidun Caliphate and establishing Mu\'awiya\'s Umayyad rule.',
    year_hijri: 40,
    year_gregorian: 661,
    category: 'POLITICAL',
    significance: 'End of Rashidun period, transition to Umayyad era.',
    location_name: 'Kufa'
  },

  // Umayyad Period
  {
    id: randomUUID(),
    title: 'Mu\'awiya founds Umayyad Caliphate',
    title_arabic: 'تأسيس الخلافة الأموية',
    description: 'Mu\'awiya ibn Abi Sufyan established the Umayyad Dynasty with Damascus as its capital, creating a hereditary caliphate.',
    year_hijri: 41,
    year_gregorian: 661,
    category: 'POLITICAL',
    significance: 'Foundation of major Islamic dynasty.',
    location_name: 'Damascus'
  },
  {
    id: randomUUID(),
    title: 'Martyrdom of Husayn at Karbala',
    title_arabic: 'مقتل الحسين بن علي',
    description: 'Husayn ibn Ali, grandson of Prophet Muhammad, was martyred at Karbala, a defining moment in Islamic history.',
    year_hijri: 61,
    year_gregorian: 680,
    category: 'POLITICAL',
    significance: 'Major tragedy shaping Islamic spirituality and Shia identity.',
    location_name: 'Karbala'
  },
  {
    id: randomUUID(),
    title: 'Siege of Makkah',
    title_arabic: 'حصار مكة',
    description: 'Umayyad forces besieged Makkah to suppress opposition, damaging the Kaaba in the process.',
    year_hijri: 64,
    year_gregorian: 683,
    category: 'MILITARY',
    significance: 'Major internal Islamic conflict affecting holiest city.',
    location_name: 'Makkah'
  },
  {
    id: randomUUID(),
    title: 'Construction of Dome of the Rock',
    title_arabic: 'بناء قبة الصخرة',
    description: 'Caliph Abd al-Malik completed the Dome of the Rock in Jerusalem, one of Islam\'s greatest architectural achievements.',
    year_hijri: 72,
    year_gregorian: 691,
    category: 'SOCIAL',
    significance: 'Iconic Islamic monument in Jerusalem.',
    location_name: 'Jerusalem'
  },
  {
    id: randomUUID(),
    title: 'Umar ibn Abd al-Aziz\'s Caliphate',
    title_arabic: 'خلافة عمر بن عبد العزيز',
    description: 'Umayyad Caliph known for justice, piety, and administrative reforms. Compilation of Islamic law advanced during his reign.',
    year_hijri: 99,
    year_gregorian: 717,
    category: 'POLITICAL',
    significance: 'Reformation period emphasizing Islamic principles.',
    location_name: 'Damascus'
  },
  {
    id: randomUUID(),
    title: 'Conquest of Spain',
    title_arabic: 'فتح الأندلس',
    description: 'Muslim forces under Tariq ibn Ziyad crossed from North Africa and conquered much of the Iberian Peninsula.',
    year_hijri: 92,
    year_gregorian: 711,
    category: 'MILITARY',
    significance: 'Major territorial expansion into Europe.',
    location_name: 'Cordoba'
  },
  {
    id: randomUUID(),
    title: 'Battle of Tours',
    title_arabic: 'معركة تور',
    description: 'Frankish forces under Charles Martel halted Muslim expansion in France at the Battle of Tours.',
    year_hijri: 114,
    year_gregorian: 732,
    category: 'MILITARY',
    significance: 'Limit of Islamic expansion in Western Europe.',
    location_name: 'Tours'
  },

  // Abbasid Era & Major Scholarly Events
  {
    id: randomUUID(),
    title: 'Abbasid Revolution',
    title_arabic: 'الثورة العباسية',
    description: 'The Abbasid Dynasty overthrew the Umayyad Caliphate, establishing a new era of Islamic civilization.',
    year_hijri: 132,
    year_gregorian: 750,
    category: 'POLITICAL',
    significance: 'Major dynasty change in Islamic history.',
    location_name: 'Kufa'
  },
  {
    id: randomUUID(),
    title: 'Foundation of Baghdad',
    title_arabic: 'تأسيس مدينة بغداد',
    description: 'Caliph al-Mansur founded Baghdad as the new capital of the Abbasid Caliphate, becoming center of Islamic learning.',
    year_hijri: 145,
    year_gregorian: 762,
    category: 'POLITICAL',
    significance: 'Establishment of greatest Islamic city of medieval world.',
    location_name: 'Baghdad'
  },
  {
    id: randomUUID(),
    title: 'Death of Imam Abu Hanifa',
    title_arabic: 'وفاة الإمام أبي حنيفة',
    description: 'Death of Abu Hanifa, founder of the Hanafi school of Islamic jurisprudence.',
    year_hijri: 150,
    year_gregorian: 767,
    category: 'SCHOLARLY',
    significance: 'Major Islamic legal tradition established.',
    location_name: 'Baghdad'
  },
  {
    id: randomUUID(),
    title: 'Death of Imam Malik',
    title_arabic: 'وفاة الإمام مالك',
    description: 'Death of Malik ibn Anas, founder of the Maliki school of Islamic jurisprudence.',
    year_hijri: 179,
    year_gregorian: 795,
    category: 'SCHOLARLY',
    significance: 'Major Islamic legal tradition established.',
    location_name: 'Medina'
  },
  {
    id: randomUUID(),
    title: 'Death of Imam al-Shafi\'i',
    title_arabic: 'وفاة الإمام الشافعي',
    description: 'Death of Muhammad ibn Idris al-Shafi\'i, founder of the Shafi\'i school of Islamic jurisprudence.',
    year_hijri: 204,
    year_gregorian: 820,
    category: 'SCHOLARLY',
    significance: 'Major Islamic legal tradition established.',
    location_name: 'Egypt'
  },
  {
    id: randomUUID(),
    title: 'Ahmad ibn Hanbal and the Mihna',
    title_arabic: 'محنة الإمام أحمد بن حنبل',
    description: 'Imam Ahmad ibn Hanbal faced persecution during the Mihna (inquisition) for defending traditional Islamic doctrine.',
    year_hijri: 218,
    year_gregorian: 833,
    category: 'SCHOLARLY',
    significance: 'Struggle for Islamic orthodoxy.',
    location_name: 'Baghdad'
  },
  {
    id: randomUUID(),
    title: 'Death of Imam Ahmad ibn Hanbal',
    title_arabic: 'وفاة الإمام أحمد بن حنبل',
    description: 'Death of Ahmad ibn Hanbal, founder of the Hanbali school of Islamic jurisprudence.',
    year_hijri: 241,
    year_gregorian: 855,
    category: 'SCHOLARLY',
    significance: 'Major Islamic legal tradition established.',
    location_name: 'Baghdad'
  },
  {
    id: randomUUID(),
    title: 'Imam Bukhari compiles Sahih',
    title_arabic: 'تصنيف صحيح البخاري',
    description: 'Imam Muhammad ibn Ismail al-Bukhari compiled his famous Sahih, one of the most authentic collections of hadith.',
    year_hijri: 232,
    year_gregorian: 846,
    category: 'SCHOLARLY',
    significance: 'Most authoritative hadith collection in Islam.',
    location_name: 'Bukhara'
  },
  {
    id: randomUUID(),
    title: 'Imam Muslim compiles Sahih',
    title_arabic: 'تصنيف صحيح مسلم',
    description: 'Imam Muslim ibn al-Hajjaj compiled Sahih Muslim, second most authoritative hadith collection.',
    year_hijri: 261,
    year_gregorian: 875,
    category: 'SCHOLARLY',
    significance: 'Second most authoritative hadith collection.',
    location_name: 'Nishapur'
  },
  {
    id: randomUUID(),
    title: 'Abu Dawud compiles Sunan',
    title_arabic: 'تصنيف سنن أبي داود',
    description: 'Abu Dawud al-Sijistani compiled his Sunan, one of the six canonical hadith collections.',
    year_hijri: 275,
    year_gregorian: 889,
    category: 'SCHOLARLY',
    significance: 'Major canonical hadith collection.',
    location_name: 'Basra'
  },
  {
    id: randomUUID(),
    title: 'Tirmidhi compiles Jami\'',
    title_arabic: 'تصنيف جامع الترمذي',
    description: 'Imam al-Tirmidhi compiled his Jami\' (al-Jami\' as-Sahih), one of the six canonical hadith collections.',
    year_hijri: 279,
    year_gregorian: 892,
    category: 'SCHOLARLY',
    significance: 'Major canonical hadith collection.',
    location_name: 'Termez'
  },
  {
    id: randomUUID(),
    title: 'Nasa\'i compiles Sunan',
    title_arabic: 'تصنيف سنن النسائي',
    description: 'Imam al-Nasa\'i compiled his Sunan, one of the six canonical hadith collections.',
    year_hijri: 303,
    year_gregorian: 915,
    category: 'SCHOLARLY',
    significance: 'Major canonical hadith collection.',
    location_name: 'Egypt'
  },
  {
    id: randomUUID(),
    title: 'Ibn Majah compiles Sunan',
    title_arabic: 'تصنيف سنن ابن ماجه',
    description: 'Ibn Majah compiled his Sunan, later recognized as one of the six canonical hadith collections.',
    year_hijri: 273,
    year_gregorian: 887,
    category: 'SCHOLARLY',
    significance: 'Major canonical hadith collection.',
    location_name: 'Qazvin'
  },
  {
    id: randomUUID(),
    title: 'Fall of Baghdad to Mongols',
    title_arabic: 'سقوط بغداد على يد المغول',
    description: 'Mongol forces under Hulagu Khan conquered Baghdad, destroying the Abbasid Caliphate and its vast libraries.',
    year_hijri: 656,
    year_gregorian: 1258,
    category: 'MILITARY',
    significance: 'End of Abbasid era and major Islamic political catastrophe.',
    location_name: 'Baghdad'
  },

  // Later Scholarly Milestones
  {
    id: randomUUID(),
    title: 'Ibn Taymiyyah\'s Era',
    title_arabic: 'عصر ابن تيمية',
    description: 'Era of Ibn Taymiyyah, influential Islamic scholar who reformed Islamic theology and jurisprudence.',
    year_hijri: 728,
    year_gregorian: 1328,
    category: 'SCHOLARLY',
    significance: 'Major scholarly reformer in Islamic history.',
    location_name: 'Damascus'
  },
  {
    id: randomUUID(),
    title: 'Al-Nawawi writes Sharh Sahih Muslim',
    title_arabic: 'شرح النووي على صحيح مسلم',
    description: 'Imam al-Nawawi wrote his comprehensive commentary on Sahih Muslim, providing deep Islamic jurisprudential analysis.',
    year_hijri: 676,
    year_gregorian: 1277,
    category: 'SCHOLARLY',
    significance: 'Major hadith commentary and jurisprudential work.',
    location_name: 'Damascus'
  },
  {
    id: randomUUID(),
    title: 'Al-Dhahabi writes Siyar A\'lam al-Nubala',
    title_arabic: 'سير أعلام النبلاء للذهبي',
    description: 'Imam al-Dhahabi compiled his biographical dictionary of Islamic scholars and righteous figures.',
    year_hijri: 748,
    year_gregorian: 1348,
    category: 'SCHOLARLY',
    significance: 'Comprehensive biographical record of Islamic figures.',
    location_name: 'Damascus'
  },
  {
    id: randomUUID(),
    title: 'Ibn Hajar al-Asqalani writes Fath al-Bari',
    title_arabic: 'فتح الباري شرح صحيح البخاري',
    description: 'Ibn Hajar al-Asqalani wrote Fath al-Bari, the most comprehensive commentary on Sahih Bukhari.',
    year_hijri: 852,
    year_gregorian: 1449,
    category: 'SCHOLARLY',
    significance: 'Definitive hadith commentary and jurisprudential work.',
    location_name: 'Cairo'
  }
];

async function seedLocations() {
  console.log('Seeding locations...');

  const locationQueries = LOCATIONS.map(location => ({
    query: `
      MERGE (l:Location {id: $id})
      SET l.name = $name,
          l.name_arabic = $name_arabic,
          l.latitude = $latitude,
          l.longitude = $longitude,
          l.modern_country = $modern_country,
          l.region = $region,
          l.description = $description,
          l.created_at = datetime()
      RETURN l.id as id
    `,
    params: {
      id: location.id,
      name: location.name,
      name_arabic: location.name_arabic,
      latitude: location.latitude,
      longitude: location.longitude,
      modern_country: location.modern_country,
      region: location.region,
      description: location.description
    }
  }));

  for (const { query, params } of locationQueries) {
    await runWrite(query, params);
  }

  console.log(`✓ Seeded ${LOCATIONS.length} locations`);
}

async function seedHistoricalEvents() {
  console.log('Seeding historical events...');

  const eventQueries = HISTORICAL_EVENTS.map(event => ({
    query: `
      MERGE (e:HistoricalEvent {id: $id})
      SET e.title = $title,
          e.title_arabic = $title_arabic,
          e.description = $description,
          e.year_hijri = $year_hijri,
          e.year_gregorian = $year_gregorian,
          e.end_year_hijri = $end_year_hijri,
          e.end_year_gregorian = $end_year_gregorian,
          e.category = $category,
          e.significance = $significance,
          e.location_name = $location_name,
          e.created_at = datetime()
      RETURN e.id as id
    `,
    params: {
      id: event.id,
      title: event.title,
      title_arabic: event.title_arabic,
      description: event.description,
      year_hijri: event.year_hijri,
      year_gregorian: event.year_gregorian,
      end_year_hijri: event.end_year_hijri || null,
      end_year_gregorian: event.end_year_gregorian || null,
      category: event.category,
      significance: event.significance,
      location_name: event.location_name
    }
  }));

  for (const { query, params } of eventQueries) {
    await runWrite(query, params);
  }

  console.log(`✓ Seeded ${HISTORICAL_EVENTS.length} historical events`);
}

async function linkEventsToLocations() {
  console.log('Linking events to locations...');

  let linkedCount = 0;

  for (const event of HISTORICAL_EVENTS) {
    const query = `
      MATCH (e:HistoricalEvent {id: $event_id})
      MATCH (l:Location {name: $location_name})
      MERGE (e)-[:OCCURRED_AT]->(l)
      RETURN e.id as event_id, l.id as location_id
    `;

    const result = await runWrite(query, {
      event_id: event.id,
      location_name: event.location_name
    });

    if (result) {
      linkedCount++;
    }
  }

  console.log(`✓ Linked ${linkedCount} events to locations`);
}

async function main() {
  try {
    console.log('Starting historical data seeding...\n');

    await seedLocations();
    await seedHistoricalEvents();
    await linkEventsToLocations();

    console.log('\n✓ Historical data seeding completed successfully!');
  } catch (error) {
    console.error('Error seeding historical data:', error);
    throw error;
  } finally {
    await closeDriver();
  }
}

main().catch(console.error);
