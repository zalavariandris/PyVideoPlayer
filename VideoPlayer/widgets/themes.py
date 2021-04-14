from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

def apply_dark_theme2(qApp):
    qApp.setStyle(QStyleFactory.create("Fusion"))

    newPalette = QPalette()
    newPalette.setColor(QPalette.Window,          QColor( 37,  37,  37));
    newPalette.setColor(QPalette.WindowText,      QColor(212, 212, 212));
    newPalette.setColor(QPalette.Base,            QColor( 60,  60,  60));
    newPalette.setColor(QPalette.AlternateBase,   QColor( 45,  45,  45));
    newPalette.setColor(QPalette.PlaceholderText, QColor(127, 127, 127));
    newPalette.setColor(QPalette.Text,            QColor(212, 212, 212));
    newPalette.setColor(QPalette.Button,          QColor( 45,  45,  45));
    newPalette.setColor(QPalette.ButtonText,      QColor(212, 212, 212));
    newPalette.setColor(QPalette.BrightText,      QColor(240, 240, 240));
    newPalette.setColor(QPalette.Highlight,       QColor( 38,  79, 120));
    newPalette.setColor(QPalette.HighlightedText, QColor(240, 240, 240));

    newPalette.setColor(QPalette.Light,           QColor( 60,  60,  60));
    newPalette.setColor(QPalette.Midlight,        QColor( 52,  52,  52));
    newPalette.setColor(QPalette.Dark,            QColor( 30,  30,  30));
    newPalette.setColor(QPalette.Mid,             QColor( 37,  37,  37));
    newPalette.setColor(QPalette.Shadow,          QColor( 0,    0,   0));

    newPalette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))

    qApp.setPalette(newPalette)

def apply_dark_theme1(qApp):
    qApp.setStyle(QStyleFactory.create("Fusion"))
    darkPalette = QPalette()
    darkColor = QColor(45,45,45)
    disabledColor = QColor(127,127,127)
    primaryColor = QColor(42, 130, 218)
    darkPalette.setColor(QPalette.Window, darkColor)
    darkPalette.setColor(QPalette.WindowText, Qt.white)
    darkPalette.setColor(QPalette.Base, QColor(18,18,18))
    darkPalette.setColor(QPalette.AlternateBase, darkColor)
    darkPalette.setColor(QPalette.ToolTipBase, Qt.white)
    darkPalette.setColor(QPalette.ToolTipText, Qt.white)
    darkPalette.setColor(QPalette.Text, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.Text, disabledColor)
    darkPalette.setColor(QPalette.Button, darkColor)
    darkPalette.setColor(QPalette.ButtonText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText, disabledColor)
    darkPalette.setColor(QPalette.BrightText, Qt.red)
    darkPalette.setColor(QPalette.Link, primaryColor)

    darkPalette.setColor(QPalette.Highlight, primaryColor)
    darkPalette.setColor(QPalette.HighlightedText, Qt.black)
    darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText, disabledColor)

    qApp.setPalette(darkPalette)

    qApp.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }");