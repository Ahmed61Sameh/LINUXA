def validate(commands):
    if (not isinstance(commands, list)): #بتشوف هي ليست ولا لا
        raise ValueError("commands must be a list")
    if (commands == []): # بتشوف لو الليست فاضية
        raise ValueError("commands must not be empty")
    for i, c in enumerate(commands):
        if not isinstance(c, dict):
            raise ValueError(f"command {i} must be a dict")

        if not c.get("action"):
            raise ValueError(f"command {i} is missing 'action'")

        if not c.get("target"):
            raise ValueError(f"command {i} is missing 'target' ")
        
def run_tasks(commands):
    validate(commands) #بتستدعي الفانكشن
    blocked = False  # بيجاوب على الامر اتعمل قبل كدا ولا لا

    for i, c in enumerate(commands):  # بيلف على كل امر
        c["id"] = i # بتكتب الرقم على الامر
        if blocked:  # لو امر قبله فشل بتسيبه وتروح للي بعده
            c["status"] = "skipped"
            continue

        try:
            execute(c) #بتعتمد على تاسك 6 بس لو نجح بتكمل عادي
        except Exception as e:
            c["status"] = "failed"
            c["error"] = str(e)  # بتحول الخطأ لنص عشان نسجله
        c.setdefault("status","failed")   # بس لو الامر فشل
        if c["status"]=="failed":
            blocked = True  #اتغيرت بس عشان الامر فشل غير كدا هتفضل فولس عادي 

    return commands
#-----------------------------------------
# فانكشن واهمية عشان الفشل الحقيقي هيجي من تاسك 6
def execute(command):
    if command.get("action") == "broken":
        raise RuntimeError("something went wrong")
    command["status"] = "success"
#----------------------------------------------
if __name__ == "__main__":
    for bad in [[], "x", [1], [{"action": "a"}], [{"target": "t"}]]:
        try:
            validate(bad)
            assert False, f"should have failed: {bad}"
        except ValueError:
            pass

    cmds = [
        {"action": "a",      "target": "t"},
        {"action": "broken", "target": "t"},
        {"action": "c",      "target": "t"},
    ]
    result = run_tasks(cmds)
    assert [c["status"] for c in result] == ["success", "failed", "skipped"]
    assert result[1]["error"] == "something went wrong"
    print("all tests passed")