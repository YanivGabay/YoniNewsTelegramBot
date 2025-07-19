from openai import OpenAI, RateLimitError
from src.config import OPENROUTER_API_KEY, YOUR_SITE_URL, YOUR_SITE_NAME
from src.prompts import get_batch_filter_prompt, get_alert_translation_prompt, get_news_summarization_prompt, get_generic_translation_prompt
from src.error_handler import handle_openai_error

def clean_response_for_logging(response, max_length=500):
    if not response:
        return "None"
    
    cleaned = response.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    
    if len(cleaned) > max_length:
        half = max_length // 2
        cleaned = cleaned[:half] + "...[TRUNCATED]..." + cleaned[-half:]
    
    return cleaned

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

# Define model lists: primary and fallback
# The first model in the list is the primary, the rest are fallbacks
MODELS = {
    "default": [
        "deepseek/deepseek-r1-0528:free",
        "meta-llama/llama-3.1-405b-instruct:free",
        "google/gemini-2.5-flash-lite-preview-06-17"
    ]
}

@handle_openai_error
def get_completion(prompt, model_list_name="default", response_format=None):
    if not OPENROUTER_API_KEY:
        print("      ERROR: OPENROUTER_API_KEY not set.")
        return "Error: OPENROUTER_API_KEY is not set."

    model_list = MODELS.get(model_list_name, MODELS["default"])

    for model in model_list:
        try:
            request_params = {
                "extra_headers": {
                    "HTTP-Referer": YOUR_SITE_URL,
                    "X-Title": YOUR_SITE_NAME,
                },
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            }
            
            if response_format:
                request_params["response_format"] = response_format
                
            print(f"      ...preparing to call OpenRouter API with model: {model}...")
            completion = client.chat.completions.create(**request_params)
            print("      ...API call completed.")

            if not completion or not completion.choices:
                print("      API response is invalid or empty.")
                # Continue to next model if this one fails to respond properly
                continue

            response_content = completion.choices[0].message.content
            
            if response_content and ('\n\n\n' in response_content or len(response_content.split('\n')) > 100):
                lines = response_content.split('\n')
                cleaned_lines = []
                consecutive_empty = 0
                for line in lines:
                    if line.strip() == '':
                        consecutive_empty += 1
                        if consecutive_empty <= 2:
                            cleaned_lines.append(line)
                    else:
                        consecutive_empty = 0
                        cleaned_lines.append(line)
                
                response_content = '\n'.join(cleaned_lines)
                print(f"      🧹 Cleaned response: removed {len(lines) - len(cleaned_lines)} excessive empty lines")

            # If we get a successful response, return it immediately
            return response_content
            
        except RateLimitError:
            print(f"      RATE LIMIT: Model '{model}' is rate-limited.")
            # If this is not the last model in the list, we'll try the next one
            if model != model_list[-1]:
                print("      -> Trying next fallback model...")
                continue
            else:
                # If it's the last model, re-raise the exception to be caught by the decorator
                print("      -> All fallback models failed due to rate limits.")
                raise
    
    # If all models fail for reasons other than rate limiting (e.g., invalid response)
    print("      ❌ All models in the list failed to provide a valid response.")
    return None

def get_structured_batch_filter_completion(articles_preview, source_lang_name, num_articles):
    properties = {}
    required = []
    
    for i in range(1, num_articles + 1):
        properties[f"article_{i}"] = {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["NEWS", "AD"]},
                "rating": {"type": "integer", "minimum": 0, "maximum": 10}
            },
            "required": ["type", "rating"],
            "additionalProperties": False
        }
        required.append(f"article_{i}")
    
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "article_ratings",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False
            }
        }
    }
    
    prompt = f"""
You are a content filter and importance rater for a news service. Rate each article:

RATING SCALE:
- 10: Breaking/urgent news (wars, major political events)
- 8-9: Important news (elections, significant policies) 
- 6-7: Regular news (standard political/global updates)
- 4-5: Minor news (small updates, local events)
- 1-3: Barely newsworthy
- 0: Advertisement/commercial content (set type to "AD")

ARTICLES TO RATE ({source_lang_name}):
{articles_preview}

Rate each article and respond with the structured JSON format.
"""
    
    print(f"    -> Calling get_completion for {num_articles} articles.")
    response = get_completion(prompt, response_format=response_format)
    print(f"    <- Returned from get_completion. Response is None: {response is None}")
    return response

def get_language_name(code):
    """Helper function to get full language name from code."""
    if code == 'he': return 'Hebrew'
    if code == 'en': return 'English'
    if code == 'es': return 'Spanish'
    return 'Unknown'

def get_language_emoji(code):
    """Helper function to get a flag emoji from language code."""
    if code == 'he': return '🇮🇱'
    if code == 'en': return '🇺🇸'
    if code == 'es': return '🇪🇸'
    return '🏳️'

