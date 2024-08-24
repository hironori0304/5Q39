import streamlit as st
import pandas as pd
import random
from datetime import datetime
import pytz

# クイズデータを読み込む関数
def load_quizzes(file):
    df = pd.read_csv(file, encoding='utf-8')
    return df

# アプリケーションのタイトル
st.title('国家試験対策アプリsmile')

# セッション状態の初期化
def initialize_session_state():
    if 'highlighted_questions' not in st.session_state:
        st.session_state.highlighted_questions = set()
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'results_history' not in st.session_state:
        st.session_state.results_history = []
    if 'shuffled_options' not in st.session_state:
        st.session_state.shuffled_options = {}
    if 'selected_years' not in st.session_state:
        st.session_state.selected_years = []
    if 'selected_categories' not in st.session_state:
        st.session_state.selected_categories = []
    if 'attempt_count' not in st.session_state:
        st.session_state.attempt_count = 0
    if 'incorrect_questions' not in st.session_state:
        st.session_state.incorrect_questions = set()
    if 'previous_selected_years' not in st.session_state:
        st.session_state.previous_selected_years = []
    if 'previous_selected_categories' not in st.session_state:
        st.session_state.previous_selected_categories = []
    if 'previous_keyword' not in st.session_state:
        st.session_state.previous_keyword = ""

initialize_session_state()

# ファイルアップロード
uploaded_file = st.file_uploader("問題データのCSVファイルをアップロードしてください", type="csv")

