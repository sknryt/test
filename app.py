import io
from datetime import date, datetime, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from openpyxl.utils import get_column_letter

import database as db

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

st.set_page_config(
    page_title="日報管理システム",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&display=swap');

/* フォント（日本語向け） */
html, body, p, h1, h2, h3, h4, h5, h6, input, textarea, button, label, li, td, th {
    font-family: 'Noto Sans JP', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
}

/* Streamlit のツールバー・フッター・メニューを非表示 */
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: transparent;
}

/* アプリ背景（目に優しいダークネイビー） */
.stApp {
    background: #0f172a;
}

/* サイドバー */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1b4b 0%, #312e81 70%, #3730a3 100%);
}
section[data-testid="stSidebar"] * {
    color: #f1f5f9 !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] label {
    border-radius: 8px;
    padding: 0.35rem 0.6rem;
    transition: background 0.15s ease;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(255, 255, 255, 0.12);
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.2);
}
section[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 0.5rem;
}
/* サイドバーのボタン（ログアウト）を常に視認できるように */
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.45);
    color: #ffffff !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255, 255, 255, 0.22);
    border-color: #ffffff;
}

/* ボタン */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(129, 140, 248, 0.35);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(90deg, #4f46e5 0%, #6366f1 100%);
    border: none;
    color: #ffffff;
}

/* フォーム・カード風コンテナ */
div[data-testid="stForm"], div[data-testid="stExpander"] {
    background: #1e293b;
    border: 1px solid #334155 !important;
    border-radius: 12px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}

