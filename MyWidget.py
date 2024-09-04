# coding:utf-8

from PySide6.QtCore import Slot
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel
from qfluentwidgets import (SubtitleLabel, setFont, IconWidget,
                            SwitchButton, PushButton)

from MyIcon import MyFluentIcon as MIF
from SysjSignal import InputSignal, SignalBase


class LabelSwitchButton(QWidget):
    def __init__(self, outputSignal, handle=None, data=None):
        super().__init__()

        self.handle = handle
        self.data = data

        self.label = QLabel(outputSignal.name)
        self.switchButton = SwitchButton() if not outputSignal.isOneShot else PushButton(text='Send')

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.switchButton)

        self.outputSignal = outputSignal

        if isinstance(self.switchButton, SwitchButton):
            self.outputSignal.emitter.sigStatusChanged.connect(self.switchButton.setChecked)
            self.switchButton.checkedChanged.connect(lambda checked: self.handleSignal(checked))
        elif isinstance(self.switchButton, PushButton):
            self.switchButton.clicked.connect(lambda: self.handleSignal(True))

    def handleSignal(self, status):
        if self.handle is not None:
            self.handle(self.data)

        self.outputSignal.changeStatus(status)


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

    def addOutputSignals(self, signals, simulatorEvent=None):
        for i in range(len(signals)):
            if simulatorEvent is not None and simulatorEvent[i] is not None:
                self.vOutputSignalsBoxLayout.addWidget(
                    LabelSwitchButton(signals[i], handle=simulatorEvent[i][0], data=simulatorEvent[i][1]))
            else:
                self.vOutputSignalsBoxLayout.addWidget(LabelSwitchButton(signals[i]))

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
