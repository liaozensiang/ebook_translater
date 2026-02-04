from flask import Flask, jsonify, request, send_from_directory
import os
import sys
import json

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.review_manager import ReviewManager
from src.llm_client import LLMClient
from deep_translator import GoogleTranslator

app = Flask(__name__, static_url_path='')
WORK_DIR = "/app/work_session" # runtime mapping
# manager = ReviewManager(WORK_DIR) <-- REMOVED global instance to avoid stale state
# Initialize LLM with model from env var if set
model_name = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
llm = LLMClient(model=model_name)
print(f"Server initialized with model: {model_name}")

@app.route('/')
def root():
    return send_from_directory('static', 'index.html')

@app.route('/api/session', methods=['GET'])
def get_session():
    # Reload in case it changed
    manager = ReviewManager(WORK_DIR)
    return jsonify(manager.session_data)

@app.route('/api/segment/<seg_id>', methods=['POST'])
def update_segment(seg_id):
    manager = ReviewManager(WORK_DIR) # Load latest state
    data = request.json
    if 'zh' in data:
        manager.update_segment_translation(seg_id, data['zh'])
    if data.get('approved'):
        manager.approve_segment(seg_id)
    return jsonify({"status": "ok"})

@app.route('/api/translate/<seg_id>', methods=['POST'])
def translate_segment(seg_id):
    manager = ReviewManager(WORK_DIR) # Load latest state
    seg = manager.get_segment(seg_id)
    if not seg:
        return jsonify({"error": "Segment not found"}), 404
    
    # Run translation efficiently
    glossary = manager.session_data.get("glossary", {})
    src_lang = manager.session_data.get("src_lang", "Japanese")
    tgt_lang = manager.session_data.get("tgt_lang", "Traditional Chinese")
    
    try:
        # Use new optimized single translation
        new_text = llm.translate_single(seg["jp"], glossary, src_lang, tgt_lang)
        if new_text:
            # Auto-save draft
            manager.update_segment_translation(seg_id, new_text)
            return jsonify({"zh": new_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    return jsonify({"error": "Translation failed"}), 500

@app.route('/api/glossary', methods=['GET'])
def get_glossary():
    # Load glossary directly from the active SESSION for consistency with UI
    manager = ReviewManager(WORK_DIR) # Force reload
    session_glossary = manager.session_data.get("glossary", {})
    return jsonify(session_glossary)

@app.route('/api/glossary', methods=['POST'])
def save_glossary():
    # Update Session AND File
    new_glossary = request.json
    
    # 1. Update active session
    manager = ReviewManager(WORK_DIR)
    manager.session_data["glossary"] = new_glossary
    manager.save_session()
    
    # 2. Update persistent file
    glossary_path = "glossary.json" # Default
    with open(glossary_path, 'w', encoding='utf-8') as f:
        json.dump(new_glossary, f, ensure_ascii=False, indent=2)
        
    return jsonify({"status": "saved"})

@app.route('/api/google', methods=['POST'])
def google_translate():
    text = request.json.get('text')
    if not text:
        return jsonify({"error": "No text provided"}), 400
    # Get languages
    manager = ReviewManager(WORK_DIR)
    # Map friendly names to Google Codes (Simplified map, can be expanded)
    # Default to auto -> zh-TW
    
    target_map = {
        "Traditional Chinese": "zh-TW",
        "Simplified Chinese": "zh-CN",
        "English": "en",
        "Japanese": "ja",
        "Korean": "ko"
    }
    tgt_lang_name = manager.session_data.get("tgt_lang", "Traditional Chinese")
    tgt_code = target_map.get(tgt_lang_name, "zh-TW")

    try:
        # translator = GoogleTranslator(source='ja', target='zh-TW')
        # Using auto-detect for source is usually safer
        zh = GoogleTranslator(source='auto', target=tgt_code).translate(text)
        return jsonify({"zh": zh})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure static dir exists
    if not os.path.exists('src/static'):
        os.makedirs('src/static')
    app.run(host='0.0.0.0', port=5000, debug=True)
