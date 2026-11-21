/**
 * Seeds the curation history tables (locations, historical events, epochs) as UNVERIFIED seed rows, through the
 * query layer (src/db/queries/history-seed.ts): idempotent, audited as `system:seed`, and never overwriting a row a
 * curator has reviewed, published or retired. Events and locations are ported from the Neo4j-era
 * src/scripts/seed-historical-data.ts with the same deterministic ids. See src/db/queries/AGENTS.md §Time and place.
 *
 *   npx tsx --conditions=react-server src/scripts/db/seed-history.ts            # writes
 *   npx tsx --conditions=react-server src/scripts/db/seed-history.ts --dry-run  # prints the plan only
 *
 * Targets DATABASE_URL only; refuses the production database.
 */
import { createHash } from 'node:crypto';
import path from 'node:path';
import { config as loadEnvironment } from 'dotenv';
import type { SeedContent, SeedOutcome, SeedRow } from '../../db/queries/history-seed';

export const SEED_ACTOR = 'system:seed';

/** The legacy seed's id rule, kept so these rows keep the ids the Neo4j curation export will carry. */
export function stableSeedId(namespace: string, ...parts: Array<string | number>): string {
  const normalized = parts
    .map((part) => String(part).normalize('NFKC').trim().toLowerCase().replace(/\s+/g, ' '))
    .join('|');
  const digest = createHash('sha256').update(`${namespace}|${normalized}`).digest('hex').slice(0, 24);
  return `${namespace}:${digest}`;
}

interface LegacyLocation {
  name: string;
  name_arabic: string;
  latitude: number;
  longitude: number;
  modern_country: string;
  region: string;
  description: string;
}

interface LegacyEvent {
  title: string;
  title_arabic: string;
  description: string;
  year_hijri: number;
  year_gregorian: number;
  end_year_hijri?: number;
  end_year_gregorian?: number;
  category: string;
  significance: string;
  location_name: string;
}

// Ported verbatim from src/scripts/seed-historical-data.ts (LOCATIONS, HISTORICAL_EVENTS).
const LEGACY_LOCATIONS: LegacyLocation[] = [
  {name: "Makkah", name_arabic: "مكة المكرمة", latitude: 21.4225, longitude: 39.8265, modern_country: "Saudi Arabia", region: "Hejaz", description: "The holiest city in Islam, birthplace of Prophet Muhammad and home to the Kaaba. Center of Islamic pilgrimage and spiritual significance."},
  {name: "Medina", name_arabic: "المدينة المنورة", latitude: 24.5247, longitude: 39.5692, modern_country: "Saudi Arabia", region: "Hejaz", description: "City of the Prophet, destination of the Hijra, and capital of the early Islamic state. Contains the Masjid al-Nabawi."},
  {name: "Jerusalem", name_arabic: "القدس", latitude: 31.7683, longitude: 35.2137, modern_country: "Palestine/Israel", region: "Levant", description: "Third holiest city in Islam, site of Al-Aqsa Mosque and the Dome of the Rock. Central to Islamic, Jewish, and Christian traditions."},
  {name: "Damascus", name_arabic: "دمشق", latitude: 33.5138, longitude: 36.2765, modern_country: "Syria", region: "Levant", description: "Capital of the Umayyad Caliphate, major center of Islamic scholarship and Quran compilation. Home to the Umayyad Mosque."},
  {name: "Baghdad", name_arabic: "بغداد", latitude: 33.3128, longitude: 44.3615, modern_country: "Iraq", region: "Mesopotamia", description: "Capital of the Abbasid Caliphate, center of Islamic learning and the House of Wisdom. One of the greatest cities of the medieval world."},
  {name: "Kufa", name_arabic: "الكوفة", latitude: 32.0106, longitude: 44.4008, modern_country: "Iraq", region: "Iraq", description: "Major city founded during the Rashidun period, important center of Quranic studies and Islamic jurisprudence."},
  {name: "Basra", name_arabic: "البصرة", latitude: 30.5273, longitude: 47.8027, modern_country: "Iraq", region: "Iraq", description: "Strategic port city founded during Rashidun era, major center of trade, Hadith scholarship, and Arabic linguistics."},
  {name: "Fustat", name_arabic: "الفسطاط", latitude: 30.0444, longitude: 31.2357, modern_country: "Egypt", region: "Egypt", description: "Early Islamic capital of Egypt, predecessor to Cairo. Major center of Islamic administration and learning."},
  {name: "Bukhara", name_arabic: "بخارى", latitude: 39.775, longitude: 64.4256, modern_country: "Uzbekistan", region: "Central Asia", description: "Major center of Islamic learning and Hadith scholarship. Birthplace of Imam Bukhari and hub of the Silk Road."},
  {name: "Nishapur", name_arabic: "نيسابور", latitude: 36.214, longitude: 58.7738, modern_country: "Iran", region: "Khorasan", description: "Important center of Islamic scholarship and Hadith collection. Hometown of Imam Muslim and numerous scholars."},
  {name: "Samarkand", name_arabic: "سمرقند", latitude: 39.6548, longitude: 66.9597, modern_country: "Uzbekistan", region: "Central Asia", description: "Major crossroads of the Silk Road and center of Islamic science, astronomy, and mathematics."},
  {name: "Karbala", name_arabic: "كربلاء", latitude: 32.5086, longitude: 44.0263, modern_country: "Iraq", region: "Iraq", description: "Holy city in Shia Islam, site of the martyrdom of Husayn ibn Ali. Major pilgrimage destination."},
  {name: "Abyssinia", name_arabic: "الحبشة", latitude: 9.145, longitude: 40.4897, modern_country: "Ethiopia", region: "East Africa", description: "Christian kingdom that provided refuge for early Muslims fleeing Meccan persecution. Important in early Islamic history."},
  {name: "Sana'a", name_arabic: "صنعاء", latitude: 15.3694, longitude: 48.2159, modern_country: "Yemen", region: "Arabia", description: "Major Islamic city and cultural center in Yemen, important for trade and Islamic governance."},
  {name: "Taif", name_arabic: "الطائف", latitude: 21.2716, longitude: 40.4158, modern_country: "Saudi Arabia", region: "Arabia", description: "Mountain city near Makkah, site of Prophet Muhammad's preaching mission and important in early Islam."},
  {name: "Badr", name_arabic: "بدر", latitude: 24.3544, longitude: 38.7472, modern_country: "Saudi Arabia", region: "Arabia", description: "Site of the Battle of Badr, first major military victory of Muslims against the Quraysh."},
  {name: "Uhud", name_arabic: "أحد", latitude: 24.6067, longitude: 39.5928, modern_country: "Saudi Arabia", region: "Arabia", description: "Mountain north of Medina, site of the Battle of Uhud where Muslims faced temporary defeat."},
  {name: "Khaybar", name_arabic: "خيبر", latitude: 25.1925, longitude: 39.4842, modern_country: "Saudi Arabia", region: "Arabia", description: "Fortress and Jewish settlement conquered by Muslims, significant in establishing Islamic authority."},
  {name: "Hudaybiyyah", name_arabic: "الحديبية", latitude: 21.8694, longitude: 39.6125, modern_country: "Saudi Arabia", region: "Arabia", description: "Coastal location where the Treaty of Hudaybiyyah was signed, peace accord between Muslims and Quraysh."},
  {name: "Yarmouk", name_arabic: "اليرموك", latitude: 32.7567, longitude: 35.7733, modern_country: "Jordan/Syria border", region: "Levant", description: "Site of the decisive Battle of Yarmouk, victory that secured Muslim control of the Levant."},
  {name: "Qadisiyyah", name_arabic: "القادسية", latitude: 31.95, longitude: 44.3667, modern_country: "Iraq", region: "Iraq", description: "Site of the Battle of Qadisiyyah, major victory that led to the conquest of Persia."},
  {name: "Siffin", name_arabic: "صفين", latitude: 35.2389, longitude: 39.3278, modern_country: "Syria", region: "Levant", description: "Site of the Battle of Siffin between Ali and Mu'awiya, major conflict in early Islamic history."},
  {name: "Termez", name_arabic: "الترمذ", latitude: 37.2622, longitude: 68.7735, modern_country: "Uzbekistan/Afghanistan", region: "Central Asia", description: "Ancient city on the Silk Road, birthplace of Imam Tirmidhi, major center of Islamic learning."},
  {name: "Qazvin", name_arabic: "قزوين", latitude: 36.2665, longitude: 50.0049, modern_country: "Iran", region: "Persia", description: "Historic Persian city and center of Islamic learning, birthplace of Ibn Majah."},
  {name: "Ray", name_arabic: "الري", latitude: 35.6667, longitude: 51.4167, modern_country: "Iran", region: "Persia", description: "Historic Persian city and major center of Islamic scholarship, near modern-day Tehran."},
  {name: "Isfahan", name_arabic: "أصفهان", latitude: 32.6769, longitude: 51.6694, modern_country: "Iran", region: "Persia", description: "Major Persian city and center of Islamic arts, sciences, and architecture."},
  {name: "Herat", name_arabic: "هرات", latitude: 34.3425, longitude: 62.1986, modern_country: "Afghanistan", region: "Central Asia", description: "Important center of Islamic learning and trade on the Silk Road."},
  {name: "Cordoba", name_arabic: "قرطبة", latitude: 37.8882, longitude: -4.7794, modern_country: "Spain", region: "Iberia", description: "Capital of the Islamic Umayyad Caliphate in Spain, center of Islamic learning and culture in medieval Europe."},
  {name: "Fez", name_arabic: "فاس", latitude: 34.0333, longitude: -5.0033, modern_country: "Morocco", region: "North Africa", description: "Major Islamic city in Morocco, center of learning and culture. Home to Al-Qarawiyyin University."},
  {name: "Cairo", name_arabic: "القاهرة", latitude: 30.0444, longitude: 31.2357, modern_country: "Egypt", region: "Egypt", description: "Capital of Egypt built on the foundation of Fustat, major center of Islamic civilization and learning."},
  {name: "Cave Hira", name_arabic: "غار حراء", latitude: 21.5011, longitude: 39.8397, modern_country: "Saudi Arabia", region: "Arabia", description: "Mountain cave near Makkah where the Prophet Muhammad received the first revelation."},
  {name: "Tours", name_arabic: "تور", latitude: 47.3915, longitude: 0.6848, modern_country: "France", region: "Europe", description: "Site of the Battle of Tours, where Muslim expansion into Europe was halted."},
];

