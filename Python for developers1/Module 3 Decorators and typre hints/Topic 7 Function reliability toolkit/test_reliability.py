"""
Test cases — Function Reliability Toolkit (Module 3)

HOW TO RUN
    Put this file in the same folder as reliability.py, then:
        python test_reliability.py

WHAT IS AND ISN'T CHECKED
    memoize and call_counter are checked closely — their behaviour is exact and
    repeatable. timer and retry are NOT auto-checked: one measures wall-clock
    time and the other depends on a function that fails at random, so a test
    would be flaky and tell you nothing useful. Check those two by running your
    own program and reading the output.

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


try:
    import reliability as R
except ImportError as e:
    print("Could not import reliability.py — expected it beside this file.")
    print(f"  (import error: {e})")
    sys.exit(1)
except Exception as e:
    print("reliability.py ran something on import instead of only defining decorators.")
    print('  Put the sample functions and the report under an if __name__ == "__main__": guard.')
    print(f"  ({type(e).__name__}: {e})")
    sys.exit(1)


def need(name):
    obj = getattr(R, name, None)
    if obj is None:
        raise NotFound(f"No '{name}' in reliability.py — either not built "
                       f"yet, or it's there under a different name")
    return obj


# ── Phase 1: the decorators ──────────────────────────────────────────────────

phase("Phase 1: memoize and call_counter")


def _memo_same_answer():
    memo = need("memoize")

    @memo
    def double(n):
        return n * 2

    assert double(21) == 42, "a memoized function must still return the right answer"
    assert double(21) == 42, "the cached call must return the same answer"


def _memo_skips_recompute():
    memo = need("memoize")
    calls = []

    @memo
    def slow(n):
        calls.append(n)
        return n * 2

    slow(5); slow(5); slow(5)
    assert len(calls) == 1, (
        f"calling with the same argument 3 times should run the real function once, "
        f"but it ran {len(calls)} times — the cache isn't being read")


def _memo_distinguishes_args():
    memo = need("memoize")
    calls = []

    @memo
    def f(n):
        calls.append(n)
        return n

    f(1); f(2); f(1)
    assert len(calls) == 2, (
        f"two different arguments should each be computed once (2 calls), got {len(calls)} — "
        "the cache key probably ignores the arguments")


def _counter():
    cc = need("call_counter")

    @cc
    def ping():
        return "pong"

    ping(); ping(); ping()
    for attr in ("calls", "call_count", "count", "num_calls"):
        if hasattr(ping, attr):
            assert getattr(ping, attr) == 3, (
                f"after 3 calls the counter should read 3, got {getattr(ping, attr)}")
            return
    raise AssertionError(
        "no call count readable on the wrapped function — store it on the wrapper, "
        "e.g. wrapper.calls, so it can be read after the calls")


def _wraps_identity():
    memo = need("memoize")

    @memo
    def uniquely_named_function():
        return 1

    assert uniquely_named_function.__name__ == "uniquely_named_function", (
        f"the wrapped function reports its name as "
        f"'{uniquely_named_function.__name__}' — add @wraps(func) to the wrapper so it "
        "keeps the original function's identity")


check("a memoized function still returns the right answer", _memo_same_answer)
check("memoize runs the real function once for a repeated argument", _memo_skips_recompute)
check("memoize caches per-argument, not one value for everything", _memo_distinguishes_args)
check("call_counter exposes how many times the function ran", _counter)
check("@wraps keeps the decorated function's __name__", _wraps_identity)

check("timer exists (behaviour not auto-checked — it measures real time)",
      lambda: need("timer") and None)
check("retry exists (behaviour not auto-checked — it depends on random failure)",
      lambda: need("retry") and None)

# ── Phase 2: applying the toolkit ────────────────────────────────────────────

phase("Phase 2: applying the toolkit")


def _stacking():
    memo, cc = need("memoize"), need("call_counter")
    calls = []

    @memo
    @cc
    def f(n):
        calls.append(n)
        return n

    f(3); f(3)
    assert len(calls) == 1, (
        "with memoize stacked above call_counter, a repeated argument should reach the "
        f"real function once, got {len(calls)}")


check("memoize and call_counter can be stacked on one function", _stacking)

print(f"\n{_tally['PASS']} passed, {_tally['FAIL']} failed, "
      f"{_tally['NOT FOUND']} not found (not built yet, or named differently)")
print("timer and retry are yours to check by running the program — see the note at the top.")
if _tally["FAIL"]:
    print("Read the FAIL lines above — each says what was expected and what it got.")
