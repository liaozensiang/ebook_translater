import argparse
import os
import sys

# Allow running as script from root or src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.aligner import Aligner
from src.translator import Translator
from src.llm_client import LLMClient
import json

def main():
    parser = argparse.ArgumentParser(description='EPUB Translator')
    subparsers = parser.add_subparsers(dest='command')

    # Valid default model
    default_model = os.getenv('LLM_MODEL', 'Qwen/Qwen2.5-7B-Instruct')

    # Align command
    align_parser = subparsers.add_parser('align')
    align_parser.add_argument('--source', required=True, help='Source Logic EPUB (e.g. JP, EN)')
    align_parser.add_argument('--reference', required=True, help='Reference Translated EPUB (e.g. ZH, ES)')
    align_parser.add_argument('--out', default='glossary.json', help='Output Glossary JSON')
    align_parser.add_argument('--model', default=default_model, help='LLM Model Name')
    align_parser.add_argument('--src-lang', default='Japanese', help='Source Language')
    align_parser.add_argument('--tgt-lang', default='Traditional Chinese', help='Target Language')

    # Translate command
    trans_parser = subparsers.add_parser('translate')
    trans_parser.add_argument('--input', required=True, help='Input JP EPUB')
    trans_parser.add_argument('--output', required=True, help='Output EPUB')
    trans_parser.add_argument('--glossary', default='glossary.json', help='Glossary JSON')
    # Extract Glossary command
    extract_parser = subparsers.add_parser('extract-glossary')
    extract_parser.add_argument('--input', required=True, help='Input JP EPUB')
    extract_parser.add_argument('--base_glossary', default='glossary.json', help='Base Glossary JSON to update')
    extract_parser.add_argument('--model', default=default_model, help='LLM Model Name')
    extract_parser.add_argument('--src-lang', default='Japanese', help='Source Language')
    extract_parser.add_argument('--tgt-lang', default='Traditional Chinese', help='Target Language')

    # --- Prepare Session Command ---
    prepare_parser = subparsers.add_parser('prepare', help='Prepare a review session from an EPUB')
    prepare_parser.add_argument('--input', required=True, help='Path to input EPUB (e.g., source/40.epub)')
    prepare_parser.add_argument('--glossary', default='glossary.json', help='Path to glossary.json')
    prepare_parser.add_argument('--work-dir', default='/app/work_session', help='Directory to store session data')
    prepare_parser.add_argument('--model', default=default_model, help='Model name')
    prepare_parser.add_argument('--src-lang', default='Japanese', help='Source Language (e.g. Japanese, English)')
    prepare_parser.add_argument('--tgt-lang', default='Traditional Chinese', help='Target Language (e.g. Traditional Chinese, Spanish)')
    prepare_parser.add_argument('--auto-translate', action='store_true', help='Automatically translate all segments with LLM')

    review_parser = subparsers.add_parser('review', help='Start the Web Review Server')
    review_parser.add_argument('--port', type=int, default=5000, help='Port to run server on')
    review_parser.add_argument('--model', default=default_model, help='LLM Model Name')

    # --- Export Command ---
    export_parser = subparsers.add_parser('export', help='Assemble final EPUB from session')
    export_parser.add_argument('--input', required=True, help='Original JP EPUB (template)')
    export_parser.add_argument('--output', required=True, help='Output ZH EPUB')
    export_parser.add_argument('--work-dir', default='/app/work_session', help='Session directory')

    args = parser.parse_args()

    args = parser.parse_args()

    # Shared Client
    # Only if args.model doesn't exist (e.g. some new command without it), fallback to default_model
    model_name = args.model if hasattr(args, 'model') else default_model
    client = LLMClient(model=model_name)

    if args.command == 'align':
        print(f"Running alignment ({args.src_lang} -> {args.tgt_lang}) and glossary extraction...")
        # Pass generic args
        aligner = Aligner(args.source, args.reference, client)
        pairs = aligner.align_chapters()
        
        # Pass language args for prompt accuracy
        glossary = aligner.extract_glossary_from_pairs(pairs, src_lang=args.src_lang, tgt_lang=args.tgt_lang)
        aligner.save_glossary(glossary, args.out)
        print(f"Glossary saved to {args.out}")

    elif args.command == 'prepare':
        llm = LLMClient(model=args.model) # Need LLM just initialized, though prepare only needs text processing
        # Use Translator class to leverage existing epub loading logic
        translator = Translator(llm, args.glossary)
        translator.prepare_review_session(args.input, args.work_dir, args.src_lang, args.tgt_lang, args.auto_translate)

    elif args.command == 'review':
        print(f"Starting Review Server on port {args.port} with model {args.model}...")
        
        # Pass model to server via env var
        os.environ['LLM_MODEL'] = args.model
        
        # We need to run the flask app import here
        # To avoid circular imports or issues, we can just run the server.py directly or import function
        from src.server import app
        app.run(host='0.0.0.0', port=args.port)

    elif args.command == 'export':
        # Need Translator for Epub logic
        llm = LLMClient() 
        translator = Translator(llm)
        translator.assemble_epub(args.input, args.work_dir, args.output)

    elif args.command == 'extract-glossary':
        print(f"Extracting new terms from {args.input}...")
        # Initialize translator just for glossary access
        translator = Translator(client, args.base_glossary)
        translator.extract_terms_from_epub(args.input, args.src_lang, args.tgt_lang, update_existing=True)


    else:
        parser.print_help()

if __name__ == '__main__':
    main()
