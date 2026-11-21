"""OpenITI text access for the history lane: markup-free text with an offset map, folded search, verbatim passages with
page locators and the enclosing section heading. Reads files as text only. See README.md §Method.
"""
import bisect
import hashlib
import re
from array import array
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXTERNAL = REPO_ROOT / 'datasets' / 'sources' / 'external'

# Work key -> (directory, file, title, title_ar, author, author death AH, tradition of the author as the work presents it)
WORKS = {
    'taqrib': ('openiti-0852IbnHajar.TaqribTahdhib', '0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.completed',
               'Taqrib al-Tahdhib', 'تقريب التهذيب', 'Ibn Hajar al-Asqalani', 852, 'Sunni'),
    'mizzi': ('openiti-0742Mizzi.TahdhibKamal', '0742Mizzi.TahdhibKamal.Shamela0003722-ara1.mARkdown',
              'Tahdhib al-Kamal fi Asma al-Rijal', 'تهذيب الكمال في أسماء الرجال', 'al-Mizzi', 742, 'Sunni'),
    'najashi': ('openiti-0450Najashi.Rijal', '0450Najashi.Rijal.Shia002931-ara1.mARkdown',
                'Rijal al-Najashi', 'رجال النجاشي', 'al-Najashi', 450, 'Imami'),
    'tusi_rijal': ('openiti-0460ShaykhTusi.Rijal', '0460ShaykhTusi.Rijal.Shia002935-ara1.mARkdown',
                   'Rijal al-Tusi', 'رجال الطوسي', 'al-Shaykh al-Tusi', 460, 'Imami'),
    'tusi_fihrist': ('openiti-0460ShaykhTusi.Fihrist', '0460ShaykhTusi.Fihrist.Shia002934-ara1.mARkdown',
                     'al-Fihrist', 'الفهرست', 'al-Shaykh al-Tusi', 460, 'Imami'),
    'khalifa': ('openiti-0240KhalifaIbnKhayyat.Tarikh', '0240IbnKhayyatCusfuri.Tarikh.JK000412-ara1.completed',
                'Tarikh Khalifa b. Khayyat', 'تاريخ خليفة بن خياط', 'Khalifa b. Khayyat al-Usfuri', 240, 'Sunni'),
    'tabari': ('openiti-0310Tabari.Tarikh', '0310Tabari.Tarikh.Shamela0009783BK1-ara1.mARkdown',
               'Tarikh al-Rusul wa-al-Muluk', 'تاريخ الرسل والملوك', 'al-Tabari', 310, 'Sunni'),
    'suyuti_khulafa': ('openiti-0911Suyuti.TarikhKhulafa', '0911Suyuti.TarikhKhulafa.Shamela0011997-ara1.completed',
                       'Tarikh al-Khulafa', 'تاريخ الخلفاء', 'al-Suyuti', 911, 'Sunni'),
    'suyuti_huffaz': ('openiti-0911Suyuti.TabaqatHuffaz', '0911Suyuti.TabaqatHuffaz.JK000753-ara1.mARkdown',
                      'Tabaqat al-Huffaz', 'طبقات الحفاظ', 'al-Suyuti', 911, 'Sunni'),
    'mufid_irshad': ('openiti-0413ShaykhMufid.Irshad', '0413ShaykhMufid.Irshad.Shia001294Vols-ara1',
                     'al-Irshad fi Marifat Hujaj Allah ala al-Ibad', 'الإرشاد في معرفة حجج الله على العباد',
                     'al-Shaykh al-Mufid', 413, 'Imami'),
    'tusi_ghayba': ('openiti-0460ShaykhTusi.Ghayba', '0460ShaykhTusi.Ghayba.Zaydiyya0000283-ara1',
                    'Kitab al-Ghayba', 'كتاب الغيبة', 'al-Shaykh al-Tusi', 460, 'Imami'),
    'ifada': ('openiti-0424AbuTalibHaruni.IfadaFiTarikhAimma', '0424AbuTalibYahyaHaruni.IfadaFiTarikhAimma.Zaydiyya0000088-ara1',
              'al-Ifada fi Tarikh al-Aimma al-Sada', 'الإفادة في تاريخ الأئمة السادة', 'Abu Talib Yahya b. al-Husayn al-Haruni',
              424, 'Zaydi'),
    'masabih': ('openiti-0353AbuCabbasHasani.Masabih', '0353AbuCabbasHasani.Masabih.Zaydiyya0000087BK1-ara1.completed',
                'al-Masabih', 'المصابيح', 'Abu al-Abbas Ahmad b. Ibrahim al-Hasani', 353, 'Zaydi'),
    'maqatil': ('openiti-0362AbuFarajIsbahani.MaqatilTalibiyyin', '0362AbuFarajIsbahani.MaqatilTalibiyyin.Shamela0012404-ara1.completed',
                'Maqatil al-Talibiyyin', 'مقاتل الطالبيين', 'Abu al-Faraj al-Isfahani', 356, None),
    'darjini': ('openiti-0670AhmadDarjini.TabaqatMashayikh', '0670AhmadDarjini.TabaqatMashayikhBiMaghrib.ShamIbadiyya0000107-ara1',
                'Tabaqat al-Mashayikh bi-al-Maghrib', 'طبقات المشايخ بالمغرب', 'Abu al-Abbas Ahmad al-Darjini', 670, 'Ibadi'),
    'shammakhi': ('openiti-0928Shammakhi.Siyar', '0928AbuCabbasShammakhi.Siyar.ShamIbadiyya0000115-ara1.mARkdown',
                  'Kitab al-Siyar', 'كتاب السير', 'Abu al-Abbas Ahmad al-Shammakhi', 928, 'Ibadi'),
    'salimi': ('openiti-1332Salimi.TuhfatAcyan', '1332NurDinSalimi.TuhfatAcyan.ShamIbadiyya0000281-ara1',
               'Tuhfat al-Ayan bi-Sirat Ahl Uman', 'تحفة الأعيان بسيرة أهل عمان', 'Nur al-Din al-Salimi', 1332, 'Ibadi'),
}

