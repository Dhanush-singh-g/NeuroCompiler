"""Compare frozen prediction diagnostics across numerical backends.

Pipeline names and structure remain exact. Only finite numerical diagnostics
allow round-off at 1e-14 absolute / 1e-12 relative tolerance. This helper must
not be used for hashes, timing protocols, or reported runtime effects.
"""
import math


def predictions_equal(actual,frozen):
    if isinstance(actual,dict) and isinstance(frozen,dict):
        return actual.keys()==frozen.keys() and all(predictions_equal(actual[k],frozen[k]) for k in actual)
    if isinstance(actual,list) and isinstance(frozen,list):
        return len(actual)==len(frozen) and all(predictions_equal(a,b) for a,b in zip(actual,frozen))
    if isinstance(actual,bool) or isinstance(frozen,bool):return type(actual) is type(frozen) and actual==frozen
    if isinstance(actual,(int,float)) and isinstance(frozen,(int,float)):
        return math.isfinite(actual) and math.isfinite(frozen) and math.isclose(actual,frozen,rel_tol=1e-12,abs_tol=1e-14)
    return type(actual) is type(frozen) and actual==frozen
