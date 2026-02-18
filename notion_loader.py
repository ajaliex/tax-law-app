import os
import streamlit as st
from notion_client import Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotionLoader:
    def __init__(self, api_key=None):
        self.api_key = api_key
        if self.api_key:
            self.notion = Client(auth=self.api_key)
        else:
            self.notion = None

    def get_dummy_data(self):
        """Returns dummy data for testing purposes."""
        data = {
            "1-1 納税義務者と課税所得等の範囲": {
                "1.納税義務者": [
                    {
                        "title": "(1)内国法人☆",
                        "answer": "内国法人とは、国内に本店又は主たる事務所を有する法人をいう。"
                    },
                    {
                        "title": "(2)外国法人",
                        "answer": "外国法人とは、内国法人以外の法人をいう。"
                    }
                ]
            },
            "1-2 デモ用テーマ": {
                "1.デモ大項目": [
                    {
                        "title": "(1)デモ小項目",
                        "answer": "これはデモ用の正解テキストです。\n複数行にわたる場合もあります。"
                    }
                ]
            }
        }
        return data, {"info": "Dummy data used"}

    def fetch_page_data(self, page_id):
        """
        Fetches and parses a Notion page content recursively.
        Returns a nested dictionary structure:
        {
            "H1 Theme": {
                "H2 Category": [
                    {"title": "H3 Point", "answer": "Toggle Content"}
                ]
            }
        }
        """
        if not self.notion:
            raise ValueError("Notion API key is not set.")

        if not self.notion:
            raise ValueError("Notion API key is not set.")

        data = {}
        debug_info = {
            "total_blocks": 0,
            "h1_count": 0,
            "h2_count": 0,
            "h3_count": 0,
            "toggles_found": 0
        }
        
        # Context tracking
        ctx = {
            "h1": None,
            "h2": None,
            "h3": None
        }

        visited = set()
        request_count = 0
        MAX_REQUESTS = 200 # Safety limit

        def traverse(block_id, depth=0):
            nonlocal request_count
            if block_id in visited or request_count >= MAX_REQUESTS:
                return
            visited.add(block_id)
            
            if depth > 10: # Depth safety
                return

            has_more = True
            start_cursor = None
            
            while has_more and request_count < MAX_REQUESTS:
                try:
                    request_count += 1
                    resp = self.notion.blocks.children.list(block_id=block_id, start_cursor=start_cursor)
                    # logger.info(f"Notion API: Fetched {len(resp['results'])} blocks for {block_id}")
                except Exception as e:
                    logger.error(f"Error traversing block {block_id}: {e}")
                    break

                for block in resp["results"]:
                    debug_info["total_blocks"] += 1
                    b_type = block["type"]
                    b_id = block["id"]
                    
                    # Log progress to terminal
                    print(f"  [{request_count}] Processing {b_type} (Blocks: {debug_info['total_blocks']})")

                    # Handle Headings
                    if b_type == "heading_1":
                        text_list = block["heading_1"]["rich_text"]
                        if text_list:
                            h1_text = text_list[0]["plain_text"]
                            ctx["h1"] = h1_text
                            ctx["h2"] = None
                            ctx["h3"] = None
                            debug_info["h1_count"] += 1
                            if h1_text not in data: data[h1_text] = {}
                            if block.get("has_children"):
                                traverse(b_id, depth + 1)
                                
                    elif b_type == "heading_2":
                        text_list = block["heading_2"]["rich_text"]
                        if text_list:
                            h2_text = text_list[0]["plain_text"]
                            ctx["h2"] = h2_text
                            ctx["h3"] = None
                            debug_info["h2_count"] += 1
                            if not ctx["h1"]:
                                ctx["h1"] = "Uncategorized"
                                if "Uncategorized" not in data: data["Uncategorized"] = {}
                            if h2_text not in data[ctx["h1"]]:
                                data[ctx["h1"]][h2_text] = []
                            if block.get("has_children"):
                                traverse(b_id, depth + 1)

                    elif b_type == "heading_3":
                        text_list = block["heading_3"]["rich_text"]
                        if text_list:
                            h3_text = text_list[0]["plain_text"]
                            ctx["h3"] = h3_text
                            debug_info["h3_count"] += 1
                            if block.get("has_children"):
                                traverse(b_id, depth + 1)

                    # Handle Answer Toggle
                    elif b_type == "toggle":
                        text_list = block["toggle"]["rich_text"]
                        if text_list and "解答" in text_list[0]["plain_text"]:
                            debug_info["toggles_found"] += 1
                            title = ctx["h3"] if ctx["h3"] else "（小見出しなし）"
                            # Note: No traverse() here to avoid redundant API calls; 
                            # _get_toggle_content handles inner text.
                            answer_text = self._get_toggle_content(b_id)
                            
                            cur_h1 = ctx["h1"] if ctx["h1"] else "Uncategorized"
                            if cur_h1 not in data: data[cur_h1] = {}
                            cur_h2 = ctx["h2"] if ctx["h2"] else "Uncategorized"
                            if cur_h2 not in data[cur_h1]: data[cur_h1][cur_h2] = []
                            
                            data[cur_h1][cur_h2].append({
                                "title": title,
                                "answer": answer_text
                            })
                        elif block.get("has_children"):
                            # Only recurse toggles that are NOT answers
                            traverse(b_id, depth + 1)
                            
                    elif b_type in ["column_list", "column", "synced_block", "template"]:
                        # Recurse into common structural containers
                        if block.get("has_children"):
                            traverse(b_id, depth + 1)

                has_more = resp["has_more"]
                start_cursor = resp["next_cursor"]
            
            if request_count >= MAX_REQUESTS:
                debug_info["warning"] = "APIリクエスト制限（200回）に達したため、スキャンを中断しました。"


        try:
             traverse(page_id)
             return data, debug_info

        except Exception as e:
            logger.error(f"Error fetching data from Notion: {e}")
            raise e

    def _get_toggle_content(self, block_id):
        """Helper to recursively fetch text content inside a toggle block."""
        text_content = []
        has_more = True
        start_cursor = None
        
        while has_more:
            response = self.notion.blocks.children.list(block_id=block_id, start_cursor=start_cursor)
            for child in response["results"]:
                c_type = child["type"]
                if c_type == "paragraph":
                    rich_text = child["paragraph"]["rich_text"]
                    if rich_text:
                        text_content.append(rich_text[0]["plain_text"])
                # Handle other block types if necessary (bulleted_list, etc.)
                elif c_type == "bulleted_list_item":
                     rich_text = child["bulleted_list_item"]["rich_text"]
                     if rich_text:
                        text_content.append("・" + rich_text[0]["plain_text"])

            has_more = response["has_more"]
            start_cursor = response["next_cursor"]
            
        return "\n".join(text_content)
