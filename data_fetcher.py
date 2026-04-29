import akshare as ak
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

MARKET_A = "a_share"
MARKET_HK = "hk_share"

# 全市场数据缓存（只加载一次，5分钟内复用）
_CACHE_TTL = 300  # 秒
# 单股数据缓存（价格/财务，5分钟内复用）
_SINGLE_STOCK_CACHE_TTL = 300  # 秒


def _a_code_with_prefix(code: str) -> str:
    code = code.strip()
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith(("60", "68")):
        return f"sh{code}"
    return f"sz{code}"


def detect_market(code: str) -> str:
    code = code.strip()
    if code.isdigit() and len(code) == 6:
        return MARKET_A
    if code.isdigit() and len(code) == 5:
        return MARKET_HK
    return MARKET_A


def normalize_hk_code(code: str) -> str:
    code = code.strip()
    if code.isdigit() and len(code) < 5:
        code = code.zfill(5)
    return code


# ── 缓存 ──
_spot_a_cache = None
_spot_a_time = 0
_spot_hk_cache = None
_spot_hk_time = 0


def _peek_a_spot_cache():
    """返回全市场缓存（若已就绪），不触发下载"""
    if _spot_a_cache is not None and (datetime.now().timestamp() - _spot_a_time) < _CACHE_TTL:
        return _spot_a_cache
    return None


def _get_a_spot():
    global _spot_a_cache, _spot_a_time
    now = datetime.now().timestamp()
    if _spot_a_cache is not None and (now - _spot_a_time) < _CACHE_TTL:
        return _spot_a_cache
    df = ak.stock_zh_a_spot()
    # 提取纯数字代码列
    df["code_raw"] = df["代码"].astype(str).apply(
        lambda c: c[2:] if c.startswith(("sh", "sz", "bj")) else c
    )
    _spot_a_cache = df
    _spot_a_time = now
    return df


def _get_hk_spot():
    """获取港股全列表（网络不稳定时返回空DataFrame）"""
    global _spot_hk_cache, _spot_hk_time
    now = datetime.now().timestamp()
    if _spot_hk_cache is not None and (now - _spot_hk_time) < _CACHE_TTL:
        return _spot_hk_cache
    try:
        df = ak.stock_hk_spot_em()
        _spot_hk_cache = df
        _spot_hk_time = now
        return df
    except Exception:
        _spot_hk_cache = pd.DataFrame()
        _spot_hk_time = now
        return _spot_hk_cache


def _resolve_hk_name(code: str) -> str | None:
    """通过个股查询解析港股名称（复用概况缓存）"""
    profile = _get_hk_profile(code)
    return profile.get("name") if profile else None


def search_stock(keyword: str) -> list[dict]:
    """搜索股票（带缓存，快速响应）"""
    keyword = keyword.strip()
    if not keyword:
        return []

    results = []

    # 纯数字 → 先搜代码，再搜名称
    is_digit = keyword.isdigit()

    # A股搜索
    try:
        df_a = _get_a_spot()
        if is_digit:
            mask = df_a["code_raw"].str.contains(keyword)
        else:
            mask = df_a["名称"].astype(str).str.contains(keyword, case=False)
        for _, row in df_a[mask].head(10).iterrows():
            results.append({
                "code": str(row["code_raw"]),
                "name": str(row["名称"]),
                "market": MARKET_A,
                "market_label": "A股",
            })
    except Exception:
        pass

    # 港股搜索（全列表网络不稳时 fallback 到个股查询）
    try:
        df_hk = _get_hk_spot()
        if not df_hk.empty:
            if is_digit:
                kw = normalize_hk_code(keyword)
                mask = df_hk["代码"].astype(str).str.contains(kw)
            else:
                mask = df_hk["名称"].astype(str).str.contains(keyword, case=False)
            for _, row in df_hk[mask].head(10).iterrows():
                results.append({
                    "code": str(row["代码"]),
                    "name": str(row["名称"]),
                    "market": MARKET_HK,
                    "market_label": "港股",
                })
        elif is_digit and len(keyword) <= 5:
            kw = normalize_hk_code(keyword)
            name = _resolve_hk_name(kw)
            if name:
                results.append({
                    "code": kw, "name": name,
                    "market": MARKET_HK, "market_label": "港股",
                })
    except Exception:
        pass

    return results


