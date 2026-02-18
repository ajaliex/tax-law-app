import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from local_loader import LocalLoader
import difflib
import Levenshtein
import os
import importlib
import local_loader
from learning_manager import LearningManager
from datetime import datetime

# Page Config
st.set_page_config(page_title="法人税法理論 暗記アプリ", layout="wide")

# Session State Initialization
if 'step' not in st.session_state:
    st.session_state.step = 'selection' # selection, step1_structure, step2_writing
if 'selected_h1' not in st.session_state:
    st.session_state.selected_h1 = None
if 'selected_h2' not in st.session_state:
    st.session_state.selected_h2 = None
if 'data' not in st.session_state:
    st.session_state.data = None
if 'debug_info' not in st.session_state:
    st.session_state.debug_info = None
if 'focus_target_idx' not in st.session_state:
    st.session_state.focus_target_idx = None
if 'last_action_time' not in st.session_state:
    st.session_state.last_action_time = datetime.now()

# Initialize Learning Manager
learning_manager = LearningManager()

# --- Learning Time Tracking Logic ---
# Logic: Calculate time elapsed since last action. 
# If page phase is "learning" (step1 or step2), add to log.
# Threshold: Ignore if interval is too long (e.g. > 30 mins) to prevent idle counting.

current_time = datetime.now()
elapsed = (current_time - st.session_state.last_action_time).total_seconds()

# Define learning steps
is_learning_mode = st.session_state.step in ['step1_structure', 'step2_writing']

if is_learning_mode:
    # If elapsed time is reasonable (e.g., less than 30 minutes), add to log
    # This accounts for the time spent "thinking" before clicking a button.
    if 0 < elapsed < 1800:  
        learning_manager.add_learning_time(elapsed)

# Update last action time for the NEXT interval
st.session_state.last_action_time = current_time


# Sidebar: Configuration & Data Loading

# Data Loading (Auto-load on startup handled below)
# Sidebar removed as per user request.

import unicodedata

# Helper Functions
def normalize_text(text):
    if not text:
        return ""
    # NFKC normalization converts full-width numbers/parens to half-width
    text = unicodedata.normalize('NFKC', text)
    # Remove spaces (full-width and half-width) to ignore stylistic differences in spacing
    return text.replace(" ", "").replace("　", "")

def compute_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    # Normalize both texts before comparison
    text1_norm = normalize_text(text1)
    text2_norm = normalize_text(text2)
    return Levenshtein.ratio(text1_norm, text2_norm) * 100

def generate_diff_html(correct, actual):
    # Normalize for diff generation too, so purely stylistic diffs don't show up
    correct_norm = normalize_text(correct)
    actual_norm = normalize_text(actual)
    
    d = difflib.Differ()
    diff_chars = list(d.compare(actual_norm, correct_norm))
    
    html = []
    html.append("<div style='font-family: monospace; white-space: pre-wrap; line-height: 1.5; background-color: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #ddd;'>")
    
    for char in diff_chars:
        code = char[0]
        text = char[2:]
        
        # Escape HTML special chars
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        
        if code == ' ':
            html.append(f"<span style='color: #333;'>{text}</span>")
        elif code == '-': # In actual, not in correct (Extra / Wrong)
            html.append(f"<span style='background-color: #dbeafe; color: #1e40af; text-decoration: line-through;'>{text}</span>")
        elif code == '+': # In correct, not in actual (Missing)
            html.append(f"<span style='background-color: #fee2e2; color: #991b1b; font-weight: bold;'>{text}</span>")
            
    html.append("</div>")
    return "".join(html)

def reset_to_selection():
    st.session_state.step = 'selection'
    st.session_state.selected_h1 = None
    st.session_state.selected_h2 = None
    st.query_params.clear()

# Main Logic
if st.session_state.data is None:
    # Auto-load on first run
    try:
        importlib.reload(local_loader)
        from local_loader import LocalLoader
        loader = LocalLoader()
        ret = loader.load_data()
        if isinstance(ret, tuple):
            st.session_state.data, st.session_state.debug_info = ret
            
            # Check query params for restoration AFTER data load
            qp = st.query_params
            if "h1" in qp:
                h1_val = qp["h1"]
                if h1_val in st.session_state.data:
                    st.session_state.selected_h1 = h1_val
                    st.session_state.step = 'step1_structure'
                    
                    if "h2" in qp:
                        h2_val = qp["h2"]
                        if h2_val in st.session_state.data[h1_val]:
                            st.session_state.selected_h2 = h2_val
                            st.session_state.step = 'step2_writing'
            st.rerun()
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")

