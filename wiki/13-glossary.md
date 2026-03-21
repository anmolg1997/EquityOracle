# Glossary

Terms used in EquityOracle, explained for developers who know programming but may not know finance.

## Finance Terms

### Stock Market Basics

**Equity / Stock / Share** — A unit of ownership in a company. When you "buy RELIANCE," you're buying a small piece of Reliance Industries.

**NSE / BSE** — National Stock Exchange and Bombay Stock Exchange. The two main stock exchanges in India. Most liquid stocks trade on NSE.

**NYSE / NASDAQ** — The two main US exchanges. NYSE is the traditional floor exchange; NASDAQ is electronic-first.

**OHLCV** — Open, High, Low, Close, Volume. The five numbers that describe a stock's trading day. Open = first trade price, Close = last trade price, High/Low = extremes, Volume = number of shares traded.

**Market Cap** — Total value of all shares: `share_price × total_shares`. Used to classify companies as large-cap (>₹20,000 Cr), mid-cap, small-cap, or micro-cap.

**Liquidity** — How easily you can buy/sell a stock without moving its price. Reliance is highly liquid (millions of shares trade daily). A micro-cap with 1,000 daily volume is illiquid.

### Price Analysis

**Moving Average (SMA/EMA)** — Average closing price over the last N days. SMA = Simple (equal weight), EMA = Exponential (recent days weighted more). The 200-day SMA is widely watched — stocks above it are considered in an uptrend.

**RSI (Relative Strength Index)** — Momentum oscillator (0–100). Below 30 = oversold (potential bounce), above 70 = overbought (potential pullback). Around 50 = neutral.

**MACD** — Moving Average Convergence Divergence. Shows the relationship between two EMAs. When the MACD line crosses above the signal line, it's bullish. The histogram shows the gap between them.

**ADX (Average Directional Index)** — Measures trend strength (not direction). Below 20 = weak/no trend. Above 25 = strong trend. Above 40 = very strong trend.

**Bollinger Bands** — A channel around the price based on standard deviations. When price touches the lower band, the stock may be oversold. When it touches the upper band, it may be overbought.

**ATR (Average True Range)** — How much a stock typically moves in a day, in price terms. A stock with ATR of ₹50 moves about ₹50/day on average. Used for setting stop-losses.

**OBV (On-Balance Volume)** — Cumulative volume indicator. Rising OBV confirms a price uptrend (buyers are showing up). Falling OBV during a price rise = bearish divergence.

**Relative Strength (RS)** — A stock's return relative to the market or its peers. RS 90 means the stock has outperformed 90% of all stocks over the measurement period.

### Fundamental Analysis

**P/E Ratio (Price-to-Earnings)** — How much you pay per rupee of earnings. P/E of 20 means you pay ₹20 for every ₹1 of annual profit. Lower = cheaper (potentially undervalued), higher = expensive (but might be growing fast).

**P/B Ratio (Price-to-Book)** — Stock price divided by book value per share. Below 1.0 means you're paying less than the company's accounting value — potentially a bargain.

**EV/EBITDA** — Enterprise Value divided by Earnings Before Interest, Tax, Depreciation, and Amortization. A valuation metric that accounts for debt. Lower = cheaper.

**ROE (Return on Equity)** — Net profit divided by shareholder equity. Measures how efficiently a company uses its investors' money. Above 15% is generally good, above 20% is excellent.

**Debt-to-Equity** — Total debt divided by shareholder equity. Higher = more leveraged = more risky. Below 1.0 is conservative.

### Trading Terms

**Slippage** — The difference between the price you expected and the price you actually got. Caused by your order moving the market. Worse for large orders in illiquid stocks.

**STT (Securities Transaction Tax)** — A tax levied by the Indian government on stock exchange transactions. Currently 0.1% on delivery trades.

**STCG / LTCG** — Short-Term Capital Gains (holding < 12 months, taxed at 20%) and Long-Term Capital Gains (holding ≥ 12 months, taxed at 12.5% above ₹1.25L exemption).

**Stop-Loss** — A predetermined price at which you sell to limit losses. A trailing stop moves up as the price rises but never moves down.

**Paper Trading** — Simulated trading with fake money. Used to test strategies without financial risk.

### Institutional Terms

**FII (Foreign Institutional Investors)** — Foreign funds investing in Indian markets. Net FII buying is generally bullish for Indian markets.

**DII (Domestic Institutional Investors)** — Indian mutual funds, insurance companies, etc. Often buy when FIIs sell, providing stability.

**Insider Deals** — Trades by company directors or promoters. Promoter buying (spending their own money on their company's stock) is often a bullish signal.

**Bulk Deal / Block Deal** — Large trades (≥0.5% of outstanding shares) that are publicly disclosed. Can indicate institutional interest.

## Technical Terms

### Architecture

**Hexagonal Architecture** — A pattern where business logic (domain) is at the center, and all external interactions (database, APIs, UI) go through abstract interfaces (ports). This makes the domain testable and swappable.

**Ports & Adapters** — Ports are abstract interfaces defined by the domain. Adapters are concrete implementations. Example: `MarketDataProvider` (port) is implemented by `IndiaDataProvider` (adapter).

**Bounded Context** — A DDD concept. Each context (Market Data, Analysis, Portfolio) has its own models, language, and rules. A "Position" in the Portfolio context means something different from a "Bollinger Position" in the Analysis context.

**Domain Event** — A notification that something happened: "recommendation created," "circuit breaker state changed." Published via the EventBus for loose coupling.

### ML Specific

**Lookahead Bias** — Using information that wasn't available at the time you're simulating. Fatal in financial ML because it makes backtests look unrealistically good.

**Survivorship Bias** — Training on only stocks that still exist today, ignoring those that went bankrupt or were delisted. Makes historical returns look better than they actually were.

**Walk-Forward Validation** — Time-respecting cross-validation. Train on past data, validate on future data, slide the window forward. Standard k-fold CV doesn't work for time series.

**Deflated Sharpe Ratio** — A Sharpe ratio adjusted for the number of strategies tested. If you try 100 strategies, the best one will look good by luck. Deflated Sharpe penalizes for this.

**Calibration** — Whether predicted probabilities match observed frequencies. A well-calibrated model that says "70% confidence" should be right about 70% of the time.

**ECE (Expected Calibration Error)** — A single number measuring calibration quality. Below 0.10 = well-calibrated.

### Infrastructure

**SSE (Server-Sent Events)** — A one-way streaming protocol from server to client over HTTP. Used here for streaming LLM-generated text (debate, thesis).

**Correlation ID** — A unique identifier attached to every request, carried through all layers. Enables tracing a single user action through logs across services.

**structlog** — A Python structured logging library. Instead of flat strings, logs are key-value pairs that can be searched and filtered.

**TimescaleDB** — A PostgreSQL extension that adds time-series optimizations. Automatic partitioning by time, compression, and time-oriented queries.