def quick_resolve(keyword: str) -> dict | None:
    """快速解析：如果输入看起来像股票代码，直接返回股票信息跳过搜索"""
    keyword = keyword.strip()
    if not keyword:
        return None

    # A股6位代码 → 直接查行情
    if keyword.isdigit() and len(keyword) == 6:
        try:
            df = _get_a_spot()
            row = df[df["code_raw"] == keyword]
            if not row.empty:
                r = row.iloc[0]
                return {
                    "code": keyword,
                    "name": str(r["名称"]),
                    "market": MARKET_A,
                    "market_label": "A股",
                }
        except Exception:
            pass

    # 港股5位代码
    if keyword.isdigit() and len(keyword) == 5:
        kw = normalize_hk_code(keyword)
        name = _resolve_hk_name(kw)
        if name:
            return {
                "code": kw, "name": name,
                "market": MARKET_HK, "market_label": "港股",
            }

    return None


# ── 指标名称映射 ──
_FIN_MAP = {
    "母公司净利润": "net_profit_parent",
    "营业总收入": "revenue",
    "营业成本": "cost",
    "净利润": "net_profit",
    "扣非净利润": "net_profit_deduct",
    "股东权益合计(净资产)": "equity",
    "经营现金流量净额": "operating_cf",
    "基本每股收益": "eps",
    "稀释每股收益": "eps_diluted",
    "每股净资产": "bps",
    "每股现金流": "cfps",
    "净资产收益率(ROE)": "roe",
    "总资产收益率(ROA)": "roa",
    "毛利率": "gross_margin",
    "销售净利率": "net_margin",
    "期间费用率": "expense_ratio",
    "资产负债率": "debt_ratio",
    "摊薄每股净资产_期末数": "bps_tanbo",
}

_HK_FIN_MAP = {
    "营业总收入(元)": "revenue",
    "营业总收入": "revenue",
    "营业成本(元)": "cost",
    "营业成本": "cost",
    "净利润(元)": "net_profit",
    "净利润": "net_profit",
    "基本每股收益(元)": "eps",
    "基本每股收益": "eps",
    "每股净资产(元)": "bps",
    "每股净资产": "bps",
    "净资产收益率": "roe",
    "净资产收益率(%)": "roe",
    "总资产收益率": "roa",
    "总资产收益率(%)": "roa",
    "毛利率": "gross_margin",
    "毛利率(%)": "gross_margin",
    "净利率": "net_margin",
    "净利率(%)": "net_margin",
    "资产负债率": "debt_ratio",
    "资产负债率(%)": "debt_ratio",
    "每股现金流(元)": "cfps",
    "每股现金流": "cfps",
    "每股营业收入(元)": "revenue_per_share",
    "每股营业收入": "revenue_per_share",
}

_profile_hk_cache = {}
_profile_hk_time = 0

# 单股数据缓存（价格/财务）
_price_cache: dict[str, tuple[dict, float]] = {}
_financial_cache: dict[str, tuple[dict, float]] = {}


def _get_hk_profile(code: str) -> dict:
    """获取港股公司概况（含行业等信息）"""
    global _profile_hk_cache, _profile_hk_time
    now = datetime.now().timestamp()
    cache_key = f"profile_{code}"
    if cache_key in _profile_hk_cache and (now - _profile_hk_time) < _CACHE_TTL:
        return _profile_hk_cache.get(cache_key, {})
    try:
        df = ak.stock_hk_company_profile_em(symbol=code)
        if not df.empty:
            row = df.iloc[0]
            profile = {
                "name": str(row.get("公司名称", "")),
                "industry": str(row.get("所属行业", "")) if row.get("所属行业") else "",
                "total_shares": str(row.get("总股本", "")) if row.get("总股本") else "",
                "business": str(row.get("主营业务", "")) if row.get("主营业务") else "",
                "listed_date": str(row.get("上市日期", "")) if row.get("上市日期") else "",
            }
            _profile_hk_cache[cache_key] = profile
            _profile_hk_time = now
            return profile
    except Exception:
        pass
    _profile_hk_cache[cache_key] = {}
    _profile_hk_time = now
    return {}