const LEGACY_EVENTS: LegacyEvent[] = [
  {title: "Birth of Prophet Muhammad", title_arabic: "ميلاد الرسول محمد صلى الله عليه وسلم", description: "Birth of Prophet Muhammad, founder of Islam. Born in Makkah on a Monday, year 53 BH (Before Hijra).", year_hijri: 0, year_gregorian: 570, category: "PROPHETIC_ERA", significance: "Beginning of Islamic history, birth of the final messenger.", location_name: "Makkah"},
  {title: "First Revelation (Bi'thah)", title_arabic: "أول الوحي والبعثة الشريفة", description: "The Prophet Muhammad received the first divine revelation in Cave Hira, beginning his prophetic mission.", year_hijri: -13, year_gregorian: 610, category: "PROPHETIC_ERA", significance: "Start of the Quran's revelation and the Islamic message.", location_name: "Cave Hira"},
  {title: "Migration to Abyssinia", title_arabic: "الهجرة الأولى إلى الحبشة", description: "A group of Muslims migrated to Abyssinia (Ethiopia) seeking refuge from Meccan persecution under the protection of the Christian king Najashi.", year_hijri: -7, year_gregorian: 615, category: "PROPHETIC_ERA", significance: "First Islamic migration to establish religious freedom.", location_name: "Abyssinia"},
  {title: "Isra and Mi'raj", title_arabic: "الإسراء والمعراج", description: "The Night Journey where Prophet Muhammad traveled from Makkah to Jerusalem and then ascended to heaven, receiving the command of five daily prayers.", year_hijri: -1, year_gregorian: 621, category: "PROPHETIC_ERA", significance: "Spiritual journey reaffirming divine connection and establishing Islamic law.", location_name: "Makkah"},
  {title: "The Hijra (Migration to Medina)", title_arabic: "الهجرة النبوية الشريفة", description: "Prophet Muhammad and Muslims migrated from Makkah to Medina, marking the start of the Islamic calendar and the establishment of the first Islamic state.", year_hijri: 1, year_gregorian: 622, category: "PROPHETIC_ERA", significance: "Foundation of Islamic community and calendar epoch.", location_name: "Medina"},
  {title: "Battle of Badr", title_arabic: "معركة بدر الكبرى", description: "First major military engagement where about 313 Muslims defeated a Meccan army of approximately 1000, establishing Islamic military authority.", year_hijri: 2, year_gregorian: 624, category: "MILITARY", significance: "First decisive Muslim victory, validates Islamic message.", location_name: "Badr"},
  {title: "Battle of Uhud", title_arabic: "معركة أحد", description: "Muslims faced temporary defeat at Mount Uhud north of Medina, learning important lessons about military discipline.", year_hijri: 3, year_gregorian: 625, category: "MILITARY", significance: "Important military lesson in Islamic history.", location_name: "Uhud"},
  {title: "Battle of the Trench (Khandaq)", title_arabic: "معركة الخندق", description: "Muslims defended Medina by digging a trench, successfully repelling a large Meccan siege force through tactical innovation.", year_hijri: 5, year_gregorian: 627, category: "MILITARY", significance: "Successful defense of Islamic state, demonstrates Muslim ingenuity.", location_name: "Medina"},
  {title: "Treaty of Hudaybiyyah", title_arabic: "صلح الحديبية", description: "Peace treaty between Muslims and Quraysh, establishing framework for coexistence and enabling Islamic expansion.", year_hijri: 6, year_gregorian: 628, category: "POLITICAL", significance: "Peace treaty facilitating Islamic growth.", location_name: "Hudaybiyyah"},
  {title: "Conquest of Makkah", title_arabic: "فتح مكة المكرمة", description: "Muslims conquered Makkah and purified the Kaaba from idolatry, spreading Islam throughout Arabia.", year_hijri: 8, year_gregorian: 630, category: "MILITARY", significance: "Most important city falls to Islam, validating the faith.", location_name: "Makkah"},
  {title: "Farewell Pilgrimage", title_arabic: "حجة الوداع", description: "Prophet Muhammad's final pilgrimage to Makkah, where he delivered the Farewell Sermon establishing Islamic principles of equality and unity.", year_hijri: 10, year_gregorian: 632, category: "PROPHETIC_ERA", significance: "Final guidance on Islamic principles and practices.", location_name: "Makkah"},
  {title: "Death of Prophet Muhammad", title_arabic: "وفاة رسول الله صلى الله عليه وسلم", description: "Prophet Muhammad passed away in Medina after completing his divine mission and establishing Islamic civilization.", year_hijri: 11, year_gregorian: 632, category: "PROPHETIC_ERA", significance: "End of prophetic era, beginning of Islamic governance.", location_name: "Medina"},
  {title: "Abu Bakr becomes Caliph", title_arabic: "خلافة أبي بكر الصديق", description: "Abu Bakr al-Siddiq became the first Caliph, establishing the precedent for Islamic leadership succession.", year_hijri: 11, year_gregorian: 632, category: "POLITICAL", significance: "First organized Islamic government under a Caliph.", location_name: "Medina"},
  {title: "Wars of Apostasy (Ridda)", title_arabic: "حروب الردة", description: "Abu Bakr unified Arabia by defeating various apostate groups who rejected Islam after the Prophet's death.", year_hijri: 11, year_gregorian: 632, end_year_hijri: 12, end_year_gregorian: 633, category: "MILITARY", significance: "Consolidation of Islamic Arabia and prevention of religious schism.", location_name: "Makkah"},
  {title: "Compilation of Quran (First)", title_arabic: "جمع القرآن الكريم", description: "Abu Bakr initiated the first official collection of the Quran into a single standardized manuscript.", year_hijri: 12, year_gregorian: 633, category: "SCHOLARLY", significance: "Preservation of the Quran in written form.", location_name: "Medina"},
  {title: "Umar becomes Caliph", title_arabic: "خلافة عمر بن الخطاب", description: "Umar ibn al-Khattab became the second Caliph, known for administrative genius and Islamic expansion.", year_hijri: 13, year_gregorian: 634, category: "POLITICAL", significance: "Period of rapid Islamic expansion and administrative reforms.", location_name: "Medina"},
  {title: "Battle of Yarmouk", title_arabic: "معركة اليرموك", description: "Decisive Muslim victory over Byzantine forces, securing control of the Levant and Syria for the Islamic caliphate.", year_hijri: 15, year_gregorian: 636, category: "MILITARY", significance: "Major territorial conquest establishing Islamic control.", location_name: "Yarmouk"},
  {title: "Conquest of Jerusalem", title_arabic: "فتح بيت المقدس", description: "Muslim forces under Umar conquered Jerusalem, the third holiest city in Islam, establishing tolerance for Christian and Jewish populations.", year_hijri: 16, year_gregorian: 637, category: "MILITARY", significance: "Conquest of major religious center with policy of religious tolerance.", location_name: "Jerusalem"},
  {title: "Conquest of Persia (Battle of Qadisiyyah)", title_arabic: "معركة القادسية", description: "Muslim forces defeated the Sassanid Persian army at Qadisiyyah, leading to the conquest of Persia and its integration into the Islamic empire.", year_hijri: 15, year_gregorian: 636, category: "MILITARY", significance: "Major territorial conquest and Sassanid empire defeat.", location_name: "Qadisiyyah"},
  {title: "Foundation of Kufa", title_arabic: "تأسيس مدينة الكوفة", description: "Umar established the garrison city of Kufa as a military and administrative center in Iraq.", year_hijri: 17, year_gregorian: 638, category: "POLITICAL", significance: "Establishment of major Islamic city and learning center.", location_name: "Kufa"},
  {title: "Foundation of Basra", title_arabic: "تأسيس مدينة البصرة", description: "Umar founded Basra as a strategic port city and garrison, becoming a major center of trade and Islamic learning.", year_hijri: 17, year_gregorian: 638, category: "POLITICAL", significance: "Establishment of major port city and Islamic center.", location_name: "Basra"},
  {title: "Foundation of Fustat", title_arabic: "تأسيس مدينة الفسطاط", description: "Muslims established Fustat as the first Islamic capital of Egypt, serving as the administrative center for centuries.", year_hijri: 21, year_gregorian: 641, category: "POLITICAL", significance: "Establishment of Islamic Egypt's first capital.", location_name: "Fustat"},
  {title: "Uthman becomes Caliph", title_arabic: "خلافة عثمان بن عفان", description: "Uthman ibn Affan became the third Caliph, expanding Islamic territory and standardizing the Quran.", year_hijri: 23, year_gregorian: 644, category: "POLITICAL", significance: "Period of Quranic standardization and further Islamic expansion.", location_name: "Medina"},
  {title: "Standardization of Quran (Uthmanic Codex)", title_arabic: "جمع القرآن الكريم على مصحف واحد", description: "Uthman standardized the Quranic text into an official canonical version distributed throughout the Islamic empire.", year_hijri: 25, year_gregorian: 645, category: "SCHOLARLY", significance: "Preservation of Quranic uniformity across Islamic world.", location_name: "Medina"},
  {title: "Assassination of Uthman", title_arabic: "مقتل عثمان بن عفان", description: "Third Caliph Uthman was assassinated by rebels, leading to civil conflict in the Islamic community.", year_hijri: 35, year_gregorian: 656, category: "POLITICAL", significance: "Major political crisis and beginning of Islamic civil strife.", location_name: "Medina"},
  {title: "Ali becomes Caliph", title_arabic: "خلافة علي بن أبي طالب", description: "Ali ibn Abi Talib became the fourth and final Rashidun Caliph, facing significant opposition and civil war.", year_hijri: 35, year_gregorian: 656, category: "POLITICAL", significance: "Fourth Caliph's rule amid civil strife.", location_name: "Medina"},
  {title: "Battle of the Camel", title_arabic: "معركة الجمل", description: "Civil war between Ali's supporters and those of Aisha, wife of the Prophet, fought near Basra.", year_hijri: 36, year_gregorian: 656, category: "MILITARY", significance: "Major internal Islamic conflict establishing precedents.", location_name: "Basra"},
  {title: "Battle of Siffin", title_arabic: "معركة صفين", description: "Major conflict between Ali and Mu'awiya, ending in arbitration that divided the Islamic community.", year_hijri: 37, year_gregorian: 657, category: "MILITARY", significance: "Significant Islamic civil war with lasting impacts.", location_name: "Siffin"},
  {title: "Assassination of Ali", title_arabic: "مقتل علي بن أبي طالب", description: "Fourth Caliph Ali was assassinated, ending the Rashidun Caliphate and establishing Mu'awiya's Umayyad rule.", year_hijri: 40, year_gregorian: 661, category: "POLITICAL", significance: "End of Rashidun period, transition to Umayyad era.", location_name: "Kufa"},
  {title: "Mu'awiya founds Umayyad Caliphate", title_arabic: "تأسيس الخلافة الأموية", description: "Mu'awiya ibn Abi Sufyan established the Umayyad Dynasty with Damascus as its capital, creating a hereditary caliphate.", year_hijri: 41, year_gregorian: 661, category: "POLITICAL", significance: "Foundation of major Islamic dynasty.", location_name: "Damascus"},
  {title: "Martyrdom of Husayn at Karbala", title_arabic: "مقتل الحسين بن علي", description: "Husayn ibn Ali, grandson of Prophet Muhammad, was martyred at Karbala, a defining moment in Islamic history.", year_hijri: 61, year_gregorian: 680, category: "POLITICAL", significance: "Major tragedy shaping Islamic spirituality and Shia identity.", location_name: "Karbala"},
  {title: "Siege of Makkah", title_arabic: "حصار مكة", description: "Umayyad forces besieged Makkah to suppress opposition, damaging the Kaaba in the process.", year_hijri: 64, year_gregorian: 683, category: "MILITARY", significance: "Major internal Islamic conflict affecting holiest city.", location_name: "Makkah"},
  {title: "Construction of Dome of the Rock", title_arabic: "بناء قبة الصخرة", description: "Caliph Abd al-Malik completed the Dome of the Rock in Jerusalem, one of Islam's greatest architectural achievements.", year_hijri: 72, year_gregorian: 691, category: "SOCIAL", significance: "Iconic Islamic monument in Jerusalem.", location_name: "Jerusalem"},
  {title: "Umar ibn Abd al-Aziz's Caliphate", title_arabic: "خلافة عمر بن عبد العزيز", description: "Umayyad Caliph known for justice, piety, and administrative reforms. Compilation of Islamic law advanced during his reign.", year_hijri: 99, year_gregorian: 717, category: "POLITICAL", significance: "Reformation period emphasizing Islamic principles.", location_name: "Damascus"},
  {title: "Conquest of Spain", title_arabic: "فتح الأندلس", description: "Muslim forces under Tariq ibn Ziyad crossed from North Africa and conquered much of the Iberian Peninsula.", year_hijri: 92, year_gregorian: 711, category: "MILITARY", significance: "Major territorial expansion into Europe.", location_name: "Cordoba"},
  {title: "Battle of Tours", title_arabic: "معركة تور", description: "Frankish forces under Charles Martel halted Muslim expansion in France at the Battle of Tours.", year_hijri: 114, year_gregorian: 732, category: "MILITARY", significance: "Limit of Islamic expansion in Western Europe.", location_name: "Tours"},
  {title: "Abbasid Revolution", title_arabic: "الثورة العباسية", description: "The Abbasid Dynasty overthrew the Umayyad Caliphate, establishing a new era of Islamic civilization.", year_hijri: 132, year_gregorian: 750, category: "POLITICAL", significance: "Major dynasty change in Islamic history.", location_name: "Kufa"},
  {title: "Foundation of Baghdad", title_arabic: "تأسيس مدينة بغداد", description: "Caliph al-Mansur founded Baghdad as the new capital of the Abbasid Caliphate, becoming center of Islamic learning.", year_hijri: 145, year_gregorian: 762, category: "POLITICAL", significance: "Establishment of greatest Islamic city of medieval world.", location_name: "Baghdad"},
  {title: "Death of Imam Abu Hanifa", title_arabic: "وفاة الإمام أبي حنيفة", description: "Death of Abu Hanifa, founder of the Hanafi school of Islamic jurisprudence.", year_hijri: 150, year_gregorian: 767, category: "SCHOLARLY", significance: "Major Islamic legal tradition established.", location_name: "Baghdad"},
  {title: "Death of Imam Malik", title_arabic: "وفاة الإمام مالك", description: "Death of Malik ibn Anas, founder of the Maliki school of Islamic jurisprudence.", year_hijri: 179, year_gregorian: 795, category: "SCHOLARLY", significance: "Major Islamic legal tradition established.", location_name: "Medina"},
  {title: "Death of Imam al-Shafi'i", title_arabic: "وفاة الإمام الشافعي", description: "Death of Muhammad ibn Idris al-Shafi'i, founder of the Shafi'i school of Islamic jurisprudence.", year_hijri: 204, year_gregorian: 820, category: "SCHOLARLY", significance: "Major Islamic legal tradition established.", location_name: "Egypt"},
  {title: "Ahmad ibn Hanbal and the Mihna", title_arabic: "محنة الإمام أحمد بن حنبل", description: "Imam Ahmad ibn Hanbal faced persecution during the Mihna (inquisition) for defending traditional Islamic doctrine.", year_hijri: 218, year_gregorian: 833, category: "SCHOLARLY", significance: "Struggle for Islamic orthodoxy.", location_name: "Baghdad"},
  {title: "Death of Imam Ahmad ibn Hanbal", title_arabic: "وفاة الإمام أحمد بن حنبل", description: "Death of Ahmad ibn Hanbal, founder of the Hanbali school of Islamic jurisprudence.", year_hijri: 241, year_gregorian: 855, category: "SCHOLARLY", significance: "Major Islamic legal tradition established.", location_name: "Baghdad"},
  {title: "Imam Bukhari compiles Sahih", title_arabic: "تصنيف صحيح البخاري", description: "Imam Muhammad ibn Ismail al-Bukhari compiled his famous Sahih, one of the most authentic collections of hadith.", year_hijri: 232, year_gregorian: 846, category: "SCHOLARLY", significance: "Most authoritative hadith collection in Islam.", location_name: "Bukhara"},
  {title: "Imam Muslim compiles Sahih", title_arabic: "تصنيف صحيح مسلم", description: "Imam Muslim ibn al-Hajjaj compiled Sahih Muslim, second most authoritative hadith collection.", year_hijri: 261, year_gregorian: 875, category: "SCHOLARLY", significance: "Second most authoritative hadith collection.", location_name: "Nishapur"},
  {title: "Abu Dawud compiles Sunan", title_arabic: "تصنيف سنن أبي داود", description: "Abu Dawud al-Sijistani compiled his Sunan, one of the six canonical hadith collections.", year_hijri: 275, year_gregorian: 889, category: "SCHOLARLY", significance: "Major canonical hadith collection.", location_name: "Basra"},
  {title: "Tirmidhi compiles Jami'", title_arabic: "تصنيف جامع الترمذي", description: "Imam al-Tirmidhi compiled his Jami' (al-Jami' as-Sahih), one of the six canonical hadith collections.", year_hijri: 279, year_gregorian: 892, category: "SCHOLARLY", significance: "Major canonical hadith collection.", location_name: "Termez"},
  {title: "Nasa'i compiles Sunan", title_arabic: "تصنيف سنن النسائي", description: "Imam al-Nasa'i compiled his Sunan, one of the six canonical hadith collections.", year_hijri: 303, year_gregorian: 915, category: "SCHOLARLY", significance: "Major canonical hadith collection.", location_name: "Egypt"},
  {title: "Ibn Majah compiles Sunan", title_arabic: "تصنيف سنن ابن ماجه", description: "Ibn Majah compiled his Sunan, later recognized as one of the six canonical hadith collections.", year_hijri: 273, year_gregorian: 887, category: "SCHOLARLY", significance: "Major canonical hadith collection.", location_name: "Qazvin"},
  {title: "Fall of Baghdad to Mongols", title_arabic: "سقوط بغداد على يد المغول", description: "Mongol forces under Hulagu Khan conquered Baghdad, destroying the Abbasid Caliphate and its vast libraries.", year_hijri: 656, year_gregorian: 1258, category: "MILITARY", significance: "End of Abbasid era and major Islamic political catastrophe.", location_name: "Baghdad"},
  {title: "Ibn Taymiyyah's Era", title_arabic: "عصر ابن تيمية", description: "Era of Ibn Taymiyyah, influential Islamic scholar who reformed Islamic theology and jurisprudence.", year_hijri: 728, year_gregorian: 1328, category: "SCHOLARLY", significance: "Major scholarly reformer in Islamic history.", location_name: "Damascus"},
  {title: "Al-Nawawi writes Sharh Sahih Muslim", title_arabic: "شرح النووي على صحيح مسلم", description: "Imam al-Nawawi wrote his comprehensive commentary on Sahih Muslim, providing deep Islamic jurisprudential analysis.", year_hijri: 676, year_gregorian: 1277, category: "SCHOLARLY", significance: "Major hadith commentary and jurisprudential work.", location_name: "Damascus"},
  {title: "Al-Dhahabi writes Siyar A'lam al-Nubala", title_arabic: "سير أعلام النبلاء للذهبي", description: "Imam al-Dhahabi compiled his biographical dictionary of Islamic scholars and righteous figures.", year_hijri: 748, year_gregorian: 1348, category: "SCHOLARLY", significance: "Comprehensive biographical record of Islamic figures.", location_name: "Damascus"},
  {title: "Ibn Hajar al-Asqalani writes Fath al-Bari", title_arabic: "فتح الباري شرح صحيح البخاري", description: "Ibn Hajar al-Asqalani wrote Fath al-Bari, the most comprehensive commentary on Sahih Bukhari.", year_hijri: 852, year_gregorian: 1449, category: "SCHOLARLY", significance: "Definitive hadith commentary and jurisprudential work.", location_name: "Cairo"},
];

