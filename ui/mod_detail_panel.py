import html
import os
import re

from PySide6.QtCore import QByteArray, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget

from core.i18n import tr
from ui.workers import PreviewImageThread


ALLOWED_EXTERNAL_LINK_SCHEMES = {"http", "https"}


def is_safe_external_link(url) -> bool:
    candidate = QUrl(url)
    return bool(
        candidate.isValid()
        and candidate.scheme().lower() in ALLOWED_EXTERNAL_LINK_SCHEMES
        and candidate.host()
    )


class ModDetailPanel(QWidget):
    """Panel showing details of selected mod."""

    def __init__(self):
        super().__init__()
        self.current_mod_data = None
        self.current_preview_url = None
        self.preview_threads = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(360, 270)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        self.preview_label.setText(tr("no_preview_available"))
        layout.addWidget(self.preview_label)

        layout.addSpacing(8)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        self.title_label = QLabel(tr("select_mod_to_view_details"))
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.title_label)

        self.author_label = QLabel("")
        info_layout.addWidget(self.author_label)

        self.file_size_label = QLabel("")
        info_layout.addWidget(self.file_size_label)

        self.last_update_label = QLabel("")
        info_layout.addWidget(self.last_update_label)

        self.last_download_label = QLabel("")
        info_layout.addWidget(self.last_download_label)

        workshop_url_container = QVBoxLayout()
        workshop_url_container.setSpacing(2)
        workshop_url_label_title = QLabel(tr("label_workshop_url"))
        workshop_url_label_title.setStyleSheet("font-weight: bold;")
        workshop_url_container.addWidget(workshop_url_label_title)

        self.workshop_url_label = QLabel("")
        self.workshop_url_label.setOpenExternalLinks(True)
        self.workshop_url_label.setStyleSheet("color: blue; text-decoration: underline;")
        self.workshop_url_label.setWordWrap(True)
        self.workshop_url_label.linkActivated.connect(self.open_workshop_url_from_signal)
        workshop_url_container.addWidget(self.workshop_url_label)
        info_layout.addLayout(workshop_url_container)

        file_path_container = QVBoxLayout()
        file_path_container.setSpacing(2)
        file_path_label_title = QLabel(tr("label_file_path"))
        file_path_label_title.setStyleSheet("font-weight: bold;")
        file_path_container.addWidget(file_path_label_title)

        self.file_path_label = QLabel("")
        self.file_path_label.setStyleSheet("color: blue; text-decoration: underline;")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setOpenExternalLinks(True)
        self.file_path_label.linkActivated.connect(self.open_mod_folder_from_signal)
        file_path_container.addWidget(self.file_path_label)
        info_layout.addLayout(file_path_container)

        layout.addLayout(info_layout)

        layout.addSpacing(5)

        desc_label = QLabel(tr("label_description"))
        desc_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(desc_label)

        self.description_text = QTextBrowser()
        self.description_text.setReadOnly(True)
        self.description_text.setOpenLinks(False)
        self.description_text.setOpenExternalLinks(False)
        self.description_text.anchorClicked.connect(self.open_description_link)
        self.description_text.setMinimumHeight(80)
        layout.addWidget(self.description_text)

        self.setLayout(layout)

    def update_mod_details(self, mod_data):
        if not mod_data:
            self.clear_details()
            return

        self.current_mod_data = mod_data
        self.title_label.setText(mod_data.get("title") or tr("unknown_mod"))

        creator = mod_data.get("creator")
        if creator:
            self.author_label.setText(tr("label_author").format(creator=creator))
        else:
            self.author_label.setText(tr("label_author_unknown"))

        file_size = mod_data.get("file_size")
        if file_size:
            size_mb = file_size / (1024 * 1024)
            self.file_size_label.setText(tr("label_size").format(size=size_mb))
        else:
            content_path = mod_data.get("content_path")
            if content_path and os.path.exists(content_path):
                try:
                    total_size = 0
                    for dirpath, _dirnames, filenames in os.walk(content_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            total_size += os.path.getsize(filepath)
                    size_mb = total_size / (1024 * 1024)
                    self.file_size_label.setText(tr("label_size").format(size=size_mb))
                except Exception:
                    self.file_size_label.setText(tr("label_size_unknown"))
            else:
                self.file_size_label.setText(tr("label_size_unknown"))

        remote_updated = mod_data.get("remote_updated_at")
        if remote_updated:
            from datetime import datetime
            dt = datetime.fromtimestamp(remote_updated)
            self.last_update_label.setText(
                tr("label_last_workshop_update").format(timestamp=dt.strftime("%Y-%m-%d %H:%M"))
            )
        else:
            self.last_update_label.setText(tr("label_last_workshop_update_unknown"))

        last_downloaded = mod_data.get("last_downloaded_at")
        if last_downloaded:
            from datetime import datetime
            dt = datetime.fromtimestamp(last_downloaded)
            self.last_download_label.setText(
                tr("label_last_downloaded").format(timestamp=dt.strftime("%Y-%m-%d %H:%M"))
            )
        else:
            self.last_download_label.setText(tr("label_last_downloaded_never"))

        workshop_id = mod_data.get("workshop_id")
        if workshop_id:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}"
            self.workshop_url_label.setText(f'<a href="{url}">{url}</a>')
        else:
            self.workshop_url_label.setText(tr("no_workshop_url_available"))

        content_path = mod_data.get("content_path")
        if content_path:
            file_url = QUrl.fromLocalFile(content_path).toString()
            self.file_path_label.setText(f'<a href="{file_url}">{content_path}</a>')
        else:
            self.file_path_label.setText(tr("no_local_files"))

        description = mod_data.get("description")
        if description:
            self.description_text.setHtml(self.format_description_html(description))
        else:
            self.description_text.setPlainText(tr("no_description_available"))

        preview_url = mod_data.get("preview_url")
        if preview_url:
            self.load_preview_image(preview_url)
        else:
            self.current_preview_url = None
            self.preview_label.clear()
            self.preview_label.setText(tr("no_preview_available"))

    def load_preview_image(self, preview_url):
        self.current_preview_url = preview_url
        self.preview_label.clear()
        self.preview_label.setText(tr("loading_preview"))

        worker = PreviewImageThread(preview_url)

        def on_loaded(url, image_data):
            if url != self.current_preview_url:
                return
            pixmap = QPixmap()
            if pixmap.loadFromData(QByteArray(image_data)):
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText(tr("preview_unavailable"))

        def on_failed(url, _error):
            if url == self.current_preview_url:
                self.preview_label.setText(tr("preview_unavailable"))

        def cleanup():
            try:
                self.preview_threads.remove(worker)
            except ValueError:
                pass

        worker.image_loaded.connect(on_loaded)
        worker.load_failed.connect(on_failed)
        worker.finished.connect(cleanup)
        self.preview_threads.append(worker)
        worker.start()

    def clear_details(self):
        self.current_mod_data = None
        self.current_preview_url = None
        self.title_label.setText(tr("select_mod_to_view_details"))
        self.author_label.setText("")
        self.file_size_label.setText("")
        self.last_update_label.setText("")
        self.last_download_label.setText("")
        self.workshop_url_label.setText("")
        self.file_path_label.setText("")
        self.description_text.setHtml("")
        self.preview_label.clear()
        self.preview_label.setText(tr("no_preview_available"))

    def open_workshop_url_from_signal(self, link):
        if is_safe_external_link(link):
            QDesktopServices.openUrl(QUrl(link))

    def open_mod_folder_from_signal(self, link):
        if self.current_mod_data:
            content_path = self.current_mod_data.get("content_path")
            if content_path and os.path.exists(content_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(content_path))

    def open_description_link(self, url):
        if is_safe_external_link(url):
            QDesktopServices.openUrl(QUrl(url))

    def format_description_html(self, description):
        text = description or ""
        link_tokens = []

        def stash_link(href, label):
            token = f"__STELLARIS_LINK_{len(link_tokens)}__"
            link_tokens.append((token, href, label))
            return token

        text = re.sub(
            r'<a\b[^>]*href\s*=["\'](.*?)["\'][^>]*>(.*?)</a>',
            lambda match: stash_link(match.group(1), re.sub(r"<.*?>", "", match.group(2))),
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        text = re.sub(
            r"\[url=(.+?)\](.+?)\[/url\]",
            lambda match: stash_link(match.group(1), match.group(2)),
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r"\[url\](.+?)\[/url\]",
            lambda match: stash_link(match.group(1), match.group(1)),
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        escaped = html.escape(text)
        escaped = re.sub(
            r"(https?://[^\s<]+)",
            lambda match: (
                f'<a href="{html.escape(match.group(1), quote=True)}">'
                f"{html.escape(match.group(1))}</a>"
            ),
            escaped,
        )

        for token, href, label in link_tokens:
            anchor = (
                f'<a href="{html.escape(href, quote=True)}">'
                f"{html.escape(label)}</a>"
            )
            escaped = escaped.replace(token, anchor)

        return escaped.replace("\n", "<br>")