def _get_financial_data_impl(code: str, market: str) -> dict:
    """获取财务摘要数据（内部实现，无缓存）"""
    result = {"quarters": [], "indicators": {}}

    if market == MARKET_A:
        try:
            df = ak.stock_financial_abstract(symbol=code)
            if df.empty:
                result["error"] = "无财务数据"
                return result

            date_cols = [c for c in df.columns[2:] if str(c).isdigit() and len(str(c)) == 8]
            if not date_cols:
                result["error"] = "无有效日期列"
                return result

            for _, row in df.iterrows():
                indicator_name = str(row["指标"]).strip()
                key = _FIN_MAP.get(indicator_name)
                if key is None:
                    continue
                series = {}
                for dc in date_cols:
                    val = _safe_float(row[dc])
                    if val is not None:
                        series[str(dc)] = val
                if series:
                    result["indicators"][key] = series

            result["quarters"] = sorted(date_cols, reverse=True)
            result["latest_quarter"] = result["quarters"][0] if result["quarters"] else ""

            latest = result["latest_quarter"]
            for k, series in result["indicators"].items():
                if latest in series:
                    result[k] = series[latest]

            history = []
            for q in result["quarters"][:8]:
                entry = {"quarter": q}
                for k, series in result["indicators"].items():
                    entry[k] = series.get(q)
                history.append(entry)
            result["history"] = history

        except Exception as e:
            result["error"] = str(e)

    elif market == MARKET_HK:
        code = normalize_hk_code(code)
        try:
            df = ak.stock_hk_financial_indicator_em(symbol=code)
            if not df.empty:
                # 查找日期列（AKShare不同版本列名可能不同）
                date_col = None
                for candidate in ("日期", "报告期", "报告日期", "截止日期", "财报周期"):
                    if candidate in df.columns:
                        date_col = candidate
                        break
                if date_col:
                    df = df.sort_values(date_col)

                history = []
                for idx, (_, row) in enumerate(df.iterrows()):
                    entry = {"quarter": f"Q{idx}"}  # 默认兜底值
                    if date_col:
                        date_raw = row.get(date_col)
                        if date_raw and str(date_raw).strip() and str(date_raw) != "nan":
                            date_str = str(date_raw).replace("-", "").replace("/", "")[:8]
                            if date_str:
                                entry["quarter"] = date_str
                    for hk_col, key in _HK_FIN_MAP.items():
                        if hk_col in df.columns:
                            val = _safe_float(row[hk_col])
                            if val is not None:
                                entry[key] = val
                                if key not in result:
                                    result[key] = val
                    # 只要有财务数据就加入
                    if len(entry) > 1:
                        history.append(entry)

                if history:
                    result["history"] = history
                    result["quarters"] = [h.get("quarter", f"Q{i}") for i, h in enumerate(history)]
                    result["latest_quarter"] = result["quarters"][-1]
                    for key in history[-1]:
                        if key not in ("quarter",):
                            result[key] = history[-1][key]
        except Exception as e:
            result["error"] = str(e)

    return result


def get_financial_data(code: str, market: str = None) -> dict:
    """获取财务摘要数据（带缓存）"""
    code = code.strip()
    if market is None:
        market = detect_market(code)
    cache_key = f"{market}_{code}"
    now = datetime.now().timestamp()
    if cache_key in _financial_cache:
        cached, ts = _financial_cache[cache_key]
        if (now - ts) < _SINGLE_STOCK_CACHE_TTL:
            return cached
    result = _get_financial_data_impl(code, market)
    _financial_cache[cache_key] = (result, now)
    return result


