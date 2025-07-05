"""
Error handling utilities for OpenAI/OpenRouter API calls
"""

from openai import (
    RateLimitError, 
    AuthenticationError, 
    PermissionDeniedError, 
    BadRequestError, 
    APIConnectionError, 
    APITimeoutError, 
    InternalServerError, 
    APIError
)

def handle_openai_error(func):
    """
    Decorator to handle OpenAI API errors with detailed messages and suggestions.
    
    Usage:
        @handle_openai_error
        def my_api_function():
            # Your OpenAI API call here
            return result
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RateLimitError as e:
            print(f"🚫 Rate limit exceeded: {e}")
            print("💡 Suggestion: Wait a few minutes before trying again, or upgrade to a paid plan")
            return None
        except AuthenticationError as e:
            print(f"🔑 Authentication failed: {e}")
            print("💡 Suggestion: Check your OPENROUTER_API_KEY in .env file")
            return None
        except PermissionDeniedError as e:
            print(f"⛔ Permission denied: {e}")
            print("💡 Suggestion: Your API key may not have access to this model")
            return None
        except BadRequestError as e:
            print(f"❌ Bad request: {e}")
            print("💡 Suggestion: Check the prompt format or model parameters")
            return None
        except APIConnectionError as e:
            print(f"🌐 Network connection error: {e}")
            print("💡 Suggestion: Check your internet connection")
            return None
        except APITimeoutError as e:
            print(f"⏰ Request timeout: {e}")
            print("💡 Suggestion: The API request took too long, try again")
            return None
        except InternalServerError as e:
            print(f"🔧 OpenRouter server error: {e}")
            print("💡 Suggestion: The API is having issues, try again in a few minutes")
            return None
        except APIError as e:
            print(f"🚨 OpenRouter API error: {e}")
            print("💡 This could be a model overload or temporary service issue")
            return None
        except Exception as e:
            print(f"🔥 Unexpected error: {type(e).__name__}: {e}")
            print("💡 This is likely a code issue, not an API issue")
            return None
    
    return wrapper 