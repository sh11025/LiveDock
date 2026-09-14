import sys
import os
import json
import re
import time
import webbrowser
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QInputDialog, QMenu, QSystemTrayIcon, QStyle, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPainterPath, QColor, QPen, QIcon

# 실행 파일 또는 스크립트 기준 절대 경로로 설정 파일 위치 지정
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
DATA_FILE = os.path.join(BASE_DIR, "channels.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
MAX_COLUMNS = 6

def resource_path(relative_path):
    """PyInstaller 번들 내부 리소스 및 현재 경로 해석"""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

FIXED_SERVERS = {
    "CHZZK": {
        "name": "치지직",
        "type": "GET",
        "health_url": "https://api.chzzk.naver.com/service/v1/channels/common",
        "main_url": "https://chzzk.naver.com"
    },
    "SOOP": {
        "name": "SOOP",
        "type": "POST",
        "health_url": "https://live.sooplive.com/afreeca/player_live_api.php",
        "post_data": {"bid": "afbroad", "mode": "landing", "player_type": "html5"},
        "main_url": "https://www.sooplive.com"
    },
    "YOUTUBE": {
        "name": "유튜브",
        "type": "GET",
        "health_url": "https://redirector.googlevideo.com/report_mapping",
        "main_url": "https://www.youtube.com"
    }
}

def detect_platform_and_id(input_str: str):
    text = input_str.strip()
    # SOOP / 아프리카TV
    if any(domain in text for domain in ["sooplive.com", "soop.co.kr", "afreecatv.com"]):
        match = re.search(r"(?:play|ch|www)?\.?(?:sooplive\.com|soop\.co\.kr|afreecatv\.com)/([a-zA-Z0-9_]+)", text)
        bj_id = match.group(1) if match else text
        return "soop", bj_id

    # 유튜브 (URL 또는 @핸들)
    if any(domain in text for domain in ["youtube.com", "youtu.be"]) or text.startswith("@"):
        if "youtube.com" in text or "youtu.be" in text:
            handle_match = re.search(r"youtube\.com/(@[a-zA-Z0-9_\-\.]+)", text)
            if handle_match:
                return "youtube", handle_match.group(1)
            ch_match = re.search(r"youtube\.com/(channel|c)/([a-zA-Z0-9_\-]+)", text)
            if ch_match:
                return "youtube", ch_match.group(2)
            return "youtube", text
        return "youtube", text
        
    # 치지직 32자리 해시 ID
    chzzk_match = re.search(r"([a-fA-F0-9]{32})", text)
    if chzzk_match:
        return "chzzk", chzzk_match.group(1)
        
    # 단순 영문/숫자면 SOOP ID 우선
    if re.match(r"^[a-zA-Z0-9_]+$", text):
        return "soop", text

    return "chzzk", text

def fetch_metadata(platform: str, channel_id: str):
    """스트리머 채널 정보(이름, 프로필 이미지 URL 등) 안전 조회"""
    try:
        if platform == "chzzk":
            url = f"https://api.chzzk.naver.com/service/v1/channels/{channel_id}"
            res = requests.get(url, headers=HEADERS, timeout=4).json()
            content = res.get("content")
            if not content:
                return None
            return {
                "name": content.get("channelName", "치지직 스트리머"),
                "img_url": content.get("channelImageUrl", ""),
                "live_url": f"https://chzzk.naver.com/live/{channel_id}"
            }
        elif platform == "soop":
            url = f"https://chapi.sooplive.com/api/{channel_id}/station"
            try:
                res = requests.get(url, headers=HEADERS, timeout=4).json()
            except Exception:
                url = f"https://chapi.soop.co.kr/api/{channel_id}/station"
                res = requests.get(url, headers=HEADERS, timeout=4).json()

            station = res.get("station")
            if not station:
                return None
            profile = res.get("profile", {})
            img_url = profile.get("profile_image", "")
            if img_url and not img_url.startswith("http"):
                img_url = f"https:{img_url}"
                
            return {
                "name": station.get("user_nick", channel_id),
                "img_url": img_url,
                "live_url": f"https://play.sooplive.com/{channel_id}"
            }
        elif platform == "youtube":
            yt_id = channel_id if channel_id.startswith("@") or channel_id.startswith("UC") else f"@{channel_id}"
            url = f"https://www.youtube.com/{yt_id}"
            res = requests.get(url, headers=HEADERS, timeout=6)
            html = res.text
            
            title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            name = title_m.group(1) if title_m else yt_id
            
            img_m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            img_url = img_m.group(1) if img_m else ""
            
            live_url = f"https://www.youtube.com/{yt_id}/live"
            return {
                "name": name,
                "img_url": img_url,
                "live_url": live_url
            }
    except Exception as e:
        print(f"[오류] 채널 메타데이터 조회 중 오류 발생: {e}")
        return None
    return None

class ImageLoaderThread(QThread):
    """메인 UI 프리징을 방지하기 위한 비동기 프로필 이미지 다운로드 스레드"""
    image_loaded = pyqtSignal(QPixmap)

    def __init__(self, img_url):
        super().__init__()
        self.img_url = img_url

    def run(self):
        try:
            if self.img_url:
                data = requests.get(self.img_url, headers=HEADERS, timeout=4).content
                img = QImage.fromData(data)
                pixmap = QPixmap.fromImage(img)
                if not pixmap.isNull():
                    self.image_loaded.emit(pixmap)
        except Exception:
            pass

class ServerHealthThread(QThread):
    health_updated = pyqtSignal(dict)

    def run(self):
        statuses = {}
        for key, info in FIXED_SERVERS.items():
            try:
                start_t = time.time()
                if info.get("type") == "POST":
                    res = requests.post(
                        info["health_url"], 
                        data=info.get("post_data", {}), 
                        headers=HEADERS, 
                        timeout=3
                    )
                else:
                    res = requests.get(
                        info["health_url"], 
                        headers=HEADERS, 
                        timeout=3, 
                        stream=True
                    )

                latency = int((time.time() - start_t) * 1000)

                if res.status_code < 400:
                    if latency > 1500:
                        state, msg = "warning", f"중계 지연 ({latency}ms)"
                    else:
                        state, msg = "healthy", f"중계 원활 ({latency}ms)"
                else:
                    state, msg = "error", f"세션 오류 ({res.status_code})"
            except requests.exceptions.Timeout:
                state, msg = "error", "타임아웃 (세션 무응답)"
            except Exception:
                state, msg = "error", "중계 서버 연결 불가"

            statuses[key] = {"state": state, "msg": msg}
            
        self.health_updated.emit(statuses)

class LiveCheckThread(QThread):
    status_updated = pyqtSignal(dict)

    def __init__(self, channels):
        super().__init__()
        self.channels = channels

    def run(self):
        results = {}
        for key in list(self.channels.keys()):
            item = self.channels.get(key)
            if not item:
                continue
            platform = item["platform"]
            cid = item["channel_id"]
            try:
                if platform == "chzzk":
                    url = f"https://api.chzzk.naver.com/polling/v2/channels/{cid}/live-status"
                    res = requests.get(url, headers=HEADERS, timeout=4).json()
                    content = res.get("content", {})
                    results[key] = {
                        "is_open": content.get("status") == "OPEN",
                        "title": content.get("liveTitle", "")
                    }
                elif platform == "soop":
                    url = "https://live.sooplive.com/afreeca/player_live_api.php"
                    data = {"bid": cid, "mode": "landing", "player_type": "html5"}
                    try:
                        res = requests.post(url, headers=HEADERS, data=data, timeout=4).json()
                    except Exception:
                        url = "https://live.soop.co.kr/afreeca/player_live_api.php"
                        res = requests.post(url, headers=HEADERS, data=data, timeout=4).json()

                    channel_data = res.get("CHANNEL", {})
                    results[key] = {
                        "is_open": str(channel_data.get("RESULT")) == "1",
                        "title": channel_data.get("TITLE", "")
                    }
                elif platform == "youtube":
                    yt_id = cid if cid.startswith("@") or cid.startswith("UC") else f"@{cid}"
                    url = f"https://www.youtube.com/{yt_id}/live"
                    res = requests.get(url, headers=HEADERS, timeout=6)
                    text = res.text
                    
                    is_live = False
                    if '"status":"LIVE"' in text or '"isLive":true' in text:
                        is_live = True
                    elif '"isLiveContent":true' in text and '"isLiveBroadcast":true' in text:
                        is_live = True
                    elif 'liveStreamability' in text and '"status":"LIVE"' in text:
                        is_live = True

                    title_m = re.search(r'<meta property="og:title" content="([^"]+)"', text)
                    title = title_m.group(1) if title_m else ""
                    results[key] = {
                        "is_open": is_live,
                        "title": title
                    }
            except Exception:
                results[key] = {"is_open": False, "title": ""}
        self.status_updated.emit(results)

class ServerStatusIcon(QWidget):
    def __init__(self, server_key, server_data):
        super().__init__()
        self.server_key = server_key
        self.display_name = server_data["name"]
        self.main_url = server_data.get("main_url", "")
        self.state = "checking"
        self.msg = "세션 확인 중..."

        self.setFixedSize(54, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_tooltip()

    def update_status(self, state, msg):
        self.state = state
        self.msg = msg
        self.update_tooltip()
        self.update()

    def update_tooltip(self):
        self.setToolTip(f"[{self.display_name} 중계 세션]\n상태: {self.msg}\n클릭 시 {self.display_name} 바로가기")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_path = QPainterPath()
        bg_path.addRoundedRect(2, 2, 50, 40, 10, 10)
        painter.fillPath(bg_path, QColor("#141418"))

        if self.state == "healthy":
            border_color = QColor("#00FFA3")
        elif self.state == "warning":
            border_color = QColor("#FFD15C")
        elif self.state == "error":
            border_color = QColor("#FF4757")
        else:
            border_color = QColor("#33333F")

        painter.setPen(QPen(border_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(2, 2, 50, 40, 10, 10)

        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, 54, 44, Qt.AlignmentFlag.AlignCenter, self.display_name)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.main_url:
            webbrowser.open(self.main_url)

class StreamerDockButton(QWidget):
    def __init__(self, key, item_data, delete_callback):
        super().__init__()
        self.key = key
        self.platform = item_data["platform"]
        self.channel_id = item_data["channel_id"]
        self.name = item_data["name"]
        self.img_url = item_data.get("img_url", "")
        self.live_url = item_data.get("live_url", "")
        self.delete_callback = delete_callback
        
        self.is_live = False
        self.profile_pixmap = None

        self.setFixedSize(72, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_profile_image()

    def load_profile_image(self):
        """프로필 이미지를 백그라운드 스레드에서 비동기로 로드하여 메인 UI 멈춤 방지"""
        if self.img_url:
            self.image_loader = ImageLoaderThread(self.img_url)
            self.image_loader.image_loaded.connect(self.on_image_loaded)
            self.image_loader.start()

    def on_image_loaded(self, pixmap):
        self.profile_pixmap = pixmap
        self.update()

    def update_status(self, is_live, title=""):
        self.is_live = is_live
        if self.platform == "chzzk":
            platform_name = "치지직"
        elif self.platform == "soop":
            platform_name = "SOOP"
        else:
            platform_name = "유튜브"
        self.setToolTip(f"[{platform_name} | {'방송 중' if is_live else '오프라인'}] {self.name}\n{title}")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_path = QPainterPath()
        bg_path.addRoundedRect(2, 2, 68, 68, 16, 16)
        painter.fillPath(bg_path, QColor("#0A0A0C"))

        img_size = 40
        img_x = (72 - img_size) // 2
        img_y = 8
        
        if self.profile_pixmap and not self.profile_pixmap.isNull():
            scaled = self.profile_pixmap.scaled(
                img_size, img_size, 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            if not self.is_live:
                scaled = QPixmap.fromImage(scaled.toImage().convertToFormat(QImage.Format.Format_Grayscale8))
            
            circle_path = QPainterPath()
            circle_path.addEllipse(img_x, img_y, img_size, img_size)
            
            painter.save()
            painter.setClipPath(circle_path)
            if not self.is_live:
                painter.setOpacity(0.35)
            painter.drawPixmap(img_x, img_y, scaled)
            painter.restore()
        else:
            painter.setBrush(QColor("#222226"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(img_x, img_y, img_size, img_size)

        if self.platform == "chzzk":
            theme_color = QColor("#00FFA3")
        elif self.platform == "soop":
            theme_color = QColor("#0090FF")
        else:
            theme_color = QColor("#FF0000")

        if self.is_live:
            painter.setPen(QPen(theme_color, 2))
            painter.drawEllipse(img_x, img_y, img_size, img_size)

        painter.setPen(QColor("#FFFFFF" if self.is_live else "#777777"))
        font = painter.font()
        font.setPixelSize(10)
        font.setBold(self.is_live)
        painter.setFont(font)
        painter.drawText(0, 52, 72, 16, Qt.AlignmentFlag.AlignCenter, self.name)

        border_pen = QPen(theme_color if self.is_live else QColor("#1E1E24"), 1.5)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(2, 2, 68, 68, 16, 16)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            webbrowser.open(self.live_url)
        elif event.button() == Qt.MouseButton.RightButton:
            menu = QMenu(self)
            del_action = menu.addAction(f"'{self.name}' 삭제")
            action = menu.exec(event.globalPosition().toPoint())
            if action == del_action:
                self.delete_callback(self.key)

class AddButton(QPushButton):
    def __init__(self, callback):
        super().__init__()
        self.setText("+")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(72, 72)
        self.setStyleSheet("""
            QPushButton {
                background-color: #0A0A0C;
                color: #555560;
                font-size: 26px;
                font-weight: bold;
                border: 2px dashed #24242C;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #141418;
                color: #00FFA3;
                border-color: #00FFA3;
            }
        """)
        self.clicked.connect(callback)

class MultiLiveDock(QWidget):
    def __init__(self):
        super().__init__()
        self.channels = self.load_channels()
        self.cards = {}
        self.server_icons = {}
        self.live_thread = None
        self.server_thread = None
        self.drag_position = QPoint()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_tray()
        self.init_ui()

        # 방송 체크 타이머 (30초)
        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self.start_live_check)
        self.live_timer.start(30000)

        # 서버 헬스체크 타이머 (60초)
        self.server_timer = QTimer(self)
        self.server_timer.timeout.connect(self.start_server_check)
        self.server_timer.start(60000)

        self.start_live_check()
        self.start_server_check()

    def init_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(14, 12, 14, 14)
        self.root_layout.setSpacing(10)

        # 상단 서버 인디케이터
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        
        server_title = QLabel("서버")
        server_title.setStyleSheet("color: #888899; font-size: 11px; font-weight: bold;")
        top_bar.addWidget(server_title)
        
        for key, data in FIXED_SERVERS.items():
            icon = ServerStatusIcon(key, data)
            self.server_icons[key] = icon
            top_bar.addWidget(icon)
        
        top_bar.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888899;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #FF4757;
                color: white;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        top_bar.addWidget(self.close_btn)

        self.root_layout.addLayout(top_bar)

        # 하단 스트리머 그리드 도크
        self.streamer_container = QWidget()
        self.grid_layout = QGridLayout(self.streamer_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(10)

        self.add_channel_btn = AddButton(self.prompt_add_channel)
        self.root_layout.addWidget(self.streamer_container)

        self.rebuild_grid()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#242630"))
        painter.setPen(QPen(QColor("#363A48"), 1.5))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)

    def rebuild_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        index = 0
        for key in list(self.channels.keys()):
            data = self.channels[key]
            if key not in self.cards:
                card = StreamerDockButton(key, data, self.delete_channel)
                self.cards[key] = card
            
            row = index // MAX_COLUMNS
            col = index % MAX_COLUMNS
            self.grid_layout.addWidget(self.cards[key], row, col)
            index += 1

        row = index // MAX_COLUMNS
        col = index % MAX_COLUMNS
        self.grid_layout.addWidget(self.add_channel_btn, row, col)
        self.adjustSize()

    def prompt_add_channel(self):
        text, ok = QInputDialog.getText(self, "채널 추가", "치지직, SOOP 또는 유튜브 채널 URL / ID(@핸들)를 입력하세요:")
        if not ok or not text.strip():
            return

        platform, channel_id = detect_platform_and_id(text)
        key = f"{platform}_{channel_id}"

        if key in self.channels:
            QMessageBox.information(self, "알림", "이미 등록된 채널입니다.")
            return

        meta = fetch_metadata(platform, channel_id)
        if not meta:
            QMessageBox.warning(self, "오류", "채널 정보를 불러올 수 없습니다.")
            return

        self.channels[key] = {
            "platform": platform,
            "channel_id": channel_id,
            "name": meta["name"],
            "img_url": meta["img_url"],
            "live_url": meta["live_url"]
        }
        self.save_channels()
        self.rebuild_grid()
        self.start_live_check()

    def delete_channel(self, key):
        if key in self.channels:
            del self.channels[key]
            self.save_channels()

        if key in self.cards:
            self.cards.pop(key).deleteLater()

        self.rebuild_grid()

    def start_live_check(self):
        if not self.channels:
            return
        # 이전 체크 스레드가 아직 실행 중이면 중복 실행 방지
        if self.live_thread is not None and self.live_thread.isRunning():
            return
        self.live_thread = LiveCheckThread(self.channels)
        self.live_thread.status_updated.connect(self.on_live_updated)
        self.live_thread.start()

    def on_live_updated(self, results):
        for key, res in list(results.items()):
            if key in self.cards:
                card = self.cards[key]
                is_open = res["is_open"]
                title = res["title"]

                if not card.is_live and is_open:
                    if card.platform == "chzzk":
                        platform_kr = "치지직"
                    elif card.platform == "soop":
                        platform_kr = "SOOP"
                    else:
                        platform_kr = "유튜브"

                    self.tray.showMessage(
                        f"[{platform_kr}] 방송 시작! - {card.name}",
                        title,
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
                card.update_status(is_open, title)

    def start_server_check(self):
        # 이전 헬스체크 스레드가 아직 실행 중이면 중복 실행 방지
        if self.server_thread is not None and self.server_thread.isRunning():
            return
        self.server_thread = ServerHealthThread()
        self.server_thread.health_updated.connect(self.on_server_health_updated)
        self.server_thread.start()

    def on_server_health_updated(self, statuses):
        for key, data in list(statuses.items()):
            if key in self.server_icons:
                icon_widget = self.server_icons[key]
                prev_state = icon_widget.state
                curr_state = data["state"]
                msg = data["msg"]

                icon_widget.update_status(curr_state, msg)

                # 서버 상태 악화 시 알림 발송
                if prev_state in ["healthy", "checking"] and curr_state in ["error", "warning"]:
                    platform_name = FIXED_SERVERS[key]["name"]
                    if curr_state == "error":
                        self.tray.showMessage(
                            f"⚠️ [{platform_name}] 중계 세션 장애 감지",
                            f"{platform_name} 스트리밍 중계 세션 연결 불가\n상태: {msg}",
                            QSystemTrayIcon.MessageIcon.Critical,
                            4000
                        )
                    elif curr_state == "warning":
                        self.tray.showMessage(
                            f"⚡ [{platform_name}] 스트리밍 지연 발생",
                            f"{platform_name} 중계 세션 응답 지연\n상태: {msg}",
                            QSystemTrayIcon.MessageIcon.Warning,
                            3000
                        )

    def init_tray(self):
        icon_path = resource_path("app_icon.ico")
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.tray.setIcon(app_icon)
            self.setWindowIcon(app_icon)
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.show()

    def load_channels(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_channels(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.channels, f, ensure_ascii=False, indent=2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def closeEvent(self, event):
        """프로그램 종료 시 실행 중인 스레드를 안전하게 정리"""
        if self.live_thread is not None and self.live_thread.isRunning():
            self.live_thread.quit()
            self.live_thread.wait(500)
        if self.server_thread is not None and self.server_thread.isRunning():
            self.server_thread.quit()
            self.server_thread.wait(500)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MultiLiveDock()
    window.show()
    sys.exit(app.exec())