if uploaded_file is not None:
    # アップロードされたファイルを読み込む
    df = load_quizzes(uploaded_file)

    # 年と分類の選択肢を取得し、「すべて」を追加
    years = df['year'].unique().tolist()
    categories = df['category'].unique().tolist()
    
    years = ['すべて'] + years
    categories = ['すべて'] + categories
    
    # ユーザーが「年」と「分類」を選択
    selected_years = st.multiselect('過去問を選択', years)
    selected_categories = st.multiselect('内容を選択', categories)

    # キーワード検索の入力
    keyword = st.text_input("キーワードで検索")

    # 選択された条件をセッション状態に保存
    st.session_state.selected_years = selected_years
    st.session_state.selected_categories = selected_categories
    st.session_state.keyword = keyword

    # 新しい問題が選択された場合に回答回数とユーザー回答をリセット
    if (st.session_state.selected_years != st.session_state.previous_selected_years or
        st.session_state.selected_categories != st.session_state.previous_selected_categories or
        st.session_state.keyword != st.session_state.previous_keyword):
        st.session_state.attempt_count = 0
        st.session_state.previous_selected_years = st.session_state.selected_years.copy()
        st.session_state.previous_selected_categories = st.session_state.selected_categories.copy()
        st.session_state.previous_keyword = st.session_state.keyword
        st.session_state.user_answers = {}  # ここで回答をリセット

       
    # 年と分類の選択に応じてデータをフィルタリング
    filtered_df = df.copy()

    if 'すべて' not in selected_years:
        filtered_df = filtered_df[filtered_df['year'].isin(selected_years)]
    if 'すべて' not in selected_categories:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
    
    # キーワード検索によるフィルタリング（問題文と選択肢を対象に検索）
    if keyword:
        keyword_lower = keyword.lower()
        filtered_df = filtered_df[
            filtered_df['question'].str.contains(keyword, case=False, na=False) |
            filtered_df[[f"option{i}" for i in range(1, 6)]].apply(lambda row: row.str.contains(keyword_lower, case=False, na=False)).any(axis=1)
        ]

    # 年とカテゴリーの選択順に基づいてソート
    if 'year' in filtered_df.columns and 'category' in filtered_df.columns:
        category_order = {category: idx for idx, category in enumerate(st.session_state.selected_categories)}
        year_order = {year: idx for idx, year in enumerate(st.session_state.selected_years)}

        filtered_df['category_order'] = filtered_df['category'].map(category_order).fillna(float('inf'))
        filtered_df['year_order'] = filtered_df['year'].map(year_order).fillna(float('inf'))

        filtered_df = filtered_df.sort_values(by=['category_order', 'year_order'])
        filtered_df = filtered_df.drop(columns=['category_order', 'year_order'])

    total_questions = len(filtered_df)
    st.write(f"選択された問題は{total_questions}問あります")

    quizzes = []
    for _, row in filtered_df.iterrows():
        options = [row[f"option{i}"] for i in range(1, 6) if pd.notna(row[f"option{i}"])]
        answers = [row[f"answer{i}"] for i in range(1, 6) if pd.notna(row[f"answer{i}"])]
        
        if row["question"] not in st.session_state.shuffled_options:
            shuffled_options = options[:]
            random.shuffle(shuffled_options)
            st.session_state.shuffled_options[row["question"]] = shuffled_options

        quiz = {
            "question": row["question"],
            "type": row["type"],
            "options": st.session_state.shuffled_options[row["question"]],
            "answers": answers
        }
        quizzes.append(quiz)

    for idx, quiz in enumerate(quizzes, start=1):
        highlight = 'background-color: #fdd; padding: 10px;' if idx in st.session_state.highlighted_questions else ''
        st.markdown(f'<div style="{highlight}">問題{idx}</div>', unsafe_allow_html=True)
        st.markdown(f'<div>{quiz["question"]}</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <style>
            div[role='radiogroup'] {
                margin-top: -20px; 
            }
            div[role='radiogroup'] > label {
                margin-bottom: 10px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        if quiz["type"] == "single":
            user_answer = st.session_state.user_answers.get(quiz["question"], None)
            selected_option = st.radio("", quiz["options"], key=f"{idx}_radio", index=quiz["options"].index(user_answer) if user_answer in quiz["options"] else None)
            st.session_state.user_answers[quiz["question"]] = selected_option
        elif quiz["type"] == "multiple":
            selected_options = st.session_state.user_answers.get(quiz["question"], [])
            for option in quiz["options"]:
                checked = option in selected_options
                if st.checkbox(option, key=f"{idx}_{option}", value=checked):
                    if option not in selected_options:
                        selected_options.append(option)
                else:
                    if option in selected_options:
                        selected_options.remove(option)
            st.session_state.user_answers[quiz["question"]] = selected_options

        st.markdown("<br>", unsafe_allow_html=True)

    # 回答ボタンを作成
    if st.button('回答'):
        # 回答回数の更新
        attempt_count = st.session_state.attempt_count + 1
        st.session_state.attempt_count = attempt_count

        # 成績の計算と間違った問題のリストの更新
        correct_count = 0
        total_questions = len(quizzes)
        highlighted_questions = set()
        incorrect_questions = set()
        incorrect_questions_texts = []  # 間違った問題文のリスト

        for idx, quiz in enumerate(quizzes, start=1):
            is_correct = False
            if quiz["type"] == "single":
                user_answer = st.session_state.user_answers.get(quiz["question"], None)
                is_correct = user_answer == quiz["answers"][0]
            elif quiz["type"] == "multiple":
                user_answers_options = set(st.session_state.user_answers.get(quiz["question"], []))
                correct_answers = set(quiz["answers"])
                is_correct = user_answers_options == correct_answers

            if is_correct:
                correct_count += 1
            else:
                incorrect_questions.add(idx)
                incorrect_questions_texts.append(quiz["question"])  # 間違った問題文を追加

        # 不正解の問題番号を保存
        st.session_state.highlighted_questions = incorrect_questions
        st.session_state.incorrect_questions = incorrect_questions

        # 回答履歴を保存
        tokyo_tz = pytz.timezone('Asia/Tokyo')
        now = datetime.now(tokyo_tz).strftime('%Y%m%d_%H%M%S')

        accuracy = correct_count / total_questions * 100

        result = {
            "日時": now,
            "過去問": ', '.join(st.session_state.selected_years),
            "内容": ', '.join(st.session_state.selected_categories),
            "キーワード": st.session_state.keyword if st.session_state.keyword else "",  # キーワードを追加
            "回答回数": attempt_count,
            "正解数": correct_count,
            "問題数": total_questions,
            "正答率": accuracy,
            "不正解の問題文": ', '.join(incorrect_questions_texts)  # 不正解の問題文を追加
        }

        st.session_state.results_history.append(result)
        

        # 正答数と問題数、正答率を表示
        st.write(f"正答数: {correct_count} / 問題数: {total_questions}")
        st.write(f"正答率: {accuracy:.2f}%")

        if accuracy == 100:
            st.success("全問正解です！ おめでとうございます!")

    # 不正解問題ボタン
    if st.button('不正解問題（ハイライト表示）'):
        st.session_state.highlighted_questions = st.session_state.incorrect_questions

# セッションステートから名前を取得し、デフォルト値に設定
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

# 回答履歴がセッションステートに存在する場合
if 'results_history' in st.session_state and st.session_state.results_history:
    st.write("回答履歴:")
    history_df = pd.DataFrame(st.session_state.results_history)
    st.write(history_df)
    
    # ユーザー名の入力フィールドを追加
    st.session_state.user_name = st.text_input("名前を入力してください", st.session_state.user_name)
    
        # 現在の日本時間を取得
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    now = datetime.now(tokyo_tz).strftime('%Y%m%d_%H%M%S')
    
   # ファイル名にユーザー名を追加
    file_name = f"{st.session_state.user_name}_回答履歴_{now}.csv" if st.session_state.user_name else f"回答履歴_{now}.csv"
    
    
    # CSVファイルを生成
    csv = history_df.to_csv(index=False).encode('utf-8-sig')
    
    # ダウンロードボタンを作成
    st.download_button(
        label="回答履歴をダウンロード",
        data=csv,
        file_name=file_name,
        mime='text/csv'
    )