def get_stock_info(code: str, market: str = None) -> dict:
    """获取基本信息 + 实时行情"""
    code = code.strip()
    if market is None:
        market = detect_market(code)
    info = {"code": code, "market": market}

    if market == MARKET_A:
        # 行情：只在缓存已就绪时使用，不主动触发全市场下载
        try:
            df_spot = _peek_a_spot_cache()
            if df_spot is not None:
                prefixed = _a_code_with_prefix(code)
                row = df_spot[df_spot["代码"].astype(str) == prefixed]
                if not row.empty:
                    r = row.iloc[0]
                    info["name"] = str(r["名称"])
                    info["latest_price"] = _safe_float(r.get("最新价"))
                    info["change_pct"] = _safe_float(r.get("涨跌幅"))
                    info["volume"] = _safe_float(r.get("成交量"))
                    info["turnover"] = _safe_float(r.get("成交额"))
                    info["high"] = _safe_float(r.get("最高"))
                    info["low"] = _safe_float(r.get("最低"))
                    info["open"] = _safe_float(r.get("今开"))
                    info["pre_close"] = _safe_float(r.get("昨收"))
        except Exception as e:
            info["error_spot"] = str(e)

        # 行业/市值（东方财富，不稳定时可跳过）
        try:
            df = ak.stock_individual_info_em(symbol=code)
            for _, row in df.iterrows():
                key = str(row["item"])
                val = str(row["value"])
                if key == "股票简称" and not info.get("name"):
                    info["name"] = val
                elif key == "行业":
                    info["industry"] = val
                elif key == "上市时间":
                    info["listed_date"] = val
                elif key == "总股本":
                    info["total_shares"] = val
                elif key == "总市值":
                    info["total_market_cap"] = val
                elif key == "流通市值":
                    info["float_market_cap"] = val
        except Exception:
            pass

    elif market == MARKET_HK:
        code = normalize_hk_code(code)
        info["code"] = code
        # 先尝全列表，不行则个股查询
        try:
            df_spot = _get_hk_spot()
            if not df_spot.empty:
                row = df_spot[df_spot["代码"].astype(str) == code]
                if not row.empty:
                    r = row.iloc[0]
                    info["name"] = str(r["名称"])
                    info["latest_price"] = _safe_float(r.get("最新价"))
                    info["change_pct"] = _safe_float(r.get("涨跌幅"))
                    info["high"] = _safe_float(r.get("最高"))
                    info["low"] = _safe_float(r.get("最低"))
                    info["open"] = _safe_float(r.get("今开"))
                    info["pre_close"] = _safe_float(r.get("昨收"))
                    info["volume"] = _safe_float(r.get("成交量"))
                    info["turnover"] = _safe_float(r.get("成交额"))
            else:
                name = _resolve_hk_name(code)
                if name:
                    info["name"] = name
        except Exception as e:
            info["error_spot"] = str(e)
            name = _resolve_hk_name(code)
            if name:
                info["name"] = name

        # 公司概况（行业、股本等）
        profile = _get_hk_profile(code)
        if profile:
            if not info.get("name") and profile.get("name"):
                info["name"] = profile["name"]
            if profile.get("industry"):
                info["industry"] = profile["industry"]
            if profile.get("total_shares"):
                info["total_shares"] = profile["total_shares"]
                # 总市值 = 总股本(股) × 最新价，API 返回的是"股"为单位的字符串
                price = info.get("latest_price")
                shares_str = profile["total_shares"]
                try:
                    shares_num = float(str(shares_str).replace(",", ""))
                    if price and shares_num > 0:
                        total_cap = price * shares_num
                        if total_cap >= 1e12:
                            info["total_market_cap"] = f"{(total_cap / 1e12):.2f}万亿"
                        elif total_cap >= 1e8:
                            info["total_market_cap"] = f"{(total_cap / 1e8):.2f}亿"
                        else:
                            info["total_market_cap"] = f"{(total_cap / 1e4):.2f}万"
                except (ValueError, TypeError):
                    pass
            if profile.get("listed_date"):
                info["listed_date"] = profile["listed_date"]

    return info