/* 日報カード */
.report-card {
    background: #1e293b;
    border-left: 4px solid #818cf8;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0 1rem 0;
    border-radius: 0 10px 10px 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

/* バッジ */
.badge-ok  { color: #4ade80; font-weight: bold; font-size: 1.05rem; }
.badge-ng  { color: #f87171; font-weight: bold; font-size: 1.05rem; }

/* メインタイトル（グラデーション文字） */
[data-testid="stMain"] h1, .block-container h1 {
    background: linear-gradient(90deg, #a5b4fc 0%, #818cf8 60%, #c7d2fe 100%);
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    color: #a5b4fc;
    font-weight: 800;
    padding-bottom: 0.3rem;
}

/* セクション見出し */
[data-testid="stMain"] h2, .block-container h2,
[data-testid="stMain"] h3, .block-container h3 {
    border-bottom: 2px solid #334155;
    padding-bottom: 0.4rem;
}

/* データフレーム */
[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 10px;
    overflow: hidden;
}

/* メトリクス数値を強調 */
[data-testid="stMetricValue"] {
    font-weight: 800;
}

/* 通知・アラート */
[data-testid="stAlert"] {
    border-radius: 10px;
}

/* タブ・入力欄の角丸 */
.stTextInput input, .stTextArea textarea, .stDateInput input, .stTimeInput input {
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


# ─── ページ: ログイン ─────────────────────────────────────────────────────────
def show_login():
    with st.container(border=True):
        st.subheader("🔐 ログイン")

        if st.session_state.pop("register_success", False):
            st.success("✅ 登録が完了しました。ログインしてください。")

        with st.form("login_form"):
            username = st.text_input("ユーザー名（氏名）")
            password = st.text_input("パスワード", type="password")
            submitted = st.form_submit_button("ログイン", type="primary", use_container_width=True)

        if submitted:
            username = username.strip()
            if not username or not password:
                st.error("ユーザー名とパスワードを入力してください。")
            else:
                user = db.verify_user(username, password)
                if user is None:
                    st.error("ユーザー名またはパスワードが正しくありません。")
                else:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.is_admin = user["is_admin"]
                    st.rerun()

        st.divider()
        st.markdown("アカウントをお持ちでない方は")
        if st.button("新規登録はこちら", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()


# ─── ページ: 新規登録 ─────────────────────────────────────────────────────────
def show_register():
    with st.container(border=True):
        st.subheader("📝 新規登録")

        with st.form("register_form"):
            username = st.text_input("ユーザー名（氏名）", placeholder="山田 太郎")
            password = st.text_input("パスワード", type="password")
            password_confirm = st.text_input("パスワード（確認）", type="password")
            submitted = st.form_submit_button("登録する", type="primary", use_container_width=True)

        if submitted:
            username = username.strip()
            if not username:
                st.error("ユーザー名を入力してください。")
            elif not password:
                st.error("パスワードを入力してください。")
            elif len(password) < 8:
                st.error("パスワードは8文字以上で設定してください。")
            elif password != password_confirm:
                st.error("パスワードが一致しません。")
            elif db.create_user(username, password, is_admin=False):
                db.add_member(username)
                st.session_state.register_success = True
                st.session_state.auth_page = "login"
                st.rerun()
            else:
                st.error("そのユーザー名は既に登録されています。")

        st.divider()
        st.markdown("既にアカウントをお持ちの方は")
        if st.button("ログイン画面に戻る", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()


# ─── 未ログイン時のトップ画面 ──────────────────────────────────────────────────
def show_auth():
    st.markdown(
        '<div style="text-align:center; padding-top:1.5rem;">'
        '<div style="font-size:3.5rem; line-height:1;">📋</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 style="text-align:center; margin-bottom:0;">日報管理システム</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center; color:#94a3b8; margin-bottom:1.5rem;">'
        "チームの日報を、もっとスマートに。</p>",
        unsafe_allow_html=True,
    )

    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"

    _, col, _ = st.columns([1, 2, 1])
    with col:
        if st.session_state.auth_page == "register":
            show_register()
        else:
            show_login()


# ─── ページ: 日報提出 ─────────────────────────────────────────────────────────
def show_submit():
    st.title("📝 日報提出")

    current_user = st.session_state.get("username", "")
    st.caption(f"提出者: {current_user}")

    # 直前の提出成功メッセージ（フォームクリア後の再実行で表示）
    flash = st.session_state.pop("submit_flash", None)
    if flash:
        st.success(flash)
        st.balloons()

    with st.form("report_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            report_date = st.date_input("日付", value=date.today(), key="sub_date")
        with col2:
            start_time_input = st.time_input("⏰ 開始時刻", value=time(9, 0), step=900, key="sub_start")
        with col3:
            end_time_input = st.time_input("⏰ 終了時刻", value=time(18, 0), step=900, key="sub_end")

        tasks = st.text_area(
            "✅ 今日やったこと（必須）",
            height=130,
            placeholder="・会議の議事録作成\n・〇〇機能の実装\n・△△の調査・確認",
            key="sub_tasks",
        )
        tomorrow_plan = st.text_area(
            "📅 明日の予定（必須）",
            height=100,
            placeholder="・〇〇のレビュー依頼\n・△△のテスト実施",
            key="sub_plan",
        )
        impressions = st.text_area(
            "💬 所感・連絡事項（任意）",
            height=80,
            placeholder="気になったこと、困っていること、共有事項など",
            key="sub_imp",
        )

        submitted = st.form_submit_button("提出する", type="primary", use_container_width=True)

    if not submitted:
        return

    name = current_user
    missing = []
    if not tasks.strip():
        missing.append("今日やったこと")
    if not tomorrow_plan.strip():
        missing.append("明日の予定")
    if missing:
        st.error(
            f"⚠️ 未入力の項目があります: **{'・'.join(missing)}** を入力してください。"
            "（所感・連絡事項は未入力でも提出できます）"
        )
        return

    start_dt = datetime.combine(date.today(), start_time_input)
    end_dt = datetime.combine(date.today(), end_time_input)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    work_hours = round((end_dt - start_dt).total_seconds() / 3600, 2)

    date_str = report_date.strftime("%Y-%m-%d")
    duplicate = db.has_submitted(name, date_str)

    db.save_report(
        date_str, name, tasks, tomorrow_plan, impressions, work_hours,
        start_time_input.strftime("%H:%M"), end_time_input.strftime("%H:%M"),
    )
    msg = (
        f"✅ {name} さんの日報（{report_date:%Y/%m/%d}）を提出しました！　"
        f"勤務時間: {start_time_input:%H:%M}〜{end_time_input:%H:%M}（{work_hours}h）"
    )
    if duplicate:
        msg += "　※同日の日報があったため追加提出として保存しました。"
    st.session_state.submit_flash = msg
    # 成功時のみフォームをクリア（エラー時は入力を保持）
    for k in ("sub_tasks", "sub_plan", "sub_imp"):
        st.session_state.pop(k, None)
    st.rerun()


# ─── ページ: 一覧・検索 ───────────────────────────────────────────────────────
def show_list():
    st.title("📋 一覧・検索")

    current_user = st.session_state.get("username", "")
    is_admin = st.session_state.get("is_admin", False)

    if is_admin:
        members = db.get_members()
        with st.expander("🔍 検索フィルター", expanded=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                date_from = st.date_input("開始日", value=date.today() - timedelta(days=30), key="lf")
                date_to   = st.date_input("終了日", value=date.today(), key="lt")
            with c2:
                name_filter = st.selectbox("名前", ["すべて"] + members, key="ln")
            with c3:
                keyword = st.text_input("キーワード検索", placeholder="本文を横断検索", key="lk")
                st.caption("「今日やったこと」「明日の予定」「所感」を同時に検索します")
    else:
        name_filter = current_user
        with st.expander("🔍 検索フィルター", expanded=True):
            st.caption("🔒 自分の日報のみ表示されます")
            c1, c2 = st.columns([2, 3])
            with c1:
                date_from = st.date_input("開始日", value=date.today() - timedelta(days=30), key="lf")
                date_to   = st.date_input("終了日", value=date.today(), key="lt")
            with c2:
                keyword = st.text_input("キーワード検索", placeholder="本文を横断検索", key="lk")
                st.caption("「今日やったこと」「明日の予定」「所感」を同時に検索します")

    df = db.get_reports(
        date_from=date_from,
        date_to=date_to,
        name=None if name_filter == "すべて" else name_filter,
        keyword=keyword.strip() or None,
    )

    st.markdown(f"**{len(df)} 件** ヒット")

    if df.empty:
        st.info("該当する日報が見つかりませんでした。")
        return

    # テーブル表示用に長文を省略
    df["勤務時間"] = df.apply(
        lambda r: f"{r['start_time']}〜{r['end_time']}" if r["start_time"] and r["end_time"] else "-",
        axis=1,
    )
    display_df = df[["id", "date", "name", "勤務時間", "tasks", "tomorrow_plan", "impressions", "work_hours", "created_at"]].copy()
    display_df.columns = ["ID", "日付", "名前", "勤務時間", "今日やったこと", "明日の予定", "所感", "実績時間(h)", "提出日時"]
    for col in ["今日やったこと", "明日の予定", "所感"]:
        display_df[col] = display_df[col].apply(
            lambda x: (str(x)[:60] + "…") if len(str(x)) > 60 else str(x)
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID":     st.column_config.NumberColumn(width="small"),
            "日付":   st.column_config.TextColumn(width="small"),
            "名前":   st.column_config.TextColumn(width="small"),
            "勤務時間": st.column_config.TextColumn(width="small"),
            "実績時間(h)": st.column_config.NumberColumn(width="small"),
            "提出日時": st.column_config.TextColumn(width="medium"),
        },
    )

    st.divider()
    st.subheader("詳細表示")

    id_options = df["id"].tolist()
    selected_id = st.selectbox(
        "日報を選択",
        id_options,
        format_func=lambda i: (
            f"ID:{i}  {df.loc[df['id']==i, 'date'].values[0]}  "
            f"{df.loc[df['id']==i, 'name'].values[0]}"
        ),
    )

    if selected_id is None:
        return

    row = df[df["id"] == selected_id].iloc[0]
    work_time_str = (
        f"{row['start_time']}〜{row['end_time']}"
        if row["start_time"] and row["end_time"] else "-"
    )
    st.markdown(
        f'<div class="report-card">'
        f'<b>日付:</b> {row["date"]} ／ <b>名前:</b> {row["name"]} ／ '
        f'<b>勤務時間:</b> {work_time_str}（{row["work_hours"]}h）<br>'
        f'<small>提出日時: {row["created_at"]}</small>'
        f"</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ 今日やったこと**")
        st.text(row["tasks"])
        st.markdown("**💬 所感・連絡事項**")
        st.text(row["impressions"] if row["impressions"] else "（なし）")
    with col2:
        st.markdown("**📅 明日の予定**")
        st.text(row["tomorrow_plan"])

    with st.expander("⚠️ この日報を削除する"):
        st.warning("削除すると元に戻せません。")
        if st.button("削除する", type="secondary", key=f"del_{selected_id}"):
            db.delete_report(int(selected_id))
            st.success("削除しました。")
            st.rerun()


# ─── ページ: 管理者機能 ───────────────────────────────────────────────────────
def show_admin():
    st.title("👔 管理者機能")

    # 1. 本日の提出状況（一般ユーザーのみ対象）
    st.subheader("📊 本日の提出状況")
    st.caption("一般ユーザーのみを対象としています（管理者は含まれません）。")

    today_str = date.today().strftime("%Y-%m-%d")
    users_df = db.get_users()
    admin_users = set(users_df.loc[users_df["is_admin"] == 1, "username"])
    members = [m for m in db.get_members() if m not in admin_users]
    submitted_today = set(db.get_today_submitters(today_str))

    if not members:
        st.info("一般ユーザーのメンバーがいません。下の「メンバー管理」から追加してください。")
    else:
        n_cols = min(len(members), 5)
        cols = st.columns(n_cols)
        for i, member in enumerate(members):
            with cols[i % n_cols]:
                if member in submitted_today:
                    st.markdown(f'<p class="badge-ok">✅ {member}</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p class="badge-ng">❌ {member}</p>', unsafe_allow_html=True)

        not_submitted = [m for m in members if m not in submitted_today]
        if not_submitted:
            st.warning(f"本日未提出: **{'、'.join(not_submitted)}**")
        else:
            st.success("🎉 全員提出済みです！")

    st.divider()

    # 2. 提出統計
    st.subheader("📈 提出統計")

    c1, c2 = st.columns(2)
    with c1:
        stats_from = st.date_input("集計開始日", value=date.today() - timedelta(days=30), key="sf")
    with c2:
        stats_to = st.date_input("集計終了日", value=date.today(), key="st")

    stats_df = db.get_submission_stats(stats_from, stats_to)

    if stats_df.empty:
        st.info("指定期間内にデータがありません。")
    else:
        col1, col2 = st.columns(2)

        with col1:
            member_counts = (
                stats_df.groupby("name")
                .size()
                .reset_index(name="提出回数")
                .sort_values("提出回数", ascending=False)
            )
            fig_bar = px.bar(
                member_counts, x="name", y="提出回数",
                title="メンバー別提出回数",
                labels={"name": "メンバー"},
                color="提出回数", color_continuous_scale="Purples",
            )
            fig_bar.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            daily_counts = (
                stats_df.groupby("date")
                .size()
                .reset_index(name="提出件数")
            )
            fig_line = px.line(
                daily_counts, x="date", y="提出件数",
                title="日別提出件数の推移",
                labels={"date": "日付"},
                markers=True,
            )
            fig_line.update_traces(line_color="#6366f1", marker_color="#6366f1")
            st.plotly_chart(fig_line, use_container_width=True)

        # メンバー別提出率（登録メンバーがいる場合のみ）
        if members:
            business_days = len(pd.bdate_range(str(stats_from), str(stats_to)))
            rate_data = []
            for m in members:
                count = int((stats_df["name"] == m).sum())
                rate = round(count / business_days * 100, 1) if business_days > 0 else 0.0
                rate_data.append({"メンバー": m, "提出率(%)": rate, "提出回数": count})

            rate_df = pd.DataFrame(rate_data).sort_values("提出率(%)", ascending=False)

            st.markdown(f"**メンバー別提出率（営業日ベース: {business_days} 日）**")
            fig_rate = px.bar(
                rate_df, x="メンバー", y="提出率(%)",
                color="提出率(%)", color_continuous_scale="RdYlGn",
                range_color=[0, 100], text="提出率(%)",
                title="メンバー別提出率",
            )
            fig_rate.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_rate.update_layout(yaxis_range=[0, 115], coloraxis_showscale=False)
            st.plotly_chart(fig_rate, use_container_width=True)
            st.dataframe(rate_df, use_container_width=True, hide_index=True)

    st.divider()

    # 3. メンバー管理（アカウント作成）
    st.subheader("👥 メンバー管理")
    st.caption("メンバーを追加すると、ログイン用アカウントも同時に作成されます。")

    with st.form("add_member_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_member = st.text_input("メンバー名", placeholder="山田 太郎")
        with col2:
            new_member_pw = st.text_input("初期パスワード（8文字以上）", type="password")
        add_btn = st.form_submit_button("アカウントを作成して追加", type="primary", use_container_width=True)

    if add_btn:
        member_name = new_member.strip()
        if not member_name:
            st.error("名前を入力してください。")
        elif len(new_member_pw) < 8:
            st.error("パスワードは8文字以上で設定してください。")
        elif not db.create_user(member_name, new_member_pw, is_admin=False):
            st.error("そのユーザー名は既に登録されています。")
        else:
            db.add_member(member_name)
            st.success(f"✅ 「{member_name}」のアカウントを作成し、メンバーに追加しました。")

    current_members = db.get_members()
    if current_members:
        for m in current_members:
            c1, c2 = st.columns([5, 1])
            c1.write(m)
            if c2.button("削除", key=f"rm_{m}", type="secondary"):
                db.delete_member(m)
                st.rerun()
    else:
        st.info("メンバーが登録されていません。")

    st.divider()

    # 4. アカウント管理
    st.subheader("🔑 アカウント管理")

    users_df = db.get_users()
    current_user = st.session_state.get("username")

    for _, u in users_df.iterrows():
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.write(u["username"])
        c2.write("👑 管理者" if u["is_admin"] else "一般ユーザー")

        if u["username"] == current_user:
            c3.caption("（自分自身は変更できません）")
            continue

        if u["is_admin"]:
            if c3.button("管理者を解除", key=f"demote_{u['username']}"):
                db.set_admin(u["username"], False)
                st.rerun()
        else:
            if c3.button("管理者にする", key=f"promote_{u['username']}"):
                db.set_admin(u["username"], True)
                st.rerun()

        if c4.button("削除", key=f"deluser_{u['username']}", type="secondary"):
            db.delete_user(u["username"])
            st.rerun()


# ─── ページ: エクスポート・週報生成 ──────────────────────────────────────────
def show_export():
    st.title("📊 エクスポート・週報生成")

    current_user = st.session_state.get("username", "")
    is_admin = st.session_state.get("is_admin", False)
    members = db.get_members() if is_admin else [current_user]

    # 1. データエクスポート
    st.subheader("📁 データエクスポート")

    c1, c2 = st.columns(2)
    with c1:
        exp_from = st.date_input("開始日", value=date.today() - timedelta(days=30), key="ef")
        exp_to   = st.date_input("終了日", value=date.today(), key="et")
    with c2:
        if is_admin:
            exp_name = st.selectbox("メンバー絞り込み", ["すべて"] + members, key="en")
        else:
            exp_name = current_user
            st.text_input("対象", value=current_user, disabled=True, key="en")

    df = db.get_reports(
        date_from=exp_from,
        date_to=exp_to,
        name=None if exp_name == "すべて" else exp_name,
    )

    if df.empty:
        st.info("該当データがありません。")
    else:
        st.markdown(f"対象: **{len(df)} 件**")

        rename_map = {
            "id": "ID", "date": "日付", "name": "名前",
            "start_time": "開始時刻", "end_time": "終了時刻", "work_hours": "実績時間(h)",
            "tasks": "今日やったこと", "tomorrow_plan": "明日の予定",
            "impressions": "所感", "created_at": "提出日時",
        }
        export_df = df[list(rename_map)].rename(columns=rename_map)

        col1, col2 = st.columns(2)

        with col1:
            csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 CSV ダウンロード",
                data=csv_bytes,
                file_name=f"daily_reports_{exp_from}_{exp_to}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col2:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                export_df.to_excel(writer, sheet_name="日報一覧", index=False)
                ws = writer.sheets["日報一覧"]
                width_map = {
                    "ID": 6, "日付": 12, "名前": 14, "開始時刻": 10, "終了時刻": 10,
                    "実績時間(h)": 12, "今日やったこと": 45, "明日の予定": 45,
                    "所感": 35, "提出日時": 20,
                }
                for idx, col_name in enumerate(export_df.columns, 1):
                    ws.column_dimensions[get_column_letter(idx)].width = width_map.get(col_name, 15)
            st.download_button(
                label="📥 Excel ダウンロード",
                data=excel_buf.getvalue(),
                file_name=f"daily_reports_{exp_from}_{exp_to}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    st.divider()

    # 2. 週報自動生成
    st.subheader("📝 週報自動生成")

    c1, c2 = st.columns(2)
    with c1:
        if is_admin:
            users_df = db.get_users()
            admin_users = set(users_df.loc[users_df["is_admin"] == 1, "username"])
            weekly_members = [m for m in members if m not in admin_users]
            if weekly_members:
                weekly_name = st.selectbox("対象メンバー（一般ユーザーのみ）", weekly_members, key="wn")
            else:
                weekly_name = None
                st.info("一般ユーザーのメンバーがいません。")
        else:
            weekly_name = current_user
            st.text_input("対象メンバー", value=current_user, disabled=True, key="wn")
    with c2:
        today = date.today()
        last_monday = today - timedelta(days=today.weekday())
        week_start = st.date_input("週の開始日（月曜日）", value=last_monday, key="ws")

    week_end = week_start + timedelta(days=6)
    st.caption(f"対象期間: {week_start:%Y/%m/%d}（月）～ {week_end:%Y/%m/%d}（日）")

    if st.button("週報を生成する", type="primary"):
        if not (weekly_name or "").strip():
            st.error("メンバーを選択してください。")
            st.stop()

        weekly_df = db.get_weekly_reports(weekly_name, week_start, week_end)
        if weekly_df.empty:
            st.warning("該当期間の日報が見つかりません。")
            st.stop()

        lines = [
            "━" * 50,
            f"週　報",
            f"氏名: {weekly_name}",
            f"期間: {week_start:%Y年%m月%d日} ～ {week_end:%Y年%m月%d日}",
            "━" * 50,
            "",
        ]
        total_hours = 0.0
        for _, row in weekly_df.iterrows():
            d = date.fromisoformat(row["date"])
            wd = WEEKDAY_JP[d.weekday()]
            total_hours += row["work_hours"]
            work_time_str = (
                f"{row['start_time']}〜{row['end_time']}"
                if row["start_time"] and row["end_time"] else "-"
            )
            lines += [
                f"■ {d:%Y/%m/%d}（{wd}）　勤務時間: {work_time_str}（{row['work_hours']}h）",
                "",
                "【今日やったこと】",
                row["tasks"],
                "",
                "【明日の予定】",
                row["tomorrow_plan"],
            ]
            if row["impressions"]:
                lines += ["", "【所感・連絡事項】", row["impressions"]]
            lines += ["", "─" * 40, ""]

        lines.insert(6, f"合計実績時間: {round(total_hours, 2)}h")
        lines.insert(7, "")

        weekly_text = "\n".join(lines)
        st.text_area("週報プレビュー", weekly_text, height=400)
        st.download_button(
            label="📥 週報をテキストでダウンロード",
            data=weekly_text.encode("utf-8"),
            file_name=f"weekly_{weekly_name}_{week_start}.txt",
            mime="text/plain",
            use_container_width=True,
        )


# ─── ページ: 設定 ─────────────────────────────────────────────────────────────
def show_settings():
    st.title("⚙️ 設定")

    current_user = st.session_state.get("username", "")

    st.subheader("🔒 パスワード変更")
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("change_pw_form", clear_on_submit=True):
            current_pw = st.text_input("現在のパスワード", type="password")
            new_pw = st.text_input("新しいパスワード（8文字以上）", type="password")
            new_pw_confirm = st.text_input("新しいパスワード（確認）", type="password")
            submitted = st.form_submit_button("変更する", type="primary", use_container_width=True)

        if submitted:
            if db.verify_user(current_user, current_pw) is None:
                st.error("現在のパスワードが正しくありません。")
            elif len(new_pw) < 8:
                st.error("新しいパスワードは8文字以上で設定してください。")
            elif new_pw != new_pw_confirm:
                st.error("新しいパスワードが一致しません。")
            elif new_pw == current_pw:
                st.error("現在のパスワードと同じです。別のパスワードを設定してください。")
            else:
                db.update_password(current_user, new_pw)
                st.success("✅ パスワードを変更しました。次回から新しいパスワードでログインしてください。")


# ─── メイン ───────────────────────────────────────────────────────────────────
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False

    if not st.session_state.logged_in:
        show_auth()
        return

    with st.sidebar:
        st.title("📋 日報管理システム")
        today = date.today()
        st.markdown(f"**{today:%Y年%m月%d日}（{WEEKDAY_JP[today.weekday()]}）**")
        label = "👑 管理者" if st.session_state.is_admin else "一般ユーザー"
        st.caption(f"ログイン中: {st.session_state.username}（{label}）")
        st.divider()

        nav_options = ["📝 日報提出", "📋 一覧・検索"]
        if st.session_state.is_admin:
            nav_options.append("👔 管理者機能")
        nav_options.append("📊 エクスポート")
        nav_options.append("⚙️ 設定")

        page = st.radio(
            "ナビゲーション",
            nav_options,
            label_visibility="collapsed",
        )

        st.divider()

        # サイドバーに簡易ダッシュボード（一般ユーザーは自分の件数のみ）
        all_df = db.get_all_reports()
        if st.session_state.is_admin:
            scope_df = all_df
            st.caption("チーム全体の提出状況")
        else:
            scope_df = all_df[all_df["name"] == st.session_state.username] if not all_df.empty else all_df
            st.caption("あなたの提出状況")
        today_count = int((scope_df["date"] == today.strftime("%Y-%m-%d")).sum()) if not scope_df.empty else 0
        col1, col2 = st.columns(2)
        col1.metric("本日", f"{today_count} 件")
        col2.metric("累計", f"{len(scope_df)} 件")

        st.divider()
        if st.button("ログアウト", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_admin = False
            st.rerun()

        st.caption("Daily Report System v2.0")

    if page == "📝 日報提出":
        show_submit()
    elif page == "📋 一覧・検索":
        show_list()
    elif page == "👔 管理者機能" and st.session_state.is_admin:
        show_admin()
    elif page == "📊 エクスポート":
        show_export()
    elif page == "⚙️ 設定":
        show_settings()


if __name__ == "__main__":
    main()
