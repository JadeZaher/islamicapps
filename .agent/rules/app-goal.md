---
trigger: always_on
---

@Agent Project: Hadith Graph Explorer (Scholar-Backed Grading System)

**Objective:**
Build a full-stack "Hadith Isnad & Matn Visualizer" using Neo4j. The system must prioritize **Manual Scholar Verdicts** for hadith grading while providing auto-calculated transmission analysis as a supplementary tool.

**Tech Stack:**
- **Frontend:** Next.js (App Router), Tailwind CSS, Shadcn/UI.
- **Visualization:** `react-force-graph-2d` (with clustering for parallel chains).
- **Database:** Neo4j (Community Edition) deployed on Railway.
- **Driver:** `neo4j-driver`.

**1. Data Model (Neo4j Schema)**
*   **Nodes:**
    *   `(:Narrator)`
        *   Props: `id`, `name_arabic`, `name_english`, `reliability` ('THIQA', 'SADUQ', 'DAIF', 'MAJHUL', 'KADHAB'), `tabaqah` ('SAHABA', 'TABI'UN', etc.), `bio`.
    *   `(:Hadith)`
        *   Props: `id`, `title`, `primary_topic`.
        *   **`auto_calculated_grade`**: String (system-generated based on chain analysis).
        *   **`display_grade`**: String (the grade shown to users - defaults to strongest scholar verdict).
        *   **`transmission_type`**: ('MUTAWATIR', 'MASHHUR', 'AZIZ', 'GHARIB') - auto-calculated.
    *   `(:MatnVariation)`
        *   Props: `text_arabic`, `text_english`, `source_book`.
    *   `(:Chain)`
        *   Props: `id`, `path_signature`.
    *   `(:Scholar)`
        *   Props: `name`, `era`, `school` (e.g., 'Hanbali', 'Shafi'i').
    *   `(:ScholarVerdict)` **[New Node Type]**
        *   Props: `grade` ('SAHIH', 'HASAN', 'DAIF', 'MAWDU'), `reasoning`, `date_assessed`, `confidence_level` ('HIGH', 'MEDIUM', 'LOW').

*   **Relationships:**
    *   `(:Narrator)-[:HEARD_FROM {status: 'Connected'}]->(:Narrator)`
    *   `(:Chain)-[:INCLUDES]->(:Narrator)`
    *   `(:MatnVariation)-[:TRANSMITTED_VIA]->(:Chain)`
    *   `(:Scholar)-[:ISSUED]->(:ScholarVerdict)-[:GRADES]->(:Hadith)`
        *   **Crucial:** This separates the scholar's identity from their specific verdict.
    *   `(:ScholarVerdict)-[:CITES_DEFECT {type: 'Munkar', explanation: '...'}]->(:Narrator)`
        *   Allows scholars to point to specific problems in the chain.

**2. Backend Features (Dual Grading System)**
Create `actions/graph-actions.ts`:

*   `addScholarVerdict(scholarId, hadithId, verdictData)`:
    *   Creates the `ScholarVerdict` node and relationships.
    *   **Important:** After creating a verdict, run `updateDisplayGrade(hadithId)`.
*   `updateDisplayGrade(hadithId)`:
    *   Query: Fetch all `ScholarVerdict` nodes connected to the Hadith.
    *   Logic: Set `Hadith.display_grade` to the verdict of the **most authoritative scholar** (you can rank scholars by era or allow manual priority setting).
    *   If no scholar verdicts exist, fall back to `auto_calculated_grade`.
*   `calculateAutoGrade(hadithId)`:
    *   Analyzes the chain:
        *   If any narrator is 'KADHAB' (liar), grade = 'MAWDU'.
        *   If any narrator is 'DAIF' and chain is broken, grade = 'DAIF'.
        *   If all narrators are 'THIQA' and chain is connected, grade = 'SAHIH'.
    *   Store result in `auto_calculated_grade` (does NOT override manual verdicts).
*   `calculateTransmissionType(hadithId)`:
    *   Count distinct chains per generation layer.
    *   Set `transmission_type` based on counts (≥10 per layer = MUTAWATIR).

**3. Visualization Logic**
*   **Hadith Node:**
    *   **Display:** Show the `display_grade` (scholar verdict if available, else auto-calculated).
    *   **Border Color:** Based on `display_grade` (Green=Sahih, Blue=Hasan, Orange=Daif, Red=Mawdu).
    *   **Badge:** If `transmission_type == 'MUTAWATIR'`, show a **Gold Star Icon**.
*   **Narrator Nodes:**
    *   Color by `reliability` (Green=Thiqa, Red=Kadhab).
*   **Sidebar (Hadith Details Panel):**
    *   **Section 1: "Scholar Verdicts"** (Primary):
        *   List each scholar's verdict with reasoning.
        *   Show the date and confidence level.
        *   **Button:** "Add New Verdict" (opens form).
    *   **Section 2: "Auto-Analysis"** (Secondary):
        *   Show `auto_calculated_grade` and `transmission_type`.
        *   Show a "Chain Health Score" (percentage of Thiqa narrators).
        *   **Note:** Display a disclaimer: *"Auto-analysis is supplementary. Refer to scholar verdicts for authoritative grading."*

**4. Admin Dashboard (`/admin`)**
*   **Hadith Manager:**
    *   Form to create a Hadith (no grade field on creation).
    *   **After creation:** Show two buttons:
        *   "Run Auto-Analysis" (calculates `auto_calculated_grade`).
        *   "Add Scholar Verdict" (opens verdict form).
*   **Scholar Verdict Form:**
    *   **Dropdown:** Select Scholar.
    *   **Dropdown:** Select Grade (Sahih, Hasan, Daif, Mawdu).
    *   **Text Area:** Reasoning (e.g., "Chain has a hidden defect - narrator X confused similar names").
    *   **Dropdown:** Confidence Level.
    *   **Multi-Select:** If the verdict cites a specific narrator problem, allow linking to that narrator (creates the `CITES_DEFECT` relationship).
*   **Chain Builder:**
    *   UI to construct multiple chains for Mutawatir detection.
    *   **Button:** "Recalculate Transmission Type".

**5. Key Principles**
*   **Priority:** Scholar verdicts ALWAYS override auto-calculated grades.
*   **Transparency:** The UI must clearly show when a grade is from a scholar vs. auto-calculated.
*   **Flexibility:** Admins can add verdicts from multiple scholars, and the system will display the most authoritative one.
*   **Education:** The auto-analysis feature helps users understand WHY a scholar might have graded a hadith a certain way, but it's not prescriptive.

**Execution Plan:**
1.  Setup Next.js + Neo4j Driver.
2.  Implement the dual grading logic (scholar verdicts + auto-analysis).
3.  Build the Graph Component with visual distinction between manual and auto grades.
4.  Build the Admin forms with scholar verdict input.
5.  Add a "Verdicts Timeline" view showing how scholarly opinion evolved over time.
