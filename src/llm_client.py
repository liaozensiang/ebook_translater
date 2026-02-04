import os
from openai import OpenAI
import json

class LLMClient:
    def __init__(self, base_url=None, api_key=None, model="Qwen/Qwen2.5-7B-Instruct"):
        self.client = OpenAI(
            base_url=base_url or os.getenv("LLM_API_URL", "http://vllm:8000/v1"),
            api_key=api_key or os.getenv("LLM_API_KEY", "sk-test")
        )
        self.model = model

    def extract_glossary(self, text, ref_text, src_lang="Japanese", tgt_lang="Traditional Chinese"):
        """
        Extracts names and terms from aligned text.
        """
        prompt = f"""
        You are a helpful assistant. 
        Compare the following {src_lang} text and its {tgt_lang} translation.
        Identify Proper Nouns (Character Names, Place Names, Weapon Names, Terminology) that are key matching terms.
        
        Rules:
        1. Output a JSON object with a "terms" key.
        2. "terms" must be a list of objects: {{"source": "...", "target": "..."}}
        3. Exclude common words.
        
        Source ({src_lang}):
        {text[:1500]}...
        
        Reference ({tgt_lang}):
        {ref_text[:1500]}...
        
        Return JSON only.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Extraction Error: {e}")
            return "{}"

    def extract_new_terms(self, text, src_lang="Japanese", tgt_lang="Traditional Chinese"):
        """
        Analyzes text to find new proper nouns.
        """
        prompt = f"""
        You are a translation assistant.
        Analyze the {src_lang} text below. Identify proper nouns (Characters, Places, Unique Items, Spells) that are likely specific to this story.
        
        Rules:
        1. Identify proper nouns.
        2. STRICTLY EXCLUDE common nouns (e.g. "Village", "Road", "School", "Time") unless part of a proper name.
        3. Output a JSON object with a "terms" key.
        4. Format: {{"source": "Original Term ({src_lang})", "target": "Translated Term ({tgt_lang})"}}
        
        Example Output:
        {{
            "terms": [
                {{"source": "Original Name", "target": "Translated Name"}}
            ]
        }}
        
        Text:
        {text[:2500]}
        
        Return JSON only.
        """
        
        try:
             response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
             return response.choices[0].message.content
        except Exception as e:
            print(f"Term Extraction Error: {e}")
            return "{}"
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Term Extraction Error: {e}")
            return "{}"

    def translate_batch(self, texts, glossary=None, src_lang="Japanese", tgt_lang="Traditional Chinese"):
        """
        Translates a batch of texts using strict JSON List output.
        Retries with simplified prompt on failure.
        """
        if not texts:
            return []

        # Prepare glossary string
        glossary_str = ""
        if glossary:
            relevant_glossary = {k: v for k, v in glossary.items() if k in "".join(texts)}
            if relevant_glossary:
                glossary_str = f"Glossary:\n{json.dumps(relevant_glossary, ensure_ascii=False)}\n"

        # Strategy 1: JSON List Format (Simpler than Object)
        system_msg = f"""You are a professional translator of {src_lang} into {tgt_lang}.
Rules:
1. Translate each line maintaining context and flow.
2. Output a JSON LIST of strings: ["translation1", "translation2"].
3. Preserve the exact number of lines (N inputs -> N outputs).
4. Use the glossary if provided.
"""

        user_content = f"{glossary_str}\nTranslate these {len(texts)} lines:\n"
        for i, text in enumerate(texts):
            user_content += f"{text}\n" # Just list them, index is implied by order

        def attempt_translation(retries=1):
            for attempt in range(retries + 1):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_content}
                        ],
                        temperature=0.3,
                        max_tokens=4096,
                        response_format={"type": "json_object"} 
                        # Note: 'json_object' usually requires 'JSON' in prompt, which we have.
                        # Some models prefer 'json_schema' but strict json_object is good for now.
                        # Actually, for list, we should wrap it: { "data": [...] } to satisfy 'json_object' requirement validation
                    )
                    content = response.choices[0].message.content
                    
                    # Try to parse
                    try:
                        data = json.loads(content)
                        # Handle { "translations": [...] } or { "data": [...] } or just [...] if model ignored constraint
                        if isinstance(data, list):
                            return data
                        for key in ['translations', 'data', 'list']:
                            if key in data and isinstance(data[key], list):
                                return data[key]
                        # If dict but no known key, maybe it used indices?
                        # Fallback
                    except json.JSONDecodeError:
                        pass
                        
                except Exception as e:
                    print(f"Batch Attempt {attempt+1} Error: {e}")
            return None

        # Updates to System Msg for the wrapper requirement
        system_msg += "Output format: { \"translations\": [ \"str1\", \"str2\" ] }"

        translations = attempt_translation(retries=1)
        
        if translations and len(translations) == len(texts):
            return translations
        
        # Fallback: Line-by-line (Slow but safe) if batch fails
        print("Batch translation failed or mismatched. Falling back to line-by-line...")
        fallback_results = []
        for text in texts:
            try:
                # specific individual prompt
                res = self.client.chat.completions.create(
                     model=self.model,
                     messages=[
                         {"role": "system", "content": f"Translate to {tgt_lang}. Output ONLY the translation."},
                         {"role": "user", "content": text}
                     ],
                     temperature=0.3
                )
                fallback_results.append(res.choices[0].message.content.strip())
            except:
                fallback_results.append(text) # worst case
        
        return fallback_results

    def translate_single(self, text, glossary=None, src_lang="Japanese", tgt_lang="Traditional Chinese"):
        """
        Translates a single segment efficiently for the Web UI.
        No JSON overhead, just direct text-to-text.
        """
        glossary_str = ""
        if glossary:
            # Simple keyword matching
            relevant = {k: v for k, v in glossary.items() if k in text}
            if relevant:
                glossary_str = f"Glossary:\n{json.dumps(relevant, ensure_ascii=False)}\n"
        
        prompt = f"""
        You are a professional translator. Translate the following {src_lang} text to {tgt_lang}.
        Output ONLY the translation. Do not include notes or explanations.
        
        {glossary_str}
        
        Text:
        {text}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Single Translation Error: {e}")
            return None
