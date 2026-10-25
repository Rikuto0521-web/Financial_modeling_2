import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# 1. ページ設定・カスタムCSSデザイン
# ---------------------------------------------------------
st.set_page_config(
    page_title="Advanced Financial Modeling & Valuation Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# プロ仕様のモダンな見た目にするためのカスタムCSS
st.markdown(
    """
    <style>
    /* メインエリアの背景とフォント調整 */
    .main {
        background-color: #f4f6f9;
    }
    /* メトリックカードの装飾 */
    div.stMetric {
        background-color: #ffffff;
        padding: 16px;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        border: 1px solid #e1e8ed;
    }
    /* ヘッダーのスタイル */
    h1, h2, h3 {
        color: #1e293b;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    /* タブの見た目改善 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 6px 6px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid #e1e8ed;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2b5c8f !important;
        color: white !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📊 財務3表連動モデル & ROIC・DCFバリュエーション")
st.caption(
    "プロフェッショナル仕様の財務モデリング・企業価値分析システム（UIブラッシュアップ版）"
)

# ---------------------------------------------------------
# 2. サイドバー：シナリオ選択 & パラメータ設定
# ---------------------------------------------------------
st.sidebar.header("⚙️ モデリング パラメータ")

# シナリオプリセットの設定
scenario = st.sidebar.radio(
    "📌 シナリオ選択",
    ["Base (基本)", "Bull (強気)", "Bear (弱気)"],
    index=0,
)

if scenario == "Bull (強気)":
    def_rev, def_cogs, def_sga, def_capex, def_wacc = 12.0, 50.0, 22.0, 6.0, 6.5
elif scenario == "Bear (弱気)":
    def_rev, def_cogs, def_sga, def_capex, def_wacc = 3.0, 60.0, 28.0, 3.0, 8.5
else:
    def_rev, def_cogs, def_sga, def_capex, def_wacc = 7.0, 55.0, 25.0, 4.0, 7.5

# エクスパンダー（折りたたみ）でサイドバーをすっきり整理
with st.sidebar.expander("📈 1. 損益・成長ドライバ", expanded=True):
    rev_growth = (
        st.slider("売上高成長率 (%)", -5.0, 25.0, def_rev, 0.5, key="rev")
        / 100.0
    )
    cogs_pct = (
        st.slider("売上原価率 (%)", 30.0, 80.0, def_cogs, 0.5, key="cogs")
        / 100.0
    )
    sga_pct = (
        st.slider("販管費率 (%)", 10.0, 40.0, def_sga, 0.5, key="sga")
        / 100.0
    )
    tax_rate = (
        st.slider("実効税率 (%)", 20.0, 40.0, 30.0, 0.5, key="tax")
        / 100.0
    )

with st.sidebar.expander("🔄 2. 運転資本・設備投資ドライバ", expanded=False):
    capex_pct = (
        st.slider(
            "設備投資率 (対売上 %)", 1.0, 15.0, def_capex, 0.5, key="capex"
        )
        / 100.0
    )
    da_pct = (
        st.slider("減価償却費率 (対売上 %)", 1.0, 10.0, 3.5, 0.5, key="da")
        / 100.0
    )
    ar_days = slider_ar = st.slider(
        "売上債権回転日数 (日)", 10, 90, 45, 1, key="ar"
    )
    inv_days = st.slider("棚卸資産回転日数 (日)", 10, 120, 30, 1, key="inv")
    ap_days = st.slider("買入債務回転日数 (日)", 10, 90, 40, 1, key="ap")

with st.sidebar.expander("💰 3. 資本構成・DCF設定", expanded=False):
    wacc = (
        st.slider(
            "WACC (資本コスト) (%)", 4.0, 12.0, def_wacc, 0.25, key="wacc"
        )
        / 100.0
    )
    perp_growth = (
        st.slider("永続成長率 (%)", 0.0, 3.0, 1.0, 0.25, key="perp")
        / 100.0
    )
    interest_rate = (
        st.slider("借入金利息率 (%)", 0.5, 5.0, 2.0, 0.1, key="int")
        / 100.0
    )

with st.sidebar.expander("🏢 4. 基準年度 初期値 (Yr 0)", expanded=False):
    base_rev = st.number_input("基準売上高 (百万円)", value=10000, step=500)
    base_cash = st.number_input("初期現金預金 (百万円)", value=2000, step=100)
    base_ppe = st.number_input(
        "初期有形固定資産 (百万円)", value=5000, step=500
    )
    base_debt = st.number_input("初期有利子負債 (百万円)", value=3000, step=500)
    base_equity = st.number_input(
        "初期株主資本 (百万円)", value=5000, step=500
    )
    shares_outstanding = st.number_input(
        "発行済株式数 (万株)", value=1000, step=100
    )

# ---------------------------------------------------------
# 3. 計算エンジン (財務3表完全連動)
# ---------------------------------------------------------
years = ["Yr 0", "Yr 1", "Yr 2", "Yr 3", "Yr 4", "Yr 5"]
num_years = 5

is_data = {
    "売上高": [base_rev],
    "売上原価": [base_rev * def_cogs / 100],
    "売上総利益": [0],
    "販管費": [base_rev * def_sga / 100],
    "営業利益 (EBIT)": [0],
    "支払利息": [0],
    "税引前利益 (EBT)": [0],
    "法人税等": [0],
    "当期純利益": [0],
}

bs_data = {
    "現金預金": [base_cash],
    "売上債権": [(base_rev * ar_days) / 365],
    "棚卸資産": [(base_rev * (def_cogs / 100) * inv_days) / 365],
    "有形固定資産 (純額)": [base_ppe],
    "資産合計": [0],
    "買入債務": [(base_rev * (def_cogs / 100) * ap_days) / 365],
    "有利子負債": [base_debt],
    "負債合計": [0],
    "株主資本 (利益余剰金含む)": [base_equity],
    "負債・純資産合計": [0],
    "BSバランスチェック (差額)": [0],
}

cf_data = {
    "営業CF": [0],
    "投資CF (CapEx)": [0],
    "財務CF": [0],
    "フリーキャッシュフロー (FCF)": [0],
    "期末現金増減": [0],
}

is_data["売上総利益"][0] = is_data["売上高"][0] - is_data["売上原価"][0]
is_data["営業利益 (EBIT)"][0] = (
    is_data["売上総利益"][0] - is_data["販管費"][0]
)
is_data["支払利息"][0] = bs_data["有利子負債"][0] * interest_rate
is_data["税引前利益 (EBT)"][0] = (
    is_data["営業利益 (EBIT)"][0] - is_data["支払利息"][0]
)
is_data["法人税等"][0] = max(0, is_data["税引前利益 (EBT)"][0] * tax_rate)
is_data["当期純利益"][0] = (
    is_data["税引前利益 (EBT)"][0] - is_data["法人税等"][0]
)

bs_data["資産合計"][0] = (
    bs_data["現金預金"][0]
    + bs_data["売上債権"][0]
    + bs_data["棚卸資産"][0]
    + bs_data["有形固定資産 (純額)"][0]
)
bs_data["負債合計"][0] = bs_data["買入債務"][0] + bs_data["有利子負債"][0]
bs_data["負債・純資産合計"][0] = (
    bs_data["負債合計"][0] + bs_data["株主資本 (利益余剰金含む)"][0]
)

for t in range(1, num_years + 1):
    rev = is_data["売上高"][t - 1] * (1 + rev_growth)
    cogs = rev * cogs_pct
    gp = rev - cogs
    sga = rev * sga_pct
    ebit = gp - sga
    interest = bs_data["有利子負債"][t - 1] * interest_rate
    ebt = ebit - interest
    tax = max(0, ebt * tax_rate)
    net_income = ebt - tax

    is_data["売上高"].append(rev)
    is_data["売上原価"].append(cogs)
    is_data["売上総利益"].append(gp)
    is_data["販管費"].append(sga)
    is_data["営業利益 (EBIT)"].append(ebit)
    is_data["支払利息"].append(interest)
    is_data["税引前利益 (EBT)"].append(ebt)
    is_data["法人税等"].append(tax)
    is_data["当期純利益"].append(net_income)

    ar = (rev * ar_days) / 365
    inv = (cogs * inv_days) / 365
    ap = (cogs * ap_days) / 365

    capex = rev * capex_pct
    da = rev * da_pct
    ppe = bs_data["有形固定資産 (純額)"][t - 1] + capex - da

    nopat = ebit * (1 - tax_rate)
    delta_nwc = (
        (ar - bs_data["売上債権"][t - 1])
        + (inv - bs_data["棚卸資産"][t - 1])
        - (ap - bs_data["買入債務"][t - 1])
    )
    cf_op = net_income + da - delta_nwc
    cf_inv = -capex
    fcf = nopat + da - capex - delta_nwc

    debt = bs_data["有利子負債"][t - 1]
    cf_fin = 0

    net_change_cash = cf_op + cf_inv + cf_fin
    cash = bs_data["現金預金"][t - 1] + net_change_cash
    equity = bs_data["株主資本 (利益余剰金含む)"][t - 1] + net_income

    total_assets = cash + ar + inv + ppe
    total_liab = ap + debt
    total_liab_eq = total_liab + equity
    bs_diff = total_assets - total_liab_eq

    bs_data["現金預金"].append(cash)
    bs_data["売上債権"].append(ar)
    bs_data["棚卸資産"].append(inv)
    bs_data["有形固定資産 (純額)"].append(ppe)
    bs_data["資産合計"].append(total_assets)
    bs_data["買入債務"].append(ap)
    bs_data["有利子負債"].append(debt)
    bs_data["負債合計"].append(total_liab)
    bs_data["株主資本 (利益余剰金含む)"].append(equity)
    bs_data["負債・純資産合計"].append(total_liab_eq)
    bs_data["BSバランスチェック (差額)"].append(bs_diff)

    cf_data["営業CF"].append(cf_op)
    cf_data["投資CF (CapEx)"].append(cf_inv)
    cf_data["財務CF"].append(cf_fin)
    cf_data["フリーキャッシュフロー (FCF)"].append(fcf)
    cf_data["期末現金増減"].append(net_change_cash)

df_is = pd.DataFrame(is_data, index=years)
df_bs = pd.DataFrame(bs_data, index=years)
df_cf = pd.DataFrame(cf_data, index=years)

# ---------------------------------------------------------
# 4. ROIC・財務比率 & DCF計算
# ---------------------------------------------------------
ratios = []
for t in range(len(years)):
    ebit = df_is["営業利益 (EBIT)"].iloc[t]
    nopat = ebit * (1 - tax_rate)
    op_assets = (
        df_bs["売上債権"].iloc[t]
        + df_bs["棚卸資産"].iloc[t]
        + df_bs["有形固定資産 (純額)"].iloc[t]
    )
    op_liab = df_bs["買入債務"].iloc[t]
    invested_capital = op_assets - op_liab

    roic = (nopat / invested_capital * 100) if invested_capital != 0 else 0
    wacc_pct = wacc * 100
    roic_spread = roic - wacc_pct
    roe = (
        (
            df_is["当期純利益"].iloc[t]
            / df_bs["株主資本 (利益余剰金含む)"].iloc[t]
        )
        * 100
        if df_bs["株主資本 (利益余剰金含む)"].iloc[t] != 0
        else 0
    )
    roa = (
        (df_is["当期純利益"].iloc[t] / df_bs["資産合計"].iloc[t]) * 100
        if df_bs["資産合計"].iloc[t] != 0
        else 0
    )
    ebit_margin = (
        (ebit / df_is["売上高"].iloc[t]) * 100
        if df_is["売上高"].iloc[t] != 0
        else 0
    )
    current_ratio = (
        (
            (
                df_bs["現金預金"].iloc[t]
                + df_bs["売上債権"].iloc[t]
                + df_bs["棚卸資産"].iloc[t]
            )
            / df_bs["買入債務"].iloc[t]
        )
        * 100
        if df_bs["買入債務"].iloc[t] != 0
        else 0
    )

    ratios.append(
        {
            "投下資本 (百万円)": invested_capital,
            "NOPAT (百万円)": nopat,
            "ROIC (%)": roic,
            "WACC (%)": wacc_pct,
            "ROICスプレッド (%)": roic_spread,
            "ROE (%)": roe,
            "ROA (%)": roa,
            "営業利益率 (%)": ebit_margin,
            "流動比率 (%)": current_ratio,
        }
    )

df_ratios = pd.DataFrame(ratios, index=years)

fcf_proj = df_cf["フリーキャッシュフロー (FCF)"].iloc[1:].tolist()
discount_factors = [(1 + wacc) ** i for i in range(1, num_years + 1)]
pv_fcf = [fcf / df for fcf, df in zip(fcf_proj, discount_factors)]
sum_pv_fcf = sum(pv_fcf)

terminal_value = (fcf_proj[-1] * (1 + perp_growth)) / (wacc - perp_growth)
pv_tv = terminal_value / ((1 + wacc) ** num_years)

enterprise_value = sum_pv_fcf + pv_tv
net_debt = df_bs["有利子負債"].iloc[0] - df_bs["現金預金"].iloc[0]
equity_value = enterprise_value - net_debt
implied_share_price = (
    (equity_value * 100) / shares_outstanding if shares_outstanding > 0 else 0
)

# ---------------------------------------------------------
# 5. タブ構成
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📑 財務3表モデル",
        "🎯 ROIC & レーシオ分析",
        "💰 DCFバリュエーション",
        "🎛️ シナリオ・感度分析",
        "📥 Excel/CSV 出力",
    ]
)

with tab1:
    st.subheader(f"📊 財務3表連動モデル (シナリオ: {scenario})")
    st.markdown("#### 損益計算書 (P&L)")
    st.dataframe(df_is.T.style.format("{:,.1f}"), use_container_width=True)

    st.markdown("#### 貸借対照表 (B/S)")
    st.dataframe(
        df_bs.T.style.format("{:,.1f}").highlight_between(
            left=-0.01,
            right=0.01,
            props="background-color: #e6ffe6;",
        ),
        use_container_width=True,
    )

    st.markdown("#### キャッシュフロー計算書 (C/F)")
    st.dataframe(df_cf.T.style.format("{:,.1f}"), use_container_width=True)

with tab2:
    st.subheader("🎯 ROICスプレッド & 財務比率 (レーシオ) 分析")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Yr 5 予想 ROIC", f"{df_ratios['ROIC (%)'].iloc[-1]:.2f}%"
    )
    c2.metric("WACC (資本コスト)", f"{wacc*100:.2f}%")
    c3.metric(
        "ROICスプレッド",
        f"{df_ratios['ROICスプレッド (%)'].iloc[-1]:.2f}%",
    )
    c4.metric(
        "Yr 5 予想 ROE", f"{df_ratios['ROE (%)'].iloc[-1]:.2f}%"
    )

    st.markdown("---")
    fig_roic = go.Figure()
    fig_roic.add_trace(
        go.Bar(
            x=years,
            y=df_ratios["ROIC (%)"],
            name="ROIC (%)",
            marker_color="#2b5c8f",
        )
    )
    fig_roic.add_trace(
        go.Scatter(
            x=years,
            y=df_ratios["WACC (%)"],
            name="WACC (%)",
            line=dict(color="#d9534f", width=3, dash="dash"),
        )
    )
    fig_roic.update_layout(
        title="ROICとWACCの比較推移", yaxis_title="%", height=400
    )
    st.plotly_chart(fig_roic, use_container_width=True)

    st.markdown("#### 財務比率一覧表")
    st.dataframe(df_ratios.T.style.format("{:,.2f}"), use_container_width=True)

with tab3:
    st.subheader("💰 DCF企業価値評価 サマリー")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("事業価値 (PV of FCF)", f"{sum_pv_fcf:,.0f} 百万円")
    m2.metric("ターミナルバリュー", f"{pv_tv:,.0f} 百万円")
    m3.metric("企業価値 (EV)", f"{enterprise_value:,.0f} 百万円")
    m4.metric(
        "理論株価",
        f"{implied_share_price:,.0f} 円",
        delta=f"株主資本: {equity_value:,.0f}百万円",
    )

    st.markdown("---")
    st.markdown("#### DCF 割引計算詳細")
    df_dcf = pd.DataFrame(
        {
            "FCF (百万円)": fcf_proj,
            "割引係数": [1 / df for df in discount_factors],
            "割引現在価値 PV (百万円)": pv_fcf,
        },
        index=years[1:],
    )
    st.dataframe(df_dcf.style.format("{:,.2f}"), use_container_width=True)

with tab4:
    st.subheader("🎛️ 感度分析 (WACC × 永続成長率)")

    wacc_list = [
        wacc - 0.01,
        wacc - 0.005,
        wacc,
        wacc + 0.005,
        wacc + 0.01,
    ]
    perp_list = [
        perp_growth - 0.005,
        perp_growth,
        perp_growth + 0.005,
        perp_growth + 0.01,
    ]

    sens_matrix = []
    for p in perp_list:
        row = []
        for w in wacc_list:
            if w <= p:
                row.append(np.nan)
                continue
            pv_f = sum([f / ((1 + w) ** (i + 1)) for i, f in enumerate(fcf_proj)])
            tv = (fcf_proj[-1] * (1 + p)) / (w - p)
            pv_t = tv / ((1 + w) ** num_years)
            ev = pv_f + pv_t
            eq = ev - net_debt
            price = (eq * 100) / shares_outstanding if shares_outstanding > 0 else 0
            row.append(round(price, 0))
        sens_matrix.append(row)

    df_sens = pd.DataFrame(
        sens_matrix,
        index=[f"永続成長率 {p*100:.1f}%" for p in perp_list],
        columns=[f"WACC {w*100:.2f}%" for w in wacc_list],
    )

    fig_sens = px.imshow(
        df_sens,
        text_auto=True,
        color_continuous_scale="Blues",
        title="理論株価の感度分析マトリクス (円)",
    )
    st.plotly_chart(fig_sens, use_container_width=True)

with tab5:
    st.subheader("📥 モデルデータ・レポートのエクスポート")
    st.markdown("計算結果をCSVまたは統合Excel形式でダウンロードできます。")

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.markdown("#### 📄 CSVダウンロード")
        csv_is = df_is.to_csv(index=True).encode("utf-8-sig")
        st.download_button(
            "損益計算書 (CSV)",
            csv_is,
            file_name=f"IS_{scenario}.csv",
            mime="text/csv",
        )
        csv_ratios = df_ratios.to_csv(index=True).encode("utf-8-sig")
        st.download_button(
            "ROIC・財務比率 (CSV)",
            csv_ratios,
            file_name=f"ratios_{scenario}.csv",
            mime="text/csv",
        )

    with col_exp2:
        st.markdown("#### 📘 統合Excelファイル")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_is.to_excel(writer, sheet_name="損益計算書(IS)")
            df_bs.to_excel(writer, sheet_name="貸借対照表(BS)")
            df_cf.to_excel(writer, sheet_name="キャッシュフロー(CF)")
            df_ratios.to_excel(writer, sheet_name="ROIC・財務比率")
            df_sens.to_excel(writer, sheet_name="DCF感度分析")

        st.download_button(
            "📊 完全版モデル (Excel) をダウンロード",
            data=buffer.getvalue(),
            file_name=f"Full_Financial_Model_{scenario}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )