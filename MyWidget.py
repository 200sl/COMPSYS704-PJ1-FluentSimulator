# coding:utf-8

from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QListWidgetItem, QSizePolicy
from qfluentwidgets import (SubtitleLabel, setFont, IconWidget,
                            SwitchButton, PushButton, LineEdit, DoubleSpinBox, ListWidget, CheckBox, ComboBox,
                            CompactSpinBox, ProgressRing)

from MyIcon import MyFluentIcon as MIF
from OrderPOS import Order, OrderRecipe, OrderStatus, OrderDao, UpdateOrderDto
from SysjSignal import InputSignal, OutputSignal


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
            self.switchButton.setChecked(outputSignal.status)
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


class RecipeCard(QWidget):
    def __init__(self, recipe: OrderRecipe):
        super().__init__()
        self.recipe = recipe

        self.mainLayout = QHBoxLayout(self)

        self.liqTypeLineEdit = LineEdit()
        self.liqTypeLineEdit.setPlaceholderText("Liquid Type")
        if recipe is not None and len(recipe.liqType) > 0:
            self.liqTypeLineEdit.setText(recipe.liqType)
        else:
            self.liqTypeLineEdit.setText("")
            self.liqTypeLineEdit.setEnabled(False)

        self.liqCapacitySpinBox = DoubleSpinBox()
        self.liqCapacitySpinBox.setRange(0, 500)
        self.liqCapacitySpinBox.setSuffix(" ml")
        self.liqCapacitySpinBox.setValue(recipe.capacity if recipe is not None else 0)
        self.liqCapacitySpinBox.setEnabled(recipe is not None)

        self.enableLiqCheckBox = CheckBox()
        self.enableLiqCheckBox.setText("Enable")
        self.enableLiqCheckBox.setChecked(recipe is not None)
        self.enableLiqCheckBox.stateChanged.connect(lambda: self.setEnable(self.enableLiqCheckBox.isChecked()))

        widgetIdx = 0
        self.mainLayout.addWidget(self.liqTypeLineEdit)
        self.mainLayout.setStretch(widgetIdx, 4)
        widgetIdx += 1
        self.mainLayout.addWidget(self.liqCapacitySpinBox)
        self.mainLayout.setStretch(widgetIdx, 2)
        widgetIdx += 1
        self.mainLayout.addWidget(self.enableLiqCheckBox)
        self.mainLayout.setStretch(widgetIdx, 0)

    def getRecipe(self):
        return OrderRecipe(self.liqTypeLineEdit.text(), self.liqCapacitySpinBox.value()) \
            if self.enableLiqCheckBox.isChecked() else None

    def setEnable(self, enable):
        self.liqTypeLineEdit.setEnabled(enable)
        self.liqCapacitySpinBox.setEnabled(enable)

    def updateRecipe(self, recipe: OrderRecipe):
        if recipe is None:
            self.liqTypeLineEdit.setText("")
            self.liqCapacitySpinBox.setValue(0)
            self.enableLiqCheckBox.setChecked(False)
            self.setEnable(False)
            return

        self.liqTypeLineEdit.setText(recipe.liqType)
        self.liqCapacitySpinBox.setValue(recipe.capacity)
        self.enableLiqCheckBox.setChecked(True)


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


