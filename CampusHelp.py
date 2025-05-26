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
            for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'ol', 'ul']):
                if tag.get_text(strip=True) or tag.name in ['p', 'div', 'li']:
                    tag.append('\n')

            body_text = ""
            body_tag = soup.find('body')
            if body_tag:
                body_text = body_tag.get_text(separator='\n', strip=True)
            else:
                body_text = soup.get_text(separator='\n', strip=True)

            with open(txt_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(body_text)
            print(f"Successfully converted and saved body text to {txt_file_path}")

        except Exception as e:
            print(f"Error converting {html_file_path} to TXT: {e}")
    print("--- HTML to TXT Conversion Process Completed ---")

def generate_github_links_json(source_json_file, output_json_dir="github_links_json"):
    """
    Processes the source JSON file to replace detailUrl fields with GitHub raw links.
    """
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/ToastyBuns3939/CampusHelp/refs/heads/main/Pages/"

    try:
        with open(source_json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Source JSON file not found at {source_json_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {source_json_file}")
        return

    if "data" not in data or not isinstance(data["data"], list):
        print("Error: JSON structure invalid. Expected a 'data' array.")
        return

    os.makedirs(output_json_dir, exist_ok=True)
    output_file_path = os.path.join(output_json_dir, os.path.basename(source_json_file))

    print(f"\n--- Generating JSON with GitHub links to {output_json_dir} ---")

    modified_data = data.copy() # Create a copy to modify

    for item in modified_data["data"]:
        base_filename = get_output_filenames(item)
        new_detail_url = f"{GITHUB_BASE_URL}{base_filename}.txt"
        item["detailUrl"] = new_detail_url
        print(f"Updated detailUrl for '{item.get('name', 'N/A')}' to: {new_detail_url}")

    try:
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            json.dump(modified_data, outfile, ensure_ascii=False, indent=4)
        print(f"Successfully generated new JSON file with GitHub links: {output_file_path}")
    except Exception as e:
        print(f"Error writing GitHub links JSON file: {e}")

    print("--- GitHub Link Generation Process Completed ---")


def display_menu():
    """Displays the main menu options."""
    print("\n--- Web Content Processor Menu ---")
    print("1. Download HTML Pages")
    print("2. Convert HTML to TXT Files")
    print("3. Generate JSON with GitHub Links")
    print("4. Exit")
    print("----------------------------------")

if __name__ == "__main__":
    SOURCE_JSON_FILE = "HelpContent.json"
    DOWNLOAD_DIR = "downloaded_pages"
    TXT_OUTPUT_DIR = "extracted_body_txt"
    GITHUB_LINKS_JSON_DIR = "github_links_json_output" # New directory for the processed JSON

    while True:
        display_menu()
        choice = input("Enter your choice (1, 2, 3, or 4): ").strip()

        if choice == '1':
            download_html_pages(SOURCE_JSON_FILE, DOWNLOAD_DIR)
        elif choice == '2':
            convert_html_to_txt(SOURCE_JSON_FILE, DOWNLOAD_DIR, TXT_OUTPUT_DIR)
        elif choice == '3':
            generate_github_links_json(SOURCE_JSON_FILE, GITHUB_LINKS_JSON_DIR)
        elif choice == '4':
            print("Exiting the program. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")