"""
Test cases — Data Validation Pipeline (Module 2)

HOW TO RUN
    Put this file in the same folder as validators.py, then:
        python test_validators.py

RESULTS
    PASS       the check succeeded
    FAIL       it ran but gave the wrong answer (the expected one is shown)
    NOT FOUND  that piece isn't there — either not built yet, or under a
               different name than the phase goal asked for
"""

import sys

class NotFound(Exception):
    """The thing being checked isn't there under the expected name."""


_tally = {"PASS": 0, "FAIL": 0, "NOT FOUND": 0}


def phase(title):
    print(f"\n--- {title} ---")


def check(label, fn):
    try:
        fn()
    except NotFound as e:
        print(f"NOT FOUND  {label}\n           {e}")
        _tally["NOT FOUND"] += 1
    except AssertionError as e:
        print(f"FAIL       {label}\n           {e}")
        _tally["FAIL"] += 1
    except Exception as e:
        print(f"FAIL       {label}\n           {type(e).__name__}: {e}")
        _tally["FAIL"] += 1
    else:
        print(f"PASS       {label}")
        _tally["PASS"] += 1


def is_true(v, why):
    assert v is True or v == 1, f"{why} — expected True, got {v!r}"


def is_false(v, why):
    assert v is False or v == 0, f"{why} — expected False, got {v!r}"


try:
    import validators as V
except ImportError as e:
    print("Could not import validators.py — expected it beside this file.")
    print(f"  (import error: {e})")
    sys.exit(1)
except Exception as e:
    print("validators.py ran something on import instead of only defining functions.")
    print('  Put your try-it-out code under an if __name__ == "__main__": guard.')
    print(f"  ({type(e).__name__}: {e})")
    sys.exit(1)


def need(name):
    fn = getattr(V, name, None)
    if fn is None:
        raise NotFound(f"No '{name}' in validators.py — either not built "
                       f"yet, or it's there under a different name")
    return fn


REC = {"name": "Alice", "age": 30, "email": "a@b.com", "department": "Sales"}

# ── Phase 1: the three validator factories ───────────────────────────────────

phase("Phase 1: validator factories")

check("make_range_validator accepts a value inside the range",
      lambda: is_true(need("make_range_validator")("age", 18, 65)(REC),
                      "age 30 is inside 18-65"))

# Boundaries: an off-by-one here is the classic bug (< vs <=).
check("make_range_validator accepts the low boundary exactly (18)",
      lambda: is_true(need("make_range_validator")("age", 18, 65)({**REC, "age": 18}),
                      "age 18 with a range of 18-65"))
check("make_range_validator accepts the high boundary exactly (65)",
      lambda: is_true(need("make_range_validator")("age", 18, 65)({**REC, "age": 65}),
                      "age 65 with a range of 18-65"))
check("make_range_validator rejects one below the range",
      lambda: is_false(need("make_range_validator")("age", 18, 65)({**REC, "age": 17}),
                       "age 17 with a range of 18-65"))
check("make_range_validator rejects one above the range",
      lambda: is_false(need("make_range_validator")("age", 18, 65)({**REC, "age": 66}),
                       "age 66 with a range of 18-65"))

check("each call to make_range_validator remembers its own range",
      lambda: (is_true(need("make_range_validator")("age", 18, 65)(REC), "30 in 18-65"),
               is_false(need("make_range_validator")("age", 40, 50)(REC), "30 in 40-50"))
      and None)

check("make_length_validator accepts a string at the limit exactly",
      lambda: is_true(need("make_length_validator")("name", 5)(REC),
                      "'Alice' is 5 characters with a limit of 5"))
check("make_length_validator rejects a string over the limit",
      lambda: is_false(need("make_length_validator")("name", 4)(REC),
                       "'Alice' is 5 characters with a limit of 4"))

check("make_required_validator accepts a record with every field present",
      lambda: is_true(need("make_required_validator")("name", "email")(REC),
                      "both fields are present and non-empty"))
check("make_required_validator rejects a record with a field missing",
      lambda: is_false(need("make_required_validator")("name", "phone")(REC),
                       "'phone' is not in the record"))
check("make_required_validator rejects an empty value, not just a missing key",
      lambda: is_false(need("make_required_validator")("name")({**REC, "name": ""}),
                       "'name' is present but empty"))
check("make_required_validator takes any number of field names",
      lambda: is_true(need("make_required_validator")("name", "age", "email", "department")(REC),
                      "all four fields are present"))

# ── Phase 2: running records through the pipeline ────────────────────────────

phase("Phase 2: pipeline and report")


def _all_pass():
    vr = need("validate_record")
    vs = [need("make_range_validator")("age", 18, 65),
          need("make_required_validator")("name", "email")]
    is_true(vr(REC, vs), "every validator passes for this record")


def _one_fails():
    vr = need("validate_record")
    vs = [need("make_range_validator")("age", 40, 50),   # 30 is outside this
          need("make_required_validator")("name", "email")]
    is_false(vr(REC, vs), "one validator fails, so the record must fail")


def _empty_list():
    vr = need("validate_record")
    is_true(vr(REC, []), "with no validators there is nothing to fail")


check("validate_record is True when every validator passes", _all_pass)
check("validate_record is False when even one validator fails", _one_fails)
check("validate_record with an empty validator list is True", _empty_list)

check("format_record returns a string",
      lambda: (lambda r: None if isinstance(r, str) else
               (_ for _ in ()).throw(AssertionError(
                   f"expected a string, got {type(r).__name__}: {r!r}")))
      (need("format_record")(REC)))

check("format_record mentions something from the record",
      lambda: (lambda r: None if any(str(v) in r for v in REC.values()) else
               (_ for _ in ()).throw(AssertionError(
                   f"the formatted string shows none of the record's values: {r!r}")))
      (need("format_record")(REC)))

print(f"\n{_tally['PASS']} passed, {_tally['FAIL']} failed, "
      f"{_tally['NOT FOUND']} not found (not built yet, or named differently)")
if _tally["FAIL"]:
    print("Read the FAIL lines above — each says what was expected and what it got.")
