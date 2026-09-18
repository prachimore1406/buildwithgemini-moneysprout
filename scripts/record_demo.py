import os
import time
import subprocess
import imageio_ffmpeg
from playwright.sync_api import sync_playwright
from generate_music import generate_upbeat_track

output_dir = "/config/.gemini/antigravity/brain/8b827626-7e91-43fe-a673-6c2b6abd6a85"
os.makedirs(output_dir, exist_ok=True)

url = "https://moneysprout-frontend-391165179520.us-east1.run.app"

def smooth_scroll(page, element_selector, distance=400, steps=12, delay=0.12):
    for i in range(steps):
        page.evaluate(f"""
            const el = document.querySelector('{element_selector}');
            if (el) el.scrollTop += {distance / steps};
        """)
        time.sleep(delay)

def smooth_scroll_to_top(page, element_selector, steps=12, delay=0.12):
    for i in range(steps):
        page.evaluate(f"""
            const el = document.querySelector('{element_selector}');
            if (el) el.scrollTop -= el.scrollTop / {steps - i};
        """)
        time.sleep(delay)

def run():
    raw_video_dir = os.path.join(output_dir, "raw_recordings")
    os.makedirs(raw_video_dir, exist_ok=True)

    with sync_playwright() as p:
        print("Launching Chromium browser for complete demo recording...")
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=raw_video_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        print(f"Navigating to {url}...")
        page.goto(url, wait_until="networkidle")
        time.sleep(4)
        
        # 1. Initial overview scroll of all dashboard tiles
        print("Overview scroll of all dashboard tiles...")
        smooth_scroll(page, "#left-panel", distance=500, steps=10, delay=0.12)
        time.sleep(2)
        smooth_scroll(page, "#left-panel", distance=500, steps=10, delay=0.12)
        time.sleep(2)
        smooth_scroll_to_top(page, "#left-panel", steps=10, delay=0.12)
        time.sleep(2)
        
        # 2. Prompt 1: Kid asking about savings goal progress
        prompt_1 = "How close am I to getting my bike?"
        print(f"Sending Prompt 1: {prompt_1}")
        page.fill("#input", prompt_1)
        time.sleep(1.5)
        page.click("#form button[type='submit']")
        
        print("Waiting for Sprout's 1st response...")
        agent_msg_1 = page.locator(".msg-row.agent").nth(0)
        agent_msg_1.wait_for(state="visible", timeout=60000)
        agent_msg_1.locator(".typing-loader").wait_for(state="detached", timeout=60000)
        print("Sprout answered Prompt 1! Pausing to read response...")
        time.sleep(7)
        
        # Scroll left panel down to highlight Active Goals & Streaks
        smooth_scroll(page, "#left-panel", distance=400, steps=10, delay=0.12)
        time.sleep(3)
        
        # 3. Prompt 2: Child asking 'What is delayed gratification?' in kid language
        prompt_2 = "What is delayed gratification?"
        print(f"Sending Prompt 2: {prompt_2}")
        page.fill("#input", prompt_2)
        time.sleep(1.5)
        page.click("#form button[type='submit']")
        
        print("Waiting for Sprout's 2nd response (Omni video, DB lookup, & Habit Badge image)...")
        agent_msg_2 = page.locator(".msg-row.agent").nth(1)
        agent_msg_2.wait_for(state="visible", timeout=120000)
        agent_msg_2.locator(".typing-loader").wait_for(state="detached", timeout=120000)
        
        print("Sprout has answered Prompt 2! Pausing to feature Sprout's full response & generated image...")
        time.sleep(8)
        
        # Scroll chat window down so Sprout's complete response and generated image are fully visible
        smooth_scroll(page, "#log", distance=500, steps=10, delay=0.12)
        time.sleep(6)
        
        # Scroll left panel to top to showcase the newly generated Omni Video Tile auto-playing
        print("Scrolling to top of dashboard to showcase auto-playing Omni Video Tile...")
        smooth_scroll_to_top(page, "#left-panel", steps=12, delay=0.12)
        time.sleep(8)
        
        # Final scroll across all tiles to confirm complete coverage
        print("Final overview scroll covering all dashboard tiles...")
        smooth_scroll(page, "#left-panel", distance=500, steps=10, delay=0.12)
        time.sleep(3)
        smooth_scroll(page, "#left-panel", distance=500, steps=10, delay=0.12)
        time.sleep(4)
        
        # Capture final screenshot
        screenshot_path = os.path.join(output_dir, "demo_final_screenshot.png")
        page.screenshot(path=screenshot_path)
        print(f"Saved final screenshot: {screenshot_path}")
        
        # Get video path
        video_obj = page.video
        video_path = video_obj.path() if video_obj else None
        
        context.close()
        browser.close()
        
        if not video_path or not os.path.exists(video_path):
            print("Raw video not found!")
            return None
            
        print(f"Raw video captured successfully: {video_path}")
        
        # Generate upbeat background audio track matching duration
        upbeat_audio = os.path.join(output_dir, "upbeat_music.wav")
        generate_upbeat_track(upbeat_audio, duration_sec=110.0)
        
        # Merge Video + Upbeat Background Audio using FFmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        final_video_webm = os.path.join(output_dir, "demo_recording.webm")
        final_video_mp4 = os.path.join(output_dir, "demo_recording.mp4")
        
        print("Merging video with upbeat background music track via FFmpeg...")
        cmd_webm = [
            ffmpeg_exe, "-y",
            "-i", video_path,
            "-i", upbeat_audio,
            "-c:v", "copy",
            "-c:a", "libopus",
            "-b:a", "128k",
            "-shortest",
            final_video_webm
        ]
        subprocess.run(cmd_webm, check=True)
        print(f"Created upbeat WebM video: {final_video_webm}")
        
        cmd_mp4 = [
            ffmpeg_exe, "-y",
            "-i", video_path,
            "-i", upbeat_audio,
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            final_video_mp4
        ]
        subprocess.run(cmd_mp4, check=True)
        print(f"Created upbeat MP4 video: {final_video_mp4}")
        
        return final_video_webm

if __name__ == "__main__":
    run()