_HARAKAT = re.compile('[ً-ٰٟـۖ-ۭ]')
_FOLD = str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ة': 'ه', 'ؤ': 'و', 'ئ': 'ي', 'ی': 'ي', 'ک': 'ك'})
_MARKUP = re.compile(r'PageV\d+P\d+[a-z]?|\bms\d+\b|~~|#META#[^\n]*|^#+ ?\|? ?|\$+ |@[A-Z]+\S*|\| ?', re.M)
_PAGE = re.compile(r'PageV(\d+)P(\d+)')
_HEADING = re.compile(r'^### ?(\|*) ?(.*)$', re.M)


def fold(text: str) -> str:
    """Letter fold used for searching only: vowel marks and tatweel removed, alef/ya/ta marbuta/hamza seats unified."""
    return _HARAKAT.sub('', text).translate(_FOLD)


def work_path(key: str) -> Path:
    directory, name = WORKS[key][0], WORKS[key][1]
    return EXTERNAL / directory / name


def openiti_uri(key: str) -> str:
    return re.sub(r'\.(completed|mARkdown|inProgress)$', '', WORKS[key][1])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def header(key: str) -> dict:
    """OpenITI `#META#` fields."""
    fields = {}
    with open(work_path(key), encoding='utf-8') as handle:
        for line in handle:
            if line.startswith('#META#Header#End'):
                break
            match = re.match(r'#META#\s*([0-9]+\.\w+)\s*::\s*(.*)$', line.strip())
            if match and match.group(2).strip() not in ('NODATA', 'NOTGIVEN', ''):
                fields[match.group(1)] = match.group(2).strip()
    return fields


