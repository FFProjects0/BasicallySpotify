# this is the wrong file, actually, haha... 
# tried by best to rewrite it!!

import sys, os, datetime
import re
import json
import random
import urllib.parse
from PyQt5 import QtWidgets, QtGui, QtCore
import vlc
from mutagen.id3 import ID3, APIC
from tinytag import TinyTag
import html
from functools import partial

album_bg = None

SUPPORTED_FORMATS = (
    '.3gp', '.aa', '.aac', '.aax', '.act', '.aiff', '.alac', '.amr', '.ape',
    '.au', '.awb', '.dss', '.dvf', '.flac', '.gs', '.iklax', '.ivs', '.m4a',
    '.m4b', '.m4p', '.mmf', '.movpkg', '.mp3', '.mpc', '.msv', '.nmf', '.ogg',
    '.oga', '.mogg', '.opus', '.ra', '.rm', '.raw', '.rf64', '.sln', '.tta',
    '.voc', '.vox', '.wav', '.wma', '.wv', '.webm', '.8svx', '.cda'
)
PLAYLISTS_FILE = "playlists.json"
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', s)]
def ms_to_mmss(ms):
    seconds = int(ms / 1000)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02}:{seconds:02}"
def get_contrasting_color(color: QtGui.QColor) -> QtGui.QColor:
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return QtGui.QColor("black") if luminance > 128 else QtGui.QColor("white")
def fill_square_pixmap(original_pixmap, size=32, bg_color=QtCore.Qt.black):
    return original_pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
def create_placeholder_pixmap(size=120, text="No Cover"):
    pixmap = QtGui.QIcon(resource_path("plit.png"))
    return pixmap
def parse_lrc(lrc_file, offset_ms=0):
    lyrics = []
    print(f"[DEBUG] parse_lrc: Attempting to parse LRC file at: {lrc_file}")
    if not os.path.exists(lrc_file):
        print("[DEBUG] parse_lrc: LRC file does not exist.")
        return lyrics
    try:
        with open(lrc_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if re.match(r'\[.*?:', line) and not re.match(r'\[\d', line):
                    continue
                matches = re.findall(r'\[(\d+):(\d+\.\d+)\]', line)
                text = re.sub(r'\[.*?\]', '', line).strip()
                for m in matches:
                    minutes = int(m[0])
                    seconds = float(m[1])
                    timestamp = int((minutes * 60 + seconds) * 1000)
                    shifted_ts = max(0, timestamp - offset_ms)
                    lyrics.append((shifted_ts, text))
        lyrics.sort(key=lambda x: x[0])
        print(f"[DEBUG] parse_lrc: Found {len(lyrics)} lines in .lrc file. offset={offset_ms} ms")
    except Exception as e:
        print("[DEBUG] parse_lrc: Exception reading file:", e)
    return lyrics
class CoverArtTaskNotifier(QtCore.QObject):
    finished = QtCore.pyqtSignal(list)
    log = QtCore.pyqtSignal(str)
class CoverArtExtractionTask(QtCore.QRunnable):
    """
    A QRunnable task that extracts cover art for a list of albums.
    Each album is a 4-tuple: (artist, album, album_path, first_audio).
    The result is a list of 5-tuples: (artist, album, album_path, first_audio, cover)
    """
    def __init__(self, albums, notifier):
        super().__init__()
        self.albums = albums
        self.notifier = notifier

    @QtCore.pyqtSlot()
    def run(self):
        enriched_albums = []
        for album in self.albums:
            artist, album_name, album_path, first_audio = album
            first_audio_path = os.path.join(album_path, first_audio)
            cover = None
            try:
                audio = ID3(first_audio_path)
                for tag in audio.values():
                    if isinstance(tag, APIC):
                        cover_data = tag.data
                        pixmap = QtGui.QPixmap()
                        if pixmap.loadFromData(cover_data):
                            cover = pixmap
                            self.notifier.log.emit(f"[DEBUG] Extracted cover for {album_name}")
                            break
            except Exception as e:
                self.notifier.log.emit(f"[DEBUG] Exception for {album_name}: {e}")
            if not cover:
                cover = QtGui.QPixmap(resource_path("plit.png"))
            enriched_albums.append((artist, album_name, album_path, first_audio, cover))
        self.notifier.finished.emit(enriched_albums)
class LyricsWidget(QtWidgets.QTextBrowser):
    from PyQt5.QtCore import pyqtSignal, QUrl
    timestampClicked = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lyrics = []
        self.current_index = -1
        self.setReadOnly(True)
        self.setStyleSheet("background-color: transparent; color: white;")
        self.document().setDefaultStyleSheet("""
            a { color: inherit; text-decoration: none; }
        """)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.on_anchor_clicked)
    def load_lyrics(self, lrc_file):
        print(f"[DEBUG] LyricsWidget.load_lyrics: Loading lyrics from: {lrc_file}")
        self.lyrics = parse_lrc(lrc_file)
        if self.lyrics:
            self.current_index = 0
            self.update_display(0)
            return
        unsynced_lines = []
        try:
            with open(lrc_file, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    # Skip empty or pure metadata tags like [ar:], [ti:], etc.
                    if not line or re.match(r'^\[.*?:.*\]$', line):
                        continue
                    # Skip any lines that contain timestamps
                    if re.search(r'\[\d+:\d+(\.\d+)?\]', line):
                        continue
                    unsynced_lines.append(line)
        except Exception as e:
            print(f"[DEBUG] LyricsWidget.load_lyrics: Could not read file: {e}")

        if unsynced_lines:
            html_line_start = "These lyrics aren't synced to the song yet.<br><br>"
            html_lines = html_line_start+"".join(f"<p>{html.escape(line)}</p>" for line in unsynced_lines)
            self.setHtml(html_lines)
            self.current_index = -1
            return
        quotes = {
            1: "Nobody here but us chickens!",
            2: "No lyrics available.",
            3: "You - 1<br>Lyrics - 0",
            4: "Kinda boring without any text to read, no?",
            5: "How you doing?",
            6: "Rahhhhhhhhhhh",
            7: "Yo",
            8: "Eminem<br>VS<br>IBS"
        }
        choice = random.randint(1, 8)
        self.setHtml(f"<i>{quotes[choice]}</i>")
        self.current_index = 0
    def on_anchor_clicked(self, url: QUrl):
        """Handle clicks on a <a href="...">…</a>"""
        try:
            ts = int(url.toString())
            self.timestampClicked.emit(ts)
        except ValueError:
            pass
    def update_display(self, current_time):
        if not self.lyrics:
            return
        index = -1
        for i, (ts, line) in enumerate(self.lyrics):
            if current_time >= ts:
                index = i
            else:
                break

        if index != self.current_index:
            self.current_index = index
            #try:
            contrast = album_bg
            color = contrast
            #except AttributeError:
            #    color = 'yellow'

            html_content = ""
            for i, (ts, line) in enumerate(self.lyrics):
                if i == index:
                    html_content += (
                        f'<p><b>'
                        f'<a style="color:{color};" href="{ts}">{line}</a>'
                        f'</b></p>'
                    )
                else:
                    html_content += (
                        f'<p><a style="color:{color};" href="{ts}">{line}</a></p>'
                    )

            self.setHtml(html_content)
            self.center_current_line()
    def center_current_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.Start)
        for _ in range(self.current_index):
            cursor.movePosition(QtGui.QTextCursor.Down)
        self.setTextCursor(cursor)

        layout = self.document().documentLayout()
        block_rect = layout.blockBoundingRect(cursor.block())
        center_y = block_rect.center().y()
        scrollbar = self.verticalScrollBar()
        viewport_height = self.viewport().height()
        new_value = int(center_y - viewport_height / 2)
        scrollbar.setValue(new_value)
