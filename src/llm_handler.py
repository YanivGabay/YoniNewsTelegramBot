from openai import OpenAI
from src.config import OPENROUTER_API_KEY, YOUR_SITE_URL, YOUR_SITE_NAME
from src.prompts import get_translation_prompt, get_batch_filter_prompt, get_translation_prompt_all_three, get_alert_translation_prompt, get_news_summarization_prompt
from src.error_handler import handle_openai_error

def clean_response_for_logging(response, max_length=500):
    """Clean response text to prevent log spam from excessive whitespace"""
    if not response:
        return "None"
    
    # Replace newlines and carriage returns with escaped versions
    cleaned = response.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    
    # Truncate if too long
    if len(cleaned) > max_length:
        half = max_length // 2
        cleaned = cleaned[:half] + "...[TRUNCATED]..." + cleaned[-half:]
    
    return cleaned

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

@handle_openai_error
def get_completion(prompt, model="deepseek/deepseek-r1-0528:free", response_format=None):
    
    if not OPENROUTER_API_KEY:
        print("      ERROR: OPENROUTER_API_KEY not set.")
        return "Error: OPENROUTER_API_KEY is not set."

    # Build the request parameters
    request_params = {
        "extra_headers": {
            "HTTP-Referer": YOUR_SITE_URL,
            "X-Title": YOUR_SITE_NAME,
        },
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    
    # Add response_format if provided (for structured outputs)
    if response_format:
        request_params["response_format"] = response_format
        
    print("      ...preparing to call OpenRouter API...")
    completion = client.chat.completions.create(**request_params)
    print("      ...API call completed.")

    if not completion or not completion.choices:
        print("      API response is invalid or empty.")
        return None

    response_content = completion.choices[0].message.content
    
    # CRITICAL: Clean response immediately to prevent log spam from excessive whitespace
    if response_content and ('\n\n\n' in response_content or len(response_content.split('\n')) > 100):
        # Suspicious response with excessive newlines - clean it
        lines = response_content.split('\n')
        # Remove excessive empty lines but keep structure
        cleaned_lines = []
        consecutive_empty = 0
        for line in lines:
            if line.strip() == '':
                consecutive_empty += 1
                if consecutive_empty <= 2:  # Allow max 2 consecutive empty lines
                    cleaned_lines.append(line)
            else:
                consecutive_empty = 0
                cleaned_lines.append(line)
        
        response_content = '\n'.join(cleaned_lines)
        print(f"      🧹 Cleaned response: removed {len(lines) - len(cleaned_lines)} excessive empty lines")

    return response_content

def get_structured_batch_filter_completion(articles_preview, source_lang_name, num_articles):
    """Get structured JSON response for batch filtering using OpenRouter's structured outputs."""
    
    # Create JSON schema for the response
    properties = {}
    required = []
    
    for i in range(1, num_articles + 1):
        properties[f"article_{i}"] = {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["NEWS", "AD"],
                    "description": "Whether this is news content or advertisement"
                },
                "rating": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "description": "Importance rating (0 for ads, 1-10 for news)"
                }
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
    response = get_completion(prompt, model="deepseek/deepseek-r1-0528:free", response_format=response_format)
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
    
    # Create previews for batch processing
    articles_preview = ""
    for i, article in enumerate(articles, 1):
        title = article.get('title', '')
        summary = article.get('summary', '')
        
        # Create much shorter preview text to reduce tokens
        if title:
            # Title + small amount of summary
            short_summary = summary[:preview_length] if summary else ""
            if short_summary:
                preview_text = f"{title}\n{short_summary}..."
            else:
                preview_text = title
        else:
            # Just the summary, but shorter
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
    
    # Parse structured JSON response
    results = []
    try:
        import json
        ratings_data = json.loads(response)
        
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
                # Fallback if article not in response
                results.append((article, 5))
                print(f"  ⚠️  Article {i+1}: Missing from response, defaulting to NEWS:5")
                
    except Exception as e:
        print(f"⚠️  Error parsing structured response: {e}")
        # Clean raw response preview to avoid log spam
        raw_preview = response.replace('\n', '\\n').replace('\r', '\\r')
        if len(raw_preview) > 200:
            raw_preview = raw_preview[:100] + "..." + raw_preview[-100:]
        print(f"   Raw response preview: {raw_preview}")
        # Fallback: treat all as NEWS with medium rating
        results = [(article, 5) for article in articles]
    
    print(f"📊 Batch filter result: {len(results)}/{len(articles)} articles kept")
    return results



