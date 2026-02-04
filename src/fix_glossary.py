import json
import os
import sys

def fix_glossary(path):
    if not os.path.exists(path):
        print(f"File {path} not found.")
        return

    print(f"Fixing glossary at {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    flat_glossary = {}
    
    # scan root
    for k, v in data.items():
        if isinstance(v, str):
            flat_glossary[k] = v
        elif isinstance(v, list) and (k == "glossary_terms" or k == "terms"):
            print(f"Found nested list under '{k}', flattening...")
            for item in v:
                jp = item.get("gloss_term_jp") or item.get("jp") or item.get("Japanese")
                zh = item.get("gloss_term_zh") or item.get("zh") or item.get("Chinese")
                if jp and zh:
                    flat_glossary[jp] = zh
        else:
            print(f"Skipping unknown non-string key: {k}")

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(flat_glossary, f, ensure_ascii=False, indent=2)
    
    print(f"Done. Saved {len(flat_glossary)} terms to {path}.")

if __name__ == "__main__":
    fix_glossary("glossary.json")
