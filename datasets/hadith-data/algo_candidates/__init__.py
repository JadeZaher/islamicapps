"""Algorithm candidates for taḥwīl-aware isnad extraction. See spec FR-0.5."""
from . import _common
from . import candidate_A_simple_set as A
from . import candidate_B_name_span as B
from . import candidate_C_lcs_suffix as C
from . import candidate_D_position_anchored as D
from . import candidate_E_no_stitch as E

CANDIDATES = {
    "A_simple_set": A.extract_branches,
    "B_name_span": B.extract_branches,
    "C_lcs_suffix": C.extract_branches,
    "D_position_anchored": D.extract_branches,
    "E_no_stitch": E.extract_branches,
}
