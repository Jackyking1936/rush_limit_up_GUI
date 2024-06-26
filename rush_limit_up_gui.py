import sys
import pickle
import json
from datetime import datetime
import pandas as pd
from pathlib import Path

from fubon_neo.sdk import FubonSDK, Order
from fubon_neo.constant import TimeInForce, OrderType, PriceType, MarketType, BSAction

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QGridLayout, QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QPlainTextEdit, QFileDialog, QSizePolicy
from PySide6.QtGui import QTextCursor, QIcon
from PySide6.QtCore import Qt, Signal, QObject, QMutex
from threading import Timer

class LoginForm(QWidget):
    def __init__(self):
        super().__init__()
        my_icon = QIcon()
        my_icon.addFile('fast_icon.png')

        self.setWindowIcon(my_icon)
        self.setWindowTitle('新一代API登入')
        self.resize(500, 200)
        
        layout_all = QVBoxLayout()

        label_warning = QLabel('本範例僅供教學參考，使用前請先了解相關內容')
        layout_all.addWidget(label_warning)

        layout = QGridLayout()

        label_your_id = QLabel('Your ID:')
        self.lineEdit_id = QLineEdit()
        self.lineEdit_id.setPlaceholderText('Please enter your id')
        layout.addWidget(label_your_id, 0, 0)
        layout.addWidget(self.lineEdit_id, 0, 1)

        label_password = QLabel('Password:')
        self.lineEdit_password = QLineEdit()
        self.lineEdit_password.setPlaceholderText('Please enter your password')
        self.lineEdit_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_password, 1, 0)
        layout.addWidget(self.lineEdit_password, 1, 1)

        label_cert_path = QLabel('Cert path:')
        self.lineEdit_cert_path = QLineEdit()
        self.lineEdit_cert_path.setPlaceholderText('Please enter your cert path')
        layout.addWidget(label_cert_path, 2, 0)
        layout.addWidget(self.lineEdit_cert_path, 2, 1)
        
        label_cert_pwd = QLabel('Cert Password:')
        self.lineEdit_cert_pwd = QLineEdit()
        self.lineEdit_cert_pwd.setPlaceholderText('Please enter your cert password')
        self.lineEdit_cert_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_cert_pwd, 3, 0)
        layout.addWidget(self.lineEdit_cert_pwd, 3, 1)

        label_acc = QLabel('Account:')
        self.lineEdit_acc = QLineEdit()
        self.lineEdit_acc.setPlaceholderText('Please enter your account')
        self.lineEdit_cert_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_acc, 4, 0)
        layout.addWidget(self.lineEdit_acc, 4, 1)

        folder_btn = QPushButton('')
        folder_btn.setIcon(QIcon('folder.png'))
        layout.addWidget(folder_btn, 2, 2)

        login_btn = QPushButton('Login')
        layout.addWidget(login_btn, 5, 0, 1, 2)

        layout_all.addLayout(layout)
        self.setLayout(layout_all)
        
        folder_btn.clicked.connect(self.showDialog)
        login_btn.clicked.connect(self.check_password)
        
        my_file = Path("./info.pkl")
        if my_file.is_file():
            with open('info.pkl', 'rb') as f:
                user_info_dict = pickle.load(f)
                self.lineEdit_id.setText(user_info_dict['id'])
                self.lineEdit_password.setText(user_info_dict['pwd'])
                self.lineEdit_cert_path.setText(user_info_dict['cert_path'])
                self.lineEdit_cert_pwd.setText(user_info_dict['cert_pwd'])
                self.lineEdit_acc.setText(user_info_dict['target_account'])


    def showDialog(self):
        # Open the file dialog to select a file
        file_path, _ = QFileDialog.getOpenFileName(self, '請選擇您的憑證檔案', 'C:\\', 'All Files (*)')

        if file_path:
            self.lineEdit_cert_path.setText(file_path)
    
    def check_password(self):
        global active_account, sdk
        msg = QMessageBox()

        fubon_id = self.lineEdit_id.text()
        fubon_pwd = self.lineEdit_password.text()
        cert_path = self.lineEdit_cert_path.text()
        cert_pwd = self.lineEdit_cert_pwd.text()
        target_account = self.lineEdit_acc.text()
        
        user_info_dict = {
            'id':fubon_id,
            'pwd':fubon_pwd,
            'cert_path':cert_path,
            'cert_pwd':cert_pwd,
            'target_account':target_account
        }      
    
        accounts = sdk.login(fubon_id, fubon_pwd, Path(cert_path).__str__(), cert_pwd)
        if accounts.is_success:
            for cur_account in accounts.data:
                if cur_account.account == target_account:
                    active_account = cur_account
                    with open('info.pkl', 'wb') as f:
                        pickle.dump(user_info_dict, f)
                    
                    self.main_app = MainApp()
                    self.main_app.show()
                    self.close()
                    
            if active_account == None:
                sdk.logout()
                msg.setWindowTitle("登入失敗")
                msg.setText("找不到您輸入的帳號")
                msg.exec()
        else:
            msg.setWindowTitle("登入失敗")
            msg.setText(accounts.message)
            msg.exec()

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class Communicate(QObject):
    # 定義一個帶參數的信號
    print_log_signal = Signal(str)
    add_new_sub_signal = Signal(str, str, float, float, float)
    update_table_row_signal = Signal(str, float, float, float)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()

        ### Layout 設定
        my_icon = QIcon()
        my_icon.addFile('fast_icon.png')

        self.setWindowIcon(my_icon)
        self.setWindowTitle("Python搶漲停程式教學範例")
        self.resize(1000, 600)
        
        # 製作上下排列layout上為庫存表，下為log資訊
        layout = QVBoxLayout()
        # 庫存表表頭
        self.table_header = ['股票名稱', '股票代號', '上市櫃', '成交', '買進', '賣出', '漲幅(%)', '委託數量', '成交數量']
        
        self.tablewidget = QTableWidget(0, len(self.table_header))
        self.tablewidget.setHorizontalHeaderLabels([f'{item}' for item in self.table_header])
        self.tablewidget.setEditTriggers(QTableWidget.NoEditTriggers)

        # 整個設定區layout
        layout_condition = QGridLayout()

        # 監控區layout
        label_monitor = QLabel('監控設定')
        layout_condition.addWidget(label_monitor, 0, 0)
        label_up_range = QLabel('漲幅(%)')
        layout_condition.addWidget(label_up_range, 1, 0)
        self.lineEdit_up_range = QLineEdit()
        self.lineEdit_up_range.setText('7')
        layout_condition.addWidget(self.lineEdit_up_range, 1, 1)
        label_up_range_post = QLabel('以上')
        layout_condition.addWidget(label_up_range_post, 1, 2)
        label_freq = QLabel('定時每')
        layout_condition.addWidget(label_freq, 2, 0)
        self.lineEdit_freq = QLineEdit()
        self.lineEdit_freq.setText('5')
        layout_condition.addWidget(self.lineEdit_freq, 2, 1)
        label_freq_post = QLabel('秒更新')
        layout_condition.addWidget(label_freq_post, 2, 2)

        # 交易區layout
        label_trade = QLabel('交易設定')
        layout_condition.addWidget(label_trade, 0, 3)
        label_trade_budget = QLabel('每檔額度')
        layout_condition.addWidget(label_trade_budget, 1, 3)
        self.lineEdit_trade_budget = QLineEdit()
        self.lineEdit_trade_budget.setText('10')
        layout_condition.addWidget(self.lineEdit_trade_budget, 1, 4)
        label_trade_budget_post = QLabel('萬元')
        layout_condition.addWidget(label_trade_budget_post, 1, 5)

        # 啟動按鈕
        self.button_start = QPushButton('開始洗價')
        self.button_start.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_start.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_start, 0, 6, 3, 1)

        # 停止按鈕
        self.button_stop = QPushButton('停止洗價')
        self.button_stop.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_stop.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_stop, 0, 6, 3, 1)
        self.button_stop.setVisible(False)
        
        # 模擬區Layout設定
        self.fake_buy = QPushButton('fake buy filled')
        self.fake_sell = QPushButton('fake sell filled')
        self.fake_websocket = QPushButton('fake websocket')
        
        layout_sim = QGridLayout()
        label_sim = QLabel('測試用按鈕')
        label_sim.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")
        label_sim.setAlignment(Qt.AlignCenter)
        layout_sim.addWidget(label_sim, 0, 1)
        layout_sim.addWidget(self.fake_buy, 1, 0)
        layout_sim.addWidget(self.fake_sell, 1, 1)
        layout_sim.addWidget(self.fake_websocket, 1, 2)
        
        # Log區Layout設定
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)

        layout.addWidget(self.tablewidget)
        layout.addLayout(layout_condition)
        layout.addLayout(layout_sim)
        layout.addWidget(self.log_text)
        self.setLayout(layout)

        ### 建立連線開始跑主要城市
        self.print_log("login success, 現在使用帳號: {}".format(active_account.account))
        self.print_log("建立行情連線...")
        sdk.init_realtime() # 建立行情連線
        self.print_log("行情連線建立OK")
        self.reststock = sdk.marketdata.rest_client.stock
        self.wsstock = sdk.marketdata.websocket_client.stock

        # slot function connect
        self.button_start.clicked.connect(self.on_button_start_clicked)
        self.button_stop.clicked.connect(self.on_button_stop_clicked)

        # communicator init and slot function connect
        self.communicator = Communicate()
        self.communicator.print_log_signal.connect(self.print_log)
        self.communicator.add_new_sub_signal.connect(self.add_new_subscribed)
        self.communicator.update_table_row_signal.connect(self.update_table_row)

        # 各參數初始化
        self.timer = None
        self.watch_percent = float(self.lineEdit_up_range.text())
        self.snapshot_freq = int(self.lineEdit_freq.text())
        self.trade_budget = float(self.lineEdit_trade_budget.text())

        open_time = datetime.today().replace(hour=9, minute=0, second=0, microsecond=0)
        self.open_unix = int(datetime.timestamp(open_time)*1000000)
        self.last_close_dict = {}
        self.subscribed_ids = {}

        self.epsilon = 0.0000001
        self.row_idx_map = {}
        self.col_idx_map = dict(zip(self.table_header, range(len(self.table_header))))
    
    def update_table_row(self, symbol, price, bid, ask):
        self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['成交']).setText(str(round(price+self.epsilon, 2)))
        if bid>0:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText(str(round(bid+self.epsilon, 2)))
        else:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText('市價')

        if ask:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText(str(round(ask+self.epsilon, 2)))
        else:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText('-')

        up_range = (price-self.last_close_dict[symbol])/self.last_close_dict[symbol]*100
        self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setText(str(round(up_range+self.epsilon, 2))+'%')

    # ['股票名稱', '股票代號', '上市櫃', '成交', '買進', '賣出', '漲幅(%)', '委託數量', '成交數量']
    def add_new_subscribed(self, symbol, tse_otc, price, bid, ask):
        ticker_res = self.reststock.intraday.ticker(symbol=symbol)
        print(ticker_res['name'])
        row = self.tablewidget.rowCount()
        self.tablewidget.insertRow(row)
        self.row_idx_map[symbol] = row
        
        for j in range(len(self.table_header)):
            if self.table_header[j] == '股票名稱':
                item = QTableWidgetItem(ticker_res['name'])
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '股票代號':
                item = QTableWidgetItem(ticker_res['symbol'])
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '上市櫃':
                item = QTableWidgetItem(tse_otc)
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '成交':
                item = QTableWidgetItem(str(round(price+self.epsilon, 2)))
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '買進':
                if bid > 0:
                    item = QTableWidgetItem(str(round(bid+self.epsilon, 2)))
                    self.tablewidget.setItem(row, j, item)
                else:
                    item = QTableWidgetItem('市價')
                    self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '賣出':
                if ask:
                    item = QTableWidgetItem(str(round(ask+self.epsilon, 2)))
                    self.tablewidget.setItem(row, j, item)
                else:
                    item = QTableWidgetItem('-')
                    self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '漲幅(%)':
                self.last_close_dict[symbol] = ticker_res['previousClose']
                up_range = (price-ticker_res['previousClose'])/ticker_res['previousClose']*100
                item = QTableWidgetItem(str(round(up_range+self.epsilon, 2))+'%')
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '委託數量':
                item = QTableWidgetItem('0')
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '成交數量':
                item = QTableWidgetItem('0')
                self.tablewidget.setItem(row, j, item)

    def handle_message(self, message):
        msg = json.loads(message)
        event = msg["event"]
        data = msg["data"]
        print(event, data)

         # subscribed事件處理
        if event == "subscribed":
            if type(data) == list:
                for subscribed_item in data:
                    id = subscribed_item["id"]
                    symbol = subscribed_item["symbol"]
                    self.communicator.print_log_signal.emit('訂閱成功...'+symbol)
                    self.subscribed_ids[symbol] = id
            else:
                id = data["id"]
                symbol = data["symbol"]
                self.communicator.print_log_signal.emit('訂閱成功'+symbol)
                self.subscribed_ids[symbol] = id
        
        elif event == "unsubscribed":
            for key, value in self.subscribed_ids.items():
                if value == data["id"]:
                    print(value)
                    remove_key = key
            self.subscribed_ids.pop(remove_key)
            self.communicator.print_log_signal.emit(remove_key+"...成功移除訂閱")

        elif event == "snapshot":
            if 'ask' in data:
                self.communicator.add_new_sub_signal.emit(data['symbol'], data['market'], data['price'], data['bid'], data['ask'])
            else:
                self.communicator.add_new_sub_signal.emit(data['symbol'], data['market'], data['price'], data['bid'], None)
        elif event == "data":
            if 'ask' in data:
                self.communicator.update_table_row_signal.emit(data['symbol'], data['price'], data['bid'], data['ask'])
            else:
                self.communicator.update_table_row_signal.emit(data['symbol'], data['price'], data['bid'], None)
            
            if 'isLimitUpAsk' in data:
                if data['isLimitUpAsk']:
                    self.communicator.print_log_signal.emit('送出市價單...'+data['symbol'])

    def handle_connect(self):
        self.communicator.print_log_signal.emit('market data connected')
    
    def handle_disconnect(self, code, message):
        if not code and not message:
            self.communicator.print_log_signal.emit(f'WebSocket已停止')
        else:
            self.communicator.print_log_signal.emit(f'market data disconnect: {code}, {message}')
    
    def handle_error(self, error):
        self.communicator.print_log_signal.emit(f'market data error: {error}')

    def snapshot_n_subscribe(self):
        self.communicator.print_log_signal.emit("snapshoting...")
        TSE_movers = self.reststock.snapshot.movers(market='TSE', type='COMMONSTOCK', direction='up', change='percent', gte=self.watch_percent)
        TSE_movers_df = pd.DataFrame(TSE_movers['data'])
        OTC_movers = self.reststock.snapshot.movers(market='OTC', type='COMMONSTOCK', direction='up', change='percent', gte=self.watch_percent)
        OTC_movers_df = pd.DataFrame(OTC_movers['data'])

        all_movers_df = pd.concat([TSE_movers_df, OTC_movers_df])
        all_movers_df = all_movers_df[all_movers_df['lastUpdated']>self.open_unix]
        
        # all_movers_df['last_close'] = all_movers_df['closePrice']-all_movers_df['change']
        # self.last_close_dict.update(dict(zip(all_movers_df['symbol'], all_movers_df['last_close'])))

        new_subscribe = list(all_movers_df['symbol'])
        new_subscribe = list(set(new_subscribe).difference(set(self.subscribed_ids.keys())))
        self.communicator.print_log_signal.emit("NEW UP SYMBOL: "+str(new_subscribe))

        if new_subscribe:
            self.wsstock.subscribe({
                'channel': 'trades',
                'symbols': new_subscribe
            })

    def on_button_start_clicked(self):

        try:
            self.watch_percent = float(self.lineEdit_up_range.text())
            if self.watch_percent > 10 or self.watch_percent < 1:
                self.print_log("請輸入正確的監控漲幅(%), 範圍1~10")
                return
        except Exception as e:
            self.print_log("請輸入正確的監控漲幅(%), "+str(e))
            return

        try:
            self.snapshot_freq = int(self.lineEdit_freq.text())
            if self.snapshot_freq < 1:
                self.print_log("請輸入正確的監控頻率(整數，最低1秒)")
                return
        except Exception as e:
            self.print_log("請輸入正確的監控頻率(整數，最低1秒), "+str(e))
            return
        
        try:
            self.trade_budget = float(self.lineEdit_trade_budget.text())
            if self.trade_budget<0:
                self.print_log("請輸入正確的每檔買入額度(萬元), 必須大於0")
                return
        except Exception as e:
            self.print_log("請輸入正確的每檔買入額度(萬元), "+str(e))
            return
        
        self.print_log("開始執行監控")
        self.lineEdit_up_range.setReadOnly(True)
        self.lineEdit_freq.setReadOnly(True)
        self.lineEdit_trade_budget.setReadOnly(True)
        self.button_start.setVisible(False)
        self.button_stop.setVisible(True)

        sdk.init_realtime()
        self.wsstock = sdk.marketdata.websocket_client.stock
        self.wsstock.on('message', self.handle_message)
        self.wsstock.on('connect', self.handle_connect)
        self.wsstock.on('disconnect', self.handle_disconnect)
        self.wsstock.on('error', self.handle_error)
        self.wsstock.connect()

        if self.subscribed_ids:
            self.wsstock.subscribe({
                'channel': 'trades',
                'symbols': list(self.subscribed_ids.keys())
            })

        self.snapshot_n_subscribe()
        self.timer = RepeatTimer(self.snapshot_freq, self.snapshot_n_subscribe)
        self.timer.start()

    def on_button_stop_clicked(self):
        self.print_log("停止執行監控")
        self.lineEdit_up_range.setReadOnly(False)
        self.lineEdit_freq.setReadOnly(False)
        self.lineEdit_trade_budget.setReadOnly(False)
        self.button_stop.setVisible(False)
        self.button_start.setVisible(True)

        self.timer.cancel()
        self.wsstock.disconnect()

    # 更新最新log到QPlainTextEdit的slot function
    def print_log(self, log_info):
        self.log_text.appendPlainText(log_info)
        self.log_text.moveCursor(QTextCursor.End)
    
    # 視窗關閉時要做的事，主要是關websocket連結
    def closeEvent(self, event):
        # do stuff
        self.print_log("disconnect websocket...")
        self.wsstock.disconnect()
        try:
            if self.timer.is_alive():
                self.timer.cancel()
        except AttributeError:
            print("no timer exist")
        
        sdk.logout()
        can_exit = True
        if can_exit:
            event.accept() # let the window close
        else:
            event.ignore()


try:
    sdk = FubonSDK()
except ValueError:
    raise ValueError("請確認網路連線")
active_account = None
 
if not QApplication.instance():
    app = QApplication(sys.argv)
else:
    app = QApplication.instance()
app.setStyleSheet("QWidget{font-size: 12pt;}")
form = LoginForm()
form.show()
 
sys.exit(app.exec())