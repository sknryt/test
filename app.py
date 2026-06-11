import io
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import database as db

st.set_page_config(
    page_title="日報管理システム",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

st.markdown("""
<style>
.report-card {
    background: #f0f4f8;
    border-left: 4px solid #1f77b4;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0 1rem 0;
    border-radius: 0 6px 6px 0;
}
.badge-ok  { color: #28a745; font-weight: bold; font-size: 1.05rem; }
.badge-ng  { color: #dc3545; font-weight: bold; font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)


# ─── ページ: ログイン ─────────────────────────────────────────────────────────
def show_login():
    st.subheader("🔐 ログイン")

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
            st.success("登録が完了しました。ログイン画面からログインしてください。")
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
    st.title("📋 日報管理システム")

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

    members = db.get_members()
    current_user = st.session_state.get("username", "")

    with st.form("report_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            report_date = st.date_input("日付", value=date.today())
        with col2:
            if members:
                input_mode = st.radio("名前", ["一覧から選択", "直接入力"], horizontal=True)
                if input_mode == "一覧から選択":
                    default_index = members.index(current_user) if current_user in members else 0
                    name = st.selectbox("メンバー", members, index=default_index, label_visibility="collapsed")
                else:
                    name = st.text_input("名前を入力", value=current_user, placeholder="山田 太郎", label_visibility="collapsed")
            else:
                name = st.text_input("名前", value=current_user, placeholder="山田 太郎")

        tasks = st.text_area(
            "✅ 今日やったこと",
            height=130,
            placeholder="・会議の議事録作成\n・〇〇機能の実装\n・△△の調査・確認",
        )
        tomorrow_plan = st.text_area(
            "📅 明日の予定",
            height=100,
            placeholder="・〇〇のレビュー依頼\n・△△のテスト実施",
        )
        impressions = st.text_area(
            "💬 所感・連絡事項（任意）",
            height=80,
            placeholder="気になったこと、困っていること、共有事項など",
        )

        submitted = st.form_submit_button("提出する", type="primary", use_container_width=True)

    if not submitted:
        return

    name = (name or "").strip()
    if not name:
        st.error("名前を入力してください。")
        return
    if not tasks.strip():
        st.error("「今日やったこと」を入力してください。")
        return
    if not tomorrow_plan.strip():
        st.error("「明日の予定」を入力してください。")
        return

    date_str = report_date.strftime("%Y-%m-%d")
    if db.has_submitted(name, date_str):
        st.warning(f"⚠️ {name} さんは {report_date:%Y/%m/%d} の日報を既に提出しています。追加提出として保存します。")

    db.save_report(date_str, name, tasks, tomorrow_plan, impressions)
    st.success(f"✅ {name} さんの日報（{report_date:%Y/%m/%d}）を提出しました！")
    st.balloons()


# ─── ページ: 一覧・検索 ───────────────────────────────────────────────────────
def show_list():
    st.title("📋 一覧・検索")

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
    display_df = df[["id", "date", "name", "tasks", "tomorrow_plan", "impressions", "created_at"]].copy()
    display_df.columns = ["ID", "日付", "名前", "今日やったこと", "明日の予定", "所感", "提出日時"]
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
    st.markdown(
        f'<div class="report-card">'
        f'<b>日付:</b> {row["date"]} ／ <b>名前:</b> {row["name"]}<br>'
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

    # 1. 本日の提出状況
    st.subheader("📊 本日の提出状況")

    today_str = date.today().strftime("%Y-%m-%d")
    members = db.get_members()
    submitted_today = set(db.get_today_submitters(today_str))

    if not members:
        st.info("メンバーが未登録です。下の「メンバー管理」から追加してください。")
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
                color="提出回数", color_continuous_scale="Blues",
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
            fig_line.update_traces(line_color="#1f77b4", marker_color="#1f77b4")
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

    # 3. メンバー管理
    st.subheader("👥 メンバー管理")

    with st.form("add_member_form"):
        col1, col2 = st.columns([4, 1])
        with col1:
            new_member = st.text_input("新しいメンバー名", placeholder="山田 太郎", label_visibility="collapsed")
        with col2:
            add_btn = st.form_submit_button("追加", type="primary", use_container_width=True)

    if add_btn:
        if new_member.strip():
            db.add_member(new_member.strip())
            st.success(f"「{new_member.strip()}」を追加しました。")
            st.rerun()
        else:
            st.error("名前を入力してください。")

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

    members = db.get_members()

    # 1. データエクスポート
    st.subheader("📁 データエクスポート")

    c1, c2 = st.columns(2)
    with c1:
        exp_from = st.date_input("開始日", value=date.today() - timedelta(days=30), key="ef")
        exp_to   = st.date_input("終了日", value=date.today(), key="et")
    with c2:
        exp_name = st.selectbox("メンバー絞り込み", ["すべて"] + members, key="en")

    df = db.get_reports(
        date_from=exp_from,
        date_to=exp_to,
        name=None if exp_name == "すべて" else exp_name,
    )

    if df.empty:
        st.info("該当データがありません。")
    else:
        st.markdown(f"対象: **{len(df)} 件**")
        col1, col2 = st.columns(2)

        with col1:
            csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="📥 CSV ダウンロード",
                data=csv_bytes,
                file_name=f"daily_reports_{exp_from}_{exp_to}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col2:
            excel_buf = io.BytesIO()
            rename_map = {
                "id": "ID", "date": "日付", "name": "名前",
                "tasks": "今日やったこと", "tomorrow_plan": "明日の予定",
                "impressions": "所感", "created_at": "提出日時",
            }
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df.rename(columns=rename_map).to_excel(
                    writer, sheet_name="日報一覧", index=False
                )
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
        if members:
            weekly_name = st.selectbox("対象メンバー", members, key="wn")
        else:
            weekly_name = st.text_input("対象メンバー名", placeholder="山田 太郎", key="wn")
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

        weekday_jp = ["月", "火", "水", "木", "金", "土", "日"]
        lines = [
            "━" * 50,
            f"週　報",
            f"氏名: {weekly_name}",
            f"期間: {week_start:%Y年%m月%d日} ～ {week_end:%Y年%m月%d日}",
            "━" * 50,
            "",
        ]
        for _, row in weekly_df.iterrows():
            d = date.fromisoformat(row["date"])
            wd = weekday_jp[d.weekday()]
            lines += [
                f"■ {d:%Y/%m/%d}（{wd}）",
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

        weekly_text = "\n".join(lines)
        st.text_area("週報プレビュー", weekly_text, height=400)
        st.download_button(
            label="📥 週報をテキストでダウンロード",
            data=weekly_text.encode("utf-8"),
            file_name=f"weekly_{weekly_name}_{week_start}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()

    # 3. 未提出者リマインド
    st.subheader("🔔 未提出者リマインドメッセージ")

    today_str = date.today().strftime("%Y-%m-%d")
    submitted_today = set(db.get_today_submitters(today_str))
    not_submitted = [m for m in members if m not in submitted_today]

    if not members:
        st.info("メンバーが登録されていません。")
    elif not not_submitted:
        st.success(f"✅ 本日（{date.today():%Y/%m/%d}）は全員提出済みです！")
    else:
        st.warning(f"本日未提出: **{'、'.join(not_submitted)}**")
        reminder = (
            f"【日報リマインド】\n\n"
            f"お疲れ様です。\n"
            f"本日（{date.today():%Y/%m/%d}）の日報がまだ提出されていない方がいます。\n\n"
            f"未提出: {', '.join(not_submitted)}\n\n"
            f"お手すきの際に提出をお願いします。\n"
            f"提出URL: （URLをここに記入）"
        )
        st.text_area("リマインドメッセージ（Slack/メール用）", reminder, height=180)
        st.caption("上記をコピーして Slack・メールなどで送付してください。")


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
        st.markdown(f"**{date.today():%Y年%m月%d日（%A）}**")
        label = "👑 管理者" if st.session_state.is_admin else "一般ユーザー"
        st.caption(f"ログイン中: {st.session_state.username}（{label}）")
        st.divider()

        nav_options = ["📝 日報提出", "📋 一覧・検索"]
        if st.session_state.is_admin:
            nav_options.append("👔 管理者機能")
        nav_options.append("📊 エクスポート")

        page = st.radio(
            "ナビゲーション",
            nav_options,
            label_visibility="collapsed",
        )

        st.divider()

        # サイドバーに簡易ダッシュボード
        all_df = db.get_all_reports()
        today_count = int((all_df["date"] == date.today().strftime("%Y-%m-%d")).sum()) if not all_df.empty else 0
        col1, col2 = st.columns(2)
        col1.metric("本日", f"{today_count} 件")
        col2.metric("累計", f"{len(all_df)} 件")

        st.divider()
        if st.button("ログアウト", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_admin = False
            st.rerun()

        st.caption("Daily Report System v1.0")

    if page == "📝 日報提出":
        show_submit()
    elif page == "📋 一覧・検索":
        show_list()
    elif page == "👔 管理者機能" and st.session_state.is_admin:
        show_admin()
    elif page == "📊 エクスポート":
        show_export()


if __name__ == "__main__":
    main()
