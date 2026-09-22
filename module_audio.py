from __future__ import annotations

from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.ui.GDT_Link import GDT_Link

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


class module_audio(GDO_Module):

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    async def gdo_install(self):
        pass

    def gdo_module_config(self) -> list[GDT]:
        return []

    def gdo_user_config(self) -> list[GDT]:
        return []

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        pass

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-audio.js')
        self.add_css('css/pygdo-audio.css')

    def gdo_init_sidebar(self, page: 'GDT_Page'):
        page._left_bar.add_field(GDT_Link().href(self.href('overview')).text('module_audio'))
