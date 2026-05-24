# Scholarly Metadata Layer — Implementation Plan

## Phase 1: Source Identification & Data Acquisition (2 tasks)

### Task 1.1: Identify grading sources already in the data
- The Shia Imami grades (33K hadiths) come from al-Khoei's Mu'jam
- Parse: which scholar's grading system do the existing grades represent?
- Map display_grade values to their scholarly source

### Task 1.2: Identify external grading databases
- Sunni: Darussalam grading of Kutub al-Sittah (available in sunnah.com data)
- Shia: al-Khoei's Mu'jam, al-Majlisi's Bihar al-Anwar gradings
- Ibadi: gradings in Musnad al-Rabi' are from the compilers
- Zaydi: Musnad Zayd has inline scholarly commentary

## Phase 2: ScholarVerdict Population (3 tasks)

### Task 2.1: Create Scholar nodes for major grading authorities
- Script: `src/scripts/seed-scholars.ts`
- Sunni: al-Bukhari, Muslim, al-Albani, Ibn Hajar, al-Dhahabi, al-Tirmidhi
- Shia: al-Khoei, al-Majlisi, al-Kulayni, al-Tusi, al-Saduq
- Zaydi: Imam Zayd ibn Ali
- Ibadi: al-Rabi' ibn Habib
- Properties: name_arabic, name_english, death_year_hijri, tradition, authority_rank, specialization

### Task 2.2: Extract ScholarVerdicts from Shia corpus
- The 33K Shia hadiths have grades from al-Khoei in display_grade
- Script: create ScholarVerdict nodes linking al-Khoei -> each graded hadith
- Properties: ruling (the grade), source_work ('Mu'jam Rijal al-Hadith'), tradition

### Task 2.3: Extract ScholarVerdicts from Sunni corpus
- Sahih Bukhari/Muslim: implicit sahih verdict from inclusion
- Create: ScholarVerdict(scholar=Bukhari, hadith=X, ruling='sahih', source_work='al-Jami al-Sahih')
- For other Sunni collections: use available grading metadata

## Phase 3: Commentary Node Population (2 tasks)

### Task 3.1: Identify commentary references in existing data
- Some hadiths may reference sharh works in their text
- Map known sharh works to their hadiths

### Task 3.2: Create Commentary seed data
- Link major sharh works to their hadith collections:
  - Fath al-Bari (Ibn Hajar) -> Sahih Bukhari
  - Sharh al-Nawawi -> Sahih Muslim
  - Mir'at al-'Uqul (al-Majlisi) -> al-Kafi
- Properties: source_work, author, tradition

## Phase 4: Practice & SchoolOfThought Linking (2 tasks)

### Task 4.1: Link hadiths to fiqh practices
- Use MotifTag nodes (47 exist) as a starting point
- Create Practice nodes for major fiqh categories: prayer, fasting, zakat, hajj, marriage, trade
- Link hadiths to practices based on chapter/topic metadata

### Task 4.2: Link practices to schools of thought
- Use existing SchoolOfThought nodes (9 exist)
- Create relationships: Practice -> INTERPRETED_BY -> SchoolOfThought

## Phase 5: Verification (1 task)

### Task 5.1: Verify scholarly layer
- Re-run data readiness audit scholarly section
- Verify: Scholar count >10, ScholarVerdict count >30K, Commentary count >5
- Spot-check: pick 10 random hadiths, verify ScholarVerdict matches display_grade
