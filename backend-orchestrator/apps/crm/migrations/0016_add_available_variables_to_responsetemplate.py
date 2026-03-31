"""
0016_add_available_variables_to_responsetemplate.py
Adds available_variables JSONField + populates existing templates.
"""
from django.db import migrations, models


# Map: (template_type, intent) → list of variable names
VARIABLES_MAP = {
    # response intents
    ("response", "GREETING"):        ["ai_agent_name"],
    ("response", "ASK_PRICE"):       ["product", "price"],
    ("response", "ASK_AVAILABILITY"):["product", "sizes", "colors"],
    ("response", "ORDER_PRODUCT"):   ["product"],
    ("response", "ASK_DELIVERY"):    [],
    ("response", "ASK_DETAILS"):     ["product"],
    ("response", "ASK_DISCOUNT"):    [],
    ("response", "ASK_LOCATION"):    [],
    ("response", "CANCEL_ORDER"):    [],
    ("response", "CHECK_PACKAGE"):   [],
    ("response", "COMPLAINT"):       [],
    ("response", "CONFIRM_DENY"):    [],
    ("response", "INFORM_INFO"):     [],
    ("response", "TRACK_ORDER"):     [],
    ("response", "UNKNOWN"):         [],
    ("response", "NOISE"):           [],
    # missing_entity
    ("missing_entity", "product"):      [],
    ("missing_entity", "color"):        ["product"],
    ("missing_entity", "size"):         ["product", "color"],
    ("missing_entity", "quantity"):     ["product"],
    ("missing_entity", "address"):      [],
    ("missing_entity", "phone_number"): [],
    # out_of_stock
    ("out_of_stock", "default"):   ["product", "color", "size"],
    ("out_of_stock", "available"): ["avail"],
    ("out_of_stock", "sizes"):     ["avail"],
    ("out_of_stock", "colors"):    ["avail"],
    # order_confirmed
    ("order_confirmed", "with_ref"): ["product", "ref"],
    ("order_confirmed", "no_ref"):   ["product"],
    # disambiguation
    ("disambiguation", "default"): ["count", "list"],
    # misc
    ("misc", "missing_entity_default"):  ["first_missing"],
    ("misc", "inform_info_default"):     ["first_missing"],
    ("misc", "inform_product_default"):  [],
    ("misc", "ask_availability_default"):[],
    ("misc", "ask_price_default"):       [],
    ("misc", "noise_default"):           [],
    ("misc", "stock_check_error"):       [],
}


def populate_variables(apps, schema_editor):
    ResponseTemplate = apps.get_model('crm', 'ResponseTemplate')
    updated = 0
    for tmpl in ResponseTemplate.objects.all():
        key = (tmpl.template_type, tmpl.intent)
        variables = VARIABLES_MAP.get(key, [])
        if variables != tmpl.available_variables:
            tmpl.available_variables = variables
            tmpl.save(update_fields=['available_variables'])
            updated += 1
    print(f"\n  ✓ Populated available_variables for {updated} templates.")


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0015_add_gemini_fallback'),
    ]

    operations = [
        migrations.AddField(
            model_name='responsetemplate',
            name='available_variables',
            field=models.JSONField(
                blank=True, default=list,
                help_text='Variables utilisables dans ce template, ex: ["product", "price"]',
            ),
        ),
        migrations.RunPython(populate_variables, migrations.RunPython.noop),
    ]
