from pathlib import Path
import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st


def do_rerun():
    """Streamlitのバージョン差を吸収して再実行する."""
    try:
        st.rerun()
    except AttributeError:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()


# =========================
# ファイル保存用のパス設定
# =========================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "logs.csv"

# =========================
# 初期設定
# =========================
DEFAULT_CONFIG = {
    "parent_password": "otetsudai123",  # 最初の親用パスワード（あとで変更できます）
    "children": ["Aちゃん", "Bくん"],   # 初期状態の子どもの例（親用タブから変更可）
    "tasks": [
        {"id": 1, "category": "お手伝い", "name": "皿洗い", "points_per_hour": 10.0},
        {"id": 2, "category": "お手伝い", "name": "洗濯物をたたむ", "points_per_hour": 10.0},
        {"id": 3, "category": "勉強", "name": "算数", "points_per_hour": 15.0},
        {"id": 4, "category": "勉強", "name": "国語", "points_per_hour": 15.0},
    ],
}


def load_config():
    """設定(config.json)を読み込む。なければ初期設定で作成。"""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    else:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """設定を保存"""
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_logs() -> pd.DataFrame:
    """ポイント履歴(logs.csv)を読み込む。なければ空のDataFrame。"""
    if LOG_PATH.exists():
        df = pd.read_csv(LOG_PATH, encoding="utf-8")
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        return df
    else:
        return pd.DataFrame(columns=["date", "child", "category", "task", "hours", "points"])


def save_logs(df: pd.DataFrame):
    """ポイント履歴を保存"""
    df.to_csv(LOG_PATH, index=False, encoding="utf-8")


# =========================
# セッション状態（親ログイン）の管理
# =========================
def init_session_state():
    if "is_parent" not in st.session_state:
        st.session_state["is_parent"] = False


def parent_sidebar(config):
    """サイドバーの親ログインUI"""
    with st.sidebar:
        st.header("👨‍👩‍👧 親メニュー")
        if not st.session_state["is_parent"]:
            pwd = st.text_input("親用パスワード", type="password")
            if st.button("ログイン"):
                if pwd == config.get("parent_password", ""):
                    st.session_state["is_parent"] = True
                    st.success("親モードでログインしました")
                    do_rerun()
                else:
                    st.error("パスワードが違います")
        else:
            st.success("親モードでログイン中")
            if st.button("ログアウト"):
                st.session_state["is_parent"] = False
                do_rerun()


# =========================
# 子ども用タブ
# =========================
def render_child_tab(child_name: str, config: dict, logs_df: pd.DataFrame):
    st.subheader(f"👦 {child_name} のページ")

    tasks = config.get("tasks", [])
    if not tasks:
        st.info("まだ項目が設定されていません。親メニューから項目を追加してください。")
        return

    # ---- 入力フォーム ----
    st.markdown("### 今日のお手伝い・お勉強を登録する")

    with st.form(key=f"form_{child_name}"):
        col1, col2 = st.columns(2)
        with col1:
            target_date = st.date_input("日付", value=date.today())
            category = st.selectbox(
                "区分（お手伝い or 勉強）",
                sorted(set(t["category"] for t in tasks)),
            )
        with col2:
            # 区分に応じた項目の候補
            options = [t for t in tasks if t["category"] == category]
            if options:
                task_label_list = [f'{t["name"]}（{t["points_per_hour"]} pt/1時間）' for t in options]
                selected_idx = st.selectbox(
                    "項目",
                    range(len(options)),
                    format_func=lambda i: task_label_list[i],
                )
                selected_task = options[selected_idx]
            else:
                selected_task = None

            hours = st.number_input(
                "時間数（例：0.5 = 30分）",
                min_value=0.25,
                max_value=8.0,
                value=0.5,
                step=0.25,
            )

        submitted = st.form_submit_button("ポイントを登録 ✨")

    if submitted:
        if selected_task is None:
            st.error("項目が選択できません。親メニューから項目を追加してください。")
        else:
            points = selected_task["points_per_hour"] * float(hours)
            new_row = {
                "date": target_date,
                "child": child_name,
                "category": selected_task["category"],
                "task": selected_task["name"],
                "hours": float(hours),
                "points": points,
            }
            updated_df = pd.concat([logs_df, pd.DataFrame([new_row])], ignore_index=True)
            save_logs(updated_df)
            st.success(f"登録しました！ ＋{points:.0f} ポイント")
            st.balloons()
            do_rerun()

    # ---- 集計・グラフ ----
    st.markdown("### これまでのポイント")

    child_df = logs_df[logs_df["child"] == child_name].copy()
    if child_df.empty:
        st.info("まだポイントが登録されていません。上のフォームから登録してみましょう。")
        return

    child_df["date"] = pd.to_datetime(child_df["date"])
    child_df = child_df.sort_values("date")

    # 累計 & 今週
    total_points = child_df["points"].sum()
    this_week_start = date.today() - timedelta(days=date.today().weekday())
    this_week_df = child_df[child_df["date"].dt.date >= this_week_start]
    this_week_points = this_week_df["points"].sum()

    col1, col2 = st.columns(2)
    col1.metric("これまでの累計ポイント", f"{int(total_points)} pt")
    col2.metric("今週のポイント（今週月曜〜）", f"{int(this_week_points)} pt")

    # 直近14日の日別ポイント
    st.markdown("#### 直近2週間の日別ポイント")
    two_weeks_ago = date.today() - timedelta(days=13)
    recent_df = child_df[child_df["date"].dt.date >= two_weeks_ago]

    if not recent_df.empty:
        daily = recent_df.groupby(recent_df["date"].dt.date)["points"].sum()
        st.bar_chart(daily)
    else:
        st.write("直近2週間のデータはまだありません。")

    # 週別ポイント（週の開始日：月曜日）
    st.markdown("#### 週ごとの合計ポイント")
    df_week = child_df.copy()
    df_week["week_start"] = df_week["date"] - pd.to_timedelta(df_week["date"].dt.weekday, unit="D")
    weekly = df_week.groupby("week_start")["points"].sum()
    st.bar_chart(weekly)

    # 履歴一覧
    st.markdown("#### 履歴一覧")
    show_df = child_df[["date", "category", "task", "hours", "points"]].sort_values("date", ascending=False)
    st.dataframe(show_df, use_container_width=True)


