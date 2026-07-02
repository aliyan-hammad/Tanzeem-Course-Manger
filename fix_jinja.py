import os
import re

files = [
    'templates/students.html',
    'templates/attendance.html',
    'templates/fees.html',
    'templates/expenses.html'
]

for file_path in files:
    if not os.path.exists(file_path):
        continue
        
    with open(file_path, 'r') as f:
        content = f.read()
        
    # We only want the {% endif %} before the end of the `content` block.
    # The `scripts` block is at the very end of the file.
    # We will replace the LAST occurrence of `{% endif %}\n{% endblock %}` with `{% endblock %}`
    
    parts = content.rsplit('{% endif %}\n{% endblock %}', 1)
    if len(parts) == 2:
        content = parts[0] + '{% endblock %}' + parts[1]
        
    with open(file_path, 'w') as f:
        f.write(content)

print("Jinja syntax fixed.")
