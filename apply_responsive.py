import os
import glob

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

    # 3. Add responsive: true to standard DataTable init
    if '.DataTable({' in content and 'responsive: true' not in content:
        content = content.replace('.DataTable({', '.DataTable({\n                responsive: true,')
        modified = True

    # 4. Handle tableOptions in dashboard.html specifically
    if 'const tableOptions = {' in content and 'responsive: true' not in content:
        content = content.replace('const tableOptions = {', 'const tableOptions = {\n        responsive: true,')
        modified = True

    # 5. Fix stat cards
    if 'class="col-md-3 mb-4"' in content:
        content = content.replace('class="col-md-3 mb-4"', 'class="col-12 col-sm-6 col-lg-3 mb-4"')
        modified = True
    if 'class="col-md-3"' in content:
        content = content.replace('class="col-md-3"', 'class="col-12 col-sm-6 col-lg-3"')
        modified = True
        
    # 6. Add dt-responsive nowrap to tables that have an id ending in _table or that we know use DataTables
    # DataTables will automatically apply responsive classes if responsive: true is passed. We just need `nowrap` so it doesn't wrap text.
    if '<table ' in content:
        # Just ensure tables have nowrap
        content = content.replace('<table class="table align-middle mb-0 bg-white"', '<table class="table align-middle mb-0 bg-white nowrap"')
        content = content.replace('<table class="table align-middle mb-0"', '<table class="table align-middle mb-0 nowrap"')
        modified = True

    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Applied fixes to {os.path.basename(filepath)}")
