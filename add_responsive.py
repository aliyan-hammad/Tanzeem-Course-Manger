import os
import glob
import re

templates_dir = '/home/alyan-hammad/tanzeem_webapp/templates'

css_link = '<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/responsive/2.5.0/css/responsive.bootstrap5.min.css"/>'
js_link = '<script type="text/javascript" src="https://cdn.datatables.net/responsive/2.5.0/js/dataTables.responsive.min.js"></script>\n<script type="text/javascript" src="https://cdn.datatables.net/responsive/2.5.0/js/responsive.bootstrap5.min.js"></script>'

for filepath in glob.glob(os.path.join(templates_dir, '*.html')):
    with open(filepath, 'r') as f:
        content = f.read()

    modified = False

    # 1. Add CSS
    if 'dataTables.bootstrap5.min.css' in content and 'responsive.bootstrap5.min.css' not in content:
        content = content.replace(
            '<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css"/>',
            f'<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css"/>\n{css_link}'
        )
        modified = True

    # 2. Add JS
    if 'dataTables.bootstrap5.min.js' in content and 'dataTables.responsive.min.js' not in content:
        content = content.replace(
            '<script type="text/javascript" src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>',
            f'<script type="text/javascript" src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>\n{js_link}'
        )
        modified = True

    # 3. Add responsive: true to DataTables init
    if '.DataTable({' in content and 'responsive: true' not in content:
        content = content.replace('.DataTable({', '.DataTable({\n                responsive: true,')
        # Also need to add class="dt-responsive nowrap" to the table tags in the template
        content = content.replace('<table class="table', '<table class="table nowrap')
        modified = True

    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated {os.path.basename(filepath)}")