class AlbumTree(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(False)
        self.setWordWrap(True)
        self.setTextElideMode(QtCore.Qt.ElideNone)
        self.setIconSize(QtCore.QSize(120, 120))
    def populate_albums_data(self, albums_data):
        self.clear()
        for album in albums_data:
            #note to self; 5-tuple: artist, album, album_path, first_audio, cover
            artist, album_name, album_path, first_audio, cover = album
            artist_items = self.findItems(artist, QtCore.Qt.MatchExactly)
            if artist_items:
                artist_item = artist_items[0]
            else:
                artist_item = QtWidgets.QTreeWidgetItem(self)
                artist_item.setText(0, artist)
                artist_item.setExpanded(False)
            album_item = QtWidgets.QTreeWidgetItem(artist_item)
            album_item.setText(0, album_name)
            album_item.setData(0, QtCore.Qt.UserRole, album_path)
            if cover:
                album_icon = QtGui.QIcon(fill_square_pixmap(cover, 32))
                album_item.setIcon(0, album_icon)
            else:
                default_icon = QtGui.QIcon(QtGui.QPixmap(resource_path("plit.png")))
                album_item.setIcon(0, default_icon)
    def filter_albums(self, query):
        query = query.lower()
        for i in range(self.topLevelItemCount()):
            artist_item = self.topLevelItem(i)
            artist_visible = False
            for j in range(artist_item.childCount()):
                album_item = artist_item.child(j)
                album_text = album_item.text(0).lower()
                artist_text = artist_item.text(0).lower()
                match = (query in album_text) or (query in artist_text)
                album_item.setHidden(not match)
                if match:
                    artist_visible = True
            artist_item.setHidden(not artist_visible)
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item and item.parent() is not None:
            album_path = item.data(0, QtCore.Qt.UserRole)
            if album_path:
                mimeData = QtCore.QMimeData()
                mimeData.setText(album_path)
                drag = QtGui.QDrag(self)
                drag.setMimeData(mimeData)
                drag.exec_(supportedActions)
class NowPlayingWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.albumLabel = QtWidgets.QLabel("")
        self.albumLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.artistLabel = QtWidgets.QLabel("")
        self.artistLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.coverLabel = QtWidgets.QLabel("Drop Album Here")
        self.coverLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.coverLabel.setMinimumSize(300, 300)
        self.songLabel = QtWidgets.QLabel("")
        self.songLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.progressSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.progressSlider.setRange(0, 100)
        self.progressSlider.setValue(0)
        self.progressSlider.setEnabled(False)
        self.timeLabel = QtWidgets.QLabel("--:-- / --:--")
        self.timeLabel.setAlignment(QtCore.Qt.AlignCenter)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.albumLabel)
        layout.addWidget(self.artistLabel)
        layout.addWidget(self.coverLabel)
        layout.addWidget(self.songLabel)
        layout.addWidget(self.progressSlider)
        layout.addWidget(self.timeLabel)
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    def dropEvent(self, event):
        album_path = event.mimeData().text()
        main_window = self.window()
        if hasattr(main_window, 'play_album'):
            try:
                main_window.play_album(album_path)
            except:
                pass
        event.acceptProposedAction()
class PlaylistShelf(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Playlists", parent)
        self.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.TopDockWidgetArea)
        self.playlists = {}
        self.current_playlist = None
        self.init_ui()
        self.load_playlists()
    def init_ui(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        toolbar = QtWidgets.QHBoxLayout()
        newPlaylistBtn = QtWidgets.QPushButton("New Playlist")
        newPlaylistBtn.clicked.connect(self.create_playlist)
        toolbar.addWidget(newPlaylistBtn)
        playPlaylistBtn = QtWidgets.QPushButton("Play Playlist")
        playPlaylistBtn.clicked.connect(self.play_current_playlist)
        toolbar.addWidget(playPlaylistBtn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.playlistList = QtWidgets.QListWidget()
        self.playlistList.setMaximumWidth(150)
        self.playlistList.itemClicked.connect(self.playlist_selected)
        self.songList = QtWidgets.QListWidget()
        self.songList.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        splitter.addWidget(self.playlistList)
        splitter.addWidget(self.songList)
        layout.addWidget(splitter)
        self.setWidget(container)
    def create_playlist(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "New Playlist", "Enter playlist name:")
        if ok and text:
            if text in self.playlists:
                QtWidgets.QMessageBox.warning(self, "Duplicate", "A playlist with that name already exists.")
            else:
                self.playlists[text] = []
                self.playlistList.addItem(text)
                self.save_playlists()
    def playlist_selected(self, item):
        playlist_name = item.text()
        self.current_playlist = playlist_name
        self.refresh_song_list()
    def refresh_song_list(self):
        self.songList.clear()
        if self.current_playlist and self.current_playlist in self.playlists:
            for song in self.playlists[self.current_playlist]:
                self.songList.addItem(os.path.basename(song))
    def add_song_to_playlist(self, song_path, playlist_name):
        if playlist_name not in self.playlists:
            QtWidgets.QMessageBox.warning(self, "Playlist not found", f"Playlist '{playlist_name}' does not exist.")
            return
        self.playlists[playlist_name].append(song_path)
        if self.current_playlist == playlist_name:
            self.refresh_song_list()
        self.save_playlists()
    def save_playlists(self):
        try:
            with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.playlists, f, indent=4)
            print("[DEBUG] Playlists saved.")
        except Exception as e:
            print("[DEBUG] Error saving playlists:", e)
    def load_playlists(self):
        if os.path.exists(PLAYLISTS_FILE):
            try:
                with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
                    self.playlists = json.load(f)
                self.playlistList.clear()
                for playlist in self.playlists:
                    self.playlistList.addItem(playlist)
                print("[DEBUG] Playlists loaded.")
            except Exception as e:
                print("[DEBUG] Error loading playlists:", e)
        else:
            self.playlists = {}
    def play_current_playlist(self):
        if not self.current_playlist:
            QtWidgets.QMessageBox.information(self, "No Playlist Selected", "Please select a playlist first.")
            return
        if hasattr(self.parent(), "play_playlist"):
            self.parent().play_playlist(self.current_playlist)
class SearchWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int)
    result = QtCore.pyqtSignal(str)

    def __init__(self, root_folder, query):
        super().__init__()
        self.root = root_folder
        self.query = query.lower()

    def run(self):
        total = 0
        for _root, _dirs, files in os.walk(self.root):
            total += sum(1 for f in files if f.lower().endswith(SUPPORTED_FORMATS))
        if total == 0:
            self.progress.emit(100)
            return

        seen = 0
        for dirpath, _dirs, files in os.walk(self.root):
            for f in files:
                if not f.lower().endswith(SUPPORTED_FORMATS):
                    continue
                seen += 1
                pct = int(seen / total * 100)
                self.progress.emit(pct)
                if self.query in f.lower():
                    full_path = os.path.join(dirpath, f)
                    self.result.emit(full_path)
        self.progress.emit(100)
