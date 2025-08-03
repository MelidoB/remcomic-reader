import os
import json
from glob import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, OrderedDict

base_dir = "cache"
json_files = sorted(glob(os.path.join(base_dir, "**", "*.json"), recursive=True))

# This will hold data as chapter -> file -> bubbles
chapter_data = defaultdict(dict)

def process_file(file_path):
    result = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if data.get("status") == "success" and "bubbles" in data:
            corrected_list = [
                {
                    "order": bubble.get("order", 0),
                    "corrected_text": bubble.get("corrected_text", "")
                }
                for bubble in data["bubbles"]
            ]
            corrected_list.sort(key=lambda x: x["order"])

            rel_path = os.path.relpath(file_path, base_dir)
            chapter = rel_path.split(os.sep)[0]
            result = (chapter, file_path, corrected_list)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return result

# Use ThreadPoolExecutor for speed
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(process_file, path) for path in json_files]
    for future in as_completed(futures):
        result = future.result()
        if result:
            chapter, path, bubbles = result
            chapter_data[chapter][path] = bubbles

# Sort chapter names naturally (e.g., chapter-1 before chapter-10)
def chapter_sort_key(name):
    try:
        return int(name.split('-')[-1])
    except:
        return name

# Split into chunks of 5 chapters
sorted_chapters = sorted(chapter_data.keys(), key=chapter_sort_key)
chunk_size = 5

for i in range(0, len(sorted_chapters), chunk_size):
    chunk = sorted_chapters[i:i + chunk_size]
    chunk_dict = OrderedDict()

    for chapter in chunk:
        # Sort files inside each chapter by number (1.json, 2.json...)
        files_dict = chapter_data[chapter]
        sorted_files = sorted(files_dict.items(), key=lambda x: int(os.path.splitext(os.path.basename(x[0]))[0]))
        chunk_dict[chapter] = OrderedDict((fpath, bubbles) for fpath, bubbles in sorted_files)

    chunk_index = i // chunk_size + 1
    filename = f"corrected_texts_part_{chunk_index:02d}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(chunk_dict, f, indent=2, ensure_ascii=False)

    print(f"Saved {filename} with chapters {chunk}")
