import re

with open('templates/dashboard.html', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if '<span class="badge bg-secondary p-2 text-truncate"' in line:
        continue # skip redundant profile
    
    m = re.search(r'<div class="card (bg-\w+(?: bg-opacity-\d+)?) text-white shadow-sm border-0 h-100">', line)
    if m:
        bg_class = m.group(1)
        color_map = {
            'bg-primary': 'text-primary',
            'bg-success': 'text-success',
            'bg-danger': 'text-danger',
            'bg-secondary': 'text-secondary',
            'bg-info': 'text-info',
            'bg-dark': 'text-dark',
            'bg-success bg-opacity-75': 'text-success'
        }
        text_color = color_map.get(bg_class, 'text-dark')
        line = line.replace(f'{bg_class} text-white', 'bg-white text-dark')
        
        lines[i] = line
        
        j = i + 1
        while j < i + 10 and j < len(lines):
            if 'text-white-50' in lines[j]:
                lines[j] = lines[j].replace('text-white-50', 'text-muted')
            if '<h3 class="mb-0 fw-bold">' in lines[j]:
                lines[j] = lines[j].replace('<h3 class="mb-0 fw-bold">', f'<h3 class="mb-0 fw-bold {text_color}">')
            if '<h3 class="mb-0 fw-bold display-6">' in lines[j]:
                lines[j] = lines[j].replace('<h3 class="mb-0 fw-bold display-6">', f'<h3 class="mb-0 fw-bold display-6 {text_color}">')
            j += 1
            
    new_lines.append(lines[i])

with open('templates/dashboard.html', 'w') as f:
    f.writelines(new_lines)
