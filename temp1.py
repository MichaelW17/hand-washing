#信号与槽（QTabWidget略）
from PyQt5.QtWidgets import  QComboBox,QTableView,QAbstractItemView,QHeaderView,QTableWidget, QTableWidgetItem, QMessageBox,QListWidget,QListWidgetItem, QStatusBar,  QMenuBar,QMenu,QAction,QLineEdit,QStyle,QFormLayout,   QVBoxLayout,QWidget,QApplication ,QHBoxLayout, QPushButton,QMainWindow,QGridLayout,QLabel
from PyQt5.QtGui import QIcon,QPixmap,QStandardItem,QStandardItemModel,QCursor,QFont,QBrush,QColor
from PyQt5.QtCore import QStringListModel,QAbstractListModel,QModelIndex,QSize,Qt,QObject,pyqtSignal

import sys
class SiganlObj(QObject):
     sendMsg=pyqtSignal(object) #定义信号

     def __init__(self):
         super(SiganlObj, self).__init__()
     def run(self):
         self.sendMsg.emit("Hello")#发射信号

class TypeSlot(QObject):#定义槽对象
     def __init__(self):
         super(TypeSlot, self).__init__()
     def get(self,msg):#定义槽函数
         print(">>",msg)

if __name__=='__main__':
    send=SiganlObj()
    slot=TypeSlot()
    send.sendMsg.connect(slot.get)#绑定信号和槽函数
    send.run()#发信号