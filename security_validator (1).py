# بنستورد الادوات اللي بنستخدمها للتحقق
from typing import Optional
from enum import Enum
from dataclasses import dataclass
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

# القرار مش هيخرج برا دول
class Decision(str, Enum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    BLOCK = "BLOCK"

#  كلاس اقولك بيها قراري النهائي وسببه و لو مفيش سبب القيمه بتبقي نص فاضي
@dataclass
class ValidationResult:
    decision: Decision
    reason: str = ""

# الكلمات دي عشان احمي النظام الاوامر متتطبقش علي النظام نفسه
PROTECTED_KEYWORDS = {
    "windows",
    "system32",
    "program files",
    "etc",
}

# بنعرف شكل الامر وبنتحقق من بياناته
class Command(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    action: str = Field(min_length=1)
    target: str = Field(min_length=1)

    name: Optional[str] = None
    new_name: Optional[str] = None

    path: Optional[str] = None
    destination_path: Optional[str] = None
    value: Optional[int] = None
    url: Optional[str] = None

    @field_validator("action")
    @classmethod    
    def normalize_action(cls, value: str) -> str:    # بنوحد شكل الامر يكون نص وبنشيل المسافات الزياده وكلو (small)
        value = value.strip().lower()

        if not value:
            raise ValueError("action must not be blank")

        return value

    @field_validator("target")
    @classmethod
    def normalize_target(cls, value: str) -> str:    # لازم يكون التارجت نص وبنشيل المسافات الزياده
        value = value.strip()

        if not value:
            raise ValueError("target must not be blank")

        return value
    
# تنظيف الحقول الاختياريه
    @field_validator(
        "name",
        "new_name",
        "path",
        "destination_path",
        "url",
    )
    @classmethod
    def clean_optional_strings(cls, value):        # الحقل ممكن يكون none ساعتها بنسيبه زي ما هوا
        if value is None:
            return value

        return value.strip()
    
# فحص المسارات
    @field_validator("path", "destination_path")
    @classmethod
    def validate_path(cls, value):
        if value is None:                           # لو المسار مش موجود مفيش حاجه نفحصها
            return value

        value = value.strip()                       # بنوحد شكل المسارات وبنشيل المسافات الزياده
        normalized_path = value.replace("\\", "/")

        path_parts = [
            part.lower()
            for part in normalized_path.split("/")
            if part
        ]

        if ".." in path_parts or "~" in path_parts: # بنرفض اشكال معينه تكون داخل المسار والايرور بتاعه موضح سببه
            raise ValueError("unsafe path")

        if any(part in PROTECTED_KEYWORDS for part in path_parts):
            raise ValueError(
                "operation not allowed on protected system path"
            )

        return value
    
# التحقق من القيم الرقميه
    @field_validator("value")
    @classmethod
    def validate_value(cls, value):      # لو القيمه مش موجوده بنسيبها none عادي
        if value is None:
            return value

        if not 0 <= value <= 100:        # لازم القيمه تكون بين ال0 وال100
            raise ValueError(
                "value must be between 0 and 100"
            )

        return value

# تحديد سياسه التعامل مع كل امر
# دي الاوامر المسموحه واللي محتاجه تاكيد من اليوزر
COMMAND_RULES = {
    "find": Decision.ALLOW,
    "open": Decision.ALLOW,
    "close": Decision.CONFIRM,
    "create": Decision.ALLOW,
    "delete": Decision.CONFIRM,
    "rename": Decision.CONFIRM,
    "list": Decision.ALLOW,
    "lock_screen": Decision.ALLOW,
    "brightness": Decision.CONFIRM,
    "volume": Decision.ALLOW,
    "mute": Decision.ALLOW,
    "restart": Decision.CONFIRM,
}

# دي البيانات اللي يعتبر مطلوبه لكل امر
REQUIRED_FIELDS = {
    "open": ["name"],
    "close": ["name"],
    "create": ["path"],
    "rename": ["name", "new_name"],
    "brightness": ["value"],
    "volume": ["value"],
}

# التحقق الامني من الامر 
def validate_command(command: Command) -> ValidationResult:    
    if not isinstance(command, Command):           # بنتاكد ان الداله استقبلت كائن فعلا
        return ValidationResult(
            Decision.BLOCK,
            "invalid command type"
        )

    decision = COMMAND_RULES.get(command.action)    # هل الامر موجود ف قايمه الاوامر المسموحه

    if decision is None:
        return ValidationResult(
            Decision.BLOCK,
            f"unsupported action: {command.action}"
        )

    required_fields = REQUIRED_FIELDS.get(         # بنجيب الحقول المطلوبه للامر ولو مفيش بحط ليست فاضيه
        command.action,
        []
    )

    for field_name in required_fields:   # هراجعهم واحده واحده ولو الحقل المطلوب قيمته none الامر غير مكتمل 
        value = getattr(command, field_name)

        if value is None:
            return ValidationResult(
                Decision.BLOCK,
                f"{command.action} requires {field_name}"
            )

        if isinstance(value, str) and not value.strip():   # لو الحقل فيه مسافات كتير بنرفضه
            return ValidationResult(
                Decision.BLOCK,
                f"{command.action} requires {field_name}"
            )
        
# الحذف محتاج اسم او مسار 
    if command.action == "delete":
        if not command.name and not command.path:
            return ValidationResult(
                Decision.BLOCK,
                "delete requires name or path"
            )
        
# وكذلك البحث
    if command.action == "find":
        if not command.name and not command.path:
            return ValidationResult(
                Decision.BLOCK,
                "find requires name or path"
            )

    if decision == Decision.CONFIRM:    # طبعا بيحتاج تاكيد من اليوزر 
        return ValidationResult(
            Decision.CONFIRM,
            "user confirmation required"
        )

    return ValidationResult(
        Decision.ALLOW,
        "valid command"
    )

# استقبال البيانات والتحقق منها يعني نتاكد انها dectionary ونحولها لكائن
def validate_command_data(data: object) -> ValidationResult:
    if not isinstance(data, dict):
        return ValidationResult(
            Decision.BLOCK,
            "input must be a dictionary"
        )

    try:                               #  وهنفحصه باستخدام المكتبه والشروط اللي فوق لو البيانات مش مطابقه لشروط Command بنرجع بلوك
        command = Command.model_validate(data)

    except ValidationError as e:
        return ValidationResult(
            Decision.BLOCK,
            str(e)
        )

    return validate_command(command)