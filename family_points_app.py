from pathlib import Path
import json
from datetime import date, timedelta
import hashlib

import pandas as pd
import streamlit as st

# ボタン用のスタイル拡張（なくても動くようにフォールバック）
try:
    from streamlit_extras.stylable_container import stylable_container
except Exception:
    stylable_container = None


def do_rerun():
    """Streamlit 再実行（バージョン差吸収）"""
    try:
        st.rerun()
    except AttributeError:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()


# =========================
# パス・定数
# =========================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "logs.csv"

# 勉強 5教科 + その他
STANDARD_STUDY_SUBJECTS = ["算数", "国語", "理科", "社会", "英語", "その他"]
# 家事プリセット
HOUSE_TASKS = ["皿洗い", "洗濯物片づけ", "掃除", "片付け"]

DEFAULT_CONFIG = {
    "parent_password": "otetsudai123",
    "children": ["Aちゃん", "Bくん"],
    "tasks": [
        {"id": 1, "category": "勉強", "name": "算数", "points_per_hour": 10.0},
        {"id": 2, "category": "勉強", "name": "国語", "points_per_hour": 10.0},
        {"id": 3, "category": "勉強", "name": "理科", "points_per_hour": 10.0},
        {"id": 4, "category": "勉強", "name": "社会", "points_per_hour": 10.0},
        {"id": 5, "category": "勉強", "name": "英語", "points_per_hour": 10.0},
        {"id": 6, "category": "勉強", "name": "その他", "points_per_hour": 10.0},
        {"id": 7, "category": "家事", "name": "皿洗い", "points_per_hour": 10.0},
        {"id": 8, "category": "家事", "name": "洗濯物片づけ", "points_per_hour": 10.0},
        {"id": 9, "category": "家事", "name": "掃除", "points_per_hour": 10.0},
        {"id": 10, "category": "家事", "name": "片付け", "points_per_hour": 10.0},
    ],
}


def get_child_alias(name: str) -> str:
    """タブ表示用に、幸芽→K, 秀芽→S に変換（それ以外はそのまま）"""
    if name == "幸芽":
        return "K"
    if name == "秀芽":
        return "S"
    return name


