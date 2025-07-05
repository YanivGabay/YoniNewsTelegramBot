#!/usr/bin/env python3
"""
Test script for the new time-based memory management system
"""
import time
import sys
import os

# Add src to path so we can import the functions
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from main import cleanup_memory, mark_as_processed, is_already_processed, processed_articles

def test_memory_system():
    """Test the time-based memory management"""
    
    print("🧪 Testing Time-Based Memory Management")
    print("=" * 50)
    
    # Clear any existing memory
    processed_articles.clear()
    
    print("📝 Test 1: Adding articles to memory")
    
    # Add some test articles
    test_articles = [
        "cnn_article_123",
        "ynet_article_456", 
        "reuters_article_789"
    ]
    
    for article_id in test_articles:
        mark_as_processed(article_id)
        print(f"   ✅ Added: {article_id}")
    
    print(f"\n📊 Memory contains {len(processed_articles)} articles")
    
    print("\n📝 Test 2: Checking duplicate detection")
    
    # Test duplicate detection
    for article_id in test_articles:
        is_duplicate = is_already_processed(article_id)
        print(f"   🔍 {article_id}: {'DUPLICATE' if is_duplicate else 'NEW'}")
    
    # Test new article
    new_article = "bbc_article_999"
    is_new = not is_already_processed(new_article)
    print(f"   🔍 {new_article}: {'NEW' if is_new else 'DUPLICATE'}")
    
    print("\n📝 Test 3: Memory cleanup (simulating old articles)")
    
    # Simulate old articles by manually setting old timestamps
    old_time = time.time() - (4 * 60 * 60)  # 4 hours ago
    processed_articles["old_article_1"] = old_time
    processed_articles["old_article_2"] = old_time - 3600  # 5 hours ago
    
    print(f"   📊 Before cleanup: {len(processed_articles)} articles")
    print(f"   📋 Articles: {list(processed_articles.keys())}")
    
    # Run cleanup
    cleanup_memory()
    
    print(f"   📊 After cleanup: {len(processed_articles)} articles")
    print(f"   📋 Remaining: {list(processed_articles.keys())}")
    
    print("\n📝 Test 4: Edge cases")
    
    # Test None/empty values
    print(f"   🔍 None article: {'DUPLICATE' if is_already_processed(None) else 'NEW'}")
    print(f"   🔍 Empty string: {'DUPLICATE' if is_already_processed('') else 'NEW'}")
    
    # Test marking None
    mark_as_processed(None)
    mark_as_processed("")
    print(f"   📊 After marking None/empty: {len(processed_articles)} articles")
    
    print("\n✅ All tests completed!")
    print(f"🎯 Final memory state: {len(processed_articles)} articles")
    
    # Show memory contents with timestamps
    if processed_articles:
        print("\n📋 Current memory contents:")
        current_time = time.time()
        for article_id, timestamp in processed_articles.items():
            age_minutes = (current_time - timestamp) / 60
            print(f"   📰 {article_id}: {age_minutes:.1f} minutes ago")

if __name__ == "__main__":
    test_memory_system() 