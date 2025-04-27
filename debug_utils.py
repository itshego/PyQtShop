from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QCheckBox, QDateTimeEdit, QSpinBox, QListWidget, 
                           QListWidgetItem, QMenu, QApplication)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QDateTime
from debug_types import DebugLevel

class DebugMessage:
    def __init__(self, message_type: DebugLevel, message: str):
        self.type = message_type
        self.message = message
        self.timestamp = QDateTime.currentDateTime()

    def get_formatted_message(self):
        return f"[{self.timestamp.toString('hh:mm:ss')}] [{self.type.name}] {self.message}"

    def get_color(self):
        colors = {
            DebugLevel.ERROR: '#FF4444',
            DebugLevel.WARNING: '#FFAA00',
            DebugLevel.INFO: '#44FF44',
            DebugLevel.DEBUG: '#FFFFFF'
        }
        return colors.get(self.type, '#FFFFFF')


class DebugWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_messages = 50
        self.messages = []
        self.auto_scroll = True
        self.active_filters = {level: True for level in DebugLevel}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top panel
        filter_panel = QHBoxLayout()
        
        # Type filters
        filter_group = QWidget()
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        self.filter_checkboxes = {}

        # Select/Deselect All button
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setCheckable(True)
        self.select_all_btn.setChecked(True)
        self.select_all_btn.clicked.connect(self.toggle_all_filters)
        filter_layout.addWidget(self.select_all_btn)
        
        filter_layout.addWidget(QLabel("Filters:"))
        for level in DebugLevel:
            checkbox = QCheckBox(level.name)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.apply_filter)
            self.filter_checkboxes[level] = checkbox
            filter_layout.addWidget(checkbox)
            
        filter_panel.addWidget(filter_group)
        
        # Time range selection
        time_layout = QHBoxLayout()
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy hh:mm:ss")
        self.date_from.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.date_from.setCalendarPopup(True)
        
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy hh:mm:ss")
        self.date_to.setDateTime(QDateTime.currentDateTime())
        self.date_to.setCalendarPopup(True)
        
        time_layout.addWidget(QLabel("From:"))
        time_layout.addWidget(self.date_from)
        time_layout.addWidget(QLabel("To:"))
        time_layout.addWidget(self.date_to)
        
        self.use_time_filter = QCheckBox("Use Time Filter")
        self.use_time_filter.setChecked(False)
        time_layout.addWidget(self.use_time_filter)
        
        filter_panel.addLayout(time_layout)
        
        # Maximum message count setting
        max_msg_layout = QHBoxLayout()
        max_msg_layout.addWidget(QLabel("Max Messages:"))
        self.max_messages_input = QSpinBox()
        self.max_messages_input.setRange(10, 10000)
        self.max_messages_input.setValue(self.max_messages)
        self.max_messages_input.valueChanged.connect(self.update_max_messages)
        max_msg_layout.addWidget(self.max_messages_input)
        
        filter_panel.addLayout(max_msg_layout)
        
        # Auto-scroll toggle
        self.auto_scroll_btn = QPushButton("Auto-scroll: ON")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        filter_panel.addWidget(self.auto_scroll_btn)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_messages)
        filter_panel.addWidget(self.clear_button)
        
        filter_panel.addStretch()
        layout.addLayout(filter_panel)
        
        # Debug messages list
        self.message_list = QListWidget()
        self.message_list.setAlternatingRowColors(True)
        self.message_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.message_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.message_list)
        
        # Style settings
        self.setStyleSheet("""
            /* Style for the list widget itself */
            QListWidget {
                background-color: #2b2b2b; /* Dark background */
                border: 1px solid #3f3f3f; /* Slightly lighter border */
                font-family: 'Consolas', monospace; /* Monospaced font for code-like look */
            }
            /* Style for individual items in the list */
            QListWidget::item {
                padding: 2px; /* Small padding around text */
            }
            /* Style for alternating row colors */
            QListWidget::item:alternate {
                background-color: #323232; /* Slightly different dark background */
            }
            /* General style for push buttons */
            QPushButton {
                padding: 2px 8px; /* Padding inside the button */
                min-width: 80px; /* Minimum width */
            }
             /* Style for date/time edit widgets */
            QDateTimeEdit {
                padding: 2px;
                min-width: 150px;
            }
            /* Style for spin box widgets */
            QSpinBox {
                padding: 2px;
                min-width: 70px;
            }
            /* Style for check boxes */
            QCheckBox {
                spacing: 5px; /* Space between indicator and text */
                margin-right: 5px; /* Margin to the right */
            }
            /* Style for the check box indicator (the box itself) */
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            /* Style for unchecked indicator */
            QCheckBox::indicator:unchecked {
                border: 1px solid #999; /* Gray border */
                background: #2b2b2b; /* Dark background */
            }
            /* Style for checked indicator */
            QCheckBox::indicator:checked {
                border: 1px solid #3f3f3f; /* Lighter border */
                background: #44FF44; /* Green background */
            }
        """)

    def show_context_menu(self, position):
        menu = QMenu()
        
        copy_selected_action = menu.addAction("Copy Selected Message")
        copy_all_action = menu.addAction("Copy All Visible Messages")
        
        action = menu.exec_(self.message_list.mapToGlobal(position))
        
        if action == copy_selected_action:
            self.copy_selected_message()
        elif action == copy_all_action:
            self.copy_all_visible_messages()
    
    def copy_selected_message(self):
        selected_items = self.message_list.selectedItems()
        if not selected_items:
            return
            
        clipboard = QApplication.clipboard()
        text = "\n".join([item.text() for item in selected_items])
        clipboard.setText(text)
    
    def copy_all_visible_messages(self):
        if self.message_list.count() == 0:
            return
            
        clipboard = QApplication.clipboard()
        text = "\n".join([self.message_list.item(i).text() for i in range(self.message_list.count())])
        clipboard.setText(text)

    def update_max_messages(self, value):
        self.max_messages = value
        # Trim older messages if the list exceeds the new maximum
        while len(self.messages) > self.max_messages:
            self.messages.pop(0)
        self.update_message_list()

    def add_message(self, debug_message: DebugMessage): # Type hint added
        self.messages.append(debug_message)
        # Ensure the message list doesn't exceed the maximum size
        while len(self.messages) > self.max_messages:
            self.messages.pop(0) # Remove the oldest message
        self.update_message_list()
        
        if self.auto_scroll:
            self.message_list.scrollToBottom()

    def toggle_auto_scroll(self, checked):
        self.auto_scroll = checked
        self.auto_scroll_btn.setText(f"Auto-scroll: {'ON' if checked else 'OFF'}")
    
    def toggle_all_filters(self, checked):
        # Set all filter checkboxes to the new state
        for checkbox in self.filter_checkboxes.values():
            checkbox.setChecked(checked)
        self.select_all_btn.setText("Deselect All" if checked else "Select All") # Text updated based on state
        self.apply_filter() # Re-apply filters after changing states

    def update_message_list(self):
        self.message_list.clear()
        
        # Update active filters based on checkbox states
        self.active_filters = {
            level: self.filter_checkboxes[level].isChecked() 
            for level in DebugLevel
        }
        
        for msg in self.messages:
            # Apply type filter
            if not self.active_filters.get(msg.type, False):
                continue
                
            # Apply time filter if enabled
            if self.use_time_filter.isChecked():
                msg_time = msg.timestamp
                if not (self.date_from.dateTime() <= msg_time <= self.date_to.dateTime()):
                     continue # Skip message if outside the selected time range
            
            item = QListWidgetItem(msg.get_formatted_message())
            item.setForeground(QColor(msg.get_color()))
            self.message_list.addItem(item)

    def apply_filter(self):
        # Update the state of the "Select/Deselect All" button
        all_checked = all(cb.isChecked() for cb in self.filter_checkboxes.values())
        self.select_all_btn.setChecked(all_checked)
        self.select_all_btn.setText("Deselect All" if all_checked else "Select All")
        
        self.update_message_list() # Refresh the list based on new filters

    def clear_messages(self):
        self.messages = []
        self.update_message_list()
