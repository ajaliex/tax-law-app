import streamlit as st
import pandas as pd
from local_loader import LocalLoader
import difflib
import Levenshtein
import os
import importlib
import local_loader

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

# Sidebar: Configuration & Data Loading
with st.sidebar:
    st.title("設定")
    st.markdown("データは `data/` フォルダ内のMarkdownファイルから読み込まれます。")
    
    if st.button("データ再読み込み"):
        with st.spinner("ファイルをスキャン中..."):
            importlib.reload(local_loader)
            from local_loader import LocalLoader
            loader = LocalLoader()
            try:
                st.session_state.data, st.session_state.debug_info = loader.load_data()
                st.success("読み込み完了！")
            except Exception as e:
                st.error(f"エラー: {e}")

import unicodedata

# Helper Functions
def normalize_text(text):
    if not text:
        return ""
    # NFKC normalization converts full-width numbers/parens to half-width
    return unicodedata.normalize('NFKC', text)

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

# Main Logic
if st.session_state.data is None:
    st.info("👈 サイドバーの「データ再読み込み」を押してデータをロードしてください。")
    
    # Auto-load on first run
    try:
        importlib.reload(local_loader)
        from local_loader import LocalLoader
        loader = LocalLoader()
        ret = loader.load_data()
        if isinstance(ret, tuple):
            st.session_state.data, st.session_state.debug_info = ret
            st.rerun()
    except Exception as e:
        # Silently fail on auto-load, let user click button
        pass

else:
    data = st.session_state.data
    
    # --- Screen 1: Selection (Step 1 Entry) ---
    if st.session_state.step == 'selection':
        st.header("Step 1: テーマ選択")
        
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
                st.rerun()

    # --- Screen 2: Step 1 Structure Recall ---
    elif st.session_state.step == 'step1_structure':
        h1 = st.session_state.selected_h1
        st.title(f"テーマ: {h1}")
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
        st.title(f"Step 2: 本文記述")
        st.subheader(f"テーマ: {h1}")
        
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
                
            selected_h2 = st.selectbox("練習する項目を選んでください", h2_options, index=current_idx)
            st.session_state.selected_h2 = selected_h2
            
            st.divider()
            
            items = h2_dict[selected_h2]
            
            # Display input boxes for each H3 item
            for i, item in enumerate(items):
                st.subheader(f"{i+1}. {item['title']}")
                
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
                    user_text = st.text_area("解答入力:", key=input_key, value=initial_val, height=150)
                    
                    if st.button("判定", key=f"btn_{input_key}"):
                        st.session_state[stable_input_key] = user_text # Save to stable storage
                        st.session_state[judged_key] = True
                        st.rerun()
                
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
                    
                    # Text area for correction (bound to session state manually or via key logic)
                    # We reuse the same stable key logic but need a new widget key to avoid duplicate ID error if we weren't careful.
                    # Actually, if we are in 'Judged' state, the original text_area is gone. 
                    # So we can render a NEW text area here that updates the SAME stable storage.
                    
                    val = st.text_area("修正入力:", value=current_input, key=f"edit_{input_key}", height=150)
                    
                    col_retry1, col_retry2 = st.columns(2)
                    
                    with col_retry1:
                        if st.button("修正して再判定", key=f"rejudge_{input_key}"):
                            st.session_state[stable_input_key] = val
                            st.rerun()
                            
                    with col_retry2:
                         # Full Reset Button
                        def reset_callback(k_stable, k_judged):
                            st.session_state[k_stable] = "" # Clear input
                            st.session_state[k_judged] = False # Reset judged state
                            
                        if st.button("リセットして最初から", key=f"reset_{input_key}"):
                             reset_callback(stable_input_key, judged_key)
                             st.rerun()

                st.divider()
            
            # Next Category Button at bottom
            if current_idx < len(h2_options) - 1:
                if st.button("次の大項目へ", type="primary"):
                    st.session_state.selected_h2 = h2_options[current_idx + 1]
                    st.rerun()
            else:
                 st.info("これが最後の項目です。")
