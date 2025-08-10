from playwright.sync_api import sync_playwright, Page, expect

def verify_video_library(page: Page):
    """
    This test verifies that the video library page loads correctly.
    """
    # 1. Arrange: Go to the application's homepage.
    page.goto("http://localhost:3000")

    # 2. Assert: Check for the main heading.
    heading = page.get_by_role("heading", name="Video Library")
    expect(heading).to_be_visible()

    # 3. Assert: Since there are no videos, expect to see the "No videos found" message.
    #    This also serves as a wait to ensure the page has loaded.
    no_videos_message = page.get_by_text("No videos found in the library.")
    expect(no_videos_message).to_be_visible()

    # 4. Screenshot: Capture the final result for visual verification.
    page.screenshot(path="jules-scratch/verification/verification.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        verify_video_library(page)
        browser.close()
