"""Maher Umar POS — mobile-first offline POS/ERP for Kivy and Android.
Database changes are additive; existing products, sales and expenses are preserved.
"""
import os
import shutil
import sqlite3
import sys
import traceback
from datetime import datetime

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

APP_TITLE = "Maher Umar POS"
SHOP_NAME = "MAHER UMAR MOBILE & COMMUNICATION"
DB_NAME = "maher_umar_pos.db"
LOW_STOCK_THRESHOLD = 5

# Android safe-area defaults: keep status/navigation bars visible.
Window.fullscreen = False
Window.softinput_mode = "below_target"


KV = r'''
#:import dp kivy.metrics.dp
<PrimaryButton@Button>:
    size_hint_y: None
    height: dp(48)
    background_normal: ''
    background_down: ''
    background_color: (0.055, 0.34, 0.42, 1)
    color: (1, 1, 1, 1)
    font_size: '15sp'
    bold: True
<BackArrowButton@Button>:
    size_hint: None, None
    size: dp(48), dp(42)
    background_normal: ''
    background_down: ''
    background_color: (0.10, 0.58, 0.30, 1)
    color: (1, 1, 1, 1)
    font_size: '25sp'
    bold: True
<SecondaryButton@Button>:
    size_hint_y: None
    height: dp(44)
    background_normal: ''
    background_down: ''
    background_color: (0.88, 0.94, 0.95, 1)
    color: (0.07, 0.26, 0.31, 1)
    font_size: '14sp'
<Field@TextInput>:
    size_hint_y: None
    height: dp(48)
    multiline: False
    padding: [dp(12), dp(13), dp(12), dp(10)]
    font_size: '15sp'
    foreground_color: (0.10, 0.17, 0.19, 1)
    hint_text_color: (0.42, 0.49, 0.51, 1)
    cursor_color: (0.05, 0.40, 0.48, 1)
    background_normal: ''
    background_active: ''
    background_color: (0.93, 0.96, 0.97, 1)
<PageHeading@Label>:
    size_hint_y: None
    height: dp(44)
    font_size: '21sp'
    bold: True
    color: (0.07, 0.19, 0.23, 1)
    halign: 'left'
    valign: 'middle'
    text_size: self.size
<HintText@Label>:
    size_hint_y: None
    height: dp(28)
    font_size: '13sp'
    color: (0.39, 0.47, 0.50, 1)
    halign: 'left'
    valign: 'middle'
    text_size: self.size

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(14)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(10)
                Label:
                    text: '[b]MAHER UMAR MOBILE & COMMUNICATION[/b]\n[size=13sp]Your store, in control[/size]'
                    markup: True
                    size_hint_y: None
                    height: dp(92)
                    font_size: '21sp'
                    color: (0.07, 0.19, 0.23, 1)
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(82)
                    padding: dp(14)
                    spacing: dp(4)
                    canvas.before:
                        Color:
                            rgba: (0.055, 0.34, 0.42, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(15)]
                    Label:
                        text: 'BUSINESS MANAGEMENT'
                        font_size: '11sp'
                        bold: True
                        color: (0.76, 0.90, 0.92, 1)
                        halign: 'left'
                        text_size: self.size
                    Label:
                        text: 'Inventory  •  Sales  •  Expenses'
                        font_size: '17sp'
                        bold: True
                        color: (1, 1, 1, 1)
                        halign: 'left'
                        text_size: self.size
                GridLayout:
                    cols: 2
                    spacing: dp(8)
                    size_hint_y: None
                    height: dp(272)
                    PrimaryButton:
                        text: 'Add Products'
                        on_release: app.go('add_products')
                    PrimaryButton:
                        text: 'Stock Management'
                        on_release: app.go('stock')
                    PrimaryButton:
                        text: 'New Sale'
                        on_release: app.go('sale')
                    SecondaryButton:
                        text: 'Expenses'
                        on_release: app.go('expenses')
                    SecondaryButton:
                        text: 'Reports & Profit'
                        on_release: app.go('reports')
                    SecondaryButton:
                        text: 'Sales History'
                        on_release: app.go('history')
                    SecondaryButton:
                        text: 'Udhaar Book'
                        on_release: app.go('udhaar')
                    SecondaryButton:
                        text: 'Database Backup'
                        on_release: app.backup_database()
                    SecondaryButton:
                        text: 'Refresh Dashboard'
                        on_release: root.refresh_summary()
                Label:
                    text: '[b]BUSINESS SNAPSHOT[/b]'
                    markup: True
                    size_hint_y: None
                    height: dp(26)
                    font_size: '14sp'
                    color: (0.20, 0.31, 0.35, 1)
                    halign: 'left'
                    text_size: self.size
                BoxLayout:
                    size_hint_y: None
                    height: max(dp(174), summary.texture_size[1] + dp(35))
                    padding: dp(14)
                    canvas.before:
                        Color:
                            rgba: (1, 1, 1, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(13)]
                    Label:
                        id: summary
                        text: root.summary_text
                        color: (0.13, 0.21, 0.24, 1)
                        halign: 'left'
                        valign: 'top'
                        text_size: self.width, None
                        font_size: '14sp'
                Label:
                    text: 'LOCAL DATABASE  •  Offline mode'
                    font_size: '11sp'
                    color: (0.42, 0.49, 0.51, 1)
                    size_hint_y: None
                    height: dp(24)
        
<ProductsScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(16), dp(48), dp(16), dp(104)]
        spacing: dp(12)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'Products & Inventory'
        HintText:
            text: 'Add new products or manage saved inventory separately.'
        PrimaryButton:
            text: '＋  Add Products'
            on_release: app.go('add_products')
        PrimaryButton:
            text: '▦  Stock Management'
            on_release: app.go('stock')
        Widget:
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')

<AddProductScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(13), dp(48), dp(13), dp(104)]
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'Add Products'
        HintText:
            text: 'Enter product details. Product discount is optional.'
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                Field:
                    id: pname
                    hint_text: 'Product name'
                Field:
                    id: pcategory
                    hint_text: 'Category (auto-detected if blank)'
                GridLayout:
                    cols: 2
                    spacing: dp(7)
                    size_hint_y: None
                    height: dp(104)
                    Field:
                        id: purchase
                        hint_text: 'Cost price (Rs.)'
                        input_filter: 'float'
                    Field:
                        id: saleprice
                        hint_text: 'Selling price (Rs.)'
                        input_filter: 'float'
                    Field:
                        id: stock
                        hint_text: 'Opening quantity'
                        input_filter: 'int'
                    Widget:
                SecondaryButton:
                    text: '＋  Add Product Discount (Optional)'
                    on_release: root.toggle_discount_form()
                BoxLayout:
                    id: discount_form
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(0)
                    opacity: 0
                    disabled: True
                    spacing: dp(7)
                    Label:
                        text: '[b]PRODUCT DISCOUNT[/b]'
                        markup: True
                        size_hint_y: None
                        height: dp(25)
                        font_size: '14sp'
                        color: (0.12, 0.25, 0.29, 1)
                        halign: 'left'
                        text_size: self.size
                    Field:
                        id: discount_percent
                        hint_text: 'Discount percentage (e.g. 10)'
                        input_filter: 'float'
                    Field:
                        id: discount_start
                        hint_text: 'Start date (automatic)'
                        readonly: True
                    Field:
                        id: discount_end
                        hint_text: 'Expiry date (DDMM, e.g. 3011)'
                        input_filter: 'int'
                        max_text_length: 4
                    Field:
                        id: discount_qty
                        hint_text: 'Minimum qualifying quantity'
                        input_filter: 'int'
                    HintText:
                        text: 'Start date is automatic. Enter expiry as DDMM; current year is added.'
                PrimaryButton:
                    text: 'Save Product'
                    on_release: root.add_product()
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')

<StockScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(13), dp(48), dp(13), dp(104)]
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'Stock Management'
            SecondaryButton:
                text: '☰'
                size_hint_x: None
                width: dp(46)
                on_release: root.open_filters()
        Label:
            text: root.filter_summary
            size_hint_y: None
            height: dp(24)
            color: (0.39, 0.47, 0.50, 1)
            font_size: '12sp'
            halign: 'left'
            text_size: self.size
        GridLayout:
            cols: 2
            spacing: dp(7)
            size_hint_y: None
            height: dp(100)
            Field:
                id: stock_product_name
                hint_text: 'Exact saved product name'
            Field:
                id: stock_add_qty
                hint_text: 'Quantity to add'
                input_filter: 'int'
            PrimaryButton:
                text: 'Add Stock'
                on_release: root.add_stock()
            SecondaryButton:
                text: 'Refresh'
                on_release: root.refresh()
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: stock_rows
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')

<SaleScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(13), dp(48), dp(13), dp(104)]
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'New Sale / Checkout'
        HintText:
            text: 'Enter product name and quantity; category and price are automatic.'
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                Field:
                    id: phone
                    hint_text: 'Customer mobile number (optional)'
                Field:
                    id: product_name
                    hint_text: 'Product name'
                Field:
                    id: quantity
                    hint_text: 'Quantity'
                    input_filter: 'int'
                PrimaryButton:
                    text: 'Add Item to Cart'
                    on_release: root.add_item()
                Label:
                    id: cart_label
                    text: root.cart_text
                    size_hint_y: None
                    height: max(dp(80), self.texture_size[1] + dp(20))
                    text_size: self.width, None
                    halign: 'left'
                    valign: 'top'
                    color: (0.12, 0.22, 0.25, 1)
                    font_size: '13sp'
                HintText:
                    text: 'Product discounts apply automatically when the quantity and date rules are met.'
                Label:
                    id: total_label
                    text: root.total_text
                    size_hint_y: None
                    height: dp(36)
                    color: (0.055, 0.34, 0.42, 1)
                    bold: True
                    font_size: '16sp'
                    halign: 'left'
                    text_size: self.size
                SecondaryButton:
                    text: 'Remove Last Item'
                    on_release: root.remove_last_item()
                PrimaryButton:
                    text: 'Done — Calculate Total & Payment'
                    on_release: root.finish_cart()
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')

<ExpensesScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(13), dp(48), dp(13), dp(104)]
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'Expenses / Kharcha Book'
        HintText:
            text: 'Add one or more expenses, then press Done to save.'
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                Field:
                    id: title
                    hint_text: 'Expense title'
                Field:
                    id: amount
                    hint_text: 'Amount (Rs.)'
                    input_filter: 'float'
                Field:
                    id: category
                    hint_text: 'Category (e.g. Utility, Transport)'
                SecondaryButton:
                    text: 'Add Expense to List'
                    on_release: root.add_to_draft()
                Label:
                    id: draft_label
                    text: root.draft_text
                    size_hint_y: None
                    height: max(dp(60), self.texture_size[1] + dp(18))
                    text_size: self.width, None
                    halign: 'left'
                    valign: 'top'
                    color: (0.14, 0.22, 0.25, 1)
                    font_size: '13sp'
                PrimaryButton:
                    text: 'Done — Save Expenses'
                    on_release: root.done_expenses()
                Label:
                    text: '[b]RECENT EXPENSES[/b]\n' + root.listing_text
                    markup: True
                    size_hint_y: None
                    height: max(dp(100), self.texture_size[1] + dp(20))
                    text_size: self.width, None
                    halign: 'left'
                    valign: 'top'
                    color: (0.14, 0.22, 0.25, 1)
                    font_size: '13sp'
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')

<ReportsScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(13), dp(48), dp(13), dp(104)]
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'Reports & Gross Profit'
        ScrollView:
            do_scroll_x: False
            Label:
                text: root.report_text
                size_hint_y: None
                height: max(dp(180), self.texture_size[1] + dp(30))
                text_size: self.width, None
                halign: 'left'
                valign: 'top'
                color: (0.14, 0.22, 0.25, 1)
                font_size: '14sp'
        PrimaryButton:
            text: 'Refresh Reports'
            on_release: root.refresh()
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')

<HistoryScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(13), dp(48), dp(13), dp(104)]
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'Sales History'
        ScrollView:
            do_scroll_x: False
            Label:
                text: root.history_text
                size_hint_y: None
                height: max(dp(160), self.texture_size[1] + dp(24))
                text_size: self.width, None
                halign: 'left'
                valign: 'top'
                color: (0.14, 0.22, 0.25, 1)
                font_size: '13sp'
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')

<UdhaarScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(13), dp(48), dp(13), dp(104)]
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (0.955, 0.972, 0.978, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(9)
            BackArrowButton:
                text: '‹'
                on_release: app.go('home')
            PageHeading:
                text: 'Udhaar Book / Outstanding'
        ScrollView:
            do_scroll_x: False
            Label:
                text: root.udhaar_text
                size_hint_y: None
                height: max(dp(160), self.texture_size[1] + dp(24))
                text_size: self.width, None
                halign: 'left'
                valign: 'top'
                color: (0.14, 0.22, 0.25, 1)
                font_size: '13sp'
        SecondaryButton:
            text: 'Back to Dashboard'
            on_release: app.go('home')
'''


