"""
AI Prompts for YoniNews Telegram Bot
All prompts are stored here for easy maintenance and modification.
"""

def _get_language_name(source_lang_code):
    """Helper function to get language name from code."""
    lang_map = {
        'he': 'Hebrew',
        'en': 'English', 
        'es': 'Spanish'
    }
    return lang_map.get(source_lang_code, source_lang_code)



def get_batch_filter_prompt(articles_preview, source_lang_name):
    """Returns the prompt for batch filtering and rating multiple articles."""
    return f"""
You are a content filter and importance rater for a news service. Your job is to:
1. Identify if each item is NEWS or ADVERTISEMENT 
2. Rate NEWS items 1-10 for importance (10 = breaking news, 1 = minor news)
3. Rate ADS as 0

The content is in {source_lang_name}.

**RESPONSE FORMAT (CRITICAL):**
You MUST respond with ONLY the ratings in this exact format:
1:NEWS:8, 2:AD:0, 3:NEWS:6, 4:NEWS:9

**DO NOT INCLUDE:**
- No explanations
- No bullet points  
- No additional text
- No notes
- No reasoning

**RATING SCALE:**
- 10: Breaking/urgent news (wars, major political events)
- 8-9: Important news (elections, significant policies) 
- 6-7: Regular news (standard political/global updates)
- 4-5: Minor news (small updates, local events)
- 1-3: Barely newsworthy
- 0: Advertisement/commercial content

**ARTICLES TO RATE:**
{articles_preview}

**YOUR RESPONSE (ONLY the comma-separated ratings):**"""



def get_alert_translation_prompt(alert_text, target_language):
    """Returns the prompt for translating emergency alerts immediately."""
    return f"""
You are an emergency alert translator. Your job is to translate urgent security alerts immediately and accurately while preserving ALL critical information.

**CRITICAL REQUIREMENTS:**
1. Preserve ALL location names, area names, and geographic references EXACTLY
2. Preserve ALL times, dates, and duration information EXACTLY  
3. Preserve ALL security terminology and alert types
4. Maintain the URGENT tone and formatting
5. Keep ALL emojis and warning symbols
6. Do NOT add explanations or commentary
7. Translate quickly and accurately

**TRANSLATE FROM HEBREW TO {target_language.upper()}:**

---
{alert_text}
---

**TRANSLATED ALERT:**"""

def get_generic_translation_prompt(text, source_language, target_language):
    """Returns a generic prompt for translating text."""
    return f"""
Translate the following text from {source_language} to {target_language}.
Provide only the translated text. Do not add any titles, notes, or explanations.

---
{text}
---
"""

def get_news_summarization_prompt(news_text, source_lang_code):
    """Returns the prompt for summarizing news channel content."""
    source_lang_name = _get_language_name(source_lang_code)
    return f"""
You are a professional news summarizer for YoniNews. Your job is to take a {source_lang_name} news message and create a clear, concise summary that captures the essential information.

**CRITICAL REQUIREMENTS:**
1. Create a clear, factual summary of the news content
2. Preserve all important names, places, dates, and numbers
3. Remove any channel branding, promotional text, or non-news content
4. Keep the tone professional and neutral
5. Focus on the key facts: WHO, WHAT, WHEN, WHERE, WHY
6. Maximum length: 2-3 sentences for short news, 4-5 sentences for longer articles
7. Write in {source_lang_name} (same language as source)
8. Do NOT translate - only summarize

**NEWS CONTENT TO SUMMARIZE:**
---
{news_text}
---

**SUMMARIZED NEWS:**"""

def get_structured_news_summary_prompt(news_text, source_lang_code):
    """Strict prompt for a JSON-only summary with a single 'summary' field."""
    source_lang_name = _get_language_name(source_lang_code)
    return f"""
You are a professional news summarizer for YoniNews. Summarize the following {source_lang_name} news message in {source_lang_name}.

RULES (STRICT):
- Write 2-4 sentences, clear and factual.
- Preserve important names, locations, dates, and numbers.
- Do NOT include headings, titles, bullet points, explanations, justifications, compliance/verification notes, reasoning, or commentary of any kind.
- Do NOT explain what you did. Do NOT describe steps, checks, or criteria. Do NOT include meta-text.
- Do NOT add emojis, markdown, decorative symbols, or visual separators (e.g., ---).
 - Output ONLY valid JSON with this exact shape: {{"summary": "..."}}
- Do NOT include markdown code fences.
- Do NOT include any text before or after the JSON object. Any extra content will be discarded.

SOURCE:
<NEWS>
{news_text}
</NEWS>

Respond ONLY with the JSON object.
"""

def get_structured_translation_prompt(text, source_language, target_language):
    """Strict prompt for a JSON-only translation with a single 'translation' field."""
    return f"""
You are a precise translator.

TASK: Translate from {source_language} to {target_language}.

RULES (STRICT):
- Output ONLY the translation content. No headings, titles, bullet points, explanations, justifications, compliance/verification notes, or commentary.
- Do NOT explain what you did. Do NOT add examples, notes, or meta-text.
- Preserve names, numbers, quotes, and URLs exactly; keep tone neutral and concise.
- Do NOT add emojis, markdown formatting, or visual separators (e.g., ---).
 - Output ONLY valid JSON with this exact shape: {{"translation": "..."}}
- Do NOT include markdown code fences.
- Do NOT include any text before or after the JSON object. Any extra content will be discarded.

SOURCE:
<TEXT>
{text}
</TEXT>

Respond ONLY with the JSON object.
"""
 