def set_kids_style():
    """全体のボタンを少し大きく・角丸にして子ども向けに"""
    st.markdown(
        """
        <style>
        div.stButton > button {
            border-radius: 999px;
            padding: 0.6em 1.4em;
            font-size: 1.1em;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pastel_button(label: str, key: str, color: str, large: bool = False, **kwargs) -> bool:
    """
    1つのボタンだけパステルカラーにするヘルパー。
    - streamlit_extras がない: 普通の st.button
    - ある: stylable_container で色指定
    ※ stylable_container には ASCII の安全な key を渡す
    """
    if stylable_container is None:
        return st.button(label, key=key, **kwargs)

    # 日本語などを含む key → ハッシュ化して ASCII の安全なキーに変換
    base = f"btn:{key}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    sc_key = f"sc_{digest}"

    if large:
        padding = "0.8em 2.4em"
        font_size = "1.15em"
    else:
        padding = "0.4em 1.2em"
        font_size = "1.0em"

    css = f"""
        button {{
            background-color: {color};
            color: #000000;
            border-radius: 999px;
            padding: {padding};
            font-size: {font_size};
            border: none;
        }}
    """
    with stylable_container(key=sc_key, css_styles=css):
        return st.button(label, key=key, **kwargs)


# =========================
# 設定ファイルまわり
# =========================
def ensure_default_study_tasks(config: dict) -> bool:
    """勉強 5教科 + その他 を入れておく（足りない分だけ追加）"""
    tasks = config.setdefault("tasks", [])
    changed = False
    max_id = max((int(t.get("id", 0)) for t in tasks), default=0)
    for subj in STANDARD_STUDY_SUBJECTS:
        exists = any(
            str(t.get("category", "")).strip() == "勉強"
            and str(t.get("name", "")) == subj
            for t in tasks
        )
        if not exists:
            max_id += 1
            tasks.append(
                {
                    "id": max_id,
                    "category": "勉強",
                    "name": subj,
                    "points_per_hour": 10.0,
                }
            )
            changed = True
    return changed


def ensure_default_house_tasks(config: dict) -> bool:
    """家事プリセットを入れておく（足りない分だけ追加）"""
    tasks = config.setdefault("tasks", [])
    changed = False
    max_id = max((int(t.get("id", 0)) for t in tasks), default=0)
    for name in HOUSE_TASKS:
        exists = any(
            str(t.get("category", "")).strip() == "家事"
            and str(t.get("name", "")) == name
            for t in tasks
        )
        if not exists:
            max_id += 1
            tasks.append(
                {
                    "id": max_id,
                    "category": "家事",
                    "name": name,
                    "points_per_hour": 10.0,
                }
            )
            changed = True
    return changed


def load_config():
    """config.json を読み込み＋カテゴリの整理＋プリセット補完"""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        config = DEFAULT_CONFIG.copy()

    changed = False
    tasks = config.setdefault("tasks", [])

    # 既存タスクのカテゴリを整理 & 勉強ポイントは1時間10ptに固定
    for t in tasks:
        cat = str(t.get("category", "")).strip()
        name = str(t.get("name", ""))

        # 古い「お手伝い」は家事に寄せる
        if cat == "お手伝い":
            cat = "家事"

        # 勉強 5教科 + その他は強制的に「勉強」扱い
        if name in STANDARD_STUDY_SUBJECTS:
            cat = "勉強"

        t["category"] = cat

        # points_per_hour を float に揃え、勉強は 10pt/h に固定
        try:
            pph = float(t.get("points_per_hour", 10.0))
        except Exception:
            pph = 10.0

        if cat == "勉強":
            pph = 10.0

        t["points_per_hour"] = pph
        changed = True

    # プリセット補完
    if ensure_default_study_tasks(config):
        changed = True
    if ensure_default_house_tasks(config):
        changed = True

    if changed:
        save_config(config)

    return config


def save_config(config: dict):
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# =========================
# ログ（ポイント履歴）
# =========================
def load_logs() -> pd.DataFrame:
    if LOG_PATH.exists():
        df = pd.read_csv(LOG_PATH, encoding="utf-8")
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        return df
    else:
        return pd.DataFrame(
            columns=["date", "child", "category", "task", "hours", "points"]
        )


def save_logs(df: pd.DataFrame):
    df.to_csv(LOG_PATH, index=False, encoding="utf-8")


# =========================
# セッション状態
# =========================
def init_session_state():
    if "is_parent" not in st.session_state:
        st.session_state["is_parent"] = False
    if "study_buffer" not in st.session_state:
        # child_name -> {subject: minutes}
        st.session_state["study_buffer"] = {}


def get_study_buffer_for_child(child_name: str) -> dict:
    buf_all = st.session_state.setdefault("study_buffer", {})
    buf_child = buf_all.get(child_name)
    if buf_child is None:
        buf_child = {}
        buf_all[child_name] = buf_child
    return buf_child


def parent_sidebar(config):
    """親ログイン用サイドバー"""
    with st.sidebar:
        st.header("👨‍👩‍👧 親メニュー")
        if not st.session_state["is_parent"]:
            pwd = st.text_input("親用パスワード", type="password")
            if st.button("ログイン", key="parent_login_btn"):
                if pwd == config.get("parent_password", ""):
                    st.session_state["is_parent"] = True
                    st.success("親モードでログインしました")
                    do_rerun()
                else:
                    st.error("パスワードが違います")
        else:
            st.success("親モードでログイン中")
            if st.button("ログアウト", key="parent_logout_btn"):
                st.session_state["is_parent"] = False
                do_rerun()


# =========================
# ヘルパー
# =========================
def find_task(config: dict, category: str, name: str):
    for t in config.get("tasks", []):
        cat = str(t.get("category", "")).strip()
        nm = str(t.get("name", ""))
        if cat == category.strip() and nm == name:
            return t
    return None


# =========================
# 子どもタブ
# =========================
def render_child_tab(child_name: str, config: dict, logs_df: pd.DataFrame):
    alias = get_child_alias(child_name)
    st.subheader(f"👦 {alias} のページ")

    tasks = config.get("tasks", [])
    if not tasks:
        st.info("まだ項目が設定されていません。親メニューから項目を追加してください。")
        return

    # ---- 勉強ボタン（15分単位）----
    st.markdown("### 📚 勉強ボタン（15分ずつためて、あとでまとめてポイント）")
    st.write(
        "やった教科のボタンをおすと、15分ずつふえます。"
        "勉強がおわったら、下の「リセット」「今日の勉強を確定」のボタンをつかってね。"
    )

    buffer = get_study_buffer_for_child(child_name)

    # 1行に2教科ずつ
    cols = st.columns(2)
    for idx, subj in enumerate(STANDARD_STUDY_SUBJECTS):
        col = cols[idx % 2]
        with col:
            task = find_task(config, "勉強", subj)
            pph = float(task.get("points_per_hour", 10.0)) if task else 10.0
            minutes = int(buffer.get(subj, 0))

            inner_cols = st.columns([2, 1, 1])
            with inner_cols[0]:
                st.markdown(f"**{subj}**")
                st.write(f"{minutes} 分（{pph:.0f} pt / 1時間）")

            plus_key = f"{child_name}_{subj}_plus"
            minus_key = f"{child_name}_{subj}_minus"

            plus = False
            minus = False
            with inner_cols[1]:
                # ＋：薄いグリーン
                plus = pastel_button("＋15分", key=plus_key, color="#C8E6C9")
            with inner_cols[2]:
                # −：薄いきいろ
                minus = pastel_button("−15分", key=minus_key, color="#FFECB3")

            if plus:
                buffer[subj] = minutes + 15
                do_rerun()
            if minus and minutes >= 15:
                buffer[subj] = minutes - 15
                do_rerun()

    # ちょっと空白
    st.markdown("<br>", unsafe_allow_html=True)

    # ---- 勉強のまとめ（リセット＆確定）----
    st.markdown("### ⏱ 勉強のまとめ")
    st.write("まちがえたときは左のリセット、勉強がおわったら右のボタンをおしてね。")

    col_left, col_space, col_right = st.columns([1, 0.2, 1])

    with col_left:
        reset_key = f"{child_name}_reset_study"
        # リセット：大きめ水色ボタン
        if pastel_button(
            "今日の勉強時間をリセット",
            key=reset_key,
            color="#B3E5FC",
            large=True,
        ):
            st.session_state["study_buffer"][child_name] = {}
            do_rerun()

    with col_right:
        confirm_key = f"{child_name}_confirm_study"
        # 確定：大きめの薄いむらさきボタン
        if pastel_button(
            "今日の勉強を確定してポイントにする",
            key=confirm_key,
            color="#D1C4E9",
            large=True,
        ):
            buf = st.session_state["study_buffer"].get(child_name, {})
            rows = []
            for subj, minutes in buf.items():
                if minutes <= 0:
                    continue
                task = find_task(config, "勉強", subj)
                pph = float(task.get("points_per_hour", 10.0)) if task else 10.0
                hours = minutes / 60.0
                points = hours * pph
                rows.append(
                    {
                        "date": date.today(),
                        "child": child_name,
                        "category": "勉強",
                        "task": subj,
                        "hours": hours,
                        "points": points,
                    }
                )
            if not rows:
                st.warning("勉強時間が0分です。先に上のボタンで時間をふやしてください。")
            else:
                updated_df = pd.concat([logs_df, pd.DataFrame(rows)], ignore_index=True)
                save_logs(updated_df)
                st.session_state["study_buffer"][child_name] = {}
                total_points = sum(r["points"] for r in rows)
                st.success(f"今日の勉強を登録しました！ 合計 ＋{total_points:.1f} ポイント")
                st.balloons()
                do_rerun()

    st.markdown("---")

    # ---- くわしい入力 ----
    st.markdown("### ✏ くわしい入力（家事や時間を細かく入れたいとき）")

    # 区分：家事 / 勉強
    category = st.radio(
        "区分を選ぶ",
        ["家事", "勉強"],
        key=f"category_radio_{child_name}",
        horizontal=True,
    )

    with st.form(key=f"detail_form_{child_name}"):
        col1, col2 = st.columns(2)
        with col1:
            target_date = st.date_input(
                "日付",
                value=date.today(),
                key=f"detail_date_{child_name}",
            )

        with col2:
            # 区分に応じて項目リストを切り替え
            if category == "家事":
                options = [
                    t for t in tasks
                    if str(t.get("category", "")).strip() == "家事"
                ]
            else:  # 勉強
                options = [
                    t for t in tasks
                    if str(t.get("category", "")).strip() == "勉強"
                ]

            if options:
                task_label_list = [
                    f'{t["name"]}（{t["points_per_hour"]} pt/1時間）'
                    for t in options
                ]
                selected_idx = st.selectbox(
                    "項目",
                    range(len(options)),
                    format_func=lambda i: task_label_list[i],
                    key=f"detail_task_{child_name}",
                )
                selected_task = options[selected_idx]
            else:
                selected_task = None
                st.write("この区分にはまだ項目がありません。親メニューから追加してください。")

            hours = st.number_input(
                "時間数（例：0.5 = 30分）",
                min_value=0.25,
                max_value=8.0,
                value=0.5,
                step=0.25,
                key=f"detail_hours_{child_name}",
            )

        submitted = st.form_submit_button("ポイントを登録 ✨")

    if submitted:
        if selected_task is None:
            st.error("項目が選択できません。親メニューから項目を追加してください。")
        else:
            points = float(selected_task["points_per_hour"]) * float(hours)
            new_row = {
                "date": target_date,
                "child": child_name,
                "category": selected_task["category"],
                "task": selected_task["name"],
                "hours": float(hours),
                "points": points,
            }
            updated_df = pd.concat(
                [logs_df, pd.DataFrame([new_row])], ignore_index=True
            )
            save_logs(updated_df)
            st.success(f"登録しました！ ＋{points:.1f} ポイント")
            st.balloons()
            do_rerun()

    # ---- きょう & こんしゅう の合計 ----
    st.markdown("### きょうと こんしゅう のポイント")

    child_df = logs_df[logs_df["child"] == child_name].copy()
    if child_df.empty:
        st.info("まだポイントが登録されていません。")
        return

    child_df["date"] = pd.to_datetime(child_df["date"])
    child_df = child_df.sort_values("date")

    today = date.today()
    today_df = child_df[child_df["date"].dt.date == today]
    today_points = today_df["points"].sum()

    this_week_start = today - timedelta(days=today.weekday())
    this_week_df = child_df[child_df["date"].dt.date >= this_week_start]
    this_week_points = this_week_df["points"].sum()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f"""
            <div style="background-color:#FFF4C1; padding:16px; border-radius:16px; text-align:center;">
              <div style="font-size:20px; font-weight:bold;">きょうのポイント</div>
              <div style="font-size:40px; font-weight:bold;">{today_points:.1f} pt</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            f"""
            <div style="background-color:#CFE9FF; padding:16px; border-radius:16px; text-align:center;">
              <div style="font-size:20px; font-weight:bold;">こんしゅうのポイント</div>
              <div style="font-size:14px;">（今週月よう日〜きょうまで）</div>
              <div style="font-size:40px; font-weight:bold;">{this_week_points:.1f} pt</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- 減点 ----
    st.markdown("#### 減点の履歴")
    penalty_df = child_df[child_df["points"] < 0].copy()
    if penalty_df.empty:
        st.write("減点はありません。")
    else:
        pen_show = penalty_df[["date", "category", "task", "points"]].sort_values(
            "date", ascending=False
        )
        pen_show["points"] = pen_show["points"].map(lambda x: f"{x:.1f} pt")
        st.dataframe(pen_show, use_container_width=True)

    if st.session_state.get("is_parent", False):
        st.markdown("#### 減点をつける（親用）")
        st.info("親モードのときだけ表示されます。理由とポイント数を入力して減点を登録します。")

        with st.form(f"penalty_form_{child_name}"):
            p_date = st.date_input(
                "日付（減点する日）",
                value=today,
                key=f"penalty_date_{child_name}",
            )
            reason = st.text_input(
                "理由（例：宿題をさぼった／けんかをした 等）",
                key=f"penalty_reason_{child_name}",
            )
            minus_points = st.number_input(
                "減点ポイント数（正の数で入力）",
                min_value=1.0,
                max_value=1000.0,
                value=10.0,
                step=1.0,
                key=f"penalty_points_{child_name}",
            )
            submit_penalty = st.form_submit_button("減点を登録")

        if submit_penalty:
            if not reason.strip():
                st.error("理由を入力してください。")
            else:
                new_row = {
                    "date": p_date,
                    "child": child_name,
                    "category": "減点",
                    "task": reason.strip(),
                    "hours": 0.0,
                    "points": -float(minus_points),
                }
                updated_df = pd.concat(
                    [logs_df, pd.DataFrame([new_row])], ignore_index=True
                )
                save_logs(updated_df)
                st.success(f"{alias} に {minus_points:.1f} pt の減点を登録しました。")
                do_rerun()

    # ---- 直近1件の取り消し ----
    st.markdown("#### 誤操作したときの取り消し（直近1件）")
    undo_key = f"undo_latest_{child_name}"
    # 取り消し：薄いピンク
    if pastel_button(
        "直近の1件を取り消す（この子の分だけ）",
        key=undo_key,
        color="#F8BBD0",
    ):
        mask = logs_df["child"] == child_name
        if not mask.any():
            st.warning("取り消すデータがありません。")
        else:
            latest_index = logs_df[mask].index.max()
            all_df = logs_df.drop(index=latest_index)
            save_logs(all_df)
            st.success("直近の1件を取り消しました。")
            do_rerun()

    # ---- 履歴一覧 & 選んで削除 ----
    st.markdown("#### 履歴一覧")
    child_df_sorted = child_df.sort_values("date", ascending=False)
    show_df = child_df_sorted[["date", "category", "task", "hours", "points"]]
    st.dataframe(show_df, use_container_width=True)

    if st.session_state.get("is_parent", False):
        st.markdown("#### 履歴から選んで削除（親用）")
        if not child_df_sorted.empty:
            choices = []
            for idx, row in child_df_sorted.iterrows():
                label = (
                    f"{idx}: {row['date']} / {row['category']} / "
                    f"{row['task']} / {row['hours']}時間 / {row['points']}pt"
                )
                choices.append((idx, label))

            labels = ["選択しない"] + [lbl for _, lbl in choices]
            selected_label = st.selectbox(
                "削除したい履歴を選んでください",
                labels,
                key=f"delete_select_{child_name}",
            )

            delete_key = f"delete_button_{child_name}"
            # 削除ボタン：グレー系
            if pastel_button(
                "選択した履歴を削除",
                key=delete_key,
                color="#CFD8DC",
            ):
                if selected_label == "選択しない":
                    st.warning("削除する履歴を選択してください。")
                else:
                    selected_idx = None
                    for idx, lbl in choices:
                        if lbl == selected_label:
                            selected_idx = idx
                            break
                    if selected_idx is None:
                        st.error("削除対象を特定できませんでした。")
                    else:
                        all_df = logs_df.drop(index=selected_idx)
                        save_logs(all_df)
                        st.success("選択した履歴を削除しました。")
                        do_rerun()


# =========================
# 親タブ
# =========================
def render_parent_tab(config: dict, logs_df: pd.DataFrame):
    st.subheader("⚙ 親用設定・管理")
    st.info("※ このタブは親用です。子どもには見せない想定です。")

    # 子ども管理
    st.markdown("### 子どもの名前の管理")
    st.write("現在の登録：", "、".join(config.get("children", [])) or "（なし）")

    col1, col2 = st.columns(2)
    with col1:
        new_child = st.text_input("子どもの名前を追加", value="", key="new_child_name")
        if st.button("子どもを追加", key="add_child_button"):
            new_child_stripped = new_child.strip()
            if not new_child_stripped:
                st.error("名前を入力してください。")
            elif new_child_stripped in config["children"]:
                st.error("すでに同じ名前が登録されています。")
            else:
                config["children"].append(new_child_stripped)
                save_config(config)
                st.success(f"{new_child_stripped} を追加しました。")
                do_rerun()
    with col2:
        if config["children"]:
            del_child = st.selectbox(
                "削除したい子ども（任意）", ["選択しない"] + config["children"]
            )
            if st.button("選択した子どもを削除", key="delete_child_button"):
                if del_child != "選択しない":
                    if len(config["children"]) <= 1:
                        st.error("子どもは1人以上必要です。")
                    else:
                        config["children"] = [
                            c for c in config["children"] if c != del_child
                        ]
                        save_config(config)
                        st.success(f"{del_child} を削除しました。")
                        do_rerun()

    st.markdown("---")

    # 項目管理
    st.markdown("### 家事・勉強の項目の管理")
    tasks = config.get("tasks", [])

    if tasks:
        df_tasks = pd.DataFrame(tasks)
        df_tasks = df_tasks[["id", "category", "name", "points_per_hour"]]
        df_tasks = df_tasks.rename(
            columns={
                "id": "ID",
                "category": "区分",
                "name": "項目名",
                "points_per_hour": "1時間あたりポイント",
            }
        )
        st.dataframe(df_tasks, use_container_width=True)
    else:
        st.write("まだ項目がありません。下のフォームから追加してください。")

    st.markdown("#### 項目を追加")
    with st.form("add_task_form"):
        col3, col4, col5 = st.columns([1, 2, 1])
        with col3:
            category = st.selectbox("区分", ["家事", "勉強"])
        with col4:
            name = st.text_input("項目名（例：皿洗い・算数ドリル など）")
        with col5:
            pph = st.number_input(
                "1時間あたりポイント（※勉強は自動で10ptになります）",
                min_value=1.0,
                max_value=1000.0,
                value=10.0,
                step=1.0,
            )

        submitted = st.form_submit_button("項目を追加")

    if submitted:
        name_stripped = name.strip()
        tasks = config.get("tasks", [])
        if not name_stripped:
            st.error("項目名を入力してください。")
        else:
            for t in tasks:
                if (
                    str(t.get("category", "")).strip() == category.strip()
                    and str(t.get("name", "")).strip() == name_stripped
                ):
                    st.error("同じ区分＋項目名がすでに登録されています。")
                    break
            else:
                next_id = max((int(t.get("id", 0)) for t in tasks), default=0) + 1

                if category == "勉強":
                    pph_to_save = 10.0
                else:
                    pph_to_save = float(pph)

                tasks.append(
                    {
                        "id": next_id,
                        "category": category,
                        "name": name_stripped,
                        "points_per_hour": pph_to_save,
                    }
                )
                config["tasks"] = tasks
                save_config(config)
                st.success("項目を追加しました。")
                do_rerun()

    st.markdown("#### 項目を削除")
    tasks = config.get("tasks", [])
    if tasks:
        task_labels = [f'{t["id"]}: {t["category"]} - {t["name"]}' for t in tasks]
        del_label = st.selectbox(
            "削除したい項目（任意）", ["選択しない"] + task_labels
        )
        if st.button("選択した項目を削除", key="delete_task_button"):
            if del_label != "選択しない":
                del_id = int(del_label.split(":")[0])
                tasks = [t for t in tasks if int(t.get("id", 0)) != del_id]
                config["tasks"] = tasks
                save_config(config)
                st.success("項目を削除しました。")
                do_rerun()

    st.markdown("---")

    # 親パスワード変更
    st.markdown("### 親用パスワードの変更")
    with st.form("change_password_form"):
        new_pwd = st.text_input("新しいパスワード", type="password")
        new_pwd2 = st.text_input("確認のため再入力", type="password")
        submitted_pwd = st.form_submit_button("パスワードを変更")

    if submitted_pwd:
        if not new_pwd:
            st.error("パスワードを入力してください。")
        elif new_pwd != new_pwd2:
            st.error("パスワードが一致しません。")
        else:
            config["parent_password"] = new_pwd
            save_config(config)
            st.success("親用パスワードを変更しました。次回から新しいパスワードでログインしてください。")

    st.markdown("---")

    # 全体ログ
    st.markdown("### 全体の履歴（親用）")
    if logs_df.empty:
        st.write("まだ登録された履歴がありません。")
    else:
        df_all = logs_df.copy()
        df_all["date"] = pd.to_datetime(df_all["date"])
        df_all = df_all.sort_values("date", ascending=False)
        st.dataframe(df_all, use_container_width=True)


# =========================
# メイン
# =========================
def main():
    st.set_page_config(
        page_title="お手伝い・お勉強ポイント帳",
        layout="wide",
        page_icon="⭐",
    )

    set_kids_style()
    st.title("お手伝い・お勉強ポイント帳")

    init_session_state()
    config = load_config()
    logs_df = load_logs()
    parent_sidebar(config)

    children = config.get("children", [])
    if not children:
        st.error("子どもの名前が設定されていません。親メニューから追加してください。")
        return

    # タブ名だけ K / S などの別名にする（データ上の名前はそのまま）
    tab_names = [f"{get_child_alias(c)}のページ" for c in children]
    if st.session_state["is_parent"]:
        tab_names.append("親用設定")

    tabs = st.tabs(tab_names)

    for i, child in enumerate(children):
        with tabs[i]:
            render_child_tab(child, config, logs_df)

    if st.session_state["is_parent"]:
        with tabs[-1]:
            render_parent_tab(config, logs_df)


if __name__ == "__main__":
    main()
