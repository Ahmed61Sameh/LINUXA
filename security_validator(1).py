
#===================================================================================

from enum import Enum
from dataclasses import dataclass


# أنواع القرارات اللي الموديول ممكن يرجعها
class Decision(str, Enum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    APPROVED = "APPROVED"


# الكلاس اللي بيرجع نتيجة التحقق
# سواء الأمر مسموح أو محتاج تأكيد
@dataclass
class ValidationResult:
    decision: Decision
    reason: str = ""


# الأوامر اللي ممكن تعمل تأثير مهم على النظام
# وبالتالي لازم المستخدم يأكدها قبل التنفيذ
CONFIRM_ACTIONS = {
    "delete",
    "remove",
    "rename",
    "move",
    "lock_screen",
    "shutdown",
    "restart",
}


# بتحدد هل الأمر يحتاج تأكيد من المستخدم
# ولا يقدر يتنفذ مباشرة
def validate_command(command: dict) -> ValidationResult:

    action = str(
        command.get("action", "")
    ).lower()

    if action in CONFIRM_ACTIONS:

        return ValidationResult(
            Decision.CONFIRM,
            "user confirmation required"
        )

    return ValidationResult(
        Decision.ALLOW
    )


# بتتعامل مع رد المستخدم بعد طلب التأكيد
# لو وافق يتحول الأمر إلى APPROVED
# ولو رفض يفضل محتاج تأكيد ومش هيتنفذ
def approved_command(
        result: ValidationResult,
        user_confirmed: bool
) -> ValidationResult:

    if result.decision != Decision.CONFIRM:
        return result

    if user_confirmed:
        return ValidationResult(
            Decision.APPROVED,
            "user approved the command"
        )

    return ValidationResult(
        Decision.CONFIRM,
        "user confirmation required"
    )
#============================================================================