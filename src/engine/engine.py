# src/engine/engine.py

from src.audit import generate_audit_report
from src.engine.planner import build_fix_plan
from src.engine.registry import MODULE_REGISTRY


def run_engine(pages, clean_urls, domain):
    """
    Core SEO repair engine.

    Responsibilities:
    - run site audit
    - build execution plan
    - execute fix modules
    - aggregate results
    """

    # -----------------------------
    # INITIAL CONTEXT
    # -----------------------------
    context = {
        "pages": pages,
        "urls": clean_urls,
        "domain": domain
    }

    # -----------------------------
    # RUN AUDIT
    # -----------------------------
    audit = generate_audit_report(pages, clean_urls)

    # -----------------------------
    # BUILD EXECUTION PLAN
    # -----------------------------
    plan = build_fix_plan(audit)

    results = {
        "audit": audit,
        "plan": plan,
        "modules": {},
        "fixed_urls": clean_urls
    }

    # -----------------------------
    # EXECUTE MODULES
    # -----------------------------
    for module_name in plan:

        module = MODULE_REGISTRY.get(module_name)

        if not module:
            continue

        try:
            module_result = module.run(context)

            # store module result
            results["modules"][module_name] = module_result

            # modules may modify URLs
            if "urls" in module_result:
                context["urls"] = module_result["urls"]

        except Exception as e:
            results["modules"][module_name] = {
                "error": str(e)
            }

    # -----------------------------
    # FINAL URL SET
    # -----------------------------
    results["fixed_urls"] = context["urls"]

    return results