# =========================
# 親用タブ（設定）
# =========================
def render_parent_tab(config: dict, logs_df: pd.DataFrame):
    st.subheader("⚙ 親用設定・管理")
    st.info("※ このタブは親用です。子どもには見せない想定です。")

    # ---- 子ども管理 ----
    st.markdown("### 子どもの名前の管理")

    st.write("現在の登録：", "、".join(config.get("children", [])) or "（なし）")

    col1, col2 = st.columns(2)
    with col1:
        new_child = st.text_input("子どもの名前を追加", value="", key="new_child_name")
        if st.button("子どもを追加"):
            new_child = new_child.strip()
            if not new_child:
                st.error("名前を入力してください。")
            elif new_child in config["children"]:
                st.error("すでに同じ名前が登録されています。")
            else:
                config["children"].append(new_child)
                save_config(config)
                st.success(f"{new_child} を追加しました。")
                do_rerun()

    with col2:
        if config["children"]:
            del_child = st.selectbox("削除したい子ども（任意）", ["選択しない"] + config["children"])
            if st.button("選択した子どもを削除"):
                if del_child != "選択しない":
                    if len(config["children"]) <= 1:
                        st.error("子どもは1人以上必要です。")
                    else:
                        config["children"] = [c for c in config["children"] if c != del_child]
                        save_config(config)
                        st.success(f"{del_child} を削除しました。")
                        do_rerun()

    st.markdown("---")

    # ---- 項目管理 ----
    st.markdown("### お手伝い・勉強項目の管理")

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
            category = st.selectbox("区分", ["お手伝い", "勉強"])
        with col4:
            name = st.text_input("項目名（例：皿洗い・算数ドリル など）")
        with col5:
            pph = st.number_input("1時間あたりポイント", min_value=1.0, max_value=1000.0, value=10.0, step=1.0)

        submitted = st.form_submit_button("項目を追加")
        if submitted:
            name = name.strip()
            if not name:
                st.error("項目名を入力してください。")
            else:
                # 同じ区分＋同じ名前は重複禁止
                for t in tasks:
                    if t["category"] == category and t["name"] == name:
                        st.error("同じ区分＋項目名がすでに登録されています。")
                        break
                else:
                    next_id = max([t["id"] for t in tasks], default=0) + 1
                    tasks.append(
                        {
                            "id": next_id,
                            "category": category,
                            "name": name,
                            "points_per_hour": float(pph),
                        }
                    )
                    config["tasks"] = tasks
                    save_config(config)
                    st.success("項目を追加しました。")
                    do_rerun()

    st.markdown("#### 項目を削除")

    if tasks:
        task_labels = [f'{t["id"]}: {t["category"]} - {t["name"]}' for t in tasks]
        del_label = st.selectbox("削除したい項目（任意）", ["選択しない"] + task_labels)
        if st.button("選択した項目を削除"):
            if del_label != "選択しない":
                del_id = int(del_label.split(":")[0])
                tasks = [t for t in tasks if t["id"] != del_id]
                config["tasks"] = tasks
                save_config(config)
                st.success("項目を削除しました。")
                do_rerun()

    st.markdown("---")

    # ---- 親パスワード変更 ----
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

    # ---- 全体ログ（親用） ----
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

    st.title("お手伝い・お勉強ポイント帳")

    st.write(
        """
        このアプリは、子どもたちがしたお手伝いやお勉強の時間に応じてポイントをためていき、
        週ごとのグラフや累計ポイントを家族で一緒に眺めるためのアプリです 😊  
        左のサイドバーから親ログインをすると、項目や子どもの名前の編集ができます。
        """
    )

    init_session_state()
    config = load_config()
    logs_df = load_logs()
    parent_sidebar(config)

    # 子どもタブ＋親用タブ
    children = config.get("children", [])
    if not children:
        st.error("子どもの名前が設定されていません。親メニューから追加してください。")
        return

    tab_names = [f"{c}のページ" for c in children]
    if st.session_state["is_parent"]:
        tab_names.append("親用設定")

    tabs = st.tabs(tab_names)

    # 子ども用タブ
    for i, child in enumerate(children):
        with tabs[i]:
            render_child_tab(child, config, logs_df)

    # 親用タブ
    if st.session_state["is_parent"]:
        with tabs[-1]:
            render_parent_tab(config, logs_df)


if __name__ == "__main__":
    main()
