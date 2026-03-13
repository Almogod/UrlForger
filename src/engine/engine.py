def run_engine(pages, clean_urls, domain, graph, progress_callback=None):
    """
    Core SEO repair engine.
    """

    # -----------------------------
    # INITIAL CONTEXT
    # -----------------------------
    context = {
        "pages": pages,
        "urls": clean_urls,
        "domain": domain,
        "graph": graph
    }

    # -----------------------------
    # RUN AUDIT
    # -----------------------------
    if progress_callback: progress_callback("Running site audit...")
    audit = generate_audit_report(pages, clean_urls)

    # -----------------------------
    # BUILD EXECUTION PLAN
    # -----------------------------
    if progress_callback: progress_callback("Building execution plan...")
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
            logger.warning("Module %s not found in registry", module_name)
            continue

        logger.info("Running module: %s", module_name)
        if progress_callback: progress_callback(f"Running module: {module_name}...")

        try:
            module_result = module.run(context)
            results["modules"][module_name] = module_result

            if "urls" in module_result:
                context["urls"] = module_result["urls"]
        except Exception as e:
            logger.error("Error running module %s: %s", module_name, e)
            results["modules"][module_name] = {"error": str(e)}

    # -----------------------------
    # FIX STRATEGY & EXECUTION
    # -----------------------------
    if progress_callback: progress_callback("Finalizing fix strategy...")
    
    # Generate strategy based on module results
    strategy = build_fix_strategy(results)
    
    # Execute the final fixes
    actions = execute_fixes(context, results["modules"], strategy)

    # Update results object
    results["actions"] = actions
    results["strategy"] = strategy
    results["fixed_urls"] = context["urls"]

    # Compute final SEO score
    results["seo_score"] = compute_score(results)

    return results
