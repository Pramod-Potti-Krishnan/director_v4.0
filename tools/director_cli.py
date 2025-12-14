#!/usr/bin/env python3
"""
Director Agent v4.0 - Interactive CLI Debug Tool

Usage:
    python tools/director_cli.py [--url URL] [--session SESSION_ID]

Features:
    - Real-time WebSocket message display
    - Color-coded message types
    - Raw JSON toggle with 'j' command
    - Commands: j (toggle JSON), q (quit), r (reconnect)
"""

import asyncio
import websockets
import json
import ssl
import uuid
import sys
from datetime import datetime

# ANSI color codes
COLORS = {
    'reset': '\033[0m',
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'gray': '\033[90m',
    'bold': '\033[1m',
}

def color(text, color_name):
    return f"{COLORS.get(color_name, '')}{text}{COLORS['reset']}"

def format_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def print_message(msg_type, payload, raw_json=None, show_raw=False):
    """Pretty-print a WebSocket message."""
    ts = color(f"[{format_timestamp()}]", 'gray')

    if msg_type == 'chat_message':
        text = payload.get('text', '')
        print(f"{ts} {color('CHAT:', 'green')} {text}")

    elif msg_type == 'action_request':
        prompt = payload.get('prompt_text', '')
        actions = [a.get('label') for a in payload.get('actions', [])]
        print(f"{ts} {color('ACTION:', 'yellow')} {prompt}")
        for i, action in enumerate(actions, 1):
            print(f"    {color(f'[{i}]', 'cyan')} {action}")

    elif msg_type == 'slide_update':
        slides = payload.get('slides', [])
        metadata = payload.get('metadata', {})
        title = metadata.get('main_title', 'Untitled')
        print(f"{ts} {color('SLIDES:', 'blue')} {len(slides)} slides for '{title}'")
        for i, slide in enumerate(slides):
            slide_title = slide.get('title', f'Slide {i+1}')
            print(f"    {color(f'[{i+1}]', 'cyan')} {slide_title}")

    elif msg_type == 'status_update':
        status = payload.get('status', '')
        text = payload.get('text', '')
        print(f"{ts} {color('STATUS:', 'magenta')} [{status}] {text}")

    elif msg_type == 'presentation_url':
        url = payload.get('url', '')
        print(f"{ts} {color('PRESENTATION:', 'green')} {url}")

    else:
        print(f"{ts} {color(f'{msg_type.upper()}:', 'gray')} {str(payload)[:200]}")

    if show_raw and raw_json:
        print(f"    {color('RAW:', 'gray')} {json.dumps(raw_json, indent=2)[:500]}")

async def receive_messages(ws, show_raw_ref):
    """Background task to receive and display messages."""
    try:
        async for message in ws:
            try:
                data = json.loads(message)
                msg_type = data.get('type', 'unknown')
                payload = data.get('payload', {})
                print_message(msg_type, payload, data, show_raw_ref[0])
                print(f"{color('> ', 'cyan')}", end='', flush=True)  # Re-print prompt
            except json.JSONDecodeError:
                print(color(f"[RAW] {message[:200]}", 'red'))
    except websockets.ConnectionClosed:
        print(color("\nConnection closed", 'yellow'))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(color(f"\nReceive error: {e}", 'red'))

async def send_message(ws, text):
    """Send a user message."""
    msg = {
        "type": "user_message",
        "data": {"text": text}
    }
    await ws.send(json.dumps(msg))
    ts = color(f"[{format_timestamp()}]", 'gray')
    print(f"{ts} {color('>>> YOU:', 'cyan')} {text}")

async def main(url=None, session_id=None):
    """Main CLI loop."""
    if not session_id:
        session_id = f"cli-debug-{uuid.uuid4().hex[:8]}"

    if not url:
        url = "wss://directorv33-production.up.railway.app"

    full_url = f"{url}/ws?session_id={session_id}&user_id=cli-debug-user"

    print(color("=" * 60, 'bold'))
    print(color("Director Agent v4.0 - CLI Debug Tool", 'bold'))
    print(color("=" * 60, 'bold'))
    print(f"Session: {color(session_id, 'cyan')}")
    print(f"URL: {color(full_url, 'gray')}")
    print(color("-" * 60, 'gray'))
    print("Commands:")
    print(f"  {color('j', 'yellow')} - Toggle raw JSON display")
    print(f"  {color('q', 'yellow')} - Quit")
    print(f"  {color('r', 'yellow')} - Reconnect")
    print(color("-" * 60, 'gray'))

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Use a mutable reference for show_raw so the receive task can see updates
    show_raw_ref = [False]

    try:
        async with websockets.connect(
            full_url,
            ssl=ssl_context,
            ping_interval=30,
            ping_timeout=10
        ) as ws:
            print(color("Connected!\n", 'green'))

            # Start receive task
            receive_task = asyncio.create_task(receive_messages(ws, show_raw_ref))

            # Input loop
            while True:
                try:
                    print(f"{color('> ', 'cyan')}", end='', flush=True)
                    # Use asyncio to read stdin
                    loop = asyncio.get_event_loop()
                    line = await loop.run_in_executor(None, sys.stdin.readline)
                    line = line.strip()

                    if not line:
                        continue

                    if line.lower() == 'q':
                        print(color("Goodbye!", 'yellow'))
                        break
                    elif line.lower() == 'j':
                        show_raw_ref[0] = not show_raw_ref[0]
                        print(color(f"Raw JSON: {'ON' if show_raw_ref[0] else 'OFF'}", 'yellow'))
                    elif line.lower() == 'r':
                        print(color("Reconnecting...", 'yellow'))
                        break
                    else:
                        await send_message(ws, line)

                except KeyboardInterrupt:
                    print(color("\nInterrupted", 'yellow'))
                    break

            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        print(color(f"Connection error: {e}", 'red'))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Director Agent CLI Debug Tool")
    parser.add_argument("--url", default="wss://directorv33-production.up.railway.app",
                        help="WebSocket URL")
    parser.add_argument("--session", default=None, help="Session ID")
    args = parser.parse_args()

    asyncio.run(main(args.url, args.session))