else:
    data = st.session_state.data
    
    # Global Stealth Mode Toggle & CSS
    # Placed here to be available on all screens
    col_global_1, col_global_2 = st.columns([9, 1])
    with col_global_2:
        stealth_mode = st.checkbox("ステルスモード", value=False, key="global_stealth_mode", label_visibility="collapsed")

    # CSS for Stealth Mode
    # color: transparent hides the text but keeps layout.
    # :hover and ::selection make it visible.
    st.markdown("""
    <style>
    .stealth-active {
        color: transparent !important;
        transition: color 0.3s ease;
    }
    .stealth-active:hover {
        color: var(--text-color) !important; 
    }
    .stealth-active::selection {
        color: var(--text-color) !important;
        background: rgba(100, 149, 237, 0.3); /* Custom highlight color to ensure visibility */
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Helper to apply class
    def stealth_class(text):
        if stealth_mode:
            return f'<span class="stealth-active">{text}</span>'
        return text

    # --- Screen 1: Selection (Step 1 Entry) ---
    if st.session_state.step == 'selection':
        st.header("Step 1: テーマ選択")
        
        # Display Learning Time
        today_sec, yest_sec = learning_manager.get_learning_time()
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            # Using markdown to simulate metric, but with stealth_class applied
            st.markdown(f"""
            <div data-testid="stMetric">
                <label style="font-size: 14px; color: rgba(49, 51, 63, 0.6);">今日の学習時間</label>
                <div style="font-size: 32px; font-weight: 600;">
                    {stealth_class(learning_manager.format_time(today_sec))}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_t2:
            st.markdown(f"""
            <div data-testid="stMetric">
                <label style="font-size: 14px; color: rgba(49, 51, 63, 0.6);">昨日の学習時間</label>
                <div style="font-size: 32px; font-weight: 600;">
                    {stealth_class(learning_manager.format_time(yest_sec))}
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.divider()
        
        h1_options = list(data.keys())
        if not h1_options:
            st.warning("データが見つかりませんでした。 `data/` フォルダに .md ファイルがあるか確認してください。")
            
            if st.session_state.debug_info:
                with st.expander("読み込みステータス", expanded=True):
                    st.json(st.session_state.debug_info)
                    st.info("""
                    **Markdownファイルの書き方:**
                    `data/` フォルダに `.md` ファイルを作成し、以下の形式で記述してください。
                    
                    ```markdown
                    # テーマ名
                    
                    ## 大項目
                    
                    ### 論点タイトル
                    ここに解答となる本文を記述します。
                    ```
                    """)
        else:
            selected_h1 = st.selectbox("学習するテーマを選択してください", h1_options)
            
            if st.button("このテーマで開始", type="primary"):
                st.session_state.selected_h1 = selected_h1
                st.session_state.step = 'step1_structure'
                st.query_params["h1"] = selected_h1
                st.rerun()

    # --- Screen 2: Step 1 Structure Recall ---
    elif st.session_state.step == 'step1_structure':
        h1 = st.session_state.selected_h1
        
        # Apply stealth to Theme
        st.markdown(f"<h1>テーマ: {stealth_class(h1)}</h1>", unsafe_allow_html=True)
        st.markdown("### 構成想起")
        st.info("このテーマに含まれる構造を思い浮かべて記述してください。")
        
        # New text area for recall output (non-judged)
        st.text_area("構成のアウトプット（メモ用）:", height=200, placeholder="ここに思い出した構成を書き出してみてください。")
        
        # Hidden answer toggle
        if st.checkbox("正解（構成ツリー）を表示する"):
            st.divider()
            h2_dict = data[h1]
            if not h2_dict:
                st.warning("このテーマには項目がありません。")
            else:
                for h2, items in h2_dict.items():
                    st.markdown(f"#### {h2}")
                    for item in items:
                        st.markdown(f"- {item['title']}")
            st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Step 2 (本文記述) へ進む", type="primary"):
                st.session_state.step = 'step2_writing'
                st.rerun()
        with col2:
            st.button("戻る", on_click=reset_to_selection)

    # --- Screen 3: Step 2 writing ---
    elif st.session_state.step == 'step2_writing':
        h1 = st.session_state.selected_h1
        
        # Apply stealth to Titles
        st.markdown(f"<h1>{stealth_class('Step 2: 本文記述')}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3>テーマ: {stealth_class(h1)}</h3>", unsafe_allow_html=True)
        
        # Move Back to Selection to top
        if st.button("テーマ選択に戻る"):
            reset_to_selection()
            st.rerun()
        
        st.divider()
        
        h2_dict = data[h1]
        h2_options = list(h2_dict.keys())
        
        if not h2_options:
            st.error("利用可能な項目がありません。")
            if st.button("戻る"):
                reset_to_selection()
                st.rerun()
        else:
            # H2 Selection
            # Find current index for selectbox
            current_h2 = st.session_state.get("selected_h2")
            try:
                current_idx = h2_options.index(current_h2) if current_h2 in h2_options else 0
            except:
                current_idx = 0
                
            def on_h2_change():
                st.session_state.selected_h2 = st.session_state.h2_select_box
                st.query_params["h2"] = st.session_state.selected_h2

            selected_h2 = st.selectbox(
                "練習する項目を選んでください", 
                h2_options, 
                index=current_idx, 
                key="h2_select_box", 
                on_change=on_h2_change
            )
            # Update state if changed (though on_change handles it, keeping sync is good)
            st.session_state.selected_h2 = selected_h2
            st.query_params["h2"] = selected_h2
            
            st.divider()
            
            items = h2_dict[selected_h2]
            
            # Display input boxes for each H3 item
            for i, item in enumerate(items):
                # Anchor for scrolling
                st.markdown(f'<div id="quest_{i}"></div>', unsafe_allow_html=True)
                
                # Apply stealth to Question Title
                st.markdown(f"<h3>{i+1}. {stealth_class(item['title'])}</h3>", unsafe_allow_html=True)
                
                # Unique keys for each item
                input_key = f"input_{h1}_{selected_h2}_{i}"
                stable_input_key = f"stable_input_{h1}_{selected_h2}_{i}" # Stable storage
                judged_key = f"judged_{h1}_{selected_h2}_{i}"
                
                # Initialize state
                if judged_key not in st.session_state:
                    st.session_state[judged_key] = False
                
                # If NOT judged yet: Allow input and judging
                if not st.session_state[judged_key]:
                    # Use a placeholder in session state if not there to avoid key errors
                    initial_val = st.session_state.get(stable_input_key, "")
                    
                    # Wrap in form to prevent partial submissions/resets
                    with st.form(key=f"form_{input_key}"):
                        user_text = st.text_area("解答入力:", key=input_key, value=initial_val, height=150)
                        submitted = st.form_submit_button("判定")
                        
                        if submitted:
                            st.session_state[stable_input_key] = user_text # Save to stable storage
                            st.session_state[judged_key] = True
                            st.rerun()

                    # Auto-focus logic after reset (kept outside form, relies on re-render)
                    if st.session_state.focus_target_idx == i:
                        components.html(
                            f"""
                            <script>
                                try {{
                                    var element = window.parent.document.getElementById("quest_{i}");
                                    if (element) {{
                                        element.scrollIntoView({{behavior: "smooth", block: "center"}});
                                        
                                        // Navigate up and down to find the textarea
                                        // (Simplified for form structure)
                                        var current = element;
                                        // ... (existing focus logic might need tweaking for form, but scroll is main part)
                                    }}
                                }} catch(e) {{ console.log(e); }}
                            </script>
                            """,
                            height=0,
                            width=0
                        )
                        st.session_state.focus_target_idx = None
                
                else:
                    # Read from stable storage
                    current_input = st.session_state.get(stable_input_key, "")
                    correct_text = item['answer']
                    
                    # Score
                    score = compute_similarity(current_input, correct_text)
                    st.metric("一致率", f"{score:.1f}%")
                    
                    # Result Display
                    if score < 100:
                        st.markdown("**差分確認:**")
                        st.markdown("凡例: <span style='background-color: #fee2e2; color: #991b1b; font-weight: bold;'>不足（赤）</span> / <span style='background-color: #dbeafe; color: #1e40af; text-decoration: line-through;'>余分（青）</span>", unsafe_allow_html=True)
                        st.markdown(generate_diff_html(correct_text, current_input), unsafe_allow_html=True)
                        
                        with st.expander("正解の全文を確認"):
                            st.text(correct_text)
                    else:
                        st.success("完璧です！")

                    # Edit & Re-judge Area
                    st.markdown("---")
                    st.markdown("**修正して再判定:**")
                    
                    # Wrap correction in form too
                    with st.form(key=f"form_edit_{input_key}"):
                        val = st.text_area("修正入力:", value=current_input, key=f"edit_{input_key}", height=150)
                        col_retry1, col_retry2 = st.columns(2)
                        with col_retry1:
                            if st.form_submit_button("修正して再判定"):
                                st.session_state[stable_input_key] = val
                                st.rerun()
                        with col_retry2:
                             # Full Reset Button is NOT a form submit button usually, but inside form it triggers submit.
                             # We use a separate button OUTSIDE the form for reset to avoid confusion? 
                             # Or use form_submit_button with logic.
                             pass

                    # Reset button outside the edit form to be safe/clear logic
                    def reset_callback(k_stable, k_judged):
                        st.session_state[k_stable] = "" # Clear input
                        st.session_state[k_judged] = False # Reset judged state
                        
                    if st.button("リセットして最初から", key=f"reset_{input_key}"):
                            reset_callback(stable_input_key, judged_key)
                            st.session_state.focus_target_idx = i
                            st.rerun()

                st.divider()
            
            # Next Category Button at bottom (keep outside forms)
            if current_idx < len(h2_options) - 1:
                if st.button("次の大項目へ", type="primary"):
                    st.session_state.selected_h2 = h2_options[current_idx + 1]
                    st.query_params["h2"] = st.session_state.selected_h2
                    st.rerun()
            else:
                 st.info("これが最後の項目です。")
