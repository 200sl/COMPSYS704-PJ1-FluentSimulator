# coding:utf-8
import sys

from PyQt6.QtCore import Qt, QEasingCurve
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel
from qfluentwidgets import (NavigationItemPosition, MessageBox, setTheme, Theme, FluentWindow,
                            NavigationAvatarWidget, qrouter, SubtitleLabel, setFont, InfoBadge, IconWidget,
                            InfoBadgePosition, FluentBackgroundTheme, SwitchButton, FlowLayout, Icon)
from qfluentwidgets import FluentIcon as FIF

from MyIcon import MyFluentIcon as MIF

from SysjSignal import OutputSignal, InputSignal, OutputSignalManager, InputSignalManager


class LabelSwitchButton(QWidget):
    def __init__(self, outputSignal):
        super().__init__()

        self.label = QLabel(outputSignal.name)
        self.switchButton = SwitchButton()

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.switchButton)

        self.outputSignal = outputSignal

        self.switchButton.checkedChanged.connect(lambda checked: outputSignal.changeStatus(checked))


class LabelStatusLight(QWidget):
    def __init__(self, inputSignal: InputSignal):
        super().__init__()
        self.layout = QHBoxLayout(self)

        self.label = QLabel(inputSignal.name)
        self.statusLight = IconWidget()
        self.statusLight.setIcon(MIF.SL_GREY)
        self.statusLight.setFixedSize(32, 32)

        self.layout.addWidget(self.statusLight)
        self.layout.addWidget(self.label)

    def setStatus(self, status):
        if status:
            self.statusLight.setIcon(MIF.SL_GREEN)
        else:
            self.statusLight.setIcon(MIF.SL_GREY)


class CdCard(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self.vStatusLightsBoxLayout = QVBoxLayout()
        self.vOutputSignalsBoxLayout = QVBoxLayout()

        self.addLayout(self.vStatusLightsBoxLayout)
        self.addLayout(self.vOutputSignalsBoxLayout)

    def addOutputSignals(self, signals):
        for signal in signals:
            self.vOutputSignalsBoxLayout.addWidget(LabelSwitchButton(signal))

    def addStatusLights(self, signals):
        statusLights = []

        for signal in signals:
            statusLight = LabelStatusLight(signal)
            statusLights.append(statusLight)
            self.vStatusLightsBoxLayout.addWidget(statusLight)

        return statusLights


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.vBoxLayout = QVBoxLayout(self)

        setFont(self.label, 16)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vBoxLayout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)
        self.setObjectName(text.replace(' ', '-'))

    def addCdCard(self, cdCard: CdCard):
        self.vBoxLayout.addLayout(cdCard)
        self.vBoxLayout.addSpacing(100)

