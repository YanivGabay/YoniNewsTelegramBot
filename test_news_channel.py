#!/usr/bin/env python3
"""
Test script for the Hebrew news channel summarization system
"""
import asyncio
from src.llm_handler import summarize_and_translate_news, get_language_emoji
from src.config import LANGUAGE_CHAT_IDS, SOURCE_NEWS_CHANNEL

async def test_news_summarization():
    """Test the news summarization and translation functionality"""
    
    # Sample Spanish news text (similar to what might come from a news channel)
    sample_news = """
📺 Noticias 24 - Ahora
🔴 Avance tecnológico: Una nueva empresa israelí de tecnología anunció hoy el desarrollo de un sistema de IA avanzado que puede traducir textos en tiempo real a 50 idiomas diferentes. El sistema, desarrollado durante 3 años, está destinado a cambiar el campo de la traducción digital.
La empresa, con sede en Tel Aviv, ya recibió una inversión de 15 millones de dólares de fondos de capital de riesgo internacionales.
💼 El CEO dijo: "Este es solo el comienzo de una revolución tecnológica"
📈 Las acciones subieron un 12% en la bolsa
#Tecnología #AI #Israel #Innovación
    """
    
    print("🧪 Testing Spanish News Channel System")
    print("=" * 60)
    print(f"📝 Sample News Text:")
    print(sample_news)
    print("\n" + "=" * 60)
    
    print("📝 Processing: Summarize → Translate → Format...")
    
    try:
        translations = await summarize_and_translate_news(sample_news, 'es')
        
        if translations:
            print("✅ Processing successful!")
            print("\n📋 Results:")
            
            for lang_code, translated_text in translations.items():
                emoji = get_language_emoji(lang_code)
                lang_name = {"he": "Hebrew", "en": "English", "es": "Spanish (Summarized)"}[lang_code]
                
                print(f"\n{emoji} {lang_name.upper()}:")
                print("-" * 50)
                print(translated_text)
                print("-" * 50)
                
        else:
            print("❌ Processing failed")
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
    
    print("\n" + "=" * 60)
    print("🔧 Configuration Check:")
    
    if SOURCE_NEWS_CHANNEL:
        print(f"✅ News channel configured: @{SOURCE_NEWS_CHANNEL}")
    else:
        print("❌ No news channel configured")
        print("💡 Add SOURCE_NEWS_CHANNEL=YourChannelName to .env")
    
    if LANGUAGE_CHAT_IDS:
        print("✅ Language chat IDs configured:")
        for lang, chat_id in LANGUAGE_CHAT_IDS.items():
            emoji = get_language_emoji(lang)
            print(f"   {emoji} {lang.upper()}: {chat_id}")
    else:
        print("❌ No language chat IDs configured")
        print("💡 Add TELEGRAM_CHAT_ID_HEBREW, TELEGRAM_CHAT_ID_ENGLISH, TELEGRAM_CHAT_ID_SPANISH to .env")
    
    print("\n💡 How it works in real-time:")
    print("1. Bot listens to your Spanish news channel 24/7")
    print("2. New message arrives → Summarize Spanish content")
    print("3. Translate summary to Hebrew & English")
    print("4. Send all 3 versions to respective language groups")
    print("5. No filtering, no caching - every message gets processed!")

if __name__ == "__main__":
    asyncio.run(test_news_summarization()) 