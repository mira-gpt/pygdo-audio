from gdo.base.GDT import GDT
from gdo.form.GDT_Form import GDT_Form
from gdo.form.MethodForm import MethodForm


class overview(MethodForm):
    def gdo_parameters(self) -> list[GDT]:
        return []

    def gdo_create_form(self, form: GDT_Form) -> None:
        super().gdo_create_form(form)

    def form_submitted(self):
        return self.msg('%s', 'Yeah!')
    