/**
 * Start years the legacy row itself contradicts, corrected from the row's own text. The id still uses the legacy
 * year so it matches the Neo4j node. "Birth of Prophet Muhammad" stored 0, but its description says 53 BH, and the
 * Hijri count has no year 0.
 */
const START_YEAR_CORRECTIONS: Record<string, { start_year_hijri: number; reason: string }> = {
  'Birth of Prophet Muhammad': { start_year_hijri: -53, reason: "legacy year_hijri 0; the row's description says 53 BH" },
};

export interface EpochSeed {
  id: string;
  name: string;
  name_arabic?: string;
  alternate_names?: Array<{ name: string; name_arabic?: string; used_by: string }>;
  parent?: string;
  tradition?: 'Sunni' | 'Imami' | 'Zaydi' | 'Ibadi';
  start: number;
  start_latest?: number;
  end: number | null;
  end_latest?: number;
  boundary_note?: string;
  overview: string;
}

/**
 * Eras, Hijri years, parents before children. Neutral descriptive names; a tradition's own name for a period is an
 * alternate labelled with who uses it. A disputed boundary is a range with a note. Every row is an unverified seed
 * awaiting a citation; none cites anything.
 */
export const EPOCHS: EpochSeed[] = [
  // Shared periods
  { id: 'epoch:prophetic-mission', name: "The Prophet's mission", name_arabic: 'العهد النبوي', start: -13, end: 11,
    alternate_names: [{ name: 'al-ʿAhd al-Nabawi', name_arabic: 'العهد النبوي', used_by: 'historians' }],
    overview: "From the first revelation (13 BH) to the Prophet's death at Medina (11 AH)." },
  { id: 'epoch:prophetic-mission-makkah', parent: 'epoch:prophetic-mission', name: 'Makkan period', name_arabic: 'العهد المكي', start: -13, end: 1,
    overview: 'The years of the mission at Makkah, up to the emigration (hijra) to Medina.' },
  { id: 'epoch:prophetic-mission-madinah', parent: 'epoch:prophetic-mission', name: 'Madinan period', name_arabic: 'العهد المدني', start: 1, end: 11,
    overview: "From the emigration to Medina to the Prophet's death." },

  { id: 'epoch:first-four-caliphs', name: 'The first four caliphs', start: 11, end: 40, end_latest: 41,
    alternate_names: [{ name: 'al-Khulafaʾ al-Rashidun (the rightly guided caliphs)', name_arabic: 'الخلفاء الراشدون', used_by: 'Sunni' }],
    boundary_note: "Ends with ʿAli's death in 40; some reckonings add al-Hasan b. ʿAli's months as caliph, to his agreement with Muʿawiya in 41.",
    overview: "The caliphates of Abu Bakr, ʿUmar, ʿUthman and ʿAli after the Prophet's death; the traditions assess this period differently, and the archive names it by its rulers." },
  { id: 'epoch:caliphate-abu-bakr', parent: 'epoch:first-four-caliphs', name: 'Caliphate of Abu Bakr', start: 11, end: 13,
    overview: "Abu Bakr's caliphate at Medina, from the Prophet's death to his own death in 13." },
  { id: 'epoch:caliphate-umar', parent: 'epoch:first-four-caliphs', name: 'Caliphate of ʿUmar b. al-Khattab', start: 13, end: 23,
    overview: "ʿUmar's caliphate at Medina, the period of the first conquests in Iraq, Syria and Egypt, to his death in 23." },
  { id: 'epoch:caliphate-uthman', parent: 'epoch:first-four-caliphs', name: 'Caliphate of ʿUthman b. ʿAffan', start: 23, start_latest: 24, end: 35,
    boundary_note: 'ʿUmar died at the end of 23; the oath to ʿUthman is dated to the last days of 23 or to Muharram 24.',
    overview: "ʿUthman's caliphate at Medina, to his killing in 35." },
  { id: 'epoch:caliphate-ali', parent: 'epoch:first-four-caliphs', name: 'Caliphate of ʿAli b. Abi Talib', start: 35, end: 40,
    overview: "ʿAli's caliphate, mostly from Kufa, the period of the battles of the Camel and Siffin, to his killing in 40." },

  { id: 'epoch:umayyad', name: 'Umayyad caliphate', name_arabic: 'الدولة الأموية', start: 41, end: 132,
    overview: "Caliphate of the Umayyad family, ruling from Damascus, from Muʿawiya b. Abi Sufyan's accession to the Abbasid revolution." },
  { id: 'epoch:umayyad-sufyanid', parent: 'epoch:umayyad', name: 'Umayyad caliphate: Sufyanid line', start: 41, end: 64,
    overview: 'Muʿawiya b. Abi Sufyan, Yazid b. Muʿawiya and Muʿawiya b. Yazid.' },
  { id: 'epoch:umayyad-marwanid', parent: 'epoch:umayyad', name: 'Umayyad caliphate: Marwanid line', start: 64, end: 132,
    overview: 'From Marwan b. al-Hakam to Marwan b. Muhammad, the last Umayyad caliph in Damascus.' },

  { id: 'epoch:abbasid', name: 'Abbasid caliphate, to the fall of Baghdad', name_arabic: 'الدولة العباسية', start: 132, end: 656,
    overview: 'Caliphate of the Abbasid family, from the revolution of 132 to the Mongol capture of Baghdad in 656.' },
  { id: 'epoch:abbasid-first-period', parent: 'epoch:abbasid', name: 'First Abbasid period', start: 132, end: 232, end_latest: 247,
    alternate_names: [{ name: 'al-ʿAsr al-ʿAbbasi al-awwal', name_arabic: 'العصر العباسي الأول', used_by: 'historians' }],
    boundary_note: "Historians end it with al-Mutawakkil's accession (232) or with his death (247).",
    overview: 'The caliphs ruled directly, from Baghdad and later Samarra.' },
  { id: 'epoch:abbasid-second-period', parent: 'epoch:abbasid', name: 'Second Abbasid period', start: 232, start_latest: 247, end: 334,
    alternate_names: [{ name: 'al-ʿAsr al-ʿAbbasi al-thani', name_arabic: 'العصر العباسي الثاني', used_by: 'historians' }],
    boundary_note: "Its start is dated to al-Mutawakkil's accession (232) or his death (247).",
    overview: 'Military commanders, many of them Turkish, held much of the power at Samarra and Baghdad, until the Buyids entered Baghdad in 334.' },
  { id: 'epoch:abbasid-buyid', parent: 'epoch:abbasid', name: 'Abbasid caliphate under the Buyids', start: 334, end: 447,
    overview: 'The Buyid amirs, a Daylami family, held power in Baghdad from 334 to the Seljuk entry in 447.' },
  { id: 'epoch:abbasid-seljuk', parent: 'epoch:abbasid', name: 'Abbasid caliphate under the Seljuks', start: 447, end: 552, end_latest: 590,
    boundary_note: "The Seljuk hold on Baghdad weakened after Sultan Sanjar's death (552); the last Seljuk sultan of Iraq died in 590.",
    overview: 'The Seljuk sultans held power in Baghdad from their entry in 447.' },

  // Imami reckoning
  { id: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: "Period of the Imams' presence (Imami reckoning)", start: 11, end: 260,
    alternate_names: [{ name: 'ʿAsr al-hudur', name_arabic: 'عصر الحضور', used_by: 'Imami' }],
    overview: "In Imami reckoning, from the Prophet's death to the death of the eleventh Imam (260), when the Imams lived among their followers; Imami rijal works often place a narrator by the Imam he transmitted from." },
  { id: 'epoch:imami-imamate-ali', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of ʿAli b. Abi Talib (Imami reckoning)', start: 11, end: 40,
    overview: "In Imami reckoning, ʿAli's imamate runs from the Prophet's death to his own death in 40." },
  { id: 'epoch:imami-imamate-hasan', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of al-Hasan b. ʿAli (Imami reckoning)', start: 40, end: 49, end_latest: 50,
    boundary_note: 'His death is reported in 49 or 50.', overview: "The imamate of al-Hasan b. ʿAli, from his father's death to his own." },
  { id: 'epoch:imami-imamate-husayn', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of al-Husayn b. ʿAli (Imami reckoning)', start: 49, start_latest: 50, end: 61,
    boundary_note: "Begins at al-Hasan's death, reported in 49 or 50.", overview: 'The imamate of al-Husayn b. ʿAli, to his killing at Karbala in 61.' },
  { id: 'epoch:imami-imamate-sajjad', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of ʿAli b. al-Husayn (Imami reckoning)', start: 61, end: 94, end_latest: 95,
    alternate_names: [{ name: 'Zayn al-ʿAbidin, al-Sajjad', used_by: 'Imami' }],
    boundary_note: 'His death is reported in 94 or 95.', overview: 'The imamate of ʿAli b. al-Husayn, from Karbala to his death at Medina.' },
  { id: 'epoch:imami-imamate-baqir', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of Muhammad b. ʿAli al-Baqir (Imami reckoning)', start: 94, start_latest: 95, end: 114, end_latest: 117,
    boundary_note: "Begins at his father's death (94 or 95); his own death is reported between 114 and 117.", overview: 'The imamate of Muhammad al-Baqir at Medina.' },
  { id: 'epoch:imami-imamate-sadiq', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of Jaʿfar b. Muhammad al-Sadiq (Imami reckoning)', start: 114, start_latest: 117, end: 148,
    boundary_note: "Begins at his father's death, reported between 114 and 117.", overview: 'The imamate of Jaʿfar al-Sadiq at Medina, the period from which the largest number of Imami reports is transmitted.' },
  { id: 'epoch:imami-imamate-kazim', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of Musa b. Jaʿfar al-Kazim (Imami reckoning)', start: 148, end: 183,
    overview: 'The imamate of Musa al-Kazim, to his death in Baghdad in 183.' },
  { id: 'epoch:imami-imamate-rida', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of ʿAli b. Musa al-Rida (Imami reckoning)', start: 183, end: 203,
    overview: 'The imamate of ʿAli al-Rida, to his death in Khurasan in 203.' },
  { id: 'epoch:imami-imamate-jawad', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of Muhammad b. ʿAli al-Jawad (Imami reckoning)', start: 203, end: 220,
    overview: 'The imamate of Muhammad al-Jawad, to his death in Baghdad in 220.' },
  { id: 'epoch:imami-imamate-hadi', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of ʿAli b. Muhammad al-Hadi (Imami reckoning)', start: 220, end: 254,
    overview: 'The imamate of ʿAli al-Hadi, mostly at Samarra, to his death in 254.' },
  { id: 'epoch:imami-imamate-askari', parent: 'epoch:imami-presence-of-the-imams', tradition: 'Imami', name: 'Imamate of al-Hasan b. ʿAli al-ʿAskari (Imami reckoning)', start: 254, end: 260,
    overview: 'The imamate of al-Hasan al-ʿAskari at Samarra, to his death in 260.' },
  { id: 'epoch:imami-lesser-occultation', tradition: 'Imami', name: 'Lesser Occultation (Imami reckoning)', start: 260, end: 329,
    alternate_names: [{ name: 'al-Ghayba al-sughra', name_arabic: 'الغيبة الصغرى', used_by: 'Imami' }],
    overview: 'In Imami belief, the twelfth Imam was hidden and reached his followers through four successive deputies; the period ends with the death of the fourth, ʿAli b. Muhammad al-Samuri, in 329.' },
  { id: 'epoch:imami-greater-occultation', tradition: 'Imami', name: 'Greater Occultation (Imami reckoning)', start: 329, end: null,
    alternate_names: [{ name: 'al-Ghayba al-kubra', name_arabic: 'الغيبة الكبرى', used_by: 'Imami' }],
    overview: 'In Imami belief, the occultation that continues from 329 with no designated deputy.' },

  // Zaydi reckoning
  { id: 'epoch:zaydi-early-imams', tradition: 'Zaydi', name: 'Early Zaydi risings and imams (Zaydi reckoning)', start: 121, start_latest: 122, end: 250,
    boundary_note: "Zayd b. ʿAli's rising at Kufa is dated 121 or 122.",
    overview: "In Zaydi reckoning, from Zayd b. ʿAli's rising at Kufa to the first Zaydi state, a period of Alid risings such as those of Yahya b. Zayd (d. 125) and Muhammad b. ʿAbd Allah al-Nafs al-Zakiyya (d. 145)." },
  { id: 'epoch:zaydi-caspian-state', tradition: 'Zaydi', name: 'Zaydi state in Tabaristan and Daylam', start: 250, end: 316,
    boundary_note: '316 ends the state founded in 250; Zaydi imams continued intermittently in the Caspian region afterwards.',
    overview: 'The Zaydi state founded by al-Hasan b. Zayd south of the Caspian Sea.' },
  { id: 'epoch:zaydi-imamate-yemen', tradition: 'Zaydi', name: 'Zaydi imamate in Yemen', start: 284, end: 1382,
    overview: 'From the arrival of al-Hadi ila al-Haqq Yahya b. al-Husayn in Yemen (284) to the end of the imamate in 1382 (1962 CE).' },

  // Ibadi reckoning
  { id: 'epoch:ibadi-imamate-hadramawt', tradition: 'Ibadi', name: 'Ibadi imamate in Hadramawt and Yemen', start: 129, end: 130,
    alternate_names: [{ name: 'Imamate of Talib al-Haqq', used_by: 'Ibadi' }],
    overview: 'The imamate of ʿAbd Allah b. Yahya al-Kindi, proclaimed in Hadramawt in 129; he was killed in 130.' },
  { id: 'epoch:ibadi-first-imamate-oman', tradition: 'Ibadi', name: 'First Ibadi imamate in Oman', start: 131, start_latest: 132, end: 134,
    boundary_note: 'The election of al-Julanda b. Masʿud is dated 131 or 132.',
    overview: 'The imamate of al-Julanda b. Masʿud, ended by an Abbasid campaign in 134.' },
  { id: 'epoch:ibadi-imamate-tripolitania', tradition: 'Ibadi', name: 'Ibadi imamate of Abu al-Khattab in Tripolitania', start: 140, end: 144,
    overview: 'The imamate of Abu al-Khattab ʿAbd al-Aʿla b. al-Samh al-Maʿafiri, which held Tripoli and Qayrawan until his death in battle in 144.' },
  { id: 'epoch:ibadi-rustamid-imamate', tradition: 'Ibadi', name: 'Rustamid imamate at Tahert', start: 160, start_latest: 162, end: 296,
    boundary_note: 'Its founding under ʿAbd al-Rahman b. Rustam is dated between 160 and 162.',
    overview: 'The Ibadi imamate of the Rustamid family at Tahert in the central Maghrib, ended in 296.' },
  { id: 'epoch:ibadi-second-imamate-oman', tradition: 'Ibadi', name: 'Second Ibadi imamate in Oman', start: 177, start_latest: 179, end: 280,
    boundary_note: 'Counted from the election of Muhammad b. Abi ʿAffan (177) or of al-Warith b. Kaʿb (179).',
    overview: 'Ibadi imams elected in Oman until an Abbasid campaign in 280.' },
];

