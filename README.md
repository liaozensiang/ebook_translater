# Universal E-Book Translator (Workbench)

A professional, human-in-the-loop translation workbench for EPUBs. Designed for Light Novels but compatible with **any language pair**.

Features:
- **LLM-Powered**: Uses vLLM, DeepSeek, or OpenAI.
- **Visual Workbench**: Human review interface to ensure quality.
- **Reference Alignment**: Learn glossary terms from previous volumes.
- **Glossary Manager**: Edit terms in real-time.
- **Universal**: Translate Japanese->Chinese, English->Spanish, etc.

## 📂 Project Structure

- `source/`: Place your **input** EPUBs here (formerly `raw_jp`).
- `reference/`: Place your **aligned** EPUBs here (for glossary extraction).
- `output/`: Generated EPUBs will appear here.
- `src/`: Source code.

## 🚀 Setup Guides (SOPs)

Choose the guide that matches your hardware:

- **[🔌 Local GPU (RTX 3090/4090)](docs/SOP_Local_GPU.md)**  
  *Run everything on one powerful machine.*
- **[☁️ Remote GPU Server](docs/SOP_Remote_Server.md)**  
  *Run AI on a server, UI on your laptop.*
- **[🔑 API Key (DeepSeek/OpenAI)](docs/SOP_API_Only.md)**  
  *No GPU required. Use cloud APIs.*

## 🛠️ Usage Workflow (New Script Method)

This tool now uses a simplified script-based workflow driven by a `.env` configuration file.

### 1. Configuration
1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` to set your paths and languages:
   ```bash
   INPUT_EPUB=source/40.epub
   OUTPUT_EPUB=output/40_zh.epub
   SRC_LANG=Japanese
   TGT_LANG=Traditional Chinese
   LLM_API_URL=http://localhost:8000/v1
   ```

### 2. Workflow Steps
Run the scripts in order:

1.  **Start vLLM (Optional)**: If you are running the Model locally on this machine.
    ```bash
    ./start_vllm.sh
    ```
    *(Wait for the server to start before proceeding)*

2.  **Step 1: Alignment & Base Glossary**
    Creates a glossary by aligning an existing Source/Translated pair (e.g., Vol 39).
    ```bash
    ./step1_align.sh
    ```

3.  **Step 2: Extract New Terms**
    Scans your **Input EPUB** for new proper nouns and adds them to the glossary.
    ```bash
    ./step2_extract_glossary.sh
    ```

4.  **Step 3: Prepare Session**
    Extracts text from the Input EPUB and prepares a review session.
    ```bash
    ./step3_prepare.sh
    ```

5.  **Step 4: Web Review**
    Starts the Web Interface at http://localhost:5000.
    - Translate segments.
    - Edit glossary terms.
    - Approve translations.
    ```bash
    ./step4_review.sh
    ```

6.  **Step 5: Export EPUB**
    Assembles the final EPUB using your approved translations.
    ```bash
    ./step5_export.sh
    ```

### 3. Verification
Check your `output/` directory for the translated EPUB. The tool uses a surgical modification approach, so all images and layout from the original EPUB are preserved exactly.
