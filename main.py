#!/usr/bin/env python3
import argparse
import sys
from src.main import main
import asyncio

def parse_arguments():
    parser = argparse.ArgumentParser(description='YoniNews Telegram Bot')
    parser.add_argument('--dev', '--test', action='store_true', 
                       help='Run in development/test mode (show translations in console without sending to Telegram)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode with verbose logging')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # Show mode information
    if args.dev:
        print("🔧 DEVELOPMENT MODE: Translations will be shown in console only")
        print("📱 No messages will be sent to actual Telegram groups")
        print("-" * 60)
    
    if args.debug:
        print("🐛 DEBUG MODE: Verbose logging enabled")
        print("-" * 60)
    
    # Run the main function with dev mode flag
    asyncio.run(main(dev_mode=args.dev, debug_mode=args.debug))