async def translate_alert_immediately(alert_text, target_language_code):
    """
    Translates an emergency alert message immediately to the target language.
    
    Args:
        alert_text (str): The Hebrew alert text to translate
        target_language_code (str): Target language code ('en' or 'es')
    
    Returns:
        str: Translated alert text, or original text if translation fails
    """
    target_language_name = get_language_name(target_language_code)
    prompt = get_alert_translation_prompt(alert_text, target_language_name)
    
    try:
        # Use DeepSeek for consistent model usage
        response = get_completion(prompt, model="deepseek/deepseek-r1-0528:free")
        if response:
            return response.strip()
        else:
            print(f"⚠️  Alert translation to {target_language_name} failed, returning original")
            return alert_text
    except Exception as e:
        print(f"❌ Error translating alert to {target_language_name}: {e}")
        return alert_text

async def translate_alert_to_all_languages(alert_text):
    """
    Translates an alert to all three languages immediately.
    
    Args:
        alert_text (str): The Hebrew alert text
        
    Returns:
        dict: {'he': original_text, 'en': english_translation, 'es': spanish_translation}
    """
    translations = {'he': alert_text}  # Original Hebrew
    
    # Translate to English and Spanish concurrently
    import asyncio
    
    english_task = translate_alert_immediately(alert_text, 'en')
    spanish_task = translate_alert_immediately(alert_text, 'es')
    
    english_translation, spanish_translation = await asyncio.gather(
        english_task, spanish_task, return_exceptions=True
    )
    
    translations['en'] = english_translation if not isinstance(english_translation, Exception) else alert_text
    translations['es'] = spanish_translation if not isinstance(spanish_translation, Exception) else alert_text
    
    return translations

async def summarize_news_content(news_text, source_lang_code):
    """
    Summarizes news content into a concise, factual summary.
    
    Args:
        news_text (str): The news text to summarize
        source_lang_code (str): Language code of the source ('he', 'en', 'es')
        
    Returns:
        str: Summarized text in the same language, or original text if summarization fails
    """
    prompt = get_news_summarization_prompt(news_text, source_lang_code)
    
    try:
        # Use DeepSeek for consistent model usage
        response = get_completion(prompt, model="deepseek/deepseek-r1-0528:free")
        if response:
            return response.strip()
        else:
            print("⚠️  News summarization failed, returning original")
            return news_text
    except Exception as e:
        print(f"❌ Error summarizing news: {e}")
        return news_text

async def summarize_and_translate_news(news_text, source_lang_code):
    """
    Summarizes news content and translates to all three languages.
    
    Args:
        news_text (str): The news text to summarize
        source_lang_code (str): Language code of the source ('he', 'en', 'es')
        
    Returns:
        dict: {'he': content, 'en': content, 'es': content}
    """
    # First, summarize the content in its original language
    print(f"📝 Summarizing {get_language_name(source_lang_code)} news content...")
    summarized_content = await summarize_news_content(news_text, source_lang_code)
    
    # Then translate the summary to all languages
    print("🔄 Translating summary to all languages...")
    translations = await translate_alert_to_all_languages(summarized_content)
    
    return translations

