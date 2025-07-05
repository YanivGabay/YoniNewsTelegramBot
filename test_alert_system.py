#!/usr/bin/env python3
"""
Test script for the emergency alert system
"""
import asyncio
from src.llm_handler import translate_alert_to_all_languages, get_language_emoji
from src.config import LANGUAGE_CHAT_IDS

async def test_alert_translation():
    """Test the alert translation functionality"""
    
    # Sample alert text (similar to PikudHaOref_all format)
    sample_alert = """🚨 עדכון (24/6/2025) 10:45

ירי רקטות וטילים - האירוע הסתיים
השוהים במרחב המוגן יכולים לצאת. בעת קבלת הנחיה או התרעה, יש לפעול בהתאם להנחיות פיקוד העורף.

אזור גולן דרום
חוף גולן, צאלון, חוף גופרה"""
    
    print("🧪 Testing Emergency Alert Translation System")
    print("=" * 60)
    print(f"📝 Sample Alert Text:")
    print(sample_alert)
    print("\n" + "=" * 60)
    
    print("🔄 Translating to all languages...")
    
    try:
        translations = await translate_alert_to_all_languages(sample_alert)
        
        if translations:
            print("✅ Translation successful!")
            print("\n📋 Results:")
            
            for lang_code, translated_text in translations.items():
                emoji = get_language_emoji(lang_code)
                lang_name = {"he": "Hebrew", "en": "English", "es": "Spanish"}[lang_code]
                
                print(f"\n{emoji} {lang_name.upper()}:")
                print("-" * 40)
                print(translated_text)
                print("-" * 40)
                
        else:
            print("❌ Translation failed")
            
    except Exception as e:
        print(f"❌ Error during translation: {e}")
    
    print("\n" + "=" * 60)
    print("🔧 Configuration Check:")
    
    if LANGUAGE_CHAT_IDS:
        print("✅ Language chat IDs configured:")
        for lang, chat_id in LANGUAGE_CHAT_IDS.items():
            emoji = get_language_emoji(lang)
            print(f"   {emoji} {lang.upper()}: {chat_id}")
    else:
        print("❌ No language chat IDs configured")
        print("💡 Add TELEGRAM_CHAT_ID_HEBREW, TELEGRAM_CHAT_ID_ENGLISH, TELEGRAM_CHAT_ID_SPANISH to .env")

if __name__ == "__main__":
    asyncio.run(test_alert_translation()) 