class Text:
    """Body of one OpenITI file: clean text, folded text (same length), offset map and page/heading/line indexes."""

    def __init__(self, key: str):
        raw = work_path(key).read_text(encoding='utf-8')
        body_start = raw.find('#META#Header#End#')
        self.raw = raw
        self.body_start = 0 if body_start < 0 else body_start
        self.pages = [(m.start(), int(m.group(1)), int(m.group(2))) for m in _PAGE.finditer(raw)]
        self.headings = [(m.start(), m.group(2).strip(), len(m.group(1))) for m in _HEADING.finditer(raw) if m.start() > self.body_start]
        self.line_starts = [0] + [m.end() for m in re.finditer('\n', raw)]
        pieces, offsets = [], array('l')
        position = self.body_start
        for markup in _MARKUP.finditer(raw, self.body_start):
            pieces.append(raw[position:markup.start()])
            offsets.extend(range(position, markup.start()))
            pieces.append(' ')
            offsets.append(markup.start())
            position = markup.end()
        pieces.append(raw[position:])
        offsets.extend(range(position, len(raw)))
        self.clean = ''.join(pieces)
        self.offsets = offsets
        # folded text drops vowel marks, so keep a folded -> clean index map
        self.folded_to_clean = array('l')
        folded_pieces, position = [], 0
        for mark in _HARAKAT.finditer(self.clean):
            folded_pieces.append(self.clean[position:mark.start()])
            self.folded_to_clean.extend(range(position, mark.start()))
            position = mark.end()
        folded_pieces.append(self.clean[position:])
        self.folded_to_clean.extend(range(position, len(self.clean)))
        self.folded = ''.join(folded_pieces).translate(_FOLD)

    def page_at(self, raw_offset: int):
        """OpenITI writes PageV markers at the END of a page: the page of a position is the first marker after it."""
        index = bisect.bisect_left([p[0] for p in self.pages], raw_offset) if self.pages else 0
        return self.pages[index][1:] if index < len(self.pages) else None

    def heading_at(self, raw_offset: int):
        index = bisect.bisect_right([h[0] for h in self.headings], raw_offset) - 1
        if index < 0:
            return None
        return re.sub(r'\s+', ' ', _MARKUP.sub(' ', self.headings[index][1])).strip()

    def year_heading_at(self, raw_offset: int):
        """Nearest preceding heading that names a year (`سنة ...`), at any level: the annal a passage sits under."""
        index = bisect.bisect_right([h[0] for h in self.headings], raw_offset) - 1
        while index >= 0:
            text = re.sub(r'\s+', ' ', _MARKUP.sub(' ', self.headings[index][1])).strip()
            if re.search(r'^(ثم (دخلت|كانت) )?سنه |^\[?حوادث السنه |في سنه ', fold(text) + ' '):
                return text
            index -= 1
        return None

    def line_at(self, raw_offset: int) -> int:
        low, high = 0, len(self.line_starts) - 1
        while low < high:
            middle = (low + high + 1) // 2
            if self.line_starts[middle] <= raw_offset:
                low = middle
            else:
                high = middle - 1
        return low + 1

    def search(self, folded_pattern: str):
        """All matches of a regex over the folded text, as (clean_start, clean_end)."""
        out = []
        for match in re.finditer(folded_pattern, self.folded):
            start = self.folded_to_clean[match.start()]
            end = self.folded_to_clean[match.end() - 1] + 1
            out.append((start, end))
        return out

    def passage(self, clean_start: int, clean_end: int, before: int = 1, after: int = 1, cap: int = 900) -> str:
        """Verbatim sentence window around a match: `before` sentence breaks back, `after` forward, whitespace collapsed."""
        text = self.clean
        breaks = re.compile(r'[.:؟!]\s|\n# ')
        start = clean_start
        for _ in range(before):
            previous = [m.end() for m in breaks.finditer(text, max(0, start - cap), max(0, start - 1))]
            start = previous[-1] if previous else _word_start(text, max(0, start - cap // 2))
        end = clean_end
        for _ in range(after):
            following = breaks.search(text, end, min(len(text), end + cap))
            end = following.start() + 1 if following else _word_end(text, min(len(text), end + cap // 2))
        return re.sub(r'\s+', ' ', text[start:end]).strip()

    def entry(self, clean_start: int, cap: int = 1200):
        """The whole `###` section holding a position (a rijal entry), verbatim, or None when longer than `cap`."""
        raw = self.raw_offset(clean_start)
        starts = [h[0] for h in self.headings]
        index = bisect.bisect_right(starts, raw) - 1
        if index < 0:
            return None
        begin = bisect.bisect_left(self.offsets, starts[index])
        finish = bisect.bisect_left(self.offsets, starts[index + 1]) if index + 1 < len(starts) else len(self.clean)
        text = re.sub(r'\s+', ' ', self.clean[begin:finish]).strip()
        return text if len(text) <= cap else None

    def raw_offset(self, clean_index: int) -> int:
        return self.offsets[min(clean_index, len(self.offsets) - 1)]


def _word_start(text: str, index: int) -> int:
    space = text.find(' ', index)
    return index if space < 0 else space + 1


def _word_end(text: str, index: int) -> int:
    space = text.rfind(' ', 0, index)
    return index if space < 0 else space


@lru_cache(maxsize=None)
def load(key: str) -> Text:
    return Text(key)