class SearchSongDialog(QtWidgets.QDialog):
    searchRequested = QtCore.pyqtSignal(str, object)
    songSelected = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find Song")
        self.setLayout(QtWidgets.QVBoxLayout())

        self.input = QtWidgets.QLineEdit(self)
        self.input.setPlaceholderText("Search for a specific song...")
        self.layout().addWidget(self.input)

        self.progressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setValue(0)
        self.layout().addWidget(self.progressBar)

        self.count = QtWidgets.QLabel(self)
        self.count.setText("Songs Found: 0")
        self.layout().addWidget(self.count)

        self.results = QtWidgets.QListWidget(self)
        self.results.setStyleSheet("color: white")
        self.layout().addWidget(self.results)

        self.input.returnPressed.connect(self.on_return)
        self.results.itemDoubleClicked.connect(self.on_item_double)
        self.worker = None

    def on_return(self):
        query = self.input.text().strip()
        if not query:
            return
        self.results.clear()
        self.progressBar.setValue(0)
        self.searchRequested.emit(query, self)

    def set_worker(self, worker):
        self.worker = worker

    def add_result(self, song_path):
        self.results.addItem(song_path)

    def on_search_finished(self):
        self.worker = None
        self.setWindowTitle("Find Song: " + str(self.results.count()))
        self.count.setText("Songs Found: " + str(self.results.count()))

    def on_item_double(self, item):
        self.songSelected.emit(item.text())
        self.accept()
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.parent = parent

        layout = QtWidgets.QVBoxLayout(self)

        vol_layout = QtWidgets.QHBoxLayout()
        vol_layout.addWidget(QtWidgets.QLabel("Volume:"))
        self.vol_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        try:
            self.vol_slider.setValue(self.parent.player.audio_get_volume())
        except:
            self.vol_slider.setValue(50)
        self.vol_slider.valueChanged.connect(self.on_volume_changed)
        vol_layout.addWidget(self.vol_slider)
        layout.addLayout(vol_layout)

        theme_layout = QtWidgets.QHBoxLayout()
        theme_layout.addWidget(QtWidgets.QLabel("Theme (not added yet):"))
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])

        current = "Dark" if self.parent.palette().color(QtGui.QPalette.Window) == QtGui.QColor("black") else "Light"
        self.theme_combo.setCurrentText(current)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        timer_layout = QtWidgets.QHBoxLayout()
        timer_layout.addWidget(QtWidgets.QLabel("Sleep timer (min):"))
        self.timer_spin = QtWidgets.QSpinBox()
        self.timer_spin.setRange(0, 120)
        timer_layout.addWidget(self.timer_spin)
        self.start_timer_btn = QtWidgets.QPushButton("Start")
        self.start_timer_btn.clicked.connect(self.on_start_timer)
        timer_layout.addWidget(self.start_timer_btn)
        layout.addLayout(timer_layout)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        btns.rejected.connect(self.accept)
        layout.addWidget(btns)

    def on_volume_changed(self, val):
        try:
            self.parent.player.audio_set_volume(val)
        except:
            pass

    def on_theme_changed(self, text):
        pal = QtGui.QPalette()
        if text == "Dark":
            pal.setColor(QtGui.QPalette.Window, QtGui.QColor("black"))
            pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor("white"))
        else:
            pal.setColor(QtGui.QPalette.Window, QtGui.QColor("white"))
            pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor("black"))
        QtWidgets.QApplication.instance().setPalette(pal)

    def on_start_timer(self):
        mins = self.timer_spin.value()
        if mins <= 0:
            return
        self.parent.start_sleep_timer(mins)
        QtWidgets.QMessageBox.information(self, "Sleep Timer", f"Player will stop in {mins} minutes.")
