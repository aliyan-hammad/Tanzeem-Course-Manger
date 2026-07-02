import os
import glob

templates_dir = '/home/alyan-hammad/tanzeem_webapp/templates'

for filepath in glob.glob(os.path.join(templates_dir, '*.html')):
    with open(filepath, 'r') as f:
        content = f.read()

    modified = False

    # Restore table-responsive where I replaced it with <div>
    # In my previous script, I did: content.replace('<div class="table-responsive">', '<div>')
    # Let's see where <div> is directly wrapping a <table. This is tricky.
    # Actually, the previous script replaced `<div class="table-responsive">` with `<div>`.
    # Let's restore it by looking at git checkout for that specific change?
    # No, I haven't committed yet! I can just do `git checkout -- templates/` to undo ALL unstaged changes, then re-apply just the grid and DataTables parts!