const LOCATION_IDS = new Map(LEGACY_LOCATIONS.map((location) => [location.name, stableSeedId('location', location.name)]));

export function locationSeedRows(): SeedRow[] {
  return LEGACY_LOCATIONS.map((location) => ({
    id: LOCATION_IDS.get(location.name)!,
    content: { ...location } as SeedContent,
  }));
}

/** Events with the location link only where the legacy name equals a seeded location; never a guessed mapping. */
export function eventSeedRows(): { rows: SeedRow[]; unlinked: Array<{ id: string; title: string; location_name: string }>; corrected: string[] } {
  const unlinked: Array<{ id: string; title: string; location_name: string }> = [];
  const corrected: string[] = [];
  const rows = LEGACY_EVENTS.map((event) => {
    const id = stableSeedId('historical-event', event.title, event.year_hijri);
    const locationId = LOCATION_IDS.get(event.location_name) ?? null;
    if (!locationId) unlinked.push({ id, title: event.title, location_name: event.location_name });
    const correction = START_YEAR_CORRECTIONS[event.title];
    if (correction) corrected.push(`${event.title}: ${correction.reason}`);
    return {
      id,
      content: {
        title: event.title,
        title_arabic: event.title_arabic,
        description: event.description,
        significance: event.significance,
        start_year_hijri: correction?.start_year_hijri ?? event.year_hijri,
        end_year_hijri: event.end_year_hijri ?? null,
        start_year_gregorian: event.year_gregorian,
        end_year_gregorian: event.end_year_gregorian ?? null,
        category: event.category,
        location_name: event.location_name,
        location_id: locationId,
      },
    };
  });
  return { rows, unlinked, corrected };
}

