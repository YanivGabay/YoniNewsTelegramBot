"""
This file contains the specialized, hardened LLM processing logic 
for the Telethon News Flow. It is kept separate to avoid impacting
the primary RSS and Alert flows.
"""
import asyncio
import re
import json

from src.llm_handler import get_completion, get_language_name
from src.prompts import get_structured_news_summary_prompt, get_structured_translation_prompt

# --- Hardened processing path for Telethon News Flow ---

async def summarize_news_content_telethon(news_text, source_lang_code):
    """A hardened version of summarize_news_content with JSON extraction for the Telethon flow."""
    prompt = get_structured_news_summary_prompt(news_text, source_lang_code)
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "news_summary", "strict": True,
            "schema": {
                "type": "object", "properties": {"summary": {"type": "string"}},
                "required": ["summary"], "additionalProperties": False
            }
        }
    }
    try:
        response = get_completion(prompt, response_format=response_format)
        if not response:
            print("⚠️  [Telethon] News summarization failed, returning original")
            return news_text

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            print("⚠️  [Telethon] Could not extract JSON from summary response, returning original")
            return news_text
        
        data = json.loads(json_match.group(0))
        summary = (data.get("summary") or "").strip()
        if not summary:
            print("⚠️  [Telethon] Empty JSON summary, returning original")
            return news_text
        return summary
    except Exception as e:
        print(f"❌ [Telethon] Error summarizing news (structured): {e}")
        return news_text

async def translate_text_immediately_telethon(text, source_language_code, target_language_code):
    """A hardened version of translate_text_immediately with JSON extraction for the Telethon flow."""
    source_language_name = get_language_name(source_language_code)
    target_language_name = get_language_name(target_language_code)
    prompt = get_structured_translation_prompt(text, source_language_name, target_language_name)
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "translation", "strict": True,
            "schema": {
                "type": "object", "properties": {"translation": {"type": "string"}},
                "required": ["translation"], "additionalProperties": False
            }
        }
    }
    try:
        response = get_completion(prompt, response_format=response_format)
        if not response:
            print(f"⚠️  [Telethon] Translation to {target_language_name} failed, returning original")
            return text

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            print(f"⚠️  [Telethon] Could not extract JSON from translation response to {target_language_name}, returning original")
            return text

        data = json.loads(json_match.group(0))
        translated = (data.get("translation") or "").strip()
        if not translated:
            print(f"⚠️  [Telethon] Empty JSON translation, returning original")
            return text
        return translated
    except Exception as e:
        print(f"❌ [Telethon] Error translating text to {target_language_name} (structured): {e}")
        return text

async def summarize_and_translate_news_telethon(news_text, source_lang_code):
    """Orchestrator for the hardened Telethon news processing pipeline."""
    print(f"📝 [Telethon] Summarizing {get_language_name(source_lang_code)} news content (hardened path)...")
    summarized_content = await summarize_news_content_telethon(news_text, source_lang_code)
    
    # Translate the summary to all languages using the hardened translator
    print("🔄 [Telethon] Translating summary to all languages (hardened path)...")
    
    translations = {source_lang_code: summarized_content}
    target_langs = {'he', 'en', 'es'} - {source_lang_code}
    tasks = []
    for lang in target_langs:
        task = translate_text_immediately_telethon(summarized_content, source_lang_code, lang)
        tasks.append((lang, task))
    
    if tasks:
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        for i, (lang, _) in enumerate(tasks):
            result = results[i]
            translations[lang] = result if not isinstance(result, Exception) else summarized_content
            
    return translations
