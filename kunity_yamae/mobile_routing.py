from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .risk_checks import has_task_keyword, normalize_task_text

AgentRole = Literal["local", "worker", "architect", "reviewer", "human"]

SENSITIVE_TERMS = (
    "iap", "purchase", "receipt", "transaction", "billing", "refund",
    "firebase", "auth", "oauth", "google sign", "apple sign", "login", "account link",
    "admob", "rewarded", "consent", "ump", "keystore", "entitlement", "nonce",
    "결제", "구매", "영수증", "환불", "로그인", "계정", "인증", "광고", "동의",
)

ARCHITECTURE_TERMS = (
    "architecture", "migration", "native crash", "sigsegv", "il2cpp", "gradle", "xcode",
    "race condition", "deadlock", "설계", "마이그레이션", "네이티브 크래시", "빌드",
)

LOCAL_TERMS = (
    "scan", "inspect package", "read manifest", "read packages-lock", "list prefab",
    "프로젝트 스캔", "패키지 확인", "프리팹 목록", "버전 확인",
)


@dataclass(frozen=True)
class AgentRoute:
    role: AgentRole
    risk: str
    requires_review: bool
    reasons: tuple[str, ...]
    policy: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def route_mobile_task(task: str, *, risk_score: int, failure_count: int = 0) -> AgentRoute:
    """Choose the cheapest safe execution lane without granting write permission.

    The result is advisory. Existing patch guards, Unity verification and human approval
    remain authoritative.
    """
    if type(risk_score) is not int or not 0 <= risk_score <= 100:
        raise ValueError("risk_score must be an integer between 0 and 100")
    if type(failure_count) is not int or failure_count < 0:
        raise ValueError("failure_count must be a non-negative integer")
    text = normalize_task_text(task)
    sensitive = tuple(term for term in SENSITIVE_TERMS if has_task_keyword(text, [term]))
    architectural = tuple(term for term in ARCHITECTURE_TERMS if has_task_keyword(text, [term]))
    local = tuple(term for term in LOCAL_TERMS if has_task_keyword(text, [term]))

    if failure_count >= 2:
        return AgentRoute(
            role="human",
            risk="blocked",
            requires_review=True,
            reasons=("automatic attempts failed twice",),
            policy=("stop automatic retries", "preserve evidence and failed outputs"),
        )

    if sensitive or architectural or risk_score >= 60 or failure_count == 1:
        reasons = []
        if failure_count == 1:
            reasons.append("worker failed once; do not repeat the same low-cost attempt")
        if sensitive:
            reasons.append("monetization, identity, privacy, or platform-sensitive scope")
        if architectural:
            reasons.append("architecture, migration, native build, or crash reasoning")
        if risk_score >= 60:
            reasons.append(f"existing Unity risk score is {risk_score}")
        return AgentRoute(
            role="architect",
            risk="high",
            requires_review=True,
            reasons=tuple(reasons),
            policy=(
                "use installed SDK/API evidence before proposing code",
                "never treat model confidence as Unity verification",
                "route final change through existing guarded patch and verification flow",
            ),
        )

    if local and risk_score <= 20:
        return AgentRoute(
            role="local",
            risk="low",
            requires_review=False,
            reasons=("deterministic inspection should not spend model tokens",),
            policy=("read only", "return observed facts only"),
        )

    if risk_score <= 35:
        return AgentRoute(
            role="worker",
            risk="low",
            requires_review=True,
            reasons=("bounded Unity change suitable for a low-cost worker",),
            policy=(
                "send only task-relevant context",
                "proposal or guarded patch only",
                "escalate instead of broadening scope",
            ),
        )

    return AgentRoute(
        role="reviewer",
        risk="medium",
        requires_review=True,
        reasons=(f"moderate Unity risk score is {risk_score}",),
        policy=(
            "review bounded worker output before application",
            "require relevant Unity verification",
        ),
    )