export function epochSeedRows(): SeedRow[] {
  return EPOCHS.map((epoch) => ({
    id: epoch.id,
    content: {
      name: epoch.name,
      name_arabic: epoch.name_arabic ?? null,
      alternate_names: epoch.alternate_names ?? [],
      parent_epoch_id: epoch.parent ?? null,
      tradition_context: epoch.tradition ?? null,
      start_year_hijri: epoch.start,
      start_year_hijri_latest: epoch.start_latest ?? null,
      end_year_hijri: epoch.end,
      end_year_hijri_latest: epoch.end_latest ?? null,
      boundary_note: epoch.boundary_note ?? null,
      overview: epoch.overview,
    },
  }));
}

function summarize(label: string, outcome: SeedOutcome): string {
  const kept = outcome.keptCurated.map((row) => `\n    kept ${row.id}: ${row.reason}`).join('');
  return `${label}: ${outcome.created.length} created, ${outcome.refreshed.length} refreshed, ${outcome.unchanged.length} unchanged, ${outcome.keptCurated.length} left as curated${kept}`;
}

/** Writes all three tables (epochs only when the table exists). Returns the outcomes for callers and tests. */
export async function seedHistory(actor = SEED_ACTOR): Promise<{ locations: SeedOutcome; events: SeedOutcome; epochs: SeedOutcome | null }> {
  const { seedHistoryRows } = await import('../../db/queries/history-seed');
  const { epochsAvailable } = await import('../../db/queries/timeline');
  const locations = await seedHistoryRows(actor, 'locations', locationSeedRows());
  const events = await seedHistoryRows(actor, 'historical_events', eventSeedRows().rows);
  const epochs = (await epochsAvailable()) ? await seedHistoryRows(actor, 'epochs', epochSeedRows()) : null;
  return { locations, events, epochs };
}

