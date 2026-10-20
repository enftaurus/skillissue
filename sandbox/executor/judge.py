import difflib
from typing import Optional
from sandbox.executor.schemas import CheckerType

class OutputJudge:
    @staticmethod
    def exact_match(actual: str, expected: str) -> bool:
        # Match exact string, allowing trailing newline normalization
        return actual.rstrip("\r\n") == expected.rstrip("\r\n")

    @staticmethod
    def token_match(actual: str, expected: str) -> bool:
        # Compare whitespace-separated tokens
        return actual.split() == expected.split()

    @staticmethod
    def float_match(actual: str, expected: str, tolerance: float = 1e-6) -> bool:
        act_tokens = actual.split()
        exp_tokens = expected.split()
        if len(act_tokens) != len(exp_tokens):
            return False
        for a, e in zip(act_tokens, exp_tokens):
            try:
                fa = float(a)
                fe = float(e)
                if abs(fa - fe) > tolerance:
                    return False
            except ValueError:
                if a != e:
                    return False
        return True

    @classmethod
    def check(
        cls,
        actual: str,
        expected: str,
        checker_type: CheckerType = "exact",
        float_tolerance: float = 1e-6,
    ) -> bool:
        if checker_type == "exact":
            return cls.exact_match(actual, expected)
        elif checker_type == "token":
            return cls.token_match(actual, expected)
        elif checker_type == "float":
            return cls.float_match(actual, expected, tolerance=float_tolerance)
        else:
            # Fallback to token match
            return cls.token_match(actual, expected)

    @staticmethod
    def make_diff(actual: str, expected: str, is_hidden: bool = False) -> Optional[str]:
        if is_hidden:
            return None
        act_lines = actual.rstrip("\r\n").splitlines(keepends=True)
        exp_lines = expected.rstrip("\r\n").splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            exp_lines,
            act_lines,
            fromfile="expected",
            tofile="actual",
            lineterm=""
        ))
        return "".join(diff) if diff else None
