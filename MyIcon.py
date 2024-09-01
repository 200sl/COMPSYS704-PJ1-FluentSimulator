from enum import Enum

from qfluentwidgets import getIconColor, Theme, FluentIconBase


class MyFluentIcon(FluentIconBase, Enum):
    """ Custom icons """

    CAPPER = "capper",
    LL = "ll",
    SL_GREEN = "sl_green",
    SL_GREY = "sl_grey",

    def path(self, theme=Theme.AUTO):
        # getIconColor() 根据主题返回字符串 "white" 或者 "black"
        return  f'./res/icons/{self.value[0]}.svg'
