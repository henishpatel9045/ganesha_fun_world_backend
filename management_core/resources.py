from import_export import resources

from .models import ExtraWhatsAppNumbers


class ExtraWANumbersResource(resources.ModelResource):

    def before_import(self, dataset, **kwargs):
        try:
            current_id = ExtraWhatsAppNumbers.objects.all().order_by("created_at").last().pk
        except Exception:
            current_id = 0
        self.current_id = current_id +1 
        dataset.headers.append("id")
        return super().before_import(dataset, **kwargs)

    def before_import_row(self, row, **kwargs):
        row["id"] = self.current_id
        return super().before_import_row(row, **kwargs)

    def after_import_row(self, row, row_result, **kwargs):
        self.current_id += 1
        return super().after_import_row(row, row_result, **kwargs)
    
    class Meta:
        model = ExtraWhatsAppNumbers
        import_id_fields = ("id",)
        fields = ("id", "number",)
        