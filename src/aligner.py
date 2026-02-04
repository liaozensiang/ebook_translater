import json
import re
from tqdm import tqdm
from src.epub_handler import load_epub, get_chapter_items, extract_text_from_html
from src.llm_client import LLMClient

class Aligner:
    def __init__(self, source_path, ref_path, llm_client=None):
        self.source_book = load_epub(source_path)
        self.ref_book = load_epub(ref_path)
        self.llm = llm_client

    def align_chapters(self):
        """Coarse alignment of file-to-file."""
        source_items = sorted([i for i in get_chapter_items(self.source_book) if 'xhtml/p-' in i.get_name()], key=lambda x: x.get_name())
        # Generic heuristic: usually 'xhtml/p-' or 'text/' etc. For now we assume typical structure.
        # If generic, might need broader filter, but let's stick to what works for now (p-*)
        ref_items = sorted([i for i in get_chapter_items(self.ref_book) if 'p-' in i.get_name()], key=lambda x: x.get_name())

        pairs = []
        
        # Helper to get valid content chapters
        def get_valid_chapters(items):
            valid = []
            for item in items:
                # heuristic: must have 'p-' in name (common for LN epubs)
                if 'p-' not in item.get_name(): continue
                text = extract_text_from_html(item.get_content())
                lines = [l for l in text.split('\n') if l.strip()]
                # content must be significant (> 50 lines) to be a story chapter
                if len(lines) > 50:
                    valid.append((item, text, len(lines)))
            # Sort by filename to ensure sequence
            valid.sort(key=lambda x: x[0].get_name())
            return valid

        print("Analyzing chapters for alignment...")
        source_valid = get_valid_chapters(get_chapter_items(self.source_book))
        ref_valid = get_valid_chapters(get_chapter_items(self.ref_book))

        print(f"Found {len(source_valid)} significant Source chapters and {len(ref_valid)} significant Ref chapters.")

        # Align index-by-index
        min_len = min(len(source_valid), len(ref_valid))
        for k in range(min_len):
            src_item, src_text, src_lines = source_valid[k]
            ref_item, ref_text, ref_lines = ref_valid[k]
            
            # Sanity check: lengths should be roughly similar (within 50% different is generous but safe)
            # e.g. 458 vs 462 is close. 1456 vs 1468 is close.
            ratio = min(src_lines, ref_lines) / max(src_lines, ref_lines)
            if ratio < 0.5:
                print(f"Skipping alignment mismatch: {src_item.get_name()} ({src_lines}L) vs {ref_item.get_name()} ({ref_lines}L)")
                continue

            print(f"Aligned: {src_item.get_name()} ({src_lines}L) <-> {ref_item.get_name()} ({ref_lines}L)")
            pairs.append({
                "source_id": src_item.get_name(),
                "ref_id": ref_item.get_name(),
                "source_text": src_text[:3000], 
                "ref_text": ref_text[:3000]
            })
        
        print(f"DEBUG: Found {len(pairs)} aligned pairs.")
        return pairs

    def extract_glossary_from_pairs(self, pairs, src_lang="Japanese", tgt_lang="Traditional Chinese"):
        """Uses LLM to extract glossary from aligned chapters."""
        full_glossary = {}
        
        print("Extracting glossary terms from aligned chapters...")
        # Process all pairs now that we have better alignment
        for pair in tqdm(pairs): 
            glossary_json = self.llm.extract_glossary(pair['source_text'], pair['ref_text'], src_lang, tgt_lang)
            try:
                data = json.loads(glossary_json)
                
                batch_terms = {}
                
                # Helper to normalize keys
                def get_kv(item):
                    k = item.get("source") or item.get("jp") or item.get("gloss_term_jp") or item.get("Japanese")
                    v = item.get("target") or item.get("zh") or item.get("gloss_term_zh") or item.get("Chinese")
                    return k, v

                # Case 1: Standard "terms" list
                if "terms" in data and isinstance(data["terms"], list):
                    for item in data["terms"]:
                         k, v = get_kv(item)
                         if k and v: batch_terms[k] = v
                         
                # Case 2: "glossary_terms" list (observed in wild)
                elif "glossary_terms" in data and isinstance(data["glossary_terms"], list):
                    for item in data["glossary_terms"]:
                         k, v = get_kv(item)
                         if k and v: batch_terms[k] = v
                         
                # Case 3: Flat dictionary (Fallback)
                elif isinstance(data, dict):
                     for k, v in data.items():
                         # BLOCK lists/dicts to prevent pollution
                         if k not in ["terms", "glossary_terms"] and isinstance(v, str):
                             batch_terms[k] = v

                if batch_terms:
                    # Filter invalid terms
                    valid_batch = {}
                    for k, v in batch_terms.items():
                        # Rule 1: Key must exist in original text
                        if k not in pair['source_text']: continue
                        
                        # Rule 2: Length checks
                        if len(k) > 20 or len(k) <= 1: continue
                        
                        # Rule 3: Common Noun/Symbol Blocklist (Python side is more reliable than Prompt)
                        # Identify common false positives seen in logs
                        blocklist = ["村", "町", "道", "街", "都市", "王国", "帝国", "世界", "人間", "彼", "彼女", "自分", 
                                     "今日", "昨日", "明日", "時間", "場所", "理由", "意味", "言葉", "名前", "ピラミッド", "ミイラ"]
                        if k in blocklist: continue
                        
                        # Rule 4: Value sanity check (should contain some CJK usually, not just English if input was JP)
                        
                        valid_batch[k] = v
                        
                    full_glossary.update(valid_batch)
            except:
                pass
                
        return full_glossary

    def save_glossary(self, glossary, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    client = LLMClient()
    aligner = Aligner('source.epub', 'reference.epub', client)
    pairs = aligner.align_chapters()
    glossary = aligner.extract_glossary_from_pairs(pairs)
    aligner.save_glossary(glossary, 'glossary.json')
    print(f"Glossary saved with {len(glossary)} items.")