def _get_price_history_impl(code: str, market: str) -> dict:
    """获取历史价格（内部实现，无缓存）"""
    prices = {}

    if market == MARKET_A:
        try:
            prefixed = _a_code_with_prefix(code)
            df = ak.stock_zh_a_hist_tx(
                symbol=prefixed,
                start_date="20240101",
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
            if not df.empty:
                date_col = "date" if "date" in df.columns else "日期"
                close_col = "close" if "close" in df.columns else "收盘"
                open_col = "open" if "open" in df.columns else "开盘"
                high_col = "high" if "high" in df.columns else "最高"
                low_col = "low" if "low" in df.columns else "最低"
                vol_col = "amount" if "amount" in df.columns else ("volume" if "volume" in df.columns else "成交量")
                df = df.sort_values(date_col)
                prices["dates"] = df[date_col].astype(str).tolist()
                prices["close"] = df[close_col].tolist()
                prices["open"] = df[open_col].tolist()
                prices["high"] = df[high_col].tolist()
                prices["low"] = df[low_col].tolist()
                prices["volume"] = df[vol_col].tolist()
        except Exception as e:
            prices["error"] = str(e)

    elif market == MARKET_HK:
        code = normalize_hk_code(code)
        try:
            df = ak.stock_hk_hist(symbol=code, period="daily", start_date="20240101",
                                  end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq")
            if not df.empty:
                df = df.sort_values("日期")
                prices["dates"] = df["日期"].astype(str).tolist()
                prices["close"] = df["收盘"].tolist()
                prices["open"] = df["开盘"].tolist()
                prices["high"] = df["最高"].tolist()
                prices["low"] = df["最低"].tolist()
                prices["volume"] = df["成交量"].tolist()
        except Exception as e:
            prices["error"] = str(e)

    return prices


def get_price_history(code: str, market: str = None) -> dict:
    """获取历史价格（带缓存）"""
    code = code.strip()
    if market is None:
        market = detect_market(code)
    cache_key = f"{market}_{code}"
    now = datetime.now().timestamp()
    if cache_key in _price_cache:
        cached, ts = _price_cache[cache_key]
        if (now - ts) < _SINGLE_STOCK_CACHE_TTL:
            return cached
    result = _get_price_history_impl(code, market)
    _price_cache[cache_key] = (result, now)
    return result


def compute_valuation(info: dict, financial: dict, prices: dict) -> dict:
    val = {}
    price = info.get("latest_price")
    eps = financial.get("eps")
    bps = financial.get("bps")

    if price and eps and eps > 0:
        val["pe_current"] = round(price / eps, 2)
    if price and bps and bps > 0:
        val["pb_current"] = round(price / bps, 2)

    closes = prices.get("close", [])
    if closes:
        if len(closes) >= 22:
            val["change_1m"] = round((closes[-1] / closes[-22] - 1) * 100, 2)
        if len(closes) >= 66:
            val["change_3m"] = round((closes[-1] / closes[-66] - 1) * 100, 2)
        if len(closes) >= 250:
            val["change_1y"] = round((closes[-1] / closes[-250] - 1) * 100, 2)

        closes_1y = closes[-250:] if len(closes) >= 250 else closes
        val["price_latest"] = closes[-1]
        val["price_high_1y"] = round(max(closes_1y), 2)
        val["price_low_1y"] = round(min(closes_1y), 2)
        val["price_history"] = closes[-250:]
        val["price_dates"] = (prices.get("dates") or [])[-250:]

    return val


def fetch_all_data(code: str, market: str = None) -> dict:
    code = code.strip()
    if market is None:
        market = detect_market(code)

    # 并行获取三个独立数据源
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_info = executor.submit(get_stock_info, code, market)
        f_financial = executor.submit(get_financial_data, code, market)
        f_prices = executor.submit(get_price_history, code, market)
        info = f_info.result()
        financial = f_financial.result()
        prices = f_prices.result()

    valuation = compute_valuation(info, financial, prices)

    return {
        "code": code,
        "market": market,
        "info": info,
        "financial": financial,
        "valuation": valuation,
        "prices": prices,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def warmup_market_data():
    """启动时预热全市场数据，使首次搜索/生成快速响应"""
    import threading

    def _warmup():
        try:
            _get_a_spot()
        except Exception:
            pass
        try:
            _get_hk_spot()
        except Exception:
            pass

    threading.Thread(target=_warmup, daemon=True).start()


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        return v if pd.notna(v) else None
    except (ValueError, TypeError):
        return None
