import os
import glob

class LocalLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir

    def load_data(self):
        """
        Scans the data directory for .md files and parses them.
        Returns:
            data: Nested dictionary {H1: {H2: [{"title": H3, "answer": text}]}}
            debug_info: Dictionary with stats
        """
        data = {}
        debug_info = {
            "files_loaded": 0,
            "h1_count": 0,
            "h2_count": 0,
            "h3_count": 0,
            "errors": []
        }

        md_files = glob.glob(os.path.join(self.data_dir, "*.md"))
        
        for file_path in md_files:
            try:
                self._parse_file(file_path, data, debug_info)
                debug_info["files_loaded"] += 1
            except Exception as e:
                debug_info["errors"].append(f"{os.path.basename(file_path)}: {str(e)}")

        return data, debug_info

    def _parse_file(self, file_path, data, debug_info):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_h1 = None
        current_h2 = None
        current_h3 = None
        
        for line in lines:
            line_str = line.strip()
            
            if line_str.startswith("# "):
                # H1: Theme
                current_h1 = line_str[2:].strip()
                if current_h1 not in data:
                    data[current_h1] = {}
                current_h2 = None
                current_h3 = None
                debug_info["h1_count"] += 1

            elif line_str.startswith("## "):
                # H2: Category
                if current_h1 is None:
                    current_h1 = "Uncategorized"
                    if current_h1 not in data: data[current_h1] = {}
                
                current_h2 = line_str[3:].strip()
                if current_h2 not in data[current_h1]:
                    data[current_h1][current_h2] = []
                current_h3 = None
                debug_info["h2_count"] += 1

            elif line_str.startswith("### "):
                # H3: Question Point
                if current_h1 is None:
                     current_h1 = "Uncategorized"
                     if current_h1 not in data: data[current_h1] = {}
                if current_h2 is None:
                     current_h2 = "Uncategorized"
                     if current_h2 not in data[current_h1]: data[current_h1][current_h2] = []

                if data[current_h1][current_h2] and data[current_h1][current_h2][-1]["title"] == "（全体）":
                    data[current_h1][current_h2][-1]["title"] = "（前文）"

                current_h3 = line_str[4:].strip()
                data[current_h1][current_h2].append({
                    "title": current_h3,
                    "answer": ""
                })
                debug_info["h3_count"] += 1

            elif current_h1 and current_h2:
                # Body text (Answer)
                if current_h3 is None:
                    if not data[current_h1][current_h2] or data[current_h1][current_h2][-1]["title"] != "（全体）":
                        data[current_h1][current_h2].append({
                            "title": "（全体）",
                            "answer": ""
                        })
                
                last_item = data[current_h1][current_h2][-1]
                
                # Append line to answer
                # If it's a completely empty line, only append if we already have content (avoid leading newlines)
                if not line_str:
                    if last_item["answer"] and not last_item["answer"].endswith("\n\n"):
                        last_item["answer"] += "\n"
                else:
                    if last_item["answer"]:
                        # If the last character isn't a newline, add one
                        sep = "" if last_item["answer"].endswith("\n") else "\n"
                        last_item["answer"] += sep + line_str
                    else:
                        last_item["answer"] = line_str

        # Post-process: strip final newlines from all answers
        for h1 in data:
            for h2 in data[h1]:
                for item in data[h1][h2]:
                    item["answer"] = item["answer"].strip()
