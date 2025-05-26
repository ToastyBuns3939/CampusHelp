import json
import requests
import os
import re
from bs4 import BeautifulSoup # This library needs to be installed: pip install beautifulsoup4

def sanitize_filename(name):
    """
    Sanitizes a string to be used as a valid filename.
    Replaces spaces with underscores, removes invalid characters,
    and truncates if too long.
    """
    s = str(name).strip()
    s = s.replace(" ", "_")
    s = re.sub(r'[^\w\s\-\.]', '', s)
    s = re.sub(r'_{2,}', '_', s)
    if len(s) > 200:
        s = s[:200]
    return s

def get_output_filenames(item):
    """
    Generates the base filename for HTML and TXT output based on
    'helpCategoryId', 'id', 'order', and 'name' fields.
    """
    help_category_id = item.get("helpCategoryId", "unknown_category")
    item_id = item.get("id", "unknown_id")
    order = item.get("order", "unknown_order")
    name = item.get("name", "unknown_name")

    # Format: helpCategoryId_id_order_name
    base_filename = f"{help_category_id}_{item_id}_{order}_{name}"
    return sanitize_filename(base_filename)

def download_html_pages(json_file_path, download_dir="downloaded_pages"):
    """
    Downloads HTML pages from a list of links specified in a JSON file.
    Skips download if the file already exists.
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}")
        return

    if "data" not in data or not isinstance(data["data"], list):
        print("Error: JSON structure invalid. Expected a 'data' array.")
        return

    os.makedirs(download_dir, exist_ok=True)
    print(f"\n--- Starting HTML Download Process to {download_dir} ---")

    for item in data["data"]:
        url = item.get("detailUrl")
        if not url:
            print(f"Skipping item due to missing 'detailUrl': {item}")
            continue

        base_filename = get_output_filenames(item)
        html_filename = base_filename + ".html"
        html_file_path = os.path.join(download_dir, html_filename)

        # Check if file already exists
        if os.path.exists(html_file_path):
            print(f"Skipping download for '{html_filename}' as it already exists.")
            continue # Skip to the next item

        try:
            print(f"Downloading: {url} to {html_file_path}")
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(html_file_path, 'wb') as output_file:
                for chunk in response.iter_content(chunk_size=8192):
                    output_file.write(chunk)
            print(f"Successfully downloaded {url}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {url}: {e}")
    print("--- HTML Download Process Completed ---")

def convert_html_to_txt(json_file_path, download_dir="downloaded_pages", txt_output_dir="extracted_body_txt"):
    """
    Converts downloaded HTML files into plain text files containing only their body text,
    preserving line breaks.
    Assumes HTML files are already present in download_dir.
    Skips conversion if the TXT file already exists.
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}")
        return

    if "data" not in data or not isinstance(data["data"], list):
        print("Error: JSON structure invalid. Expected a 'data' array.")
        return

    os.makedirs(txt_output_dir, exist_ok=True)
    print(f"\n--- Starting HTML to TXT Conversion Process to {txt_output_dir} ---")

    for item in data["data"]:
        base_filename = get_output_filenames(item)
        html_filename = base_filename + ".html" # The exact filename we expect
        html_file_path = os.path.join(download_dir, html_filename)

        if not os.path.exists(html_file_path):
            print(f"Warning: Corresponding HTML file '{html_filename}' not found in '{download_dir}'. Skipping conversion.")
            continue

        txt_filename = base_filename + ".txt"
        txt_file_path = os.path.join(txt_output_dir, txt_filename)

        # Check if TXT file already exists
        if os.path.exists(txt_file_path):
            print(f"Skipping conversion for '{txt_filename}' as it already exists.")
            continue # Skip to the next item

        try:
            print(f"Converting {html_file_path} to TXT (body text only)...")
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'html.parser')
            
            # --- Preserve line breaks ---
            # Replace <br> tags with newline characters
            for br_tag in soup.find_all('br'):
                br_tag.replace_with('\n')
            
            # Replace common block-level elements with newline characters to simulate line breaks
            # This is an approximation and might need adjustment based on specific HTML structure
            for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'ol', 'ul']):
                tag.append('\n') # Add a newline after the content of block-level tags

            body_text = ""
            body_tag = soup.find('body')
            if body_tag:
                # Use get_text with separator='\n' to ensure text is joined with newlines
                # and strip=True to clean up excessive whitespace
                body_text = body_tag.get_text(separator='\n', strip=True)
            else:
                body_text = soup.get_text(separator='\n', strip=True)

            with open(txt_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(body_text)
            print(f"Successfully converted and saved body text to {txt_file_path}")

        except Exception as e:
            print(f"Error converting {html_file_path} to TXT: {e}")
    print("--- HTML to TXT Conversion Process Completed ---")

if __name__ == "__main__":
    # --- Configuration ---
    SOURCE_JSON_FILE = "HelpContent.json"
    DOWNLOAD_HTML = True  # Set to True to download HTML pages
    CONVERT_TO_TXT = True # Set to True to convert HTML to TXT

    # --- Run Processes ---
    if DOWNLOAD_HTML:
        download_html_pages(SOURCE_JSON_FILE)

    if CONVERT_TO_TXT:
        convert_html_to_txt(SOURCE_JSON_FILE)

    if not DOWNLOAD_HTML and not CONVERT_TO_TXT:
        print("No operation selected. Set DOWNLOAD_HTML or CONVERT_TO_TXT to True.")