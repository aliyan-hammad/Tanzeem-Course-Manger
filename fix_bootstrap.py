import os
import glob
import re

templates_dir = '/home/alyan-hammad/tanzeem_webapp/templates'

for filepath in glob.glob(os.path.join(templates_dir, '*.html')):
    with open(filepath, 'r') as f:
        content = f.read()

    modified = False

    # 1. Remove table-responsive
    # It usually looks like <div class="table-responsive">\n<table...
    # We can just remove `<div class="table-responsive">` entirely, but then we have an extra `</div>` at the end of the table.
    # It's better to use regex to find `<div class="table-responsive">...</table>\n</div>` and just extract the table?
    # Or just let it be, DataTables Responsive works fine inside table-responsive but the scrollbar might appear briefly.
    # The official docs say DataTables Responsive Extension conflicts with .table-responsive.
    # Let's replace `<div class="table-responsive">` with `<div>` to avoid breaking tags.
    if '<div class="table-responsive">' in content:
        content = content.replace('<div class="table-responsive">', '<div>')
        modified = True

    # 2. Fix stat cards in dashboard.html and reports.html
    # They usually use "col-md-3" or "col-md-4". Let's change to "col-12 col-sm-6 col-lg-3"
    # Actually, let's look for `class="col-md-3"` and replace it
    if 'class="col-md-3 mb-4"' in content:
        content = content.replace('class="col-md-3 mb-4"', 'class="col-12 col-sm-6 col-lg-3 mb-4"')
        modified = True
    if 'class="col-md-3"' in content:
        content = content.replace('class="col-md-3"', 'class="col-12 col-sm-6 col-lg-3"')
        modified = True

    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated Bootstrap grids in {os.path.basename(filepath)}")
