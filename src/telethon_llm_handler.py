"""
This file contains the specialized, hardened LLM processing logic 
for the Telethon News Flow. It is kept separate to avoid impacting
the primary RSS and Alert flows.
"""
import asyncio
import json

from src.llm_handler import get_completion, get_language_name
from src.prompts import get_structured_news_summary_prompt, get_structured_translation_prompt

# --- Hardened processing path for Telethon News Flow ---

async def summarize_news_content_telethon(news_text, source_lang_code):
    """A hardened version of summarize_news_content for the Telethon flow."""
    prompt = get_structured_news_summary_prompt(news_text, source_lang_code)
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "news_summary", "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["headline", "body"], "additionalProperties": False
            }
        }
    }
    try:
        response = get_completion(prompt, response_format=response_format)
        if not response:
            print("❌ [Telethon] News summarization failed - all models unavailable")
            return None

        data = json.loads(response)
        headline = (data.get("headline") or "").strip()
        body = (data.get("body") or "").strip()
        if not body:
            print("❌ [Telethon] Empty JSON summary body")
            return None
        return {"headline": headline, "body": body}
    except Exception as e:
        print(f"❌ [Telethon] Error summarizing news (structured): {e}")
        return None

async def translate_text_immediately_telethon(text, source_language_code, target_language_code):
    """A hardened version of translate_text_immediately for the Telethon flow."""
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
            print(f"❌ [Telethon] Translation to {target_language_name} failed - all models unavailable")
            return None

        data = json.loads(response)
        translated = (data.get("translation") or "").strip()
        if not translated:
            print(f"❌ [Telethon] Empty JSON translation to {target_language_name}")
            return None
        return translated
    except Exception as e:
        print(f"❌ [Telethon] Error translating text to {target_language_name} (structured): {e}")
        return None

async def summarize_and_translate_news_telethon(news_text, source_lang_code):
    """Orchestrator for the hardened Telethon news processing pipeline."""
    print(f"📝 [Telethon] Summarizing {get_language_name(source_lang_code)} news content (hardened path)...")
    summary = await summarize_news_content_telethon(news_text, source_lang_code)

    if not summary:
        print("❌ [Telethon] Cannot proceed with translation - summarization failed")
        return {}

    headline = summary.get("headline", "")
    body = summary.get("body", "")

    translations = {source_lang_code: {"headline": headline, "body": body}}
    target_langs = {'he', 'en', 'es'} - {source_lang_code}

    print("🔄 [Telethon] Translating headline + body to all languages (hardened path)...")
    for lang in target_langs:
        body_task = translate_text_immediately_telethon(body, source_lang_code, lang)
        headline_task = translate_text_immediately_telethon(headline, source_lang_code, lang) if headline else None

        tasks_to_run = [body_task]
        if headline_task:
            tasks_to_run.append(headline_task)

        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

        t_body = results[0] if results[0] and not isinstance(results[0], Exception) else None
        t_headline = ""
        if headline_task:
            t_headline = results[1] if len(results) > 1 and results[1] and not isinstance(results[1], Exception) else ""

        if t_body:
            translations[lang] = {"headline": t_headline, "body": t_body}
        else:
            print(f"❌ [Telethon] Skipping {get_language_name(lang)} - translation failed")

    return translations