def get_translations_all_three(article_text, source_lang_code):
    """
    Translates article to ALL three languages (he, en, es) including cleaned source.
    Returns a dictionary with all 3 languages.
    """
    all_langs = {'he', 'en', 'es'}
    translations_to_request = [get_language_name(lang) for lang in all_langs]
    source_lang_name = get_language_name(source_lang_code)

    prompt = get_translation_prompt_all_three(article_text, source_lang_name, translations_to_request)
    raw_response = get_completion(prompt)
    if not raw_response:
        return {}

    # Parse the structured response for all 3 languages
    translations = {}
    for lang_code in all_langs:
        lang_name_upper = get_language_name(lang_code).upper()
        start_tag = f"---YONI-NEWS-{lang_name_upper}-START---"
        end_tag = f"---YONI-NEWS-{lang_name_upper}-END---"
        try:
            start_index = raw_response.find(start_tag)
            if start_index == -1:
                continue
            start_index += len(start_tag)
            end_index = raw_response.find(end_tag)
            if end_index == -1:
                end_index = raw_response.find(end_tag, start_index)
                if end_index == -1:
                    continue
            
            translation_text = raw_response[start_index:end_index].strip()
            if translation_text:
                # Reconstruct title/summary structure for translated text
                parts = translation_text.split('\n', 1)
                if len(parts) > 1 and article_text.count('\n') > 0:
                    translations[lang_code] = {'title': parts[0], 'summary': parts[1].strip()}
                else:
                    translations[lang_code] = {'title': '', 'summary': translation_text}
        except Exception as e:
            print(f"Could not parse translation for {lang_name_upper}: {e}")

    return translations

def get_translations(article_text, source_lang_code):
    """
    Translates article to the other two languages from the set (he, en, es).
    Returns a dictionary of the translated texts.
    """
    target_langs = {'he', 'en', 'es'}
    if source_lang_code in target_langs:
        target_langs.remove(source_lang_code)

    translations_to_request = [get_language_name(lang) for lang in target_langs]
    source_lang_name = get_language_name(source_lang_code)

    prompt = get_translation_prompt(article_text, source_lang_name, translations_to_request)
    raw_response = get_completion(prompt)
    if not raw_response:
        return {}

    # Parse the structured response
    translations = {}
    for lang_code in target_langs:
        lang_name_upper = get_language_name(lang_code).upper()
        start_tag = f"---YONI-NEWS-{lang_name_upper}-START---"
        end_tag = f"---YONI-NEWS-{lang_name_upper}-END---"
        try:
            start_index = raw_response.find(start_tag)
            if start_index == -1:
                continue
            start_index += len(start_tag)
            end_index = raw_response.find(end_tag)
            if end_index == -1:
                # Try finding the end tag from the start tag's position
                end_index = raw_response.find(end_tag, start_index)
                if end_index == -1:
                    continue
            
            translation_text = raw_response[start_index:end_index].strip()
            if translation_text:
                # Reconstruct title/summary structure for translated text
                parts = translation_text.split('\n', 1)
                if len(parts) > 1 and article_text.count('\n') > 0:
                     # This logic assumes the first line of the translation is the title
                    translations[lang_code] = {'title': parts[0], 'summary': parts[1].strip()}
                else:
                    translations[lang_code] = {'title': '', 'summary': translation_text}
        except Exception as e:
            print(f"Could not parse translation for {lang_name_upper}: {e}")

    return translations


if __name__ == '__main__':
    test_article_en = "A new study shows that programming with an AI assistant can significantly increase developer productivity.\nThis is the summary part of the article."
    print("--- Testing English to Hebrew/Spanish ---")
    translations_from_en = get_translations(test_article_en, 'en')
    for lang, content in translations_from_en.items():
        print(f"--- Translation to {get_language_name(lang)} ---")
        print(f"Title: {content['title']}")
        print(f"Summary: {content['summary']}")
        print("\n")

    test_article_he = "מחקר חדש מראה כי תכנות עם עוזר AI יכול להגדיל משמעותית את הפרודוקטיביות של מפתחים."
    print("--- Testing Hebrew to English/Spanish ---")
    translations_from_he = get_translations(test_article_he, 'he')
    for lang, text in translations_from_he.items():
        print(f"--- Translation to {get_language_name(lang)} ---")
        print(text)
        print("\n") 