async function main() {
  loadEnvironment({ path: path.resolve(process.cwd(), '.env.local'), quiet: true });
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error('DATABASE_URL is not set.');
  if ((process.env.DATABASE_URL_PRODUCTION && url === process.env.DATABASE_URL_PRODUCTION) || new URL(url).pathname === '/railway') {
    throw new Error('DATABASE_URL points at the production database; the seed is not run against production from here.');
  }
  const events = eventSeedRows();
  console.log(`Plan: ${LEGACY_LOCATIONS.length} locations, ${events.rows.length} events, ${EPOCHS.length} epochs (all unverified seed).`);
  console.log('Events loaded without a location link (no seeded location has that name; not guessed):');
  for (const row of events.unlinked) console.log(`  ${row.id}  "${row.title}" -> "${row.location_name}"`);
  for (const line of events.corrected) console.log(`Start year corrected from the row's own text: ${line}`);
  if (process.argv.includes('--dry-run')) return;

  const { getDatabase } = await import('../../db/client');
  try {
    const outcome = await seedHistory();
    console.log(summarize('locations', outcome.locations));
    console.log(summarize('historical_events', outcome.events));
    console.log(outcome.epochs ? summarize('epochs', outcome.epochs)
      : 'epochs: skipped, the epochs table is not in this database yet (src/db/ops/pending/epochs.pending.sql).');
  } finally {
    await getDatabase().$client.end({ timeout: 5 });
  }
}

if (/seed-history\.ts$/.test(process.argv[1] ?? '')) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
