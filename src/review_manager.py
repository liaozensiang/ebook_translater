import json
import os
import uuid

class ReviewManager:
    def __init__(self, work_dir):
        self.work_dir = work_dir
        self.session_file = os.path.join(work_dir, "session.json")
        self.session_data = self._load_session()

    def _load_session(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"project_name": "", "segments": []}

    def save_session(self):
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)

    def create_session(self, project_name, segments, glossary_map, src_lang="Japanese", tgt_lang="Traditional Chinese"):
        """
        Initializes a new session.
        segments: list of {"id": str, "jp": str, "zh": str, "status": "pending"}
        glossary_map: complete glossary dict
        """
        self.session_data = {
            "project_name": project_name,
            "src_lang": src_lang,
            "tgt_lang": tgt_lang,
            "glossary": glossary_map,
            "segments": segments
        }
        self.save_session()

    def get_segment(self, segment_id):
        for seg in self.session_data["segments"]:
            if seg["id"] == segment_id:
                # Enrich with glossary matches for UI
                matches = {}
                for term, trans in self.session_data["glossary"].items():
                    if term in seg["jp"]:
                        matches[term] = trans
                seg["glossary_matches"] = matches
                return seg
        return None

    def update_segment_translation(self, segment_id, new_zh):
        for seg in self.session_data["segments"]:
            if seg["id"] == segment_id:
                seg["zh"] = new_zh
                self.save_session()
                return True
        return False

    def approve_segment(self, segment_id):
        for seg in self.session_data["segments"]:
            if seg["id"] == segment_id:
                seg["status"] = "approved"
                self.save_session()
                return True
        return False

    def get_all_segments(self):
        return self.session_data["segments"]

    def export_content(self):
        """Returns the full translated text (list of paragraphs)."""
        return [seg["zh"] for seg in self.session_data["segments"]]
