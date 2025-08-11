import html
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from requests import RequestException

load_dotenv(".env")
BASE_API_URL = os.getenv("BACKED_DEV_HOST", "http://localhost:5000")


@dataclass
class FacebookPost:
    index: int
    author: str
    content: str
    author_link: str
    post_link: str
    delay: str
    timestamp: str
    posinset: str


class FacebookPageParser:

    def __init__(self, input_dir: str = "input", output_dir: str = "output"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.filename_pattern = re.compile(r"^facebook_page_(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}\.\d+Z)\.html$")
        self.cutoff_phrases = ["Like", "Comment", "reactions:", "All reactions:"]

    def normalize_duration(self, duration_str: str) -> str:
        """Normalize the duration string by reversing if it starts with a letter."""
        if duration_str and duration_str[0].isalpha():
            return duration_str[::-1]
        return duration_str

    def find_newest_file(self) -> tuple[str, str, datetime]:
        """Find the newest Facebook page HTML file in the input directory."""
        timestamped_files = []

        if not os.path.exists(self.input_dir):
            raise FileNotFoundError(f"Input directory '{self.input_dir}' not found.")

        for filename in os.listdir(self.input_dir):
            match = self.filename_pattern.match(filename)
            if match:
                timestamp_str = match.group(1)
                try:
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H_%M_%S.%fZ")
                    timestamped_files.append((dt, filename, timestamp_str))
                except ValueError as e:
                    print(f"Warning: Could not parse timestamp in {filename}: {e}")
                    continue

        if not timestamped_files:
            raise FileNotFoundError("No matching facebook_page_*.html files found in the input folder.")

        # Sort by datetime and get the newest
        timestamped_files.sort()
        newest_dt, newest_file, newest_timestamp_str = timestamped_files[-1]

        return newest_file, newest_timestamp_str, newest_dt

    def load_html_content(self, filename: str) -> str:
        """Load HTML content from the specified file."""
        file_path = os.path.join(self.input_dir, filename)
        try:
            with open(file_path, encoding="utf-8") as file:
                return file.read()
        except OSError as e:
            raise OSError(f"Could not read file {file_path}: {e}") from e

    def clean_feed_div(self, feed_div) -> None:
        """Remove unwanted elements from the feed div."""
        # Remove positioning spans
        for span in feed_div.find_all("span", style="position: absolute; top: 3em;"):
            span.decompose()

        # Remove spans containing only "Facebook"
        for span in feed_div.find_all("span"):
            if span.get_text(strip=True) == "Facebook":
                span.decompose()

    def extract_text_content(self, div, author: str) -> str:
        """Extract and clean text content from a message div."""
        full_text = div.get_text(separator=" ", strip=True)
        if not full_text:
            return ""

        # Remove cutoff phrases
        for cutoff in self.cutoff_phrases:
            if cutoff in full_text:
                full_text = full_text.split(cutoff, 1)[0].strip()
                break

        # Remove author prefix and "Shared with Private group" content
        text_without_author = full_text.removeprefix(author).strip()
        cut_marker = "Shared with Private group"
        before, sep, after = text_without_author.partition(cut_marker)

        return after.strip() if sep else before.strip()

    def calculate_post_timestamp(self, duration_str: str, base_timestamp: str) -> str:
        """Calculate the actual post timestamp from duration and base timestamp."""
        duration_str = self.normalize_duration(duration_str)
        duration_match = re.match(r"(\d+)([smhd])", duration_str)

        if not duration_match:
            raise ValueError(f"Invalid duration format: {duration_str}")

        value, unit = int(duration_match.group(1)), duration_match.group(2)

        # Convert to timedelta
        unit_map = {
            "s": timedelta(seconds=value),
            "m": timedelta(minutes=value),
            "h": timedelta(hours=value),
            "d": timedelta(days=value)
        }

        if unit not in unit_map:
            raise ValueError(f"Unsupported duration unit: {unit}")

        delta = unit_map[unit]
        base_dt = datetime.strptime(base_timestamp, "%Y-%m-%dT%H_%M_%S.%fZ")
        new_dt = base_dt + delta

        return new_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def extract_links_and_author(self, div, base_timestamp: str) -> tuple[str, str, str, str, str]:
        """Extract author, author link, post link, and timestamp from the message div."""
        author = ""
        author_link = ""
        post_link = ""
        timestamp = ""
        delay = None

        a_tags = div.find_all("a", href=True)
        found_groups_link = False
        found_full_facebook_link = False

        for a in a_tags:
            raw_href = a["href"]
            href = html.unescape(raw_href)
            a_text = a.get_text(strip=True)

            # Extract author and author link from groups link
            if a_text and not found_groups_link and href.startswith("/groups/"):
                author = a_text
                author_link = "https://www.facebook.com" + href.rsplit("/", 1)[0]
                found_groups_link = True

            # Extract post link and timestamp from full Facebook link
            if not found_full_facebook_link and href.startswith("https://www.facebook.com/groups"):
                duration_str = a_text
                post_link = href.rsplit("/", 1)[0]  # This is the specific post link
                try:
                    timestamp = self.calculate_post_timestamp(duration_str, base_timestamp)
                    delay = duration_str
                except ValueError as e:
                    print(f"Warning: Could not calculate timestamp: {e}")
                    timestamp = base_timestamp
                found_full_facebook_link = True

            # Stop if both links found
            if found_groups_link and found_full_facebook_link:
                break

        return author, author_link, post_link, timestamp, delay

    def parse_messages(self, soup: BeautifulSoup, base_timestamp: str) -> list[FacebookPost]:
        """Parse all messages from the HTML content."""
        feed_div = soup.find("div", attrs={"role": "feed"})

        if not feed_div:
            raise ValueError("No <div role='feed'> found in the HTML content.")

        self.clean_feed_div(feed_div)
        message_divs = feed_div.find_all("div", attrs={"aria-posinset": True})

        posts = []

        for i, div in enumerate(message_divs, start=1):
            posinset = div.get("aria-posinset", "")

            # Skip empty messages
            full_text = div.get_text(separator=" ", strip=True)
            if not full_text:
                continue

            author, author_link, post_link, timestamp, delay = self.extract_links_and_author(div, base_timestamp)
            content = self.extract_text_content(div, author)

            post = FacebookPost(
                index=i,
                author=author,
                content=content,
                author_link=author_link,
                post_link=post_link,
                delay=delay,
                timestamp=timestamp.replace("_", ":"),
                posinset=posinset
            )

            posts.append(post)

        return posts

    def save_to_json(self, posts: list[FacebookPost], base_filename: str) -> str | None:
        """Save posts to the JSON file in the output directory."""
        # Extract timestamp from the base filename for the output filename
        timestamp_match = self.filename_pattern.match(base_filename)
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            output_filename = f"facebook_posts_{timestamp_str}.json"
        else:
            # Fallback if a pattern doesn't match
            current_time = datetime.now().strftime("%Y-%m-%dT%H_%M_%S.%fZ")
            output_filename = f"facebook_posts_{current_time}.json"

        output_path = os.path.join(self.output_dir, output_filename)

        # Convert posts to dictionaries for JSON serialization
        posts_data = [asdict(post) for post in posts]

        # Count posts with links
        total_posts = len(posts)
        posts_with_author_link = sum(1 for post in posts if post.author_link)
        posts_with_post_link = sum(1 for post in posts if post.post_link)
        posts_with_both_links = sum(1 for post in posts if post.author_link and post.post_link)

        # Create metadata
        output_data = {
            "metadata": {
                "source_file": base_filename,
                "extracted_at": datetime.now().isoformat(),
                "total_posts": total_posts,
                "posts_with_author_link": posts_with_author_link,
                "posts_with_post_link": posts_with_post_link,
                "posts_with_both_links": posts_with_both_links,
                "posts_with_both_links_ratio": (posts_with_both_links / total_posts) if total_posts > 0 else 0,
                "parser_version": "1.0"
            },
            "posts": posts_data
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"\nSaved {total_posts} posts to: {output_path}")
            return output_path

        except OSError as e:
            print(f"Error saving JSON file: {e}")

    def print_post(self, post: FacebookPost) -> None:
        """Print a formatted Facebook post."""
        lines = [
            f"Message {post.index} (aria-posinset={post.posinset}):",
            f"Author: {post.author}" if post.author else None,
            f"  → Author Link: {post.author_link}" if post.author_link else None,
            f"  → Post Link: {post.post_link}" if post.post_link else None,
            f"Timestamp: {post.timestamp}" if post.timestamp else None,
            f"Delay: {post.delay}" if post.delay else None,
            post.content,
            "-" * 40
        ]
        print("\n".join(filter(None, lines)))

    def push_to_server(self, offers: list[FacebookPost]):
        headers = {
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json"
        }

        for offer in offers:
            if not offer.author_link or not offer.post_link:
                continue

            payload = {
                "author": offer.author,
                "raw_data": offer.content,
                "author_uid": offer.author_link,
                "offer_uid": offer.post_link,
                "timestamp": offer.timestamp,
                "source": "bot"
            }

            try:
                response = requests.post(
                    f"{BASE_API_URL}/offers/raw",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                response.raise_for_status()

            except RequestException as e:
                logger.error(f"Error pushing offer to server: {e}, {offer.index}")

    def run(self) -> list[FacebookPost]:
        """Main execution method."""
        try:
            # Find and load the newest file
            newest_file, newest_timestamp_str, newest_dt = self.find_newest_file()
            html_content = self.load_html_content(newest_file)

            print(f"Using file: {newest_file}")
            print(f"Extracted timestamp: {newest_timestamp_str}")
            print("X" * 40, "\n\n")

            # Parse the HTML content
            soup = BeautifulSoup(html_content, "lxml")
            posts = self.parse_messages(soup, newest_timestamp_str)

            # Print all posts
            for post in posts:
                self.print_post(post)

            if posts:
                self.save_to_json(posts, newest_file)

            self.push_to_server(posts)
            return posts

        except Exception as e:
            logger.error(f"Error: {e}")
            return []


def main():
    """Main function to run the Facebook page parser."""
    parser = FacebookPageParser()
    posts = parser.run()
    print(f"\nProcessed {len(posts)} posts successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting gracefully.")
