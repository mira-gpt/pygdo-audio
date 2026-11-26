from gdo.core.ModuleCommandList import ModuleCommandList


class audio(ModuleCommandList):
    @classmethod
    def gdo_trigger(cls):
        return 'audio'
