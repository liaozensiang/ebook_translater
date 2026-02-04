import os
from bs4 import BeautifulSoup, NavigableString
from tqdm import tqdm
from src.epub_handler import load_epub, save_epub, get_chapter_items
from src.llm_client import LLMClient
import json

class Translator:
    def __init__(self, llm_client, glossary_path=None):
        self.llm = llm_client
        self.glossary = {}
        if glossary_path and os.path.exists(glossary_path):
            with open(glossary_path, 'r', encoding='utf-8') as f:
                self.glossary = json.load(f)
        self.glossary_path = glossary_path

    def extract_terms_from_epub(self, input_path, src_lang="Japanese", tgt_lang="Traditional Chinese", update_existing=True):
        """
        Scans values to find new terms and updates the glossary file.
        Now allows scanning the full book or a large subset.
        """
        book = load_epub(input_path)
        items = get_chapter_items(book)
        
        print(f"Scanning {len(items)} chapters in {input_path} for new terms ({src_lang} -> {tgt_lang})...")
        
        new_terms_map = {}
        # We can scan more now since it's a dedicated step
        for item in tqdm(items):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text()
            
            # Skip very short texts
            if len(text) < 200:
                continue
                
            # Inspect first 5000 chars (increased from 3000)
            chunk_to_analyze = text[:5000]
            
            # Optimization: Don't pass the HUGE existing glossary to the LLM prompt.
            # It wastes tokens and might confuse the model. 
            # We will filter out known terms in Python AFTER extraction.
            terms_json = self.llm.extract_new_terms(chunk_to_analyze, src_lang, tgt_lang) 

            try:
                # Clean up potential markdown formatting
                clean_json = terms_json.strip()
                if clean_json.startswith("```"):
                    lines = clean_json.split('\n')
                    # Remove first line if it is ``` or ```json
                    if lines[0].strip().startswith("```"):
                        lines = lines[1:]
                    # Remove last line if it is ```
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    clean_json = "\n".join(lines).strip()
                
                data = json.loads(clean_json)
                
                # Handle new format: {"terms": [{"jp": "...", "zh": "..."}]}
                raw_terms = {}
                
                # Helper to normalize keys
                def get_kv(item):
                    # Try specific generic keys first, then language specific
                    k = item.get("source") or item.get("jp") or item.get(src_lang) or item.get("Japanese")
                    v = item.get("target") or item.get("zh") or item.get(tgt_lang) or item.get("Chinese")
                    return k, v

                if "terms" in data and isinstance(data["terms"], list):
                    for item in data["terms"]:
                        k, v = get_kv(item)
                        if k and v: raw_terms[k] = v
                elif "glossary_terms" in data and isinstance(data["glossary_terms"], list):
                    for item in data["glossary_terms"]:
                        k, v = get_kv(item)
                        if k and v: raw_terms[k] = v
                else:
                    # Fallback
                    if isinstance(data, dict):
                         for k, v in data.items():
                             if k not in ["terms", "glossary_terms"] and isinstance(v, str):
                                 raw_terms[k] = v

                # Filter invalid terms
                valid_data = {}
                blocklist = ["村", "町", "道", "街", "都市", "王国", "帝国", "世界", "人間", "彼", "彼女", "自分", 
                             "今日", "昨日", "明日", "時間", "場所", "理由", "意味", "言葉", "名前", "ピラミッド", "ミイラ"]

                for k, v in raw_terms.items():
                    if k in self.glossary: continue # Filter strictly here
                    if k not in chunk_to_analyze: continue
                    if len(k) > 20: continue
                    if len(k) <= 1: continue
                    if k in blocklist: continue
                    valid_data[k] = v

                if valid_data:
                    new_terms_map.update(valid_data)
                    print(f"DEBUG: Found {len(valid_data)} terms in chapter.") 
            except Exception as e:
                print(f"DEBUG: JSON Parse Error: {e}")
                print(f"DEBUG: Raw Output: {terms_json[:500]}...")
                pass
        
        if new_terms_map:
            print(f"Found {len(new_terms_map)} new terms.")
            if update_existing:
                self.glossary.update(new_terms_map)
                if self.glossary_path:
                    with open(self.glossary_path, 'w', encoding='utf-8') as f:
                        json.dump(self.glossary, f, ensure_ascii=False, indent=2)
                    print(f"Updated glossary saved to {self.glossary_path}")
            return new_terms_map
        else:
            print("No new terms found.")
            return {}

    def prepare_review_session(self, input_path, work_dir, src_lang="Japanese", tgt_lang="Traditional Chinese", auto_translate=False):
        """
        Extracts text from EPUB and initializes a review session.
        Returns the number of segments created.
        """
        print(f"Preparing review session for {input_path} ({src_lang} -> {tgt_lang})...")
        book = load_epub(input_path)
        items = get_chapter_items(book)
        
        from src.review_manager import ReviewManager
        import uuid
        
        segments = []
        
        for item in items:
            # We focus on main content
            if 'p-' not in item.get_name(): continue
            
            raw_html = item.get_content().decode('utf-8')
            # Use XML parser to ensure valid XHTML output (e.g. self-closing tags) which is required for EPUBs
            # 'html.parser' produces HTML5 void tags (e.g. <img>) which breaks Calibre
            soup = BeautifulSoup(raw_html, 'xml')
            
            # Extract paragraphs to Translate
            for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                if p.find(['p', 'div', 'blockquote']): continue
                
                text = p.get_text().strip()
                if not text: continue
                
                # Create a segment
                seg = {
                    "id": str(uuid.uuid4()),
                    "chapter": item.get_name(),
                    "jp": text,
                    "zh": "", 
                    "status": "pending"
                }
                segments.append(seg)

        # Auto-Translate if requested
        if auto_translate:
            print(f"Auto-translating {len(segments)} segments with {self.llm.model}...")
            # We use single translation for robustness and to reuse the prompt logic
            # This might be slow but it's safe and interactive (users see progress bar)
            for seg in tqdm(segments, desc="Translating"):
                try:
                    # Reuse the same logic as the UI
                    trans = self.llm.translate_single(seg['jp'], self.glossary, src_lang, tgt_lang)
                    if trans:
                        seg['zh'] = trans
                        # We keep status as 'pending' so user still has to 'Approve' it? 
                        # Or maybe 'draft'? For now 'pending' implies it needs review.
                except Exception as e:
                    print(f"Error translating segment {seg['id']}: {e}")

        # Initialize Manager
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
            
        mgr = ReviewManager(work_dir)
        mgr.create_session(os.path.basename(input_path), segments, self.glossary, src_lang=src_lang, tgt_lang=tgt_lang)
        
        print(f"Session created with {len(segments)} segments in {work_dir}")
        return len(segments)

    def assemble_epub(self, original_epub_path, session_dir, output_path):
        """
        Reconstructs the EPUB using direct ZipFile manipulation to ensure
        files that are not translated remain 100% bit-identical (preserving SVGs, covers, etc).
        """
        print(f"Assembling EPUB from {session_dir}...")
        import zipfile
        
        # Load Session Data
        from src.review_manager import ReviewManager
        mgr = ReviewManager(session_dir)
        session_data = mgr.session_data
        segments = session_data.get("segments", [])
        
        # Create lookup: filename -> list of segments
        # Note: session segments use 'chapter' which comes from item.get_name()
        # In ebooklib, names are usually relative paths like 'OEBPS/text/foo.xhtml' or just 'text/foo.xhtml'
        # We need to match these to zipfile entries.
        chapter_map = {}
        for seg in segments:
            chap = seg["chapter"]
            if chap not in chapter_map: chapter_map[chap] = []
            chapter_map[chap].append(seg)
            
        print(f"Loaded translations for {len(chapter_map)} files.")

        with zipfile.ZipFile(original_epub_path, 'r') as in_zip, \
             zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
            
            # Iterate every file in the original EPUB
            for info in in_zip.infolist():
                filename = info.filename
                
                # Check if we should modify this file
                # We try to match the filename. ebooklib names usually match zip paths.
                # E.g. session "xhtml/p-001.xhtml" vs zip "OEBPS/xhtml/p-001.xhtml"
                # We'll check if the session chapter name ends with the filename or vice versa
                
                target_segments = None
                matched_chap_name = None
                
                # Exact match first
                if filename in chapter_map:
                    target_segments = chapter_map[filename]
                    matched_chap_name = filename
                else:
                    # Fuzzy match: duplicate/suffix check
                    # Often ebooklib strips 'OEBPS/' or similar.
                    # We check if any chapter key is a suffix of the filename
                    for chap_name in chapter_map:
                         if filename.endswith(chap_name):
                             # Ambiguity check: if we have "a/b.xhtml" and "b.xhtml", ending with "b.xhtml" is risky.
                             # But in EPUB structure usually unique enough.
                             target_segments = chapter_map[chap_name]
                             matched_chap_name = chap_name
                             break
                
                # Logic: If found segments, verify they have translations
                valid_modification = False
                if target_segments:
                     # Check for actual content
                     if any(s.get("zh") and s["zh"].strip() for s in target_segments):
                         valid_modification = True
                     else:
                         print(f"Skipping {filename} (Matched {matched_chap_name} but no translations)")
                
                if valid_modification:
                    # Apply Translation
                    # print(f"Translating {filename}...")
                    content = in_zip.read(filename).decode('utf-8')
                    
                    # Parse
                    soup = BeautifulSoup(content, 'xml')
                    
                    seg_idx = 0
                    modified = False
                    
                    # We only traverse text nodes, same strategy as prepare
                    for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                        if p.find(['p', 'div', 'blockquote']): continue
                        text = p.get_text().strip()
                        if not text: continue
                        
                        if seg_idx < len(target_segments):
                            seg = target_segments[seg_idx]
                            
                            if seg["jp"] == text:
                                if seg["zh"]:
                                    p.string = seg["zh"]
                                    modified = True
                                seg_idx += 1
                            else:
                                pass # Mismatch or skip

                    if modified:
                        # Write modified content
                        # Use minimal xml formatter
                        new_content = soup.encode(encoding='utf-8', formatter='minimal')
                        out_zip.writestr(info, new_content)
                        continue
                    else:
                        print(f"File parsed but no text replaced: {filename}")
                        # Fallback to copy original
                
                # Fallback: Copy original byte-for-byte
                # This preserves cover images, fonts, css, and untranslated text exactly.
                raw_data = in_zip.read(filename)
                out_zip.writestr(info, raw_data)

        print(f"Assembled EPUB saved to {output_path}")