class OrderCard(QVBoxLayout):
    newOrder = Signal(Order)
    startOrder = Signal(Order)

    def __init__(self, order: Order):
        super().__init__()
        self.order = order

        self.orderInfoLayout = QHBoxLayout()
        self.addLayout(self.orderInfoLayout)

        self.orderIdLabel = QLabel("Order ID:")
        self.orderInfoLayout.addWidget(self.orderIdLabel)

        self.orderProgressRing = ProgressRing()
        self.progressLabel = QLabel("0/0")

        self.orderProgressRing.setTextVisible(True)

        self.orderInfoLayout.addWidget(self.orderProgressRing)
        self.orderInfoLayout.addWidget(self.progressLabel)

        self.updateProgressRing()

        self.nameLineEdit = LineEdit()
        self.nameLineEdit.setPlaceholderText("Name")
        self.addWidget(self.nameLineEdit)

        self.descLineEdit = LineEdit()
        self.descLineEdit.setPlaceholderText("Description")
        self.addWidget(self.descLineEdit)

        self.bottleInfoLayout = QHBoxLayout()
        self.addLayout(self.bottleInfoLayout)

        items = ["100mL", "500mL", "1000mL", "2000mL"]
        self.bottleSizeComboBox = ComboBox()
        self.bottleSizeComboBox.addItems(items)
        self.bottleSizeComboBox.setCurrentIndex(0)

        self.bottleInfoLayout.addWidget(self.bottleSizeComboBox)
        self.bottleInfoLayout.addSpacing(100)

        self.bottleCountSpinBox = CompactSpinBox()
        self.bottleCountSpinBox.setRange(1, 100)
        self.bottleCountSpinBox.setValue(1)
        self.bottleCountSpinBox.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.bottleInfoLayout.addWidget(self.bottleCountSpinBox)

        self.recipeCardList = []
        for i in range(4):
            self.recipeCardList.append(RecipeCard(None))
            self.addWidget(self.recipeCardList[i])

        for i in range(len(order.recipe) if order is not None else 0):
            self.recipeCardList[i].updateRecipe(order.recipe[i])

        self.buttonHLayout = QHBoxLayout()

        self.saveButton = PushButton()
        self.saveButton.setText("Save")
        self.saveButton.clicked.connect(self.saveOrder)

        self.emitButton = PushButton()
        self.emitButton.setText("Emit")
        self.emitButton.clicked.connect(self.emitOrder)

        self.buttonHLayout.addWidget(self.saveButton)
        self.buttonHLayout.addWidget(self.emitButton)

        self.addLayout(self.buttonHLayout)

        self.updateOrder(self.order)

    def updateProgressRing(self):
        if self.order is None or self.order.orderStatus == OrderStatus.WAITING.value:
            self.orderProgressRing.setCustomBackgroundColor("grey", "grey")
            self.orderProgressRing.setRange(0, 100)
            self.orderProgressRing.setValue(0)
        elif self.order.orderStatus == OrderStatus.PRODUCING.value:
            self.orderProgressRing.setCustomBackgroundColor("orange", "orange")
            self.orderProgressRing.setRange(0, 100)
            self.orderProgressRing.setValue(self.order.producedAmount / self.order.count * 100)
        else:
            self.orderProgressRing.setCustomBackgroundColor("green", "green")
            self.orderProgressRing.setRange(0, 100)
            self.orderProgressRing.setValue(100)

    def updateOrder(self, newOrder: Order):
        self.order = newOrder
        self.updateProgressRing()

        if newOrder is None:
            self.orderIdLabel.setText("Order ID:")
            self.progressLabel.setText("0/0")
            self.nameLineEdit.setText("")
            self.descLineEdit.setText("")
            self.bottleSizeComboBox.setCurrentIndex(0)
            self.bottleCountSpinBox.setValue(1)

            for i in range(4):
                self.recipeCardList[i].updateRecipe(None)

            return

        self.orderIdLabel.setText(f"Order ID: {newOrder.orderId}")
        self.descLineEdit.setText(newOrder.desc)
        self.progressLabel.setText(f"{newOrder.producedAmount}/{newOrder.count}")
        self.nameLineEdit.setText(newOrder.name)
        self.bottleCountSpinBox.setValue(newOrder.count)

        if newOrder.bottleSizeInMilliL == 100:
            self.bottleSizeComboBox.setCurrentIndex(0)
        elif newOrder.bottleSizeInMilliL == 500:
            self.bottleSizeComboBox.setCurrentIndex(1)
        elif newOrder.bottleSizeInMilliL == 1000:
            self.bottleSizeComboBox.setCurrentIndex(2)
        elif newOrder.bottleSizeInMilliL == 2000:
            self.bottleSizeComboBox.setCurrentIndex(3)

        self.bottleCountSpinBox.setValue(newOrder.count)

        count = 0
        for i in range(len(newOrder.recipe)):
            self.recipeCardList[i].updateRecipe(newOrder.recipe[i])
            count += 1

        for i in range(count, 4):
            self.recipeCardList[i].updateRecipe(None)

    def saveOrder(self):
        self.order = Order(0, self.nameLineEdit.text(), self.descLineEdit.text(),
                           int(self.bottleSizeComboBox.currentText().replace("mL", "")),
                           self.bottleCountSpinBox.value())

        for i in range(4):
            recipe = self.recipeCardList[i].getRecipe()
            if recipe is not None:
                self.order.addRecipe(recipe)

        self.newOrder.emit(self.order)

    def emitOrder(self):
        self.startOrder.emit(self.order)


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


class PosWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.orderDao = OrderDao()
        self.orderDao.sigMngr.sigOrderListChanged.connect(lambda: self.updateViewList())

        self.hBoxLayoutMain = QHBoxLayout(self)

        self.orderListView = ListWidget()

        for oneItem in self.orderDao.getOrderIdList():
            self.orderListView.addItem(str(oneItem))

        self.orderListView.setCurrentIndex(self.orderListView.model().index(0, 0))
        self.orderListView.itemClicked.connect(lambda item: self.updateOrderCard(item))

        if len(self.orderDao.getOrderList()) > 0:
            self.orderCard = OrderCard(self.orderDao.getOrderList()[0])
        else:
            self.orderCard = OrderCard(None)

        self.orderCard.newOrder.connect(self.saveOrder)
        self.orderCard.startOrder.connect(self.startOrder)

        self.hBoxLayoutMain.addWidget(self.orderListView)
        self.hBoxLayoutMain.addLayout(self.orderCard)
        self.hBoxLayoutMain.setStretch(0, 1)
        self.hBoxLayoutMain.setStretch(1, 6)

        self.outputSignal = None

        self.setObjectName("pos-widget")

    def updateViewList(self):
        self.orderListView.clear()
        for oneItem in self.orderDao.getOrderIdList():
            oneQItem = QListWidgetItem(oneItem)
            self.orderListView.addItem(oneQItem)

    def updateOrderCard(self, item):
        id = int(item.text())
        orderList = self.orderDao.getOrderList()
        self.orderCard.updateOrder(orderList[id - 1] if id > 0 else None)

    def updateOneOrder(self, updateOrderDto: UpdateOrderDto):
        order = self.orderDao.getOrderById(updateOrderDto.orderId)
        order.producedAmount = updateOrderDto.bottleIndex

        if order.producedAmount == order.count:
            order.orderStatus = OrderStatus.COMPLETED.value

        self.orderDao.updateOrder(order)
        self.orderCard.updateOrder(order)

    def updateFirstOrder(self):
        order = self.orderDao.getOrderById(1)
        order.producedAmount += 1

        if order.producedAmount == order.count:
            order.orderStatus = OrderStatus.COMPLETED.value

        self.orderDao.updateOrder(order)
        self.orderCard.updateOrder(order)

    def saveOrder(self, order: Order):
        self.orderDao.addOrder(order)

    def startOrder(self, order: Order):
        order.orderStatus = OrderStatus.PRODUCING.value

        self.outputSignal.changeStatus(True)
        self.outputSignal.signalDto.value = order.toJson()

        self.orderDao.updateOrder(order)
        self.orderCard.updateOrder(order)

    def setOutputSignal(self, outputSignal: OutputSignal):
        self.outputSignal = outputSignal