def ai_batch_filter_content(articles, source_lang_code, preview_length=80):
    """
    Uses AI to filter and rate multiple articles at once using previews.
    Returns list of tuples: [(article, rating), ...]
    """
    if not articles:
        return []
        
    source_lang_name = get_language_name(source_lang_code)
    
    articles_preview = ""
    for i, article in enumerate(articles, 1):
        title = article.get('title', '')
        summary = article.get('summary', '')
        
        if title:
            short_summary = summary[:preview_length] if summary else ""
            if short_summary:
                preview_text = f"{title}\n{short_summary}..."
            else:
                preview_text = title
        else:
            preview_text = summary[:preview_length] + "..." if summary else "No content"
            
        articles_preview += f"\nArticle {i}: {preview_text}\n"
    
    print(f"🔍 Batch filtering {len(articles)} articles (≤{preview_length} chars each)")
    print("  -> Calling get_structured_batch_filter_completion...")
    
    # Use structured outputs for reliable parsing
    response = get_structured_batch_filter_completion(articles_preview, source_lang_name, len(articles))
    print(f"  <- Returned from get_structured_batch_filter_completion. Response is None: {response is None}")
    
    if not response:
        print("❌ Batch filter failed, defaulting all to NEWS:5")
        return [(article, 5) for article in articles]
    
    # Clean response before logging to avoid excessive whitespace
    response_preview = response.replace('\n', '\\n').replace('\r', '\\r')
    if len(response_preview) > 500:
        response_preview = response_preview[:250] + "..." + response_preview[-250:]
    print(f"📋 AI Response: {response_preview}")
    
    results = []
    try:
        import json
        import re
        
        cleaned_response = response
        if response:
            cleaned_response = re.sub(r'```(?:json)?\s*', '', cleaned_response)
            cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
            cleaned_response = re.sub(r'[\x00-\x1F\x7F]', '', cleaned_response)
        
        ratings_data = json.loads(cleaned_response)
        
        for i, article in enumerate(articles):
            article_key = f"article_{i+1}"
            
            if article_key in ratings_data:
                article_data = ratings_data[article_key]
                content_type = article_data.get('type', 'NEWS')
                rating = article_data.get('rating', 5)
                
                if content_type == 'NEWS' and rating > 0:
                    results.append((article, rating))
                    print(f"  ✅ Article {i+1}: {content_type}:{rating}")
                else:
                    print(f"  ❌ Article {i+1}: {content_type}:{rating} (filtered out)")
            else:
                results.append((article, 5))
                print(f"  ⚠️  Article {i+1}: Missing from response, defaulting to NEWS:5")
                
    except Exception as e:
        print(f"⚠️  Error parsing structured response: {e}")
        raw_preview = response.replace('\n', '\\n').replace('\r', '\\r')
        if len(raw_preview) > 200:
            raw_preview = raw_preview[:100] + "..." + raw_preview[-100:]
        print(f"   Raw response preview: {raw_preview}")
        results = [(article, 5) for article in articles]
    
    print(f"📊 Batch filter result: {len(results)}/{len(articles)} articles kept")
    return results


async def translate_text_immediately(text, source_language_code, target_language_code):
    source_language_name = get_language_name(source_language_code)
    target_language_name = get_language_name(target_language_code)
    prompt = get_generic_translation_prompt(text, source_language_name, target_language_name)
    
    try:
        response = get_completion(prompt)
        if response:
            return response.strip()
        else:
            print(f"⚠️  Generic translation to {target_language_name} failed, returning original")
            return text
    except Exception as e:
        print(f"❌ Error translating text to {target_language_name}: {e}")
        return text

async def translate_text_to_all_languages(text, source_lang_code):
    translations = {source_lang_code: text}
    
    import asyncio
    
    target_langs = {'he', 'en', 'es'} - {source_lang_code}
    tasks = []
    
    for lang in target_langs:
        task = translate_text_immediately(text, source_lang_code, lang)
        tasks.append((lang, task))
        
    if tasks:
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for i, (lang, _) in enumerate(tasks):
            result = results[i]
            translations[lang] = result if not isinstance(result, Exception) else text
            
    return translations


async def translate_alert_immediately(alert_text, target_language_code):
    target_language_name = get_language_name(target_language_code)
    prompt = get_alert_translation_prompt(alert_text, target_language_name)
    
    try:
        # Use DeepSeek and fallbacks for consistent model usage
        response = get_completion(prompt)
        if response:
            return response.strip()
        else:
            print(f"⚠️  Alert translation to {target_language_name} failed, returning original")
            return alert_text
    except Exception as e:
        print(f"❌ Error translating alert to {target_language_name}: {e}")
        return alert_text

async def translate_alert_to_all_languages(alert_text, source_lang='he'):
    translations = {source_lang: alert_text}  # Original in source language
    
    # Translate to other languages
    import asyncio
    
    target_langs = {'he', 'en', 'es'} - {source_lang}
    tasks = []
    
    for lang in target_langs:
        task = translate_alert_immediately(alert_text, lang)
        tasks.append((lang, task))
    
    if tasks:
        results = await asyncio.gather(
            *[task for _, task in tasks], return_exceptions=True
        )
        
        for i, (lang, _) in enumerate(tasks):
            result = results[i]
            translations[lang] = result if not isinstance(result, Exception) else alert_text
    
    return translations

async def summarize_news_content(news_text, source_lang_code):
    prompt = get_news_summarization_prompt(news_text, source_lang_code)
    
    try:
        # Use DeepSeek and fallbacks for consistent model usage
        response = get_completion(prompt)
        if response:
            return response.strip()
        else:
            print("⚠️  News summarization failed, returning original")
            return news_text
    except Exception as e:
        print(f"❌ Error summarizing news: {e}")
        return news_text

async def summarize_and_translate_news(news_text, source_lang_code):
    # First, summarize the content in its original language
    print(f"📝 Summarizing {get_language_name(source_lang_code)} news content...")
    summarized_content = await summarize_news_content(news_text, source_lang_code)
    
    # Then translate the summary to all languages using the generic translator
    print("🔄 Translating summary to all languages...")
    translations = await translate_text_to_all_languages(summarized_content, source_lang_code)
    
    return translations

 