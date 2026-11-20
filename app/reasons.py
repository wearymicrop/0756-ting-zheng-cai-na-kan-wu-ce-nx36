REASONS = {
    "BAD_VERSION": "文书版本字段有误", "DUPLICATE_VERSION": "文书版本号重复", "VERSION_ORPHAN": "找不到前版文书",
    "VERSION_CYCLE": "修订关系成环", "VERSION_ORDER": "后版发布时间不晚于前版", "BAD_PASSAGE": "段落记录字段有误",
    "ANCHOR_CONFLICT": "同版锚点操作冲突", "VERSION_UNAVAILABLE": "段落对应版本不可用",
    "PAGE_INVALID": "页码超出文书范围", "BAD_DIRECTORY": "登记名册字段有误", "SPEAKER_CONFLICT": "登记号对应多条名册行",
    "AMBIGUOUS_NAME": "同名发言待识别", "SPEAKER_UNKNOWN": "未在名册中识别发言人", "BAD_OPINION": "发言主题或立场有误",
    "ANCHOR_MISSING": "移页或删段缺少前段", "REVISION_FORK": "修订分支的段落内容不一致", "ANCHOR_DELETED": "文书已删段",
    "ANCHOR_UNRESOLVED": "锚点尚有未解决的修订", "ANCHOR_CHANGED": "同一锚点的发言人或诉求变化",
    "BAD_DECISION": "采纳记录字段有误", "DECISION_CONFLICT": "同版采纳结论冲突", "DECISION_FORK": "意见有不同采纳结论",
    "DECISION_MISSING": "缺少适用采纳结论", "DECISION_ANCHOR": "采纳记录缺少对应段落", "CONTACT_MISSING": "缺少可用寄送地址",
    # 旧案卷影响册（M8）
    "IMPACT_MAINTAIN": "新规则下结论与页码均不变，维持原勘误",
    "IMPACT_SUPPLEMENT": "结论或末版页码变化，须向收件人追补寄送",
    "IMPACT_WITHDRAW": "原勘误条目在新规则下已不存在，须撤回",
    "IMPACT_SERVED_LOCKED": "已送达记录冻结，仅出具补寄或撤回单，不改原结论",
    "BASELINE_NOT_FOUND": "找不到作为旧版的归档案卷",
    "SUPPLEMENT_TABLES": "补交数据只能覆盖原有输入表",
    "DISPATCH_UNKNOWN": "该案卷没有对应的寄送台账条目",
    "IMPACT_INTERRUPTED": "重算中断，已恢复旧版影响册",
}

# 影响册与寄送台账的状态标签，供工作台页面统一渲染。
STATUS_LABELS = {
    "maintain": "维持", "supplement": "追补", "withdraw": "撤回", "served": "已送达", "pending": "待寄送",
}
