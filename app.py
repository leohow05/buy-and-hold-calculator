import math
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="Buy and Hold Calculator",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Buy and Hold Calculator")

st.write(
    "See how much your investment would be worth if you bought a stock "
    "on the first trading day of 2020 and held it until today."
)


@st.cache_data(ttl=3600)
def search_company(query):
    query = query.strip()

    if not query:
        return []

    try:
        result = yf.Search(
            query=query,
            max_results=10,
            news_count=0,
        )

        matches = []

        for quote in result.quotes:
            ticker = quote.get("symbol")

            company_name = (
                quote.get("shortname")
                or quote.get("longname")
                or ticker
            )

            exchange = (
                quote.get("exchDisp")
                or quote.get("exchange")
                or "Unknown"
            )

            if ticker:
                matches.append(
                    {
                        "ticker": ticker,
                        "company_name": company_name,
                        "exchange": exchange,
                    }
                )

        return matches

    except Exception:
        return [
            {
                "ticker": query.upper(),
                "company_name": query.upper(),
                "exchange": "Unknown",
            }
        ]


@st.cache_data(ttl=3600)
def download_stock_data(ticker):
    end_date = date.today() + timedelta(days=1)

    data = yf.download(
        ticker,
        start="2020-01-01",
        end=end_date.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.copy()
    data.index = pd.to_datetime(data.index)
    data = data.dropna(subset=["Close"])

    return data


st.sidebar.header("Investment Settings")

company_query = st.sidebar.text_input(
    "Search company or ticker",
    value="Apple",
    placeholder="Example: Apple, AAPL, Tesla, TSLA",
)

investment_amount = st.sidebar.number_input(
    "Initial investment amount",
    min_value=1.0,
    value=10000.0,
    step=1000.0,
)

allow_fractional_shares = st.sidebar.checkbox(
    "Allow fractional shares",
    value=True,
)


matches = search_company(company_query)

if not matches:
    st.warning("No company found.")
    st.stop()


company_options = {}

for match in matches:
    label = (
        f"{match['company_name']} "
        f"({match['ticker']}) — {match['exchange']}"
    )

    company_options[label] = match


selected_label = st.sidebar.selectbox(
    "Select company",
    options=list(company_options.keys()),
)

selected_company = company_options[selected_label]

ticker = selected_company["ticker"]
company_name = selected_company["company_name"]


try:
    stock_data = download_stock_data(ticker)

except Exception as error:
    st.error(f"Unable to download stock data: {error}")
    st.stop()


if stock_data.empty:
    st.error(
        f"No stock data was found for {ticker}. "
        "Please try another ticker."
    )
    st.stop()


first_trading_date = stock_data.index[0]
latest_trading_date = stock_data.index[-1]

purchase_price = float(stock_data["Close"].iloc[0])
latest_price = float(stock_data["Close"].iloc[-1])


if allow_fractional_shares:
    shares_purchased = investment_amount / purchase_price
    remaining_cash = 0

else:
    shares_purchased = math.floor(
        investment_amount / purchase_price
    )

    remaining_cash = (
        investment_amount
        - shares_purchased * purchase_price
    )


if shares_purchased <= 0:
    st.error(
        "Your investment amount is too low to buy one share."
    )
    st.stop()


stock_data["Portfolio Value"] = (
    stock_data["Close"] * shares_purchased
    + remaining_cash
)

stock_data["Return Percentage"] = (
    stock_data["Portfolio Value"]
    / investment_amount
    - 1
) * 100


current_value = float(
    stock_data["Portfolio Value"].iloc[-1]
)

total_profit = current_value - investment_amount

total_return_percent = (
    total_profit / investment_amount
) * 100


st.subheader(f"{company_name} ({ticker})")

st.caption(
    f"Investment period: "
    f"{first_trading_date.strftime('%B %d, %Y')} to "
    f"{latest_trading_date.strftime('%B %d, %Y')}"
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Initial Investment",
    f"${investment_amount:,.2f}",
)

col2.metric(
    "Purchase Price",
    f"${purchase_price:,.2f}",
)

col3.metric(
    "Current Value",
    f"${current_value:,.2f}",
)

col4.metric(
    "Total Return",
    f"{total_return_percent:,.2f}%",
    delta=f"${total_profit:,.2f}",
)


st.subheader("Investment Value Over Time")

value_chart = go.Figure()

value_chart.add_trace(
    go.Scatter(
        x=stock_data.index,
        y=stock_data["Portfolio Value"],
        mode="lines",
        name="Portfolio Value",
    )
)

value_chart.add_hline(
    y=investment_amount,
    line_dash="dash",
    annotation_text="Initial Investment",
)

value_chart.update_layout(
    xaxis_title="Date",
    yaxis_title="Portfolio Value",
    hovermode="x unified",
)

value_chart.update_yaxes(
    tickprefix="$",
)

st.plotly_chart(
    value_chart,
    use_container_width=True,
)


st.subheader("Cumulative Return Over Time")

return_chart = go.Figure()

return_chart.add_trace(
    go.Scatter(
        x=stock_data.index,
        y=stock_data["Return Percentage"],
        mode="lines",
        name="Return Percentage",
    )
)

return_chart.add_hline(
    y=0,
    line_dash="dash",
    annotation_text="Break-even",
)

return_chart.update_layout(
    xaxis_title="Date",
    yaxis_title="Return Percentage",
    hovermode="x unified",
)

return_chart.update_yaxes(
    ticksuffix="%",
)

st.plotly_chart(
    return_chart,
    use_container_width=True,
)


with st.expander("View Historical Data"):
    st.dataframe(
        stock_data[
            [
                "Close",
                "Portfolio Value",
                "Return Percentage",
            ]
        ].sort_index(ascending=False),
        use_container_width=True,
    )


csv_data = stock_data[
    [
        "Close",
        "Portfolio Value",
        "Return Percentage",
    ]
].to_csv().encode("utf-8")

st.download_button(
    "Download Results as CSV",
    data=csv_data,
    file_name=f"{ticker}_investment_results.csv",
    mime="text/csv",
)


st.caption(
    "This calculator does not include taxes, fees, "
    "currency conversion costs, or brokerage charges."
)
