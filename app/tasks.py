"""
Tasks for generating stock reports
"""
import datetime
import time
import re
from vnstock import Vnstock, Trading
from app.models import StockSymbol
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from config import Config

# Bỏ qua SSL verification cho vnstock (tạm thời fix lỗi SSL)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Danh sách các nguồn dữ liệu để thử (theo thứ tự ưu tiên)
DATA_SOURCES = Config.VNSTOCK_DATA_SOURCES


def _get_fireant_in_thread(symbol: str) -> str:
    """
    Hàm helper để chạy Playwright trong thread riêng
    """
    url = f"https://fireant.vn/ma-chung-khoan/{symbol}"
    print(f"🔗 Đang mở FireAnt: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = browser.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                try:
                    page.wait_for_selector("td.font-bold.text-right", timeout=10000)
                except Exception as e:
                    print(f"⚠️ Không tìm thấy selector: {e}")
                page.wait_for_timeout(3000)
            except PlaywrightTimeoutError:
                print(f"⚠️ FireAnt timeout cho {symbol}")
                browser.close()
                return "N/A"

            page.wait_for_timeout(10000)
            html = page.content()
            browser.close()

        if "Checking your browser" in html or "Cloudflare" in html:
            print(f"⚠️ Bị chặn bởi Cloudflare cho {symbol}")
            return "N/A"

        # Regex tìm "Tổng giá trị ... X tỷ"
        m = re.search(r"Tổng giá trị[\s\S]{0,200}?([\d\.\,]+)\s*tỷ", html, re.IGNORECASE)

        if not m:
            print(f"⚠️ Không tìm thấy 'Tổng giá trị' cho {symbol}")
            return "N/A"

        value_str = m.group(1).strip()
        print(f"✅ FireAnt - {symbol}: Tổng giá trị = {value_str} tỷ")
        return f"{value_str} tỷ"

    except Exception as e:
        print(f"❌ Lỗi Playwright cho {symbol}: {e}")
        return "N/A"


def get_total_value_from_fireant(symbol: str) -> str:
    """
    Lấy tổng giá trị giao dịch từ FireAnt bằng Playwright.
    Chạy trong thread riêng để tránh xung đột với asyncio loop.
    """
    print(f"🔍 DEBUG: Starting FireAnt crawl for {symbol}")
    try:
        # Chạy trong thread riêng với timeout 30s
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_get_fireant_in_thread, symbol)
            result = future.result(timeout=30)
            print(f"✅ DEBUG: FireAnt result for {symbol}: {result}")
            return result
    except FutureTimeoutError:
        print(f"⏱️ Timeout khi lấy dữ liệu FireAnt cho {symbol}")
        return "N/A"
    except Exception as e:
        print(f"❌ Lỗi khi lấy dữ liệu FireAnt cho {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return "N/A"


def index_change_str(symbol: str, today_query: str) -> str:
    """
    Lấy thông tin chỉ số VN-Index hoặc HNX-Index từ vnstock quote API.
    Thử nhiều nguồn dữ liệu khác nhau để tránh lỗi 403.
    """
    print(f"🔍 Đang lấy dữ liệu cho {symbol}...")
    
    # Thử từng nguồn dữ liệu cho đến khi thành công
    last_error = None
    for source in DATA_SOURCES:
        try:
            print(f"🔄 Thử nguồn {source} cho {symbol}...")
            stock = Vnstock(symbol=symbol, source=source).stock()
            
            # Lấy lịch sử 5 ngày gần nhất để có ít nhất 2 phiên
            start_dt = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
            df = stock.quote.history(symbol=symbol, start=start_dt, end=today_query, interval='1D')
            
            if df is None or len(df) < 1:
                print(f"⚠️ Không có dữ liệu lịch sử cho {symbol} từ {source}")
                continue
            
            # Lấy phiên gần nhất
            last_row = df.iloc[-1]
            close = float(last_row['close'])
            volume = float(last_row.get('volume', 0)) / 1e6
            
            # Tính delta nếu có ít nhất 2 phiên
            if len(df) >= 2:
                prev_close = float(df.iloc[-2]['close'])
                delta = close - prev_close
            else:
                # Nếu chỉ có 1 phiên, dùng open làm tham chiếu
                open_price = float(last_row.get('open', close))
                delta = close - open_price
            
            print(f"✅ {symbol} (nguồn {source}): close={close}, delta={delta}, volume={volume}")
            
            s = f"{close:,.2f} điểm -"
            if delta > 0:
                s += f" tăng {delta:,.2f} điểm"
            elif delta < 0:
                s += f" giảm {abs(delta):,.2f} điểm"
            else:
                s += " không thay đổi"
            
            # Lấy tổng giá trị từ FireAnt
            total_value_fireant = get_total_value_from_fireant(symbol)
            s += f" - Tổng giá trị giao dịch: {total_value_fireant}"
            s += f" - Tổng khối lượng giao dịch: {volume:,.1f} triệu cổ phiếu"
            
            return s
            
        except Exception as e:
            last_error = e
            print(f"⚠️ Lỗi với nguồn {source} cho {symbol}: {type(e).__name__}")
            continue
    
    # Nếu tất cả nguồn đều thất bại
    print(f"❌ Lỗi lấy chỉ số {symbol} từ tất cả nguồn: {last_error}")
    return f"Không có dữ liệu {symbol}."


def generate_report_text() -> str:
    """
    Tạo nội dung báo cáo thị trường
    Returns: String chứa báo cáo
    """
    print("🔔 Chuẩn bị gửi báo cáo...")
    
    # Get all stock symbols from database
    syms = StockSymbol.query.all()
    codes = [s.code for s in syms]
    
    print(f"🔔 Chuẩn bị gửi báo cáo cho {len(codes)} mã: {codes}")
    
    if not codes:
        return "⚠️ Không có mã chứng khoán nào để tạo báo cáo.\nSử dụng /add <MÃ> để thêm mã."
    
    today_query = datetime.datetime.now().strftime("%Y-%m-%d")
    today_vn = datetime.datetime.now().strftime("%d/%m/%Y")
    
    # Lấy dữ liệu chỉ số VN-Index
    try:
        vnindex_str = index_change_str('VNINDEX', today_query)
    except Exception as e:
        print(f"Lỗi lấy VN-Index: {e}")
        vnindex_str = "Không có dữ liệu VN-Index hôm nay."
    
    try:
        hnxindex_str = index_change_str('HNXINDEX', today_query)
    except Exception as e:
        print(f"Lỗi lấy HNX-Index: {e}")
        hnxindex_str = "Không có dữ liệu HNX-Index hôm nay."
    
    # Lấy bảng giá - Thử nhiều nguồn dữ liệu
    df = None
    last_error = None
    
    for source in DATA_SOURCES:
        try:
            print(f"🔄 Thử lấy bảng giá từ nguồn {source}...")
            trading = Trading(source=source)
            df = trading.price_board(codes)
            print(f"✅ Lấy bảng giá thành công từ {source} cho {len(codes)} mã")
            break  # Thành công, thoát vòng lặp
        except Exception as e:
            last_error = e
            print(f"⚠️ Lỗi với nguồn {source}: {type(e).__name__}: {e}")
            continue
    
    # Nếu tất cả nguồn đều thất bại
    if df is None:
        print(f"❌ Lỗi lấy bảng giá từ tất cả nguồn: {last_error}")
        return f"❌ Không thể lấy dữ liệu thị trường. Vui lòng thử lại sau."
    
    try:
        # Flatten MultiIndex columns: ('match', 'match_price') -> 'match_price'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in df.columns.values]
        
        print(f"DEBUG - Columns after flatten: {df.columns.tolist()[:20]}")
    except Exception as e:
        print(f"❌ Lỗi xử lý cột: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Lỗi khi xử lý dữ liệu: {str(e)}"
    
    # Tính giá thay đổi: match_price - ref_price
    df['price_change'] = df['match_match_price'] - df['listing_ref_price']
    
    lines = []
    lines.append(f"BÁO CÁO THỊ TRƯỜNG NGÀY {today_vn}\n")
    lines.append("KÍNH GỬI: CHỦ TỊCH HĐQT TẬP ĐOÀN ĐỨC LONG GIA LAI\n")
    lines.append(f"Chỉ số VN-Index: {vnindex_str}\n")
    lines.append(f"Chỉ số HNX-Index: {hnxindex_str}\n")
    
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        code = row.get('listing_symbol', '')
        match_price = row.get('match_match_price', 0)
        ref_price = row.get('listing_ref_price', 0)
        price_change = row.get('price_change', 0)
        
        # Kiểm tra nếu mã bị đình chỉ (không có giá)
        if pd.isna(match_price) or match_price == 0:
            lines.append(f"{i}. {code}")
            lines.append(f"   Đình chỉ giao dịch\n")
            continue
        
        # Format thay đổi giá (match_price - ref_price)
        try:
            price_change = float(price_change) if pd.notna(price_change) else 0
            if price_change > 0:
                change = f"tăng {price_change:,.0f} đ"
            elif price_change < 0:
                change = f"giảm {abs(price_change):,.0f} đ"
            else:
                change = "không thay đổi"
        except:
            change = "không xác định"
        
        # Lấy khối lượng giao dịch
        vol = row.get('match_accumulated_volume', row.get('match_match_vol', 0))
        try:
            vol = int(vol) if pd.notna(vol) else 0
        except:
            vol = 0
        
        lines.append(f"{i}. {code}")
        lines.append(f"   Giá đóng cửa: {match_price:,.0f} đ - {change}")
        lines.append(f"   Khối lượng giao dịch: {vol:,}\n")
    
    report_text = "\n".join(lines)
    print("✅ Đã tạo xong báo cáo")
    print(report_text)
    
    return report_text