class VinylPlayer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Basically Spotify but Local LMAO")
        self.setWindowIcon(QtGui.QIcon(resource_path("icon.ico")))
        self.resize(1100, 600)
        self.is_paused = False
        self.current_tracks = []
        self.current_album_path = None
        self.repeat_mode = 0
        self.random_shuffle_active = False
        self.album_shuffle_active = False
        self.original_tracks = None
        self.current_song = ""
        self.playlists = {}  # managed by PlaylistShelf

        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.setCentralWidget(main_splitter)
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        self.searchBox = QtWidgets.QLineEdit()
        self.searchBox.setPlaceholderText("Search for albums or artists...")
        self.searchBox.textChanged.connect(self.filter_albums)
        left_layout.addWidget(self.searchBox)
        self.albumTree = AlbumTree(self)
        left_layout.addWidget(self.albumTree)
        main_splitter.addWidget(left_widget)

        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        top_right_widget = QtWidgets.QWidget()
        top_right_layout = QtWidgets.QVBoxLayout(top_right_widget)
        self.nowPlayingWidget = NowPlayingWidget(self)
        top_right_layout.addWidget(self.nowPlayingWidget)
        controls_layout = QtWidgets.QHBoxLayout()
        self.prev_button = QtWidgets.QPushButton()
        self.pause_button = QtWidgets.QPushButton()
        self.next_button = QtWidgets.QPushButton()
        self.prev_button.setIcon(QtGui.QIcon(resource_path("prev.png")))
        self.pause_button.setIcon(QtGui.QIcon(resource_path("paws.png")))
        self.next_button.setIcon(QtGui.QIcon(resource_path("next.png")))
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.next_button)
        controls_container = QtWidgets.QWidget()
        controls_container.setLayout(controls_layout)
        top_right_layout.addWidget(controls_container)
        mode_layout = QtWidgets.QHBoxLayout()
        self.randomShuffleButton = QtWidgets.QPushButton()
        self.albumShuffleButton = QtWidgets.QPushButton()
        self.repeatButton = QtWidgets.QPushButton()
        self.randomShuffleButton.setIcon(QtGui.QIcon(resource_path("plit.png")))
        self.randomShuffleButton.setToolTip("Random Shuffle: OFF")
        self.albumShuffleButton.setIcon(QtGui.QIcon(resource_path("shuf.png")))
        self.albumShuffleButton.setToolTip("Album Shuffle: OFF")
        self.repeatButton.setIcon(QtGui.QIcon(resource_path("RepX.png")))
        self.repeatButton.setToolTip("Repeat: OFF")
        mode_layout.addWidget(self.randomShuffleButton)
        mode_layout.addWidget(self.albumShuffleButton)
        mode_layout.addWidget(self.repeatButton)
        mode_container = QtWidgets.QWidget()
        mode_container.setLayout(mode_layout)
        top_right_layout.addWidget(mode_container)
        right_splitter.addWidget(top_right_widget)

        self.trackList = QtWidgets.QListWidget()
        self.trackList.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.trackList.itemDoubleClicked.connect(self.track_double_clicked)
        self.trackList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.trackList.customContextMenuRequested.connect(self.open_track_context_menu)
        right_splitter.addWidget(self.trackList)
        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)

        self.prev_button.clicked.connect(self.play_previous)
        self.next_button.clicked.connect(self.play_next)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.randomShuffleButton.clicked.connect(self.toggle_random_shuffle)
        self.albumShuffleButton.clicked.connect(self.toggle_album_shuffle)
        self.repeatButton.clicked.connect(self.cycle_repeat_mode)
        self.sliderPressed = False
        self.nowPlayingWidget.progressSlider.sliderPressed.connect(self.slider_pressed)
        self.nowPlayingWidget.progressSlider.sliderMoved.connect(self.slider_moved)
        self.nowPlayingWidget.progressSlider.sliderReleased.connect(self.slider_released)
        self.vlc_instance = vlc.Instance("--no-video")
        self.player = self.vlc_instance.media_player_new()
        self.media_list_player = vlc.MediaListPlayer()
        self.media_list = vlc.MediaList()
        self.media_list_player.set_media_player(self.player)
        self.media_list_player.set_media_list(self.media_list)
        self.current_album_cover = None

        # Lyrics dock
        self.lyricsWidget = LyricsWidget(self)
        self.lyricsWidget.timestampClicked.connect(self.seek_to)
        self.lyricsDock = QtWidgets.QDockWidget("Lyrics", self)
        self.lyricsDock.setWidget(self.lyricsWidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.lyricsDock)
        toggleLyricsAction = self.lyricsDock.toggleViewAction()
        self.menuBar().addAction(toggleLyricsAction)

        settingsAction = QtWidgets.QAction("Settings", self)
        settingsAction.triggered.connect(self.open_settings_dialog)
        self.menuBar().addAction(settingsAction)

        # Shortcuts
        self.searchShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        self.searchShortcut.activated.connect(self.open_search_dialog)
        self.searchShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("X"), self)
        self.searchShortcut.activated.connect(self.toggle_pause)
        self.searchShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Z"), self)
        self.searchShortcut.activated.connect(self.play_previous)
        self.searchShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("C"), self)
        self.searchShortcut.activated.connect(self.play_next)
        self.searchShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("R"), self)
        self.searchShortcut.activated.connect(self.cycle_repeat_mode)
        self.searchShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("S"), self)
        self.searchShortcut.activated.connect(self.toggle_album_shuffle)
        self.searchShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("T"), self)
        self.searchShortcut.activated.connect(self.toggle_random_shuffle)

        # Playlist shelf dock
        #self.playlistShelf = PlaylistShelf(self)
        #self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.playlistShelf)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_now_playing)
        self.timer.start()


    def _row_to_track_index(self, row):
        count = -1
        for r in range(self.trackList.count()):
            item = self.trackList.item(r)
            if item.flags() & QtCore.Qt.ItemIsSelectable:
                count += 1
            if r == row:
                return count
        return None

    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        dlg.exec_()

    def start_sleep_timer(self, minutes):
        # Cancel any existing sleep timer
        try:
            self._sleep_timer.stop()
        except:
            pass

        # Compute end time
        self._sleep_end = datetime.datetime.now() + datetime.timedelta(minutes=minutes)

        # Create a QTimer that fires every second to update title
        self._sleep_timer = QtCore.QTimer(self)
        self._sleep_timer.setInterval(1000)
        self._sleep_timer.timeout.connect(self._update_sleep_countdown)
        self._sleep_timer.start()

    def _update_sleep_countdown(self):
        remaining = self._sleep_end - datetime.datetime.now()
        if remaining.total_seconds() <= 0:
            self._sleep_timer.stop()
            self.toggle_pause()
            self.setWindowTitle("Basically Spotify but Local LMAO")
        else:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            self.setWindowTitle(f"Sleeping in {mins:02}:{secs:02}")
    def open_search_dialog(self):
        dlg = SearchSongDialog(self)
        dlg.searchRequested.connect(self.start_song_search)
        dlg.songSelected.connect(self.play_found_song)
        dlg.exec_()

    def start_song_search(self, query, dialog):
        worker = SearchWorker("./Tracks", query)
        worker.progress.connect(dialog.progressBar.setValue)
        worker.result.connect(partial(dialog.add_result))
        worker.finished.connect(dialog.on_search_finished)
        dialog.set_worker(worker)
        worker.start()

    def play_found_song(self, song_path):
        album_path, filename = os.path.split(song_path)
        if album_path != self.current_album_path:
            self.play_album(album_path)
        if filename in self.current_tracks:
            idx = self.current_tracks.index(filename)
            self.media_list_player.play_item_at_index(idx)
    def seek_to(self, ms_timestamp: int):
        if hasattr(self, 'player') and self.player:
            self.player.set_time(ms_timestamp)

            length = self.player.get_length()
            if length > 0:
                pos = int((ms_timestamp / length) * 100)
                self.nowPlayingWidget.progressSlider.setValue(pos)
    def filter_albums(self, text):
        self.albumTree.filter_albums(text)
    def slider_pressed(self):
        self.sliderPressed = True
    def slider_moved(self, position):
        self.sliderPressed = True
        total = self.player.get_length()
        if total > 0:
            total_str = ms_to_mmss(total)
            new_time = int((position / 1000) * total)
            current_str = ms_to_mmss(new_time)
            self.nowPlayingWidget.timeLabel.setText(f"{current_str} / {total_str}")
    def slider_released(self):
        self.sliderPressed = False
        total = self.player.get_length()
        if total > 0:
            slider_value = self.nowPlayingWidget.progressSlider.value()
            new_time = int((slider_value / 100) * total)
            print(f"[DEBUG] slider_released: Setting player time to {new_time} ms")
            self.player.set_time(new_time)
    def extract_cover(self, song_path):
        print(f"[DEBUG] extract_cover: Checking ID3 tags for: {song_path}")
        try:
            audio = ID3(song_path)
            for tag in audio.values():
                if isinstance(tag, APIC):
                    cover_data = tag.data
                    pixmap = QtGui.QPixmap()
                    if pixmap.loadFromData(cover_data):
                        print("[DEBUG] extract_cover: Found embedded cover art.")
                        return pixmap
        except Exception as e:
            print("[DEBUG] extract_cover: Exception:", e)
        print("[DEBUG] extract_cover: No cover found.")
        return None
    def update_background_from_cover(self):
        if self.current_album_cover:
            small = self.current_album_cover.scaled(1, 1, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
            avg_color = QtGui.QColor(small.toImage().pixel(0, 0))
            self.text_color = get_contrasting_color(avg_color)
            album_bg = get_contrasting_color(avg_color).name()
            self.current_bg_color = avg_color
            self.current_text_color = self.text_color

            palette = self.palette()
            palette.setColor(QtGui.QPalette.Window, avg_color)
            palette.setColor(QtGui.QPalette.WindowText, self.text_color)
            self.setPalette(palette)

            self.nowPlayingWidget.songLabel.setStyleSheet(f"color: {self.text_color.name()};")
            self.nowPlayingWidget.timeLabel.setStyleSheet(f"color: {self.text_color.name()};")
            self.nowPlayingWidget.coverLabel.setStyleSheet(f"color: {self.text_color.name()};")
            self.nowPlayingWidget.albumLabel.setStyleSheet(f"color: {self.text_color.name()};")
            self.nowPlayingWidget.artistLabel.setStyleSheet(f"color: {self.text_color.name()};")
            self.trackList.setStyleSheet(f"background-color: {avg_color.name()}; color: {self.text_color.name()};")
            if hasattr(self, 'playlistShelf'):
                self.playlistShelf.playlistList.setStyleSheet(f"background-color: {avg_color.name()}; color: {self.text_color.name()};")
                self.playlistShelf.songList.setStyleSheet(f"background-color: {avg_color.name()}; color: {self.text_color.name()};")
            self.lyricsWidget.setStyleSheet(f"background-color: transparent; color: {self.text_color.name()};")
    def play_album(self, album_path, start_index=0):
        print(f"[DEBUG] play_album: Attempting to play album at {album_path}")
        audio_files = [f for f in os.listdir(album_path) if f.lower().endswith(SUPPORTED_FORMATS)]
        if not audio_files:
            print("[DEBUG] play_album: No supported audio files found in that album.")
            QtWidgets.QMessageBox.warning(self, "No songs", "No supported audio files found in this album.")
            return

        sorted_files = sorted(audio_files, key=natural_sort_key)
        self.current_album_path = album_path

        # set cover and labels from first track
        first_song = sorted_files[0]
        song_path = os.path.join(album_path, first_song)
        print(f"[DEBUG] play_album: first_song = {first_song}")
        self.current_album_cover = self.extract_cover(song_path)
        if self.current_album_cover:
            scaled = self.current_album_cover.scaled(
                self.nowPlayingWidget.coverLabel.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.nowPlayingWidget.coverLabel.setPixmap(scaled)
        else:
            self.nowPlayingWidget.coverLabel.setPixmap(QtGui.QPixmap(resource_path("imag.png")))
        tag: TinyTag = TinyTag.get(song_path)
        self.nowPlayingWidget.albumLabel.setText(tag.album)
        self.nowPlayingWidget.artistLabel.setText(tag.artist)
        self.update_background_from_cover()

        # Initialize media list and clear track list for grouped display
        self.media_list = vlc.MediaList()
        self.media_list_player.set_media_list(self.media_list)
        self.trackList.clear()

        # Group tracks by disc based on 'Part of set' (disc) metadata
        self.track_item_rows = []
        # Helper to build a clean title
        def build_title(full_path, tag_info):
            # strip extension, take basename
            name = os.path.splitext(os.path.basename(full_path))[0]
            m = re.match(r'(\d+)\.\s*(.*)', name)
            if m:
                track_num, fallback = m.groups()
                display_title = tag_info.title or fallback
                return f"{track_num}. {display_title}"
            else:
                # no leading "01. ", just show tag title or file name
                return tag_info.title or name
        disc_groups = {}
        for f in sorted_files:
            full_path = os.path.join(album_path, f)
            tag_info = TinyTag.get(full_path)
            # TinyTag.disc should be an int if present
            disc_no = tag_info.disc if tag_info.disc and isinstance(tag_info.disc, int) else 1
            disc_groups.setdefault(disc_no, []).append((f, tag_info))

        # Flatten tracks and populate media list and trackList with disc headings
        flat_tracks = []
        #print(sorted(disc_groups.keys()))
        if sorted(disc_groups.keys()) == [1]:
            for disc_no in sorted(disc_groups.keys()):
                # Add non-selectable disc heading
                heading_item = QtWidgets.QListWidgetItem(f"Disc {disc_no}")
                iconpixmap = QtGui.QPixmap(resource_path("disc.png"))
                iconpixmapMASK = iconpixmap.createMaskFromColor(QtGui.QColor("black"), QtCore.Qt.MaskMode.MaskOutColor)
                iconpixmap.fill(QtGui.QColor(QtGui.QColor(self.text_color.name())))
                iconpixmap.setMask(iconpixmapMASK)
                heading_item.setIcon(QtGui.QIcon(iconpixmap))
                #heading_item.setIcon(QtGui.QIcon(resource_path("disc.png")))
                heading_item.setBackground(get_contrasting_color((QtGui.QColor(self.text_color.name()))))

                heading_item.setFlags(heading_item.flags() & ~QtCore.Qt.ItemIsSelectable)
                #self.trackList.addItem(heading_item)
                for f, tag_info in disc_groups[disc_no]:
                    # full_path = os.path.join(album_path, f)
                    # media = self.vlc_instance.media_new(os.path.abspath(full_path))
                    # self.media_list.add_media(media)
                    # title = f"{f+1}. {tag_info.title}" if tag_info.title else f
                    # item = QtWidgets.QListWidgetItem(title)
                    # self.trackList.addItem(item)

                    full_path = os.path.join(album_path, f)
                    media = self.vlc_instance.media_new(os.path.abspath(full_path))
                    self.media_list.add_media(media)
                    flat_tracks.append(f)
                    # Display track title
                    # Helper to build a clean title
                    title = build_title(full_path, tag_info)
                    #title = f"{str(full_path).split(". ")[0].split("\\")[3]}. {tag_info.title}" if tag_info.title else f"{str(full_path).split(". ")[0]}. {tag_info.title}"
                    item = QtWidgets.QListWidgetItem(title)
                    self.trackList.addItem(item)

                    # Update current_tracks to the new flattened order
                    self.current_tracks = flat_tracks
        else:
            for disc_no in sorted(disc_groups.keys()):
                # Add non-selectable disc heading
                heading_item = QtWidgets.QListWidgetItem(f"Disc {disc_no}")
                iconpixmap = QtGui.QPixmap(resource_path("disc.png"))
                iconpixmapMASK = iconpixmap.createMaskFromColor(QtGui.QColor("black"), QtCore.Qt.MaskMode.MaskOutColor)
                iconpixmap.fill(QtGui.QColor(QtGui.QColor(self.text_color.name())))
                iconpixmap.setMask(iconpixmapMASK)
                heading_item.setIcon(QtGui.QIcon(iconpixmap))
                #heading_item.setIcon(QtGui.QIcon(resource_path("disc.png")))
                heading_item.setBackground(get_contrasting_color((QtGui.QColor(self.text_color.name()))))

                heading_item.setFlags(heading_item.flags() & ~QtCore.Qt.ItemIsSelectable)
                self.trackList.addItem(heading_item)
                for f, tag_info in disc_groups[disc_no]:
                    full_path = os.path.join(album_path, f)
                    media = self.vlc_instance.media_new(os.path.abspath(full_path))
                    self.media_list.add_media(media)
                    flat_tracks.append(f)
                    # Display track title
                    title = f"{str(full_path).split(". ")[0].split("\\")[3]}. {tag_info.title}" if tag_info.title else f"{str(full_path).split(". ")[0]}. {tag_info.title}"
                    item = QtWidgets.QListWidgetItem(title)
                    self.trackList.addItem(item)

                    # Update current_tracks to the new flattened order
                    self.current_tracks = flat_tracks

        # Start playback
        self.media_list_player.play_item_at_index(start_index)
        self.is_paused = False
        self.pause_button.setIcon(QtGui.QIcon(resource_path("paws.png")))
        self.pause_button.setToolTip("Pause")
        self.nowPlayingWidget.progressSlider.setEnabled(True)
        self.random_shuffle_active = False
        try:
            base, ext = os.path.splitext(song_path)
        except:
            pass
        lrc_file = base + ".lrc"
        print(f"[DEBUG] play_album: Looking for LRC file at {lrc_file}")
        self.lyricsWidget.load_lyrics(lrc_file)
        self.current_song = os.path.basename(song_path)

    def track_double_clicked(self, item):
        row = self.trackList.row(item)
        print(f"[DEBUG] track_double_clicked: row={row}")
        track_idx = self._row_to_track_index(row)
        if track_idx is not None:
            self.media_list_player.play_item_at_index(track_idx)
    def play_next(self):
        print("[DEBUG] play_next clicked.")
        self.media_list_player.next()
        if self.is_paused == True:
            self.is_paused = not self.is_paused
            self.pause_button.setIcon(QtGui.QIcon(resource_path("paws.png")))
            self.pause_button.setToolTip("Pause")
    def play_previous(self):
        print("[DEBUG] play_previous clicked.")
        self.media_list_player.previous()
        if self.is_paused == True:
            self.is_paused = not self.is_paused
            self.pause_button.setIcon(QtGui.QIcon(resource_path("paws.png")))
            self.pause_button.setToolTip("Pause")
    def toggle_pause(self):
        print("[DEBUG] toggle_pause clicked.")
        self.media_list_player.pause()
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.setIcon(QtGui.QIcon(resource_path("play.png")))
            self.pause_button.setToolTip("Play")
        else:
            self.pause_button.setIcon(QtGui.QIcon(resource_path("paws.png")))
            self.pause_button.setToolTip("Pause")
    def update_now_playing(self):
        length = self.player.get_length()
        current_time = self.player.get_time()
        print(f"[DEBUG] update_now_playing: length={length}, current_time={current_time}")
        if not self.sliderPressed and length > 0:
            progress = int((current_time / length) * 100)
            self.nowPlayingWidget.progressSlider.setValue(progress)
            total_str = ms_to_mmss(length)
            current_str = ms_to_mmss(current_time)
            self.nowPlayingWidget.timeLabel.setText(f"{current_str} / {total_str}")
        media = self.player.get_media()
        if media:
            mrl = media.get_mrl()
            decoded = urllib.parse.unquote(mrl)
            if decoded.startswith("file://"):
                local_path = decoded.replace("file:///", "")
                decoded = local_path
            song_name = os.path.basename(decoded)
            tag: TinyTag = TinyTag.get(decoded)
            self.nowPlayingWidget.songLabel.setText(tag.title)
            if not hasattr(self, "current_song") or self.current_song != song_name:
                self.current_song = song_name
                base, ext = os.path.splitext(decoded)
                lrc_file = base + ".lrc"
                print(f"[DEBUG] update_now_playing: New song detected. Loading lyrics from {lrc_file}")
                self.lyricsWidget.load_lyrics(lrc_file)
            current_base = os.path.splitext(song_name)[0]
            for i, track in enumerate(self.current_tracks):
                for flat_idx, track in enumerate(self.current_tracks):
                    if os.path.splitext(track)[0] == current_base:
                        #selectable_row = self._row_to_track_index(flat_idx if False else None)
                        sel_rows = [
                            r for r in range(self.trackList.count())
                            if self.trackList.item(r).flags() & QtCore.Qt.ItemIsSelectable
                        ]
                        if flat_idx < len(sel_rows):
                            self.trackList.setCurrentRow(sel_rows[flat_idx])
                        break

        else:
            self.nowPlayingWidget.songLabel.setText("Drop Album Here")
            self.nowPlayingWidget.albumLabel.setText("")
            self.nowPlayingWidget.artistLabel.setText("")
        if hasattr(self, "lyricsWidget"):
            self.lyricsWidget.update_display(current_time)
    def toggle_random_shuffle(self):
        print("[DEBUG] toggle_random_shuffle clicked.")
        if not self.random_shuffle_active:
            song_list = []
            for root, dirs, files in os.walk("./Tracks"):
                for f in files:
                    if f.lower().endswith(SUPPORTED_FORMATS):
                        song_list.append((root, f))
            if not song_list:
                print("[DEBUG] No songs found for random shuffle.")
                return
            random.shuffle(song_list)
            self.random_shuffle_active = True
            self.album_shuffle_active = False
            self.randomShuffleButton.setIcon(QtGui.QIcon(resource_path("plit_green.png")))
            self.randomShuffleButton.setToolTip("Random Shuffle: ON")
            self.albumShuffleButton.setIcon(QtGui.QIcon(resource_path("shuf.png")))
            self.albumShuffleButton.setToolTip("Album Shuffle: OFF")
            album_path, filename = song_list[0]
            print(f"[DEBUG] toggle_random_shuffle: random album={album_path}, track={filename}")
            self.play_album(album_path)
            sorted_files = sorted([f for f in os.listdir(album_path) if f.lower().endswith(SUPPORTED_FORMATS)], key=natural_sort_key)
            try:
                index = sorted_files.index(filename)
            except ValueError:
                index = 0
            self.media_list_player.play_item_at_index(index)
        else:
            self.random_shuffle_active = False
            self.randomShuffleButton.setIcon(QtGui.QIcon(resource_path("plit.png")))
            self.randomShuffleButton.setToolTip("Random Shuffle: OFF")
    def toggle_album_shuffle(self):
        print("[DEBUG] toggle_album_shuffle clicked.")
        if self.current_album_path is None or not self.current_tracks:
            print("[DEBUG] No current album or tracks to shuffle.")
            return
        if not self.album_shuffle_active:
            self.album_shuffle_active = True
            self.albumShuffleButton.setIcon(QtGui.QIcon(resource_path("shuf_green.png")))
            self.albumShuffleButton.setToolTip("Album Shuffle: ON")
            self.original_tracks = list(self.current_tracks)
            shuffled = self.original_tracks[:]
            random.shuffle(shuffled)
            self.current_tracks = shuffled
            self.media_list = vlc.MediaList()
            for f in self.current_tracks:
                full_path = os.path.join(self.current_album_path, f)
                media = self.vlc_instance.media_new(os.path.abspath(full_path))
                self.media_list.add_media(media)
            self.media_list_player.set_media_list(self.media_list)
            self.trackList.clear()
            for index, f in enumerate(self.current_tracks):
                tag: TinyTag = TinyTag.get(os.path.join(self.current_album_path, f))
                item = QtWidgets.QListWidgetItem(f"{index+1}. {tag.title}")
                self.trackList.addItem(item)
            self.media_list_player.play_item_at_index(0)
        else:
            self.album_shuffle_active = False
            self.albumShuffleButton.setIcon(QtGui.QIcon(resource_path("shuf.png")))
            self.albumShuffleButton.setToolTip("Album Shuffle: OFF")
            if self.original_tracks:
                self.current_tracks = self.original_tracks
                self.media_list = vlc.MediaList()
                for f in self.current_tracks:
                    full_path = os.path.join(self.current_album_path, f)
                    media = self.vlc_instance.media_new(os.path.abspath(full_path))
                    self.media_list.add_media(media)
                self.media_list_player.set_media_list(self.media_list)
                self.trackList.clear()
                for index, f in enumerate(self.current_tracks):
                    tag: TinyTag = TinyTag.get(os.path.join(self.current_album_path, f))
                    item = QtWidgets.QListWidgetItem(f"{index+1}. {tag.title}")
                    self.trackList.addItem(item)
                self.media_list_player.play_item_at_index(0)
    def cycle_repeat_mode(self):
        print("[DEBUG] cycle_repeat_mode clicked.")
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == 0:
            self.media_list_player.set_playback_mode(vlc.PlaybackMode.default)
            self.repeatButton.setIcon(QtGui.QIcon(resource_path("RepX.png")))
            self.repeatButton.setToolTip("Repeat: OFF")
        elif self.repeat_mode == 1:
            self.media_list_player.set_playback_mode(vlc.PlaybackMode.loop)
            self.repeatButton.setIcon(QtGui.QIcon(resource_path("rept.png")))
            self.repeatButton.setToolTip("Repeat Album: ON")
        elif self.repeat_mode == 2:
            self.media_list_player.set_playback_mode(vlc.PlaybackMode.repeat)
            self.repeatButton.setIcon(QtGui.QIcon(resource_path("repA.png")))
            self.repeatButton.setToolTip("Repeat Track: ON")
    def open_track_context_menu(self, position):
        menu = QtWidgets.QMenu()
        if hasattr(self, 'current_bg_color') and hasattr(self, 'current_text_color'):
            menu.setStyleSheet(f"background-color: {self.current_bg_color.name()}; color: {self.current_text_color.name()};")
        addToPlaylistMenu = menu.addMenu("Add to Playlist")
        if self.playlistShelf.playlistList.count() > 0:
            for i in range(self.playlistShelf.playlistList.count()):
                playlist_name = self.playlistShelf.playlistList.item(i).text()
                addToPlaylistMenu.addAction(playlist_name)
            addToPlaylistMenu.addSeparator()
            addToPlaylistMenu.addAction("New Playlist...")
        else:
            addToPlaylistMenu.setEnabled(False)
        action = menu.exec_(self.trackList.viewport().mapToGlobal(position))
        if action:
            if action.text() == "New Playlist...":
                self.playlistShelf.create_playlist()
            else:
                current_item = self.trackList.currentItem()
                if current_item:
                    row = self.trackList.row(current_item)
                    song_file = self.current_tracks[row]
                    song_path = os.path.join(self.current_album_path, song_file) if self.current_album_path else song_file
                    self.playlistShelf.add_song_to_playlist(song_path, action.text())
    def play_playlist(self, playlist_name):
        songs = self.playlistShelf.playlists.get(playlist_name, [])
        if not songs:
            QtWidgets.QMessageBox.information(self, "Empty Playlist", "This playlist is empty.")
            return
        self.media_list = vlc.MediaList()
        for song_path in songs:
            media = self.vlc_instance.media_new(os.path.abspath(song_path))
            self.media_list.add_media(media)
        self.media_list_player.set_media_list(self.media_list)
        self.nowPlayingWidget.albumLabel.setText(playlist_name)
        self.trackList.clear()
        self.current_tracks = songs[:]
        for index, song_path in enumerate(songs):
            tag = TinyTag.get(song_path)
            item = QtWidgets.QListWidgetItem(f"{index+1}. {tag.title}")
            self.trackList.addItem(item)
        first_song = songs[0]
        self.current_album_cover = self.extract_cover(first_song)
        if self.current_album_cover:
            scaled = self.current_album_cover.scaled(
                self.nowPlayingWidget.coverLabel.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.nowPlayingWidget.coverLabel.setPixmap(scaled)
        else:
            self.nowPlayingWidget.coverLabel.setPixmap(QtGui.QPixmap(resource_path("imag.png")))
        base, ext = os.path.splitext(first_song)
        lrc_file = base + ".lrc"
        self.lyricsWidget.load_lyrics(lrc_file)
        self.current_album_path = ""
        self.media_list_player.play_item_at_index(0)
class IndexerWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(list)

    def __init__(self, tracks_folder):
        super().__init__()
        self.tracks_folder = tracks_folder

    def run(self):
        albums = []
        if not os.path.exists(self.tracks_folder):
            self.log.emit("Tracks directory not found.")
            self.finished.emit(albums)
            return

        try:
            artists = sorted(os.listdir(self.tracks_folder), key=natural_sort_key)
        except Exception as e:
            self.log.emit(f"Error listing tracks folder: {e}")
            self.finished.emit(albums)
            return

        total_artists = len(artists)
        self.log.emit("Starting indexing...")
        for i, artist in enumerate(artists):
            artist_path = os.path.join(self.tracks_folder, artist)
            if not os.path.isdir(artist_path):
                continue

            try:
                albums_in_artist = sorted(os.listdir(artist_path), key=natural_sort_key)
            except Exception as e:
                self.log.emit(f"{artist}: error listing albums: {e}")
                continue

            artist_album_logs = []
            for album in albums_in_artist:
                album_path = os.path.join(artist_path, album)
                if not os.path.isdir(album_path):
                    continue
                try:
                    audio_files = [f for f in os.listdir(album_path) if f.lower().endswith(SUPPORTED_FORMATS)]
                except Exception as e:
                    self.log.emit(f"{artist} - {album}: error listing files: {e}")
                    continue
                if audio_files:
                    first_audio = sorted(audio_files, key=natural_sort_key)[0]
                    albums.append((artist, album, album_path, first_audio))
                    artist_album_logs.append(album)
            if artist_album_logs:
                self.log.emit(f"{artist}: indexed albums -> " + ", ".join(artist_album_logs))
            else:
                self.log.emit(f"{artist}: no valid albums found.")
            self.log.emit(f"Finished artist {artist} ({i+1}/{total_artists})")
            self.msleep(10)
        self.finished.emit(albums)
class ManagerCursor(QtCore.QObject): #https://stackoverflow.com/questions/55455881/is-there-a-way-to-create-a-custom-animated-gif-qcursor
    def __init__(self, parent=None):
        super(ManagerCursor, self).__init__(parent)
        self._movie = None
        self._widget = None
        self._last_cursor = None

    def setMovie(self, movie):
        if isinstance(self._movie, QtGui.QMovie):
            if not self._movie != QtGui.QMovie.NotRunning:
                self._movie.stop()
            del self._movie
        self._movie = movie
        self._movie.frameChanged.connect(self.on_frameChanged)
        self._movie.started.connect(self.on_started)
        self._movie.finished.connect(self.restore_cursor)

    def setWidget(self, widget):
         self._widget = widget

    @QtCore.pyqtSlot()
    def on_started(self):
        if self._widget is not None:
            self._last_cursor = self._widget.cursor()

    @QtCore.pyqtSlot()
    def restore_cursor(self):
        if self._widget is not None:
            if self._last_cursor is not None:
                self._widget.setCursor(self._last_cursor)
        self._last_cursor = None

    @QtCore.pyqtSlot()
    def start(self):
        if self._movie is not None:
            self._movie.start()

    @QtCore.pyqtSlot()
    def stop(self):
        if self._movie is not None:
            self._movie.stop()
            self.restore_cursor()

    @QtCore.pyqtSlot()
    def on_frameChanged(self):
        pixmap = self._movie.currentPixmap()
        cursor = QtGui.QCursor(pixmap)
        if self._widget is not None:
            if self._last_cursor is None:
                self._last_cursor = self._widget.cursor()
            self._widget.setCursor(cursor)
class LogSplashScreen(QtWidgets.QWidget):
    start_indexing = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__(None, QtCore.Qt.FramelessWindowHint)


        self.setFixedSize(500, 400)
        self.setStyleSheet("background-color: black; color: white;")
        layout = QtWidgets.QVBoxLayout(self)
        folderLayout = QtWidgets.QHBoxLayout()
        self.folderLineEdit = QtWidgets.QLineEdit("./Tracks", self)
        folderLayout.addWidget(self.folderLineEdit)
        browseButton = QtWidgets.QPushButton("Browse", self)
        browseButton.clicked.connect(self.browse_folder)
        folderLayout.addWidget(browseButton)
        layout.addLayout(folderLayout)
        self.startButton = QtWidgets.QPushButton("Start Indexing", self)
        self.startButton.clicked.connect(self.emit_start_indexing)
        layout.addWidget(self.startButton)
        self.logOutput = QtWidgets.QTextEdit(self)
        self.logOutput.setReadOnly(True)
        self.logOutput.setStyleSheet("background-color: black; color: white;")
        layout.addWidget(self.logOutput)

        self._manager = ManagerCursor(self)
        movie = QtGui.QMovie(resource_path("spinner32.gif"))
        self._manager.setMovie(movie)
        self._manager.setWidget(self)

    def browse_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Tracks Folder", self.folderLineEdit.text())
        if folder:
            self.folderLineEdit.setText(folder)

    def emit_start_indexing(self):
        self._manager.start()
        self.startButton.setEnabled(False)
        self.folderLineEdit.setEnabled(False)
        self.start_indexing.emit(self.folderLineEdit.text())

    def append_log(self, message):
        self.logOutput.append(message)
        self.logOutput.verticalScrollBar().setValue(self.logOutput.verticalScrollBar().maximum())
# Global variable to hold the main window so it isn't garbage collected.
MAIN_WINDOW = None
INDEXER_WORKER = None
def on_start_indexing(tracks_folder):
    global INDEXER_WORKER
    INDEXER_WORKER = IndexerWorker(tracks_folder)
    INDEXER_WORKER.log.connect(splash.append_log)

    def finished_handler(albums):
        global INDEXER_WORKER
        INDEXER_WORKER.deleteLater()
        INDEXER_WORKER = None
        notifier = CoverArtTaskNotifier()
        notifier.finished.connect(cover_finished)
        notifier.log.connect(splash.append_log)
        task = CoverArtExtractionTask(albums, notifier)
        QtCore.QThreadPool.globalInstance().start(task)

    def cover_finished(enriched_albums):
        global MAIN_WINDOW
        MAIN_WINDOW = VinylPlayer()
        MAIN_WINDOW.albumTree.populate_albums_data(enriched_albums)
        splash.close()
        MAIN_WINDOW.show()

    INDEXER_WORKER.finished.connect(finished_handler)
    INDEXER_WORKER.start()
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor("black"))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("white"))
    # ——— Load Spotify‑style theme ———
    #qss_path = resource_path("spotify.qss")
    #if os.path.exists(qss_path):
    #    with open(qss_path, "r", encoding="utf-8") as f:
    #        app.setStyleSheet(f.read())
    #else:
    #    print(f"[WARNING] spotify.qss not found at {qss_path}")
    app.setPalette(palette)
    app.setStyleSheet("""
        QSlider::groove:horizontal { border: 1px solid #999; height: 8px; background: #333; margin: 2px 0; }
        QSlider::handle:horizontal { background: white; border: 1px solid #777; width: 18px; margin: -2px 0; border-radius: 3px; }
        QListWidget { background-color: #111; border: none; }
        QScrollBar:vertical { background: #111; width: 12px; margin: 0px; border: none; }
        QScrollBar::handle:vertical { background: #444; min-height: 20px; border: none; border-radius: 4px; }
        QDockWidget { titlebar-close-icon: url(close.png); titlebar-normal-icon: url(undock.png); }
    """)
    splash = LogSplashScreen()
    splash.show()
    splash.start_indexing.connect(on_start_indexing)
    sys.exit(app.exec_())
