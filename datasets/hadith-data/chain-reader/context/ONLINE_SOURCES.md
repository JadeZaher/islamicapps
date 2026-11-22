---
type: reference
---
# Online sources for the text and metadata check

For the text and metadata checker only (`prompt-v2-text.md`), never for chain readers (they stay offline and independent). Everything
below comes from what the project's audits recorded (`datasets/hadith-data/chain-audit/{sunni,imami,round2,round3,ibadi-zaydi}/README.md`);
nothing here was re-tested. The builder does not fetch anything: each packet carries lookup keys in `context.text_and_metadata.lookup`.

## Rules for every request

1. Send only public references or public Arabic text: a collection and number, a printed-edition volume and page, an Arabic opening or matn phrase of 6-8 words.
   Never the packet id, a report id, a work name taken from our database, anything about this project, its owner, its database, the review
   pipeline or the fact that a check is running. Use a generic client name (no contact details).
2. Save each fetched page next to the answer with its URL, UTC time and the intent, as the audits did (`fetched/`).
3. Respect limits: stop on HTTP 429 and honour Retry-After; no bypass of Cloudflare or login walls (403 sources are not retried).
4. An online claim in an output carries the URL (or edition, volume, page) and an exact quote from the page. A checker that could not fetch writes `not_checked` with the reason.

## What worked, by tradition and work

| tradition / work | source and address | verifies | limits (from the audits) | key in the packet |
|---|---|---|---|---|
| Sunni: Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasa'i, Ibn Majah | **api.turath.io** `GET https://api.turath.io/search?q=<Arabic words>&ver=3[&page=n]`, then the printed page text of the hit (Risala, Arnaut, Abd al-Baqi, Sultaniyya, Bashar editions) | wording of the text; printed edition, volume, page; the isnad as printed | worked for all nine Sunni collections; **HTTP 429 after about 230 requests, Retry-After about 1,800 s**; accept a hit only if at least 65% of the first 60 words occur in the aligned page slice | `matn_phrase_ar`, `opening_words_ar` |
| same six | **hadith-api on jsDelivr** `https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/<ara-collection>/<number>.json` | Arabic wording by collection and number; its own numbering | worked in the audit for these six; text lineage is sunnah.com, so it is independent of our parsing but **not of our text**; numbering is the edition's own, check against the matn | `hadith_api` |
| Sunni: Ahmad, Darimi, Muwatta | **api.turath.io** as above (Musnad Ahmad Risala ed., Darimi, Muwatta Yahya) | wording, volume, page, the printed isnad (our text is the matn only; the chain field is separate) | same 429 limit; search by the matn phrase | `matn_phrase_ar` |
| Sunni: sunnah.com, dorar.net | -- | -- | **HTTP 403 (Cloudflare challenge) to automated reading; not used** | `sunnah_com_blocked` is the reference only, for a human |
| Imami: all Thaqalayn works | **Thaqalayn public API** `https://www.thaqalayn-api.net/api/v2/<bookId>` (the audit wrote `thaqalayn-api.net/api/v2/<bookId>`) | Arabic and English text, chapter, volume, URL, gradings (Muhsini, al-Behbudi, al-Majlisi), `thaqalaynSanad` | no rate limit seen; it is **our own source**, so it checks our loading, not the original; `thaqalayn.net/hadith/...` pages returned 404 to a non-browser client | `thaqalayn_api` (bookId, id) |
| Imami: Kafi and others | **Noor Hadith** `https://hadith.inoor.ir/service/api` : `elastic/v2/ElasticHadithList` (POST, search by opening words), `hadith/HadithRejalList/v2?hadithId=<id>` (GET) | wording, the site's structured sanad list (one entry per sub-chain, compiler as order 0) | the search endpoint is **rate limited (429, Retry-After about 1.9 h after roughly 100 requests)**; the GET was not limited; a hit whose text differs from ours was discarded as a mismatch | `opening_words_ar` |
| Imami: others | al-islam.org (403), shiaonlinelibrary.com (DNS failure), ar.wikishia.net (timeout), lib.eshia.ir (reachable, no per-report structured chain) | -- | not usable | -- |
| Ibadi: al-Rabi' | **OpenITI GitHub raw** `0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1` (and `pre-clean` branch) | the written text; **same transcription as ours, so not independent** | worked; ar.wikipedia «مسند الربيع بن حبيب» and «أبو عبيدة مسلم بن أبي كريمة» worked for chain shape | `openiti` |
| Ibadi, Zaydi | api.turath.io, shamela.ws, archive.org, ketabonline, al-maktaba, alukah | a second text | **did not work**: none of the three works is indexed; others timed out, 403 or no host | -- |
| Zaydi: Musnad Zayd | OpenITI raw `0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1` (and the recension files held locally) | the written text; not independent | worked | `openiti` |
| Imami: Sahifat al-Rida | OpenITI `0225AH` Sahifat al-Rida: `Zaydiyya0000121-ara1.completed` (al-Tabarsi route) and `Masaha001003-ara1` | independent recensions of the Sahifa; Imam chain | worked; 55 of 76 sampled reports located | `openiti` |

## How the checker should use them

- Text wording: the two cheapest independent checks are Turath (printed page) for the Sunni works and the local hadith-kg / Riwayat copies already in the packet; for Thaqalayn works the API only re-checks our loading.
- Numbering and chapter: printed-edition numbering differs from sunnah.com numbering (Muslim 2945 in our data is 2097 in hadith-kg's edition). A different number is a lead; settle it with the printed page (Turath gives volume and page) before filing `wrong_number`.
- Gradings: only Thaqalayn's API and the local `hadith_assessments` carry graders and sources; no online source was found that works for Sunni gradings (sunnah.com and dorar are blocked).
- Budget: about 1 request per report for Turath; 284 pilot reports stay under the observed 429 threshold only if split over runs. Plan for Retry-After.
