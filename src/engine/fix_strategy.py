def build_fix_strategy(engine_results):

    modules = engine_results.get("modules", {})

    strategy = []

    for module_name, result in modules.items():

        if not result:
            continue

        issues = result.get("issues")

        if not issues:
            continue

        strategy.append(module_name)

    return strategy
