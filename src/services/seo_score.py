def compute_score(engine_results):
    score = 100
    
    # 1. Deductions from modules (Cap at 50% to avoid score 0 just from modules)
    total_module_deduction = 0
    modules = engine_results.get("modules", {})
    for module_name, result in modules.items():
        if not result:
            continue
        issues = result.get("issues")
        if not issues:
            continue
        # Subtract based on issue count, but cap deduction per module at 10
        total_module_deduction += min(len(issues) * 2, 10)

    score -= min(total_module_deduction, 50)
    
    # Audit component score (if available)
    audit = engine_results.get("audit", {})
    audit_score = audit.get("score", 100)
    
    # Final weight: 60% engine modules, 40% audit baseline
    final_score = int((score * 0.6) + (audit_score * 0.4))
    
    return max(0, min(100, final_score))
