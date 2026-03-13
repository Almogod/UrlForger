# src/engine/fix_executor.py

def execute_fixes(context, module_results):

    actions = []

    for module, result in module_results.items():

        if not result:
            continue

        if module == "meta":
            actions += apply_meta_fixes(result)

        elif module == "image_seo":
            actions += apply_image_fixes(result)

        elif module == "schema":
            actions += apply_schema_fixes(result)

    return actions


def apply_meta_fixes(result):

    actions = []

    fixes = result.get("fixes", {})

    for url, data in fixes.items():

        actions.append({
            "type": "meta_update",
            "url": url,
            "title": data.get("title"),
            "description": data.get("description")
        })

    return actions