def money(value):
    return f"Rs. {float(value or 0):,.2f}"


def detect_category(name, category=""):
    if category and category.strip():
        return category.strip().upper()
    value = (name or "").casefold()
    if "fast charger" in value:
        return "FAST CHARGER"
    if any(x in value for x in ("airbud", "airbuds", "airpod", "earbud", "wireless buds")):
        return "AIRBUDS"
    if any(x in value for x in ("handsfree", "headset", "neckband", "earphone")):
        return "HANDSFREE"
    if "charger" in value:
        return "CHARGER"
    if any(x in value for x in ("vivo", "oppo", "samsung", "iphone", "tecno", "infinix", "itel", "mobile", "phone", "redmi", "realme")):
        return "MOBILE"
    if any(x in value for x in ("cable", "cover", "protector", "glass", "adapter", "memory card", "power bank")):
        return "ACCESSORIES"
    return "GENERAL"


class DialogBody(BoxLayout):
    """Light, high-contrast surface for Android confirmation dialogs."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._dialog_bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._sync_dialog_bg, size=self._sync_dialog_bg)

    def _sync_dialog_bg(self, *_):
        self._dialog_bg.pos = self.pos
        self._dialog_bg.size = self.size


def show_message(message, title="Maher Umar POS"):
    """High-contrast confirmation dialog with height adapted to the message."""
    body = DialogBody(orientation="vertical", padding=[dp(18), dp(14), dp(18), dp(14)], spacing=dp(12))
    label = Label(
        text=str(message or ""), color=(0.04, 0.10, 0.12, 1),
        halign="left", valign="top", font_size="15sp", bold=False,
        size_hint_y=None,
    )
    body.add_widget(label)

    def fit_label(*_):
        label.text_size = (max(dp(160), body.width - dp(36)), None)
        label.texture_update()
        label.height = max(dp(78), label.texture_size[1] + dp(18))

    body.bind(width=fit_label)
    close = Button(
        text="OK", size_hint_y=None, height=dp(48), background_normal="",
        background_down="", background_color=(0.04, 0.36, 0.44, 1),
        color=(1, 1, 1, 1), font_size="16sp", bold=True,
    )
    body.add_widget(close)
    dialog = Popup(
        title=str(title), content=body, size_hint=(0.92, None), height=dp(230),
        auto_dismiss=False, background_color=(1, 1, 1, 1),
        title_color=(0.04, 0.13, 0.16, 1),
        separator_color=(0.04, 0.36, 0.44, 1), title_size="18sp",
    )

    def resize_dialog(*_):
        fit_label()
        max_height = max(dp(260), Window.height * 0.72)
        dialog.height = min(max(label.height + dp(112), dp(210)), max_height)

    body.bind(width=resize_dialog)
    close.bind(on_release=dialog.dismiss)
    dialog.bind(on_open=resize_dialog)
    dialog.open()
    return dialog


class Store:
    def __init__(self, path):
        self.db_path = path if os.path.isabs(path) else os.path.join(App.get_running_app().user_data_dir, path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_and_migrate()

    def _columns(self, table):
        return {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}

    def _add_column(self, table, column, definition):
        if column not in self._columns(table):
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _create_and_migrate(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'GENERAL', purchase_price REAL NOT NULL DEFAULT 0,
            sale_price REAL NOT NULL DEFAULT 0, stock INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT '',
            discount_percent REAL NOT NULL DEFAULT 0,
            discount_start_date TEXT NOT NULL DEFAULT '',
            discount_end_date TEXT NOT NULL DEFAULT '',
            discount_min_qty INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, customer_phone TEXT,
            total_amount REAL NOT NULL DEFAULT 0, paid_amount REAL NOT NULL DEFAULT 0,
            balance REAL NOT NULL DEFAULT 0, sale_date TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS sale_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER NOT NULL REFERENCES sales(id),
            product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL,
            price REAL NOT NULL, purchase_price REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            amount REAL NOT NULL, category TEXT NOT NULL DEFAULT 'General', expense_date TEXT NOT NULL DEFAULT ''
        );
        """)
        # Additive migrations only: never drop or reset existing shop data.
        for column, definition in (("customer_name", "TEXT"), ("customer_phone", "TEXT"),
                                   ("total_amount", "REAL NOT NULL DEFAULT 0"),
                                   ("paid_amount", "REAL NOT NULL DEFAULT 0"),
                                   ("balance", "REAL NOT NULL DEFAULT 0"), ("sale_date", "TEXT NOT NULL DEFAULT ''"),
                                   ("discount", "REAL NOT NULL DEFAULT 0"),
                                   ("net_amount", "REAL NOT NULL DEFAULT 0"), ("status", "TEXT NOT NULL DEFAULT 'PAID'")):
            self._add_column("sales", column, definition)
        for column, definition in (("category", "TEXT NOT NULL DEFAULT 'GENERAL'"),
                                   ("purchase_price", "REAL NOT NULL DEFAULT 0"),
                                   ("sale_price", "REAL NOT NULL DEFAULT 0"), ("stock", "INTEGER NOT NULL DEFAULT 0"),
                                   ("created_at", "TEXT NOT NULL DEFAULT ''"),
                                    ("discount_percent", "REAL NOT NULL DEFAULT 0"),
                                    ("discount_start_date", "TEXT NOT NULL DEFAULT ''"),
                                    ("discount_end_date", "TEXT NOT NULL DEFAULT ''"),
                                    ("discount_min_qty", "INTEGER NOT NULL DEFAULT 0")):
            self._add_column("products", column, definition)
        for column, definition in (("customer_name", "TEXT"), ("customer_phone", "TEXT"),
                                   ("discount", "REAL NOT NULL DEFAULT 0"), ("net_amount", "REAL NOT NULL DEFAULT 0"),
                                   ("status", "TEXT NOT NULL DEFAULT 'PAID'")):
            self._add_column("sales", column, definition)
        for column, definition in (("purchase_price", "REAL NOT NULL DEFAULT 0"),):
            self._add_column("sale_items", column, definition)
        # Older terminal database used `customer` and may have net_amount already.
        cols = self._columns("sales")
        if "customer" in cols:
            self.conn.execute("UPDATE sales SET customer_name=customer WHERE (customer_name IS NULL OR customer_name='')")
        self.conn.execute("UPDATE sales SET net_amount=total_amount-discount WHERE net_amount=0 AND total_amount>0")
        self.conn.execute("UPDATE sales SET status=CASE WHEN balance<=0 THEN 'PAID' ELSE 'DUE' END WHERE status IS NULL OR status=''")
        self.conn.commit()

    def products(self, order="name"):
        ordering = {"newest": "created_at DESC, id DESC", "oldest": "created_at ASC, id ASC",
                    "low": "stock ASC, name COLLATE NOCASE", "discounted": "name COLLATE NOCASE",
                    "name": "name COLLATE NOCASE"}.get(order, "name COLLATE NOCASE")
        return self.conn.execute(f"SELECT * FROM products ORDER BY {ordering}").fetchall()

    def find_products(self, query):
        q = (query or "").strip()
        if not q:
            return []
        rows = self.conn.execute("SELECT * FROM products WHERE LOWER(name)=LOWER(?) ORDER BY name", (q,)).fetchall()
        if rows:
            return rows
        return self.conn.execute("SELECT * FROM products WHERE name LIKE ? ORDER BY name LIMIT 20", (f"%{q}%",)).fetchall()

    def add_stock(self, name, quantity):
        name = (name or "").strip()
        if not name:
            raise ValueError("Product name enter karein.")
        if quantity <= 0:
            raise ValueError("Add stock quantity 1 ya us se zyada honi chahiye.")
        matches = self.find_products(name)
        if not matches or matches[0]["name"].casefold() != name.casefold():
            raise ValueError("Exact saved product name enter karein.")
        with self.conn:
            self.conn.execute("UPDATE products SET stock=stock+? WHERE id=?", (quantity, matches[0]["id"]))
        return matches[0]["id"]

    def add_product(self, name, category, purchase, sale, stock, discount_percent=0,
                    discount_start_date="", discount_end_date="", discount_min_qty=0):
        name = name.strip()
        if not name:
            raise ValueError("Product name enter karein.")
        if purchase < 0 or sale < 0 or stock < 0:
            raise ValueError("Prices aur stock negative nahi ho sakte.")
        if discount_percent < 0 or discount_percent >= 100:
            raise ValueError("Discount 0 se zyada aur 100% se kam hona chahiye.")
        if discount_percent:
            if not discount_start_date or not discount_end_date or discount_min_qty <= 0:
                raise ValueError("Discount ke liye start date, expiry date aur minimum quantity lazmi hain.")
            try:
                start = datetime.strptime(discount_start_date, "%Y-%m-%d").date()
                end = datetime.strptime(discount_end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Dates YYYY-MM-DD format mein enter karein.")
            if end < start:
                raise ValueError("Expiry date start date se pehle nahi ho sakti.")
        else:
            discount_start_date = discount_end_date = ""
            discount_min_qty = 0
        category = detect_category(name, category)
        with self.conn:
            existing = self.conn.execute("SELECT id FROM products WHERE LOWER(name)=LOWER(?)", (name,)).fetchone()
            if existing:
                raise ValueError("Yeh product pehle se saved hai. Quantity barhane ke liye Stock Management use karein.")
            now = datetime.now().isoformat(timespec="seconds")
            cur = self.conn.execute("""INSERT INTO products(name,category,purchase_price,sale_price,stock,created_at,
                discount_percent,discount_start_date,discount_end_date,discount_min_qty) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (name, category, purchase, sale, stock, now, discount_percent, discount_start_date, discount_end_date, discount_min_qty))
            return cur.lastrowid

    def create_sale(self, customer, phone, items, subtotal, discount, paid):
        if not items:
            raise ValueError("Cart mein pehle product add karein.")
        if discount < 0 or discount > subtotal:
            raise ValueError("Discount subtotal se zyada nahi ho sakta.")
        net = round(subtotal - discount, 2)
        if paid < 0 or paid > net:
            raise ValueError("Received amount 0 aur final total ke darmiyan honi chahiye.")
        due = round(net - paid, 2)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            # Validate all stock first, then save sale + items + deductions atomically.
            for item in items:
                row = self.conn.execute("SELECT stock,purchase_price FROM products WHERE id=?", (item["product_id"],)).fetchone()
                if row is None:
                    raise ValueError(f"Product '{item['name']}' inventory mein nahi mila.")
                if item["quantity"] <= 0 or item["quantity"] > row["stock"]:
                    raise ValueError(f"{item['name']} ka stock kam hai. Available: {row['stock']}.")
                item["purchase_price"] = row["purchase_price"]
            cur = self.conn.execute("INSERT INTO sales(customer_name,customer_phone,total_amount,paid_amount,balance,sale_date,discount,net_amount,status) VALUES(?,?,?,?,?,?,?,?,?)",
                                    (customer.strip() or "Walk-in", phone.strip(), subtotal, paid, due, now, discount, net, "PAID" if due == 0 else "DUE"))
            sale_id = cur.lastrowid
            for item in items:
                self.conn.execute("INSERT INTO sale_items(sale_id,product_id,quantity,price,purchase_price) VALUES(?,?,?,?,?)",
                                  (sale_id, item["product_id"], item["quantity"], item["price"], item["purchase_price"]))
                cur2 = self.conn.execute("UPDATE products SET stock=stock-? WHERE id=? AND stock>=?", (item["quantity"], item["product_id"], item["quantity"]))
                if cur2.rowcount != 1:
                    raise ValueError(f"Stock changed for {item['name']}; sale was not saved.")
        return sale_id, net, due

    def add_expense(self, title, amount, category):
        if not title.strip() or amount <= 0:
            raise ValueError("Expense title aur positive amount enter karein.")
        with self.conn:
            self.conn.execute("INSERT INTO expenses(title,amount,category,expense_date) VALUES(?,?,?,?)",
                              (title.strip(), amount, category.strip() or "General", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    def totals(self):
        return {"products": self.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
                "units": self.conn.execute("SELECT COALESCE(SUM(stock),0) FROM products").fetchone()[0],
                "sales": self.conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0],
                "revenue": self.conn.execute("SELECT COALESCE(SUM(net_amount),SUM(total_amount),0) FROM sales").fetchone()[0],
                "due": self.conn.execute("SELECT COALESCE(SUM(balance),0) FROM sales").fetchone()[0],
                "expenses": self.conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0],
                "low": self.conn.execute("SELECT COUNT(*) FROM products WHERE stock<=?", (LOW_STOCK_THRESHOLD,)).fetchone()[0]}

    def expenses(self):
        return self.conn.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 50").fetchall()

    def sales_history(self):
        rows = self.conn.execute("""SELECT s.*, COALESCE(s.net_amount,s.total_amount) AS payable,
            (SELECT COALESCE(SUM(si.quantity*COALESCE(si.purchase_price,p.purchase_price,0)),0)
             FROM sale_items si LEFT JOIN products p ON p.id=si.product_id WHERE si.sale_id=s.id) AS cost
            FROM sales s ORDER BY s.id DESC LIMIT 200""").fetchall()
        return rows

    def sale_items(self, sale_id):
        return self.conn.execute("""SELECT si.*,p.name,p.category FROM sale_items si LEFT JOIN products p ON p.id=si.product_id WHERE si.sale_id=?""", (sale_id,)).fetchall()

    def backup(self):
        folder = os.path.join(App.get_running_app().user_data_dir, "Backups")
        os.makedirs(folder, exist_ok=True)
        dest_path = os.path.join(folder, "maher_umar_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db")
        dest = sqlite3.connect(dest_path)
        try:
            self.conn.backup(dest)
        finally:
            dest.close()
        return dest_path


class MainScreen(Screen):
    summary_text = StringProperty("")
    def on_pre_enter(self, *args): self.refresh_summary()
    def refresh_summary(self):
        t = App.get_running_app().store.totals()
        self.summary_text = (f"Products listed       {t['products']}\nUnits in stock          {t['units']}\nSales recorded         {t['sales']}\nNet sales                 {money(t['revenue'])}\nOutstanding due       {money(t['due'])}\nTotal expenses        {money(t['expenses'])}\nLow-stock products  {t['low']}")


class ProductsScreen(Screen):
    """Navigation hub for product entry and stock management."""


class AddProductScreen(Screen):
    def on_pre_enter(self, *args):
        for key in ("pname", "pcategory", "purchase", "saleprice", "stock",
                    "discount_percent", "discount_start", "discount_end", "discount_qty"):
            if key in self.ids:
                self.ids[key].text = ""
        self.ids.discount_start.text = datetime.now().strftime("%d-%m-%Y")
        form = self.ids.discount_form
        form.height = dp(0)
        form.opacity = 0
        form.disabled = True

    def toggle_discount_form(self):
        form = self.ids.discount_form
        opening = form.disabled
        if opening:
            self.ids.discount_start.text = datetime.now().strftime("%d-%m-%Y")
            form.height = dp(300)
            form.opacity = 1
            form.disabled = False
        else:
            form.height = dp(0)
            form.opacity = 0
            form.disabled = True
            for key in ("discount_percent", "discount_end", "discount_qty"):
                self.ids[key].text = ""

    @staticmethod
    def _parse_expiry(raw):
        digits = "".join(ch for ch in (raw or "") if ch.isdigit())
        if len(digits) != 4:
            raise ValueError("Expiry date mein DDMM format mein 4 digits enter karein, misal: 3011.")
        day, month = int(digits[:2]), int(digits[2:])
        year = datetime.now().year
        try:
            expiry = datetime(year, month, day).date()
        except ValueError:
            raise ValueError("Expiry date valid nahi. DDMM dobara check karein.")
        return expiry.strftime("%Y-%m-%d")

    def add_product(self):
        try:
            name = self.ids.pname.text.strip()
            category = self.ids.pcategory.text.strip()
            purchase = float(self.ids.purchase.text or 0)
            sale = float(self.ids.saleprice.text or 0)
            stock = int(self.ids.stock.text or 0)
            pct = float(self.ids.discount_percent.text or 0)
            qty = int(self.ids.discount_qty.text or 0)
            if pct:
                start_display = self.ids.discount_start.text.strip()
                try:
                    start = datetime.strptime(start_display, "%d-%m-%Y").strftime("%Y-%m-%d")
                except ValueError:
                    start = datetime.now().strftime("%Y-%m-%d")
                end = self._parse_expiry(self.ids.discount_end.text)
            else:
                start = end = ""
                qty = 0
            pid = App.get_running_app().store.add_product(
                name, category, purchase, sale, stock, pct, start, end, qty
            )
            App.get_running_app().refresh_home()
            App.get_running_app().root.get_screen("stock").refresh()
            self.on_pre_enter()
            show_message(
                f"Product saved successfully.\nProduct ID: {pid}\nAvailable in Stock Management and checkout.",
                "Product saved"
            )
        except (ValueError, sqlite3.Error) as exc:
            show_message(str(exc), "Check product details")


class StockScreen(Screen):
    filter_summary = StringProperty("Showing all products")
    active_filter = "All products"

    def on_pre_enter(self, *args):
        self.refresh()

    def set_filter(self, value):
        self.active_filter = value
        self.filter_summary = "Filter: " + value
        self.refresh()

    def open_filters(self):
        store = App.get_running_app().store
        categories = sorted({str(p["category"] or "GENERAL") for p in store.products()}, key=str.casefold)
        options = ["All products", "Newest product", "Old products", "Low stock products", "Discounted products"]
        options.extend(category for category in categories if category not in options)
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        scroller = ScrollView(do_scroll_x=False)
        menu = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        menu.bind(minimum_height=menu.setter("height"))
        popup = Popup(
            title="Filter Stock",
            content=scroller,
            size_hint=(0.9, 0.78),
            background_color=(1, 1, 1, 1),
            title_color=(0.08, 0.16, 0.18, 1),
            separator_color=(0.055, 0.34, 0.42, 1),
            title_size="18sp"
        )
        for option in options:
            button = Button(
                text=option, size_hint_y=None, height=dp(44),
                background_normal="", background_down="",
                background_color=(0.88, 0.94, 0.95, 1),
                color=(0.07, 0.26, 0.31, 1), font_size="14sp"
            )
            button.bind(on_release=lambda instance, selected=option: (popup.dismiss(), self.set_filter(selected)))
            menu.add_widget(button)
        scroller.add_widget(menu)
        popup.open()

    def add_stock(self):
        try:
            name = self.ids.stock_product_name.text.strip()
            quantity = int(self.ids.stock_add_qty.text or 0)
            pid = App.get_running_app().store.add_stock(name, quantity)
            self.ids.stock_product_name.text = ""
            self.ids.stock_add_qty.text = ""
            self.refresh()
            App.get_running_app().refresh_home()
            show_message(f"Stock updated for product ID {pid}.", "Stock updated")
        except (ValueError, sqlite3.Error) as exc:
            show_message(str(exc), "Unable to update stock")

    @staticmethod
    def _make_product_card(product):
        card = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(122),
            padding=[dp(10), dp(8), dp(10), dp(8)], spacing=dp(5)
        )
        with card.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
        card.bind(pos=lambda widget, value: setattr(bg, "pos", value))
        card.bind(size=lambda widget, value: setattr(bg, "size", value))
        status = "OUT OF STOCK" if int(product["stock"]) <= 0 else (
            "LOW STOCK" if int(product["stock"]) <= LOW_STOCK_THRESHOLD else "IN STOCK"
        )
        title = Label(
            text=f"[b]{product['name']}[/b]  •  {status}",
            markup=True, size_hint_y=None, height=dp(26),
            color=(0.07, 0.19, 0.23, 1), font_size="14sp",
            halign="left", valign="middle", text_size=(Window.width - dp(70), None)
        )
        details = GridLayout(cols=2, rows=2, spacing=dp(4), size_hint_y=None, height=dp(66))
        fields = [
            ("CATEGORY", str(product["category"] or "GENERAL")),
            ("COST PRICE", money(product["purchase_price"])),
            ("SELL PRICE", money(product["sale_price"])),
            ("QUANTITY", str(product["stock"]))
        ]
        for label, value in fields:
            cell = Label(
                text=f"[color=64777d]{label}[/color]  [b]{value}[/b]",
                markup=True, color=(0.12, 0.22, 0.25, 1), font_size="11sp",
                halign="left", valign="middle", text_size=(Window.width / 2 - dp(40), None)
            )
            details.add_widget(cell)
        card.add_widget(title)
        card.add_widget(details)
        return card

    def refresh(self):
        container = self.ids.stock_rows
        container.clear_widgets()
        all_rows = list(App.get_running_app().store.products(order="name"))
        selected = self.active_filter
        if selected == "Newest product":
            all_rows.sort(key=lambda p: (p["created_at"] or "", int(p["id"])), reverse=True)
        elif selected == "Old products":
            all_rows.sort(key=lambda p: (p["created_at"] or "", int(p["id"])))
        elif selected == "Low stock products":
            all_rows = [p for p in all_rows if int(p["stock"]) <= LOW_STOCK_THRESHOLD]
        elif selected == "Discounted products":
            all_rows = [p for p in all_rows if float(p["discount_percent"] or 0) > 0]
        elif selected != "All products":
            all_rows = [p for p in all_rows if str(p["category"] or "GENERAL").casefold() == selected.casefold()]

        if not all_rows:
            container.add_widget(Label(
                text="No products match this filter.", size_hint_y=None, height=dp(80),
                color=(0.14, 0.22, 0.25, 1), font_size="14sp"
            ))
            return

        grouped = {}
        for product in all_rows:
            category = str(product["category"] or "GENERAL").upper()
            grouped.setdefault(category, []).append(product)
        for category in sorted(grouped, key=str.casefold):
            header = Label(
                text=f"[b]{category}[/b]  •  {len(grouped[category])} product(s)",
                markup=True, size_hint_y=None, height=dp(32),
                color=(0.055, 0.34, 0.42, 1), font_size="14sp",
                halign="left", valign="middle", text_size=(Window.width - dp(35), None)
            )
            container.add_widget(header)
            for product in grouped[category]:
                container.add_widget(self._make_product_card(product))


class SaleScreen(Screen):
    cart_text = StringProperty("Cart is empty. Add a product by name.")
    total_text = StringProperty("Subtotal: Rs. 0.00")
    def __init__(self, **kwargs):
        super().__init__(**kwargs); self.cart = []
    def on_pre_enter(self, *args): self.update_cart()
    def add_item(self):
        query = self.ids.product_name.text.strip()
        try: qty = int(self.ids.quantity.text or "0")
        except ValueError: show_message("Quantity whole number mein enter karein.", "Invalid quantity"); return
        if not query: show_message("Product name enter karein.", "Product required"); return
        if qty <= 0: show_message("Quantity 1 ya us se zyada honi chahiye.", "Invalid quantity"); return
        matches = App.get_running_app().store.find_products(query)
        if not matches: show_message(f"'{query}' inventory mein nahi mila. Pehle Products & Stock mein add karein.", "Product not found"); return
        if len(matches) > 1 and matches[0]["name"].casefold() != query.casefold():
            self.choose_product(matches, qty); return
        self._add_matched(dict(matches[0]), qty)
    def choose_product(self, matches, qty):
        box = DialogBody(orientation="vertical", padding=dp(10), spacing=dp(6))
        pop = Popup(title="Select matching product", content=box, size_hint=(0.92, 0.82),
                    background_color=(1, 1, 1, 1), title_color=(0.08, 0.16, 0.18, 1),
                    separator_color=(0.08, 0.52, 0.30, 1), title_size="18sp")
        sc = ScrollView(); items = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6)); items.bind(minimum_height=items.setter("height"))
        for row in matches:
            btn = Button(text=f"{row['name']} • {row['category']} • {money(row['sale_price'])} • Stock {row['stock']}", size_hint_y=None, height=dp(50), background_normal="", background_color=(0.88,0.94,0.95,1), color=(0.07,0.26,0.31,1))
            btn.bind(on_release=lambda instance, p=dict(row): (pop.dismiss(), self._add_matched(p, qty)))
            items.add_widget(btn)
        sc.add_widget(items); box.add_widget(sc); pop.open()
    def _add_matched(self, product, qty):
        existing = next((x for x in self.cart if x["product_id"] == product["id"]), None)
        already = existing["quantity"] if existing else 0
        if product["stock"] < already + qty:
            show_message(f"{product['name']} ka available stock {product['stock']} hai.", "Insufficient stock"); return
        if existing: existing["quantity"] += qty
        else: self.cart.append({"product_id": product["id"], "name": product["name"], "category": detect_category(product["name"], product["category"]), "quantity": qty, "price": float(product["sale_price"]), "purchase_price": float(product["purchase_price"]), "discount_percent": float(product.get("discount_percent", 0) or 0), "discount_start_date": product.get("discount_start_date", ""), "discount_end_date": product.get("discount_end_date", ""), "discount_min_qty": int(product.get("discount_min_qty", 0) or 0)})
        self.ids.product_name.text = ""; self.ids.quantity.text = ""; self.update_cart()
    def subtotal(self): return round(sum(i["quantity"] * i["price"] for i in self.cart), 2)
    @staticmethod
    def _item_discount(item, today=None):
        today = today or datetime.now().date()
        pct = float(item.get("discount_percent", 0) or 0)
        minimum = int(item.get("discount_min_qty", 0) or 0)
        if pct <= 0 or minimum <= 0 or int(item["quantity"]) < minimum:
            return 0.0
        try:
            start = datetime.strptime(item.get("discount_start_date", ""), "%Y-%m-%d").date()
            end = datetime.strptime(item.get("discount_end_date", ""), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return 0.0
        if not start <= today <= end:
            return 0.0
        return round(int(item["quantity"]) * float(item["price"]) * pct / 100, 2)

    def product_discount_amount(self):
        today = datetime.now().date()
        return round(min(self.subtotal(), sum(self._item_discount(item, today) for item in self.cart)), 2)

    def discount_amount(self):
        # Product promotions are calculated by the app; no manual checkout discount is needed.
        return self.product_discount_amount()
    def update_cart(self):
        if not self.cart: self.cart_text = "Cart is empty. Add a product by name."
        else:
            today = datetime.now().date()
            lines = []
            for i, item in enumerate(self.cart):
                line_total = item["quantity"] * item["price"]
                item_discount = self._item_discount(item, today)
                line = f"{i+1}. {item['name']} ({item['category']})\n   Qty {item['quantity']} × {money(item['price'])} = {money(line_total)}"
                if item_discount:
                    line += f"\n   Automatic product discount: −{money(item_discount)}"
                lines.append(line)
            self.cart_text = "\n\n".join(lines)
        sub = self.subtotal(); disc = self.discount_amount()
        self.total_text = f"Subtotal: {money(sub)}   Discount: {money(disc)}\nFinal payable: {money(max(0, sub-disc))}"
    def remove_last_item(self):
        if self.cart: self.cart.pop(); self.update_cart()
        else: show_message("Cart already empty.")
    def finish_cart(self):
        if not self.cart: show_message("Pehle cart mein product add karein.", "Cart empty"); return
        self.update_cart(); subtotal = self.subtotal(); discount = self.discount_amount(); final = round(subtotal-discount,2)
        if final < 0: show_message("Discount subtotal se zyada nahi ho sakta."); return
        body = DialogBody(orientation="vertical", padding=dp(12), spacing=dp(8))
        body.add_widget(Label(text=f"Subtotal: {money(subtotal)}\nDiscount: {money(discount)}\nFINAL PAYABLE: {money(final)}", size_hint_y=None, height=dp(95), color=(0.08,0.12,0.14,1), halign="left"))
        received = TextInput(hint_text="Amount received (Rs.)", input_filter="float", multiline=False, size_hint_y=None, height=dp(48), padding=[dp(10),dp(12)])
        body.add_widget(received)
        note = Label(text="Due amount will be saved in Udhaar Book if payment is partial.", size_hint_y=None, height=dp(35), color=(0.22,0.29,0.31,1), font_size="13sp")
        body.add_widget(note)
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        cancel = Button(text="Cancel", background_normal="", background_color=(0.88,0.94,0.95,1), color=(0.07,0.26,0.31,1))
        confirm = Button(text="Confirm Sale", background_normal="", background_color=(0.055,0.34,0.42,1), color=(1,1,1,1), bold=True)
        row.add_widget(cancel); row.add_widget(confirm); body.add_widget(row)
        pop = Popup(title="Checkout & Payment", content=body, size_hint=(0.92,None), height=dp(340), auto_dismiss=False,
                    background_color=(1, 1, 1, 1), title_color=(0.08, 0.16, 0.18, 1),
                    separator_color=(0.08, 0.52, 0.30, 1), title_size="18sp")
        cancel.bind(on_release=pop.dismiss)
        confirm.bind(on_release=lambda *_: self.commit_sale(pop, received.text, subtotal, discount))
        pop.open()
    def commit_sale(self, popup, received, subtotal, discount):
        try:
            received_amount = float(received or 0)
            if received_amount < 0:
                raise ValueError("Received amount negative nahi ho sakti.")
            customer = "Walk-in"
            phone = self.ids.phone.text.strip()
            store = App.get_running_app().store
            net_expected = round(subtotal - discount, 2)
            change = round(max(0.0, received_amount - net_expected), 2)
            credited_paid = min(received_amount, net_expected)
            sale_id, net, due = store.create_sale(customer, phone, self.cart, subtotal, discount, credited_paid)
            items = [dict(x) for x in self.cart]
            today = datetime.now().date()
            for item in items:
                item["discount_amount"] = self._item_discount(item, today)
            invoice_path = App.get_running_app().generate_invoice(sale_id, customer, phone, items, subtotal, discount, net, credited_paid, due, change)
            popup.dismiss(); self.cart = []; self.ids.phone.text = ""; self.update_cart()
            App.get_running_app().refresh_home()
            message = f"Sale #{sale_id} saved successfully.\nSubtotal: {money(subtotal)}\nDiscount: {money(discount)}\nPayable: {money(net)}\nAmount tendered: {money(received_amount)}\nChange to return: {money(change)}\nOutstanding due: {money(due)}"
            if invoice_path: message += f"\n\nInvoice saved at:\n{invoice_path}"
            Clock.schedule_once(lambda _dt, text=message: show_message(text, "Sale completed"), 0.25)
        except (ValueError, sqlite3.Error) as exc:
            popup.dismiss()
            Clock.schedule_once(lambda _dt, text=str(exc): show_message(text, "Sale not saved"), 0.25)


class ExpensesScreen(Screen):
    listing_text = StringProperty("")
    draft_text = StringProperty("No draft expenses added yet.")
    def __init__(self, **kwargs): super().__init__(**kwargs); self.draft = []
    def on_pre_enter(self, *args): self.refresh()
    def refresh(self):
        rows = App.get_running_app().store.expenses()
        self.listing_text = "\n\n".join(f"{r['title']} • {money(r['amount'])}\n{r['category']} | {r['expense_date']}" for r in rows) or "No expenses recorded yet."
    def add_to_draft(self):
        title = self.ids.title.text.strip()
        try: amount = float(self.ids.amount.text or 0)
        except ValueError: show_message("Valid expense amount enter karein."); return
        if not title or amount <= 0: show_message("Expense title aur amount 0 se zyada enter karein."); return
        self.draft.append({"title": title, "amount": amount, "category": self.ids.category.text.strip() or "General"})
        self.ids.title.text = ""; self.ids.amount.text = ""; self.ids.category.text = ""; self.update_draft()
    def update_draft(self):
        self.draft_text = "\n\n".join(f"{i+1}. {x['title']} • {money(x['amount'])} • {x['category']}" for i,x in enumerate(self.draft)) or "No draft expenses added yet."
        if self.draft: self.draft_text += f"\n\nDraft total: {money(sum(x['amount'] for x in self.draft))}"
    def done_expenses(self):
        if not self.draft: show_message("Pehle Add Expense to List se kam az kam ek entry add karein.", "Nothing to save"); return
        store = App.get_running_app().store
        try:
            with store.conn:
                for x in self.draft:
                    store.conn.execute("INSERT INTO expenses(title,amount,category,expense_date) VALUES(?,?,?,?)", (x["title"], x["amount"], x["category"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            count = len(self.draft); total = sum(x["amount"] for x in self.draft); self.draft = []; self.update_draft(); self.refresh(); App.get_running_app().refresh_home()
            show_message(f"{count} expense(s) saved.\nTotal: {money(total)}", "Expenses saved")
        except sqlite3.Error as exc: show_message(str(exc), "Expense not saved")


class ReportsScreen(Screen):
    report_text = StringProperty("")
    def on_pre_enter(self, *args): self.refresh()
    def refresh(self):
        store = App.get_running_app().store; t = store.totals(); rows = store.sales_history()
        gross_profit = sum(float(r["payable"] or 0) - float(r["cost"] or 0) for r in rows)
        net_before_other_costs = gross_profit - t["expenses"]
        self.report_text = (f"BUSINESS SUMMARY\n\nProducts listed: {t['products']}\nUnits in stock: {t['units']}\nLow-stock products: {t['low']}\nSales recorded: {t['sales']}\n\nNET SALES: {money(t['revenue'])}\nOutstanding due: {money(t['due'])}\nTotal expenses: {money(t['expenses'])}\n\nESTIMATED GROSS PROFIT: {money(gross_profit)}\nAfter recorded expenses: {money(net_before_other_costs)}\n\nNote: Profit is estimated from saved purchase costs; historical items without stored cost may be approximate.")


class HistoryScreen(Screen):
    history_text = StringProperty("")
    def on_pre_enter(self, *args): self.refresh()
    def refresh(self):
        rows = App.get_running_app().store.sales_history()
        self.history_text = "\n\n".join(f"Sale #{r['id']} • {r['sale_date']}\nCustomer: {r['customer_name'] or 'Walk-in'} | Phone: {r['customer_phone'] or '—'}\nSubtotal: {money(r['total_amount'])} | Discount: {money(r['discount'])}\nPayable: {money(r['payable'])} | Received: {money(r['paid_amount'])} | Due: {money(r['balance'])}\nEstimated gross profit: {money(float(r['payable'] or 0)-float(r['cost'] or 0))}" for r in rows) or "No sales recorded yet."


class UdhaarScreen(Screen):
    udhaar_text = StringProperty("")
    def on_pre_enter(self, *args): self.refresh()
    def refresh(self):
        rows = App.get_running_app().store.conn.execute("SELECT * FROM sales WHERE balance>0 ORDER BY id DESC").fetchall()
        total = sum(float(r["balance"] or 0) for r in rows)
        self.udhaar_text = "OUTSTANDING CUSTOMER BALANCES\n\n" + ("\n\n".join(f"Sale #{r['id']} • {r['sale_date']}\nCustomer: {r['customer_name'] or 'Walk-in'}\nPhone: {r['customer_phone'] or '—'}\nDue: {money(r['balance'])}" for r in rows) or "Alhamdulillah, koi outstanding udhaar nahi.") + f"\n\nTOTAL OUTSTANDING: {money(total)}"


class MaherUmarPOSApp(App):
    def build(self):
        self.title = APP_TITLE
        self.store = Store(os.path.join(self.user_data_dir, DB_NAME))
        Builder.load_string(KV)
        manager = ScreenManager()
        manager.add_widget(MainScreen(name="home")); manager.add_widget(ProductsScreen(name="products")); manager.add_widget(AddProductScreen(name="add_products")); manager.add_widget(StockScreen(name="stock")); manager.add_widget(SaleScreen(name="sale")); manager.add_widget(ExpensesScreen(name="expenses")); manager.add_widget(ReportsScreen(name="reports")); manager.add_widget(HistoryScreen(name="history")); manager.add_widget(UdhaarScreen(name="udhaar"))
        return manager
    def go(self, screen_name):
        self.root.current = screen_name
    def refresh_home(self):
        if self.root and "home" in self.root.screen_names: self.root.get_screen("home").refresh_summary()
    def backup_database(self):
        try:
            path = self.store.backup(); show_message(f"Database backup created successfully:\n{path}\n\nKeep a copy outside the app as well.", "Backup complete")
        except Exception as exc: show_message(f"Backup failed: {exc}", "Backup error")
    def generate_invoice(self, sale_id, customer, phone, items, subtotal, discount, net, paid, due, change=0):
        """Write a lightweight one-page PDF using built-in PDF syntax (no extra package)."""
        folder = os.path.join(self.user_data_dir, "Invoices")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"invoice_{sale_id:06d}.pdf")
        lines = [SHOP_NAME, "CUSTOMER INVOICE", "="*48, f"Invoice: {sale_id}", f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"Customer: {customer}", f"Phone: {phone or '-'}", "-"*48]
        for item in items:
            lines.append(f"{item['name']} ({item['category']})")
            lines.append(f"  {item['quantity']} x {money(item['price'])} = {money(item['quantity']*item['price'])}")
            item_discount = float(item.get("discount_amount", 0) or 0)
            if item_discount:
                lines.append(f"  Automatic product discount: -{money(item_discount)}")
        lines += ["-"*48, f"Subtotal: {money(subtotal)}", f"Discount: {money(discount)}", f"FINAL PAYABLE: {money(net)}", f"Amount received: {money(paid)}", f"Change returned: {money(change)}", f"Balance due: {money(due)}", "Thank you for shopping with us!"]
        # Use a standard Helvetica font and escape PDF string literals.
        def esc(value):
            value = str(value).encode("ascii", "replace").decode("ascii")
            return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        try:
            content = ["BT", "/F1 10 Tf", "48 800 Td", "14 TL"]
            for index, line in enumerate(lines):
                if index:
                    content.append("T*")
                content.append(f"({esc(line)}) Tj")
            content.append("ET")
            stream = "\n".join(content).encode("latin-1", "replace")
            objects = [
                b"<< /Type /Catalog /Pages 2 0 R >>",
                b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
                b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
            ]
            pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            offsets = [0]
            for number, obj in enumerate(objects, 1):
                offsets.append(len(pdf))
                pdf.extend(f"{number} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
            xref = len(pdf)
            pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("ascii"))
            for offset in offsets[1:]:
                pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
            pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
            with open(path, "wb") as f: f.write(pdf)
            return path
        except OSError:
            return None
    def on_stop(self):
        if hasattr(self, "store"):
            try: self.store.conn.close()
            except sqlite3.Error: pass


if __name__ == "__main__":
    try:
        MaherUmarPOSApp().run()
    except Exception:
        error_text = traceback.format_exc()
        try:
            app = App.get_running_app()
            log_dir = app.user_data_dir if app and app.user_data_dir else os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(log_dir, "crash_log.txt"), "a", encoding="utf-8") as log:
                log.write(f"\n\n--- CRASH: {datetime.now()} ---\n{error_text}")
        except Exception:
            print("Could not save crash log.")
        print(error_text, file=sys.stderr)